# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-or-later
# pylint: disable=import-outside-toplevel, too-many-branches, too-many-statements
# pylint: disable=broad-except  # network/MQTT errors come in many exception types
"""Network transport for online games: Wi-Fi and the two Adafruit IO feeds.

The game state and its rules are in chess_online; this module only sends and
receives the JSON values. Settings in settings.toml:

  ADAFRUIT_AIO_USERNAME, ADAFRUIT_AIO_KEY   this board's Adafruit IO account
  CPCHESS_OPPONENT  the opponent's Adafruit IO username, or "user/feed"
                    (two boards on one account need different feeds)
  CPCHESS_FEED      this board's feed key (default "cpchess")
  CPCHESS_NET       "mqtt" (default; HTTP as fallback) or "http" (polling only)
  CPCHESS_POLL_S    HTTP poll period while waiting for the opponent (default 60)
  CIRCUITPY_WIFI_SSID, CIRCUITPY_WIFI_PASSWORD   Wi-Fi credentials

On first connect the board creates its feed if needed and makes it public, so
the opponent can read it without a key. It then reads the newest value of both
feeds to pick up any game in progress, subscribes to the opponent's feed over
MQTT, and publishes its own moves over HTTP. If MQTT is off or down, the
opponent's feed is polled over HTTP instead.

Net.step() is called from the main loop. It does at most one slow operation
per call so the screen can show progress. Requests block for ~0.5-2 s, so the
app only calls it while the engine isn't searching.
"""

import os
import time

import chess_online as co

AIO_HOST = "io.adafruit.com"
API = "https://io.adafruit.com/api/v2/"
MQTT_PORT = 8883
MQTT_LOOP_S = 0.5  # how often to check MQTT for messages
MQTT_CONNECT_TIMEOUT = 2  # socket timeout while connecting (TLS takes ~1.3 s)
MQTT_SOCKET_TIMEOUT = 0.02  # socket timeout once connected, keeps checks short
SAFETY_POLL_S = 300  # HTTP poll period for the opponent's feed when MQTT is up
MY_TURN_POLL_FACTOR = 5  # without MQTT, poll this many times slower on our turn
BACKOFF_S = (5, 10, 30, 60, 120)  # retry delays after consecutive failures
FEED_DESCRIPTION = "CircuitPython Chess online game state (JSON, one value per move)"


def load_online():
    """Reads settings.toml. Returns (chess_online.Online, dict of Net settings);
    the Online's error is set if a required setting is missing."""
    user = os.getenv("ADAFRUIT_AIO_USERNAME")
    key = os.getenv("ADAFRUIT_AIO_KEY")
    feed = (os.getenv("CPCHESS_FEED") or co.DEFAULT_FEED).lower()
    opp = co.parse_id(os.getenv("CPCHESS_OPPONENT"))
    error = None
    if not user or not key:
        error = "Set ADAFRUIT_AIO_USERNAME and ADAFRUIT_AIO_KEY in settings.toml"
    elif opp is None:
        error = "Set CPCHESS_OPPONENT in settings.toml"
    online = co.Online((user, feed) if user else None, opp, error)
    mode = (os.getenv("CPCHESS_NET") or "mqtt").lower()
    try:
        poll_s = int(os.getenv("CPCHESS_POLL_S") or 60)
    except (TypeError, ValueError):
        poll_s = 60
    return online, {"key": key, "mqtt": mode != "http", "poll_s": max(10, poll_s)}


def _short(e):
    """A short on-screen description of an exception."""
    text = str(e) or type(e).__name__
    if text.startswith("[Errno"):
        text = text.split("]", 1)[-1].strip() or text
    return text[:40]


class _Request(Exception):
    def __init__(self, status, text=""):
        super().__init__("HTTP %d %s" % (status, text))
        self.status = status


class Net:
    def __init__(
        self,
        ctrl,
        key,
        mqtt=True,
        poll_s=60,
        log=None,
        pool=None,
        ssl_context=None,
        clock=None,
    ):
        """ctrl: the chess_ctrl.Controller (its .online holds the ids and outbox).
        pool, ssl_context: created from wifi.radio if not given."""
        self.ctrl = ctrl
        self.online = ctrl.online
        self.user, self.feed = self.online.me
        self.opp_user, self.opp_feed = self.online.opp
        self.key = key
        self.use_mqtt = mqtt
        self.poll_s = poll_s
        self.log = log
        self.pool, self.ssl_context = pool, ssl_context
        self.clock = clock or time.monotonic
        self.phase = "wifi"
        self.http = None
        self.mqtt = None
        self.io_mqtt = None
        self.retry_at = 0
        self.fails = 0
        self.next_loop = 0
        self.next_poll = 0
        self.mqtt_retry_at = 0
        self.mqtt_fails = 0
        # replaces the connection status until the opponent's feed has a value
        self.opp_problem = None

    def _say(self, text):
        if self.log:
            self.log("Net: " + text)

    def _status(self, text, bad=False, connected=None):
        self.ctrl.net_status(text, bad, connected)

    # ------------------------------------------------------------ HTTP

    def _headers(self, auth=True):
        h = {"User-Agent": "CircuitPythonChess-AIO"}
        if auth:
            h["X-AIO-KEY"] = self.key
        return h

    def _request(self, method, url, auth=True, json=None):
        """Returns the response JSON (None if empty). Raises _Request on HTTP errors."""
        h = self._headers(auth)
        if json is not None:
            h["Content-Type"] = "application/json"
        with self.http.request(method, url, json=json, headers=h) as r:
            status = r.status_code
            if status >= 400:
                text = ""
                try:
                    text = str(r.json().get("error", ""))[:60]
                except Exception:  # noqa: BLE001 - body may not be JSON
                    pass
                raise _Request(status, text)
            body = r.text
        if not body or body == "null":
            return None
        import json as _json

        return _json.loads(body)

    def _last_value(self, user, feed):
        """The newest value of user's feed, or None if there is no feed or data."""
        auth = user.lower() == self.user.lower()  # other users' feeds are public
        try:
            d = self._request(
                "GET",
                "%s%s/feeds/%s/data/last?include=value" % (API, user, feed),
                auth=auth,
            )
        except _Request as e:
            if e.status == 404:
                return None
            raise
        return d.get("value") if isinstance(d, dict) else None

    def _opp_feed_exists(self):
        """True if the opponent's feed exists and is public. Usernames and feed
        keys are case-sensitive in Adafruit IO URLs."""
        auth = self.opp_user.lower() == self.user.lower()
        try:
            self._request(
                "GET", "%s%s/feeds/%s" % (API, self.opp_user, self.opp_feed), auth=auth
            )
        except _Request as e:
            if e.status in (401, 403, 404):
                return False
            raise
        return True

    def _ensure_feed(self):
        """Creates this board's feed if needed and makes sure it is public."""
        url = "%s%s/feeds/%s" % (API, self.user, self.feed)
        try:
            f = self._request("GET", url)
        except _Request as e:
            if e.status != 404:
                raise
            self._say("creating feed %s/%s" % (self.user, self.feed))
            f = self._request(
                "POST",
                "%s%s/feeds" % (API, self.user),
                json={
                    "feed": {
                        "name": self.feed,
                        "key": self.feed,
                        "description": FEED_DESCRIPTION,
                        "visibility": "public",
                    }
                },
            )
        if f.get("visibility") != "public":
            self._say("making feed %s/%s public" % (self.user, self.feed))
            self._request("PUT", url, json={"feed": {"visibility": "public"}})

    def _publish_http(self, text):
        self._request(
            "POST",
            "%s%s/feeds/%s/data" % (API, self.user, self.feed),
            json={"value": text},
        )

    # ------------------------------------------------------------ MQTT

    def _mqtt_connect(self):
        import adafruit_minimqtt.adafruit_minimqtt as MQTT
        from adafruit_io.adafruit_io import IO_MQTT

        client = MQTT.MQTT(
            broker=AIO_HOST,
            port=MQTT_PORT,
            is_ssl=True,
            username=self.user,
            password=self.key,
            socket_pool=self.pool,
            ssl_context=self.ssl_context,
            socket_timeout=MQTT_CONNECT_TIMEOUT,
            recv_timeout=10,
            keep_alive=60,
            connect_retries=1,
        )
        io = IO_MQTT(client)
        io.on_message = self._on_message
        # account error and throttle topics, which IO_MQTT.on_message can't parse
        client.add_topic_callback("%s/errors" % self.user, self._on_error)
        client.add_topic_callback("%s/throttle" % self.user, self._on_error)
        io.connect()
        self.mqtt, self.io_mqtt = client, io
        client.subscribe("%s/errors" % self.user)
        client.subscribe("%s/throttle" % self.user)
        io.subscribe(feed_key=self.opp_feed, shared_user=self.opp_user)
        # MiniMQTT uses one timeout for both connecting and loop(); shorten it now
        # that the connection is up so each loop() check is quick.
        # pylint: disable=protected-access
        client._socket_timeout = MQTT_SOCKET_TIMEOUT
        client._sock.settimeout(MQTT_SOCKET_TIMEOUT)

    def _mqtt_drop(self):
        m = self.mqtt
        self.mqtt = self.io_mqtt = None
        if m is not None:
            try:
                m.disconnect()
            except Exception:  # noqa: BLE001 - the connection is dropped anyway
                pass

    def _on_message(self, _io, feed_key, payload):
        if feed_key == self.opp_feed:
            self._from_opp(payload)

    def _on_error(self, _client, topic, message):
        self._say("%s: %s" % (topic, message))
        self._status("IO: " + str(message)[:40], True)

    # ------------------------------------------------------------ the loop

    def _connection_line(self):
        if self.opp_problem:
            return self.opp_problem
        if self.mqtt is not None:
            return "Online (MQTT)"
        return "Online (HTTP, every %d s)" % self.poll_s

    def _status_ok(self):
        bad = bool(self.opp_problem) and self.opp_problem.startswith("No public feed")
        self._status(self._connection_line(), bad, True)

    def _from_opp(self, value):
        if self.opp_problem:
            self.opp_problem = None
            if self.phase == "ready":
                self._status_ok()
        self.ctrl.remote_state(value)

    def step(self, waiting=False):
        """Does any network work that is due. waiting: True when it is the
        opponent's turn (polls more often)."""
        now = self.clock()
        if self.phase == "ready" and self.use_mqtt:
            self._step_mqtt(now)
        if now < self.retry_at:
            return
        try:
            self._step_http(now, waiting)
        except Exception as e:  # noqa: BLE001 - network errors vary in type
            self._failed(now, e)

    def _failed(self, now, e):
        wait = BACKOFF_S[min(self.fails, len(BACKOFF_S) - 1)]
        self.fails += 1
        if "Throttle" in type(e).__name__ or getattr(e, "status", 0) == 429:
            wait = max(wait, 60)
        self._say("%s failed: %r (retry in %d s)" % (self.phase, e, wait))
        self._status("Offline: " + _short(e), True, False)
        self.retry_at = now + wait

    def _ok(self):
        self.fails = 0
        self._status_ok()

    def _step_mqtt(self, now):
        """Connects to MQTT and checks for messages. Sending always uses HTTP,
        whose response confirms delivery."""
        if self.mqtt is None:
            if now < self.mqtt_retry_at or now < self.retry_at:
                return
            self._status("Connecting to MQTT...", False, self.online.connected)
            try:
                self._mqtt_connect()
                self.mqtt_fails = 0
                self.next_poll = now  # catch anything sent before subscribing
            except Exception as e:  # noqa: BLE001
                self._mqtt_lost(now, e, "connect")
            self._status(self._connection_line(), False, self.online.connected)
            return
        if now >= self.next_loop:
            self.next_loop = now + MQTT_LOOP_S
            try:
                self.io_mqtt.loop(timeout=MQTT_SOCKET_TIMEOUT)
            except Exception as e:  # noqa: BLE001
                self._mqtt_lost(now, e, "loop")
                self._status(self._connection_line(), False, self.online.connected)

    def _mqtt_lost(self, now, e, what):
        self._mqtt_drop()
        wait = BACKOFF_S[min(self.mqtt_fails, len(BACKOFF_S) - 1)] * 2
        self.mqtt_fails += 1
        self.mqtt_retry_at = now + wait
        self.next_poll = min(self.next_poll, now + self.poll_s)  # poll HTTP meanwhile
        cause = getattr(e, "__cause__", None)
        self._say(
            "MQTT %s failed: %r%s (retry in %d s)"
            % (what, e, " <- %r" % cause if cause else "", wait)
        )

    def _step_http(self, now, waiting):
        o = self.online
        if self.phase == "wifi":
            self._status("Connecting to Wi-Fi...", False, False)
            if self.pool is None:
                import adafruit_connection_manager
                import wifi

                if not wifi.radio.connected:
                    ssid = os.getenv("CIRCUITPY_WIFI_SSID")
                    if not ssid:
                        raise RuntimeError("Set CIRCUITPY_WIFI_SSID in settings.toml")
                    wifi.radio.connect(ssid, os.getenv("CIRCUITPY_WIFI_PASSWORD") or "")
                self.pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
                self.ssl_context = adafruit_connection_manager.get_radio_ssl_context(
                    wifi.radio
                )
            import adafruit_requests

            self.http = adafruit_requests.Session(self.pool, self.ssl_context)
            self.phase = "feed"
            self._status("Setting up the feed...", False, False)
            return
        if self.phase == "feed":
            self._ensure_feed()
            self.phase = "sync"
            self.fails = 0
            self._status("Reading the game...", False, False)
            return
        if self.phase == "sync":
            mine = self._last_value(self.user, self.feed)
            theirs = self._last_value(self.opp_user, self.opp_feed)
            if mine is not None:
                self.ctrl.remote_state(mine, from_opp=False)
            if theirs is not None:
                self._from_opp(theirs)
            else:
                self._say("no value on %s/%s yet" % (self.opp_user, self.opp_feed))
            self.next_poll = now + self.poll_s
            self.phase = "ready"
            self.fails = 0
            if theirs is None:
                if self._opp_feed_exists():
                    self.opp_problem = "%s hasn't played yet" % self.opp_user
                else:
                    self.opp_problem = (
                        "No public feed %s/%s (check the name: case matters)"
                        % (self.opp_user, self.opp_feed)
                    )
            self._status_ok()
            self.ctrl.net_synced()
            return

        # ready
        out = o.outbox
        if out is not None:
            text = out.to_json()
            self._publish_http(text)
            if o.outbox is out:
                o.outbox = None
            self._say("sent %r (%d bytes)" % (out, len(text)))
            self._ok()
            self.ctrl.net_sent()
            return
        if now >= self.next_poll:
            if self.mqtt is not None:
                period = SAFETY_POLL_S
            else:
                period = self.poll_s if waiting else self.poll_s * MY_TURN_POLL_FACTOR
            self.next_poll = now + period
            v = self._last_value(self.opp_user, self.opp_feed)
            if v is not None:
                self._from_opp(v)
            self._ok()

    def poll_now(self):
        """Polls the opponent's feed at the next step()."""
        self.next_poll = 0
