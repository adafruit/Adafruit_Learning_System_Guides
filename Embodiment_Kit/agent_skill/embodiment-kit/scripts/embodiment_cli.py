#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
"""CLI for sending commands to an MCU over Adafruit IO MQTT or HTTP and waiting for an ack."""

# pylint: disable=import-outside-toplevel, too-many-locals, too-many-return-statements
import argparse
import json
import os
import sys
import time
import uuid
from os import getenv

import requests

DEFAULT_TIMEOUT = 10  # sec
TX_FEED = "embodiment.client-to-mcu"
RX_FEED = "embodiment.mcu-to-client"
HTTP_ENDPOINT = "/embodiment_kit"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Send a command to the embodiment MCU and wait for ack. Output response JSON.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        help="Name of the command to send (e.g. show_squinch_face).",
    )
    parser.add_argument(
        "arguments",
        nargs="*",
        metavar="key=value",
        help="Optional arguments as key=value pairs (e.g. frequency=440 duration=0.5).",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=None,
        help=f"Seconds to wait for ack (default: {DEFAULT_TIMEOUT}, or 22 for show_prompt).",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress connection/status logging; only print the ack response.",
    )
    parser.add_argument(
        "--commandlist",
        action="store_true",
        help="Print available commands and their arguments, then exit.",
    )
    return parser.parse_args()


def parse_arguments(raw_args):
    result = {}
    for item in raw_args:
        if "=" not in item:
            raise argparse.ArgumentTypeError(f"Argument must be key=value format, got: {item!r}")
        key, _, raw_value = item.partition("=")
        if raw_value.startswith("0x") or raw_value.startswith("0X"):
            try:
                value = int(raw_value, 16)
            except ValueError:
                value = raw_value
        else:
            try:
                value = json.loads(raw_value)
            except json.JSONDecodeError:
                value = raw_value.encode('raw_unicode_escape').decode('unicode_escape')
        result[key] = value
    return result


def build_payload(command_name, arguments, command_uuid):
    return {
        "messages": [
            {
                "metadata": {"type": "command"},
                "command": {
                    "name": command_name,
                    "arguments": arguments,
                    "uuid": command_uuid,
                },
            }
        ]
    }


def normalize_host_url(host):
    """Ensure the host has a scheme; default to http:// if missing."""
    host = host.strip().rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = "http://" + host
    return host


def send_via_http(host, payload, command_uuid, timeout, log):
    """Send the command via HTTP POST to the embodiment kit device.

    Returns the ack message dict on success, or None on failure/timeout.
    """
    url = normalize_host_url(host) + HTTP_ENDPOINT
    log(f"POSTing to {url}...")

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )
    except requests.exceptions.Timeout:
        log(f"HTTP request timed out after {timeout}s")
        return None
    except requests.exceptions.RequestException as e:
        log(f"HTTP request failed: {e}")
        return None

    if response.status_code != 200:
        log(f"HTTP request returned status {response.status_code}: {response.text}")
        return None

    try:
        data = response.json()
    except ValueError as e:
        log(f"Could not decode response JSON: {e}")
        return None

    # The device responds with the same envelope format. Find the ack message
    # matching our command uuid.
    for msg in data.get("messages", []):
        metadata = msg.get("metadata", {})
        command = msg.get("command", {})
        if metadata.get("type") == "ack" and command.get("uuid") == command_uuid:
            return msg

    # If no ack-typed message is found but there's exactly one message, accept it
    # (some devices may not tag the response as ack).
    messages = data.get("messages", [])
    if len(messages) == 1:
        return messages[0]

    log("No matching ack found in HTTP response")
    return None


def send_via_aio(aio_username, aio_key, payload, command_uuid, timeout, log):
    """Send the command via Adafruit IO MQTT and wait for an ack.

    Returns the ack message dict on success, or None on timeout.
    """
    # Imported lazily so HTTP-only users don't need these packages installed.
    import adafruit_connection_manager
    import adafruit_minimqtt.adafruit_minimqtt as MQTT
    from adafruit_io.adafruit_io import IO_HTTP, IO_MQTT

    state = {"status": "waiting", "uuid": command_uuid, "response": None}

    radio = adafruit_connection_manager.CPythonNetwork()
    socket_pool = adafruit_connection_manager.get_radio_socketpool(radio)
    ssl_context = adafruit_connection_manager.get_radio_ssl_context(radio)

    # pylint: disable=unused-argument
    # The arguments aren't used, but omitting them causes exception from MQTT library
    def on_connect(client):
        client.subscribe(RX_FEED)

    def on_disconnect(client):
        pass

    def on_subscribe(client, userdata, topic, granted_qos):
        pass

    def on_unsubscribe(client, userdata, topic, pid):
        pass

    def on_message(client, feed_id, raw_payload):
        try:
            data = json.loads(raw_payload)
        except json.JSONDecodeError as e:
            log(f"Could not decode message payload: {e}")
            return

        for msg in data.get("messages", []):
            metadata = msg.get("metadata", {})
            command = msg.get("command", {})
            if (
                metadata.get("type") == "ack"
                and command.get("uuid") == state["uuid"]
            ):
                state["status"] = "received"
                state["response"] = msg
                return

    mqtt_client = MQTT.MQTT(
        broker="io.adafruit.com",
        port=8883,
        username=aio_username,
        password=aio_key,
        is_ssl=True,
        socket_pool=socket_pool,
        ssl_context=ssl_context,
    )

    io_rx = IO_MQTT(mqtt_client)
    io_rx.on_connect = on_connect
    io_rx.on_disconnect = on_disconnect
    io_rx.on_subscribe = on_subscribe
    io_rx.on_unsubscribe = on_unsubscribe
    io_rx.on_message = on_message

    io_rx.connect()

    io_tx = IO_HTTP(aio_username, aio_key, requests)
    tx_feed = io_tx.get_feed(TX_FEED)

    io_tx.send_data(tx_feed["key"], json.dumps(payload))

    start = time.monotonic()
    while time.monotonic() - start < timeout and state["status"] == "waiting":
        io_rx.loop()

    try:
        io_rx.disconnect()
    except Exception:
        pass

    if state["status"] == "received":
        return state["response"]
    return None


def main():
    args = parse_args()

    if args.commandlist:
        help_path = os.path.join(os.path.dirname(__file__), "embodiment_cli_help.md")
        with open(help_path) as f:
            print(f.read())
        return 0

    if not args.command:
        print("ERROR: command is required.", file=sys.stderr)
        sys.exit(2)

    def log(*msg):
        if not args.quiet:
            print(*msg, file=sys.stderr)

    # Determine which transport to use. Prefer the local HTTP device if
    # EMBODIMENT_KIT_HOST is set; otherwise fall back to Adafruit IO.
    embodiment_host = getenv("EMBODIMENT_KIT_HOST")
    aio_username = getenv("ADAFRUIT_AIO_USERNAME")
    aio_key = getenv("ADAFRUIT_AIO_KEY")

    use_http = bool(embodiment_host)
    use_aio = bool(aio_username and aio_key)

    if not use_http and not use_aio:
        print(
            "ERROR: no transport configured. Set EMBODIMENT_KIT_HOST for direct HTTP, "
            "or set ADAFRUIT_AIO_USERNAME and ADAFRUIT_AIO_KEY for Adafruit IO.",
            file=sys.stderr,
        )
        sys.exit(2)

    command_uuid = str(uuid.uuid4())
    try:
        arguments = parse_arguments(args.arguments)
    except argparse.ArgumentTypeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    user_specified_timeout = args.timeout is not None
    if args.command == "show_prompt":
        timeout = args.timeout if user_specified_timeout else 22.0
        duration = arguments.get("timeout")
        if duration is not None:
            if user_specified_timeout and timeout <= duration:
                print(
                    f"ERROR: --timeout ({timeout}s) must be greater than"
                    + f" duration ({duration}s) for show_prompt.",
                    file=sys.stderr,
                )
                sys.exit(2)
            elif not user_specified_timeout and duration >= timeout:
                timeout = duration + 2
        args.timeout = timeout
    else:
        if not user_specified_timeout:
            args.timeout = DEFAULT_TIMEOUT

    payload = build_payload(args.command, arguments, command_uuid)

    if use_http:
        response = send_via_http(
            embodiment_host, payload, command_uuid, args.timeout, log
        )
    else:
        response = send_via_aio(
            aio_username, aio_key, payload, command_uuid, args.timeout, log
        )

    if response is not None:
        print(json.dumps(response))
        return 0

    print(
        f"ERROR: timed out after {args.timeout}s waiting for ack to uuid {command_uuid}",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
