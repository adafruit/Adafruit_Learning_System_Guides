# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Four stems off the eMMC *as four WAV files*, four faders controling their level."""

# pylint: skip-file
import gc
import time

import audiobusio
import board
import digitalio

import adafruit_cs42l42

# `adafruit_tas2505` is imported inside `DriverAudio.__init__`, and only
# when a speaker is actually wanted.

import sp1_controls
import sp1_wavplayer

__version__ = "3.2.0"

STEMS = (0, 1, 2, 3)  # stem per fader, left to right
TAPER = 2  # fader**TAPER -> voice level; see the docstring
FADER_POLL = 4  # faders sampled per chunk; see poll_count()
BAR = 12  # characters in a meter bar


GC_EVERY = 64

# --------------------------------------------------------------------------
# the playlist, and the four buttons on LADDER2

PLAYLIST = sp1_wavplayer.DEFAULT_MOUNT + "/playlist.json"

MAX_PLAYLIST_BYTES = 8192

REPEAT = False

# VOL+/VOL- move the live output's level by this much
VOLUME_STEP = 0.05

HOLD_DELAY = 0.45
REPEAT_INTERVAL = 0.12

BUTTON_LOCKOUT = 0.08
# ROCKER- past this far into a track restarts it rather than going back one.
PREV_RESTART_SECONDS = 3.0

RATE = sp1_wavplayer.RATE
BLOCK_SECONDS = sp1_wavplayer.BLOCK_SECONDS

I2S_BUFFER_MS = 16  # I2SOut.c's `buffer_length_ms`
I2S_DMA_BYTES = (RATE * I2S_BUFFER_MS * 2 * 2 // 1000 + 3) & ~3  # 3,072 B
I2S_DMA_BUFFERS = 2

SCLK_HZ = 3_072_000
SCLK_PER_FRAME = 64

BIT_DEPTH = 24

CS_MIN_DB = -62.0
TAS_MIN_DB = -63.5

SPEAKER_VOLUME = 0.85  # of 0 to -63.5 dB digital: -9.5 dB
SPEAKER_GAIN = 12  # class-D driver, dB: one of 6/12/18/24/32

DETECT_DEBOUNCE_MS = 500

RAMP_STEPS = 6
RAMP_PAUSE = 0.004

OUTPUTS = ("none", "headphones", "speaker", "both", "auto")


def _fraction_to_db(value, min_db):
    """0.0-1.0 -> dB, linear in dB (so it is linear in perceived loudness)."""
    if value <= 0.0:
        return min_db
    if value >= 1.0:
        return 0.0
    return min_db * (1.0 - value)


class DriverAudio:
    """The oscillator, both codecs and the I2S bus using the driver libraries."""

    def __init__(
        self,
        output="headphones",
        volume=0.5,
        minus6=False,
        speaker_volume=SPEAKER_VOLUME,
        speaker_gain=SPEAKER_GAIN,
        speaker_ramp=False,
        speaker=True,
        i2c=None,
    ):
        if output not in OUTPUTS:
            raise ValueError("output must be one of {}".format(OUTPUTS))

        self.speaker_ramp = speaker_ramp
        self._output = output
        self._muted = True
        self._sample = None
        self._loop = False
        self._reserve = None

        self._osc = None
        self._cs_reset = None
        self._tas_reset = None
        self.headphone = None  # adafruit_cs42l42.CS42L42
        self.speaker_dac = None  # adafruit_tas2505.TAS2505, or None
        self.i2s = None
        try:
            self._osc = digitalio.DigitalInOut(board.OSC_EN)
            self._osc.direction = digitalio.Direction.OUTPUT
            self._osc.value = True  # SCLK, and everything downstream

            self._cs_reset = digitalio.DigitalInOut(board.CS42_RESET)
            self._cs_reset.direction = digitalio.Direction.OUTPUT
            self._cs_reset.value = False

            if i2c is None:
                i2c = board.I2C()
            self.headphone = adafruit_cs42l42.CS42L42(i2c, reset_pin=self._cs_reset)
            self.headphone.configure_clocks(sclk_hz=SCLK_HZ)

            self.headphone.configure_asp(
                sample_rate=RATE,
                bit_depth=BIT_DEPTH,
                generate_lrck=True,
                sclk_per_frame=SCLK_PER_FRAME,
            )

            self.headphone.headphone_output = True
            self.headphone.muted = True
            self.headphone.full_scale_volume = -6.0 if minus6 else 0.0
            self.headphone.dac_volume = _fraction_to_db(volume, CS_MIN_DB)
            self.headphone.enable_tip_sense(DETECT_DEBOUNCE_MS)

            if speaker:
                self._tas_reset = digitalio.DigitalInOut(board.TAS_RESET)
                self._tas_reset.direction = digitalio.Direction.OUTPUT
                self._tas_reset.value = False
                time.sleep(0.01)
                self._tas_reset.value = True
                time.sleep(0.01)

                import adafruit_tas2505  # 22.6 KB of heap: see the top

                self.speaker_dac = adafruit_tas2505.TAS2505(i2c)
                self.speaker_dac.configure_clocks(
                    RATE, BIT_DEPTH, bclk_ratio=SCLK_PER_FRAME
                )

                self.speaker_dac.speaker_output = True
                self.speaker_dac.dac_mute = True
                self.speaker_dac.speaker_power = False
                self.speaker_dac.speaker_volume = 0.0  # analog: no pad
                self.speaker_dac.speaker_gain = speaker_gain
                self.speaker_dac.dac_volume = _fraction_to_db(
                    speaker_volume, TAS_MIN_DB
                )

            self.i2s = audiobusio.I2SOut(
                board.I2S_BCLK, board.I2S_LRCLK, board.I2S_DOUT, external_clock=True
            )
        except Exception:
            self.deinit()
            raise

    # -- playing -----------------------------------------------------------

    def reserve(self):
        """Hold the DMA buffers' worth of heap until the next `play()`.
        Returns the bytes held. Idempotent, and free to call on a path that
        never plays -- `stop()` and `deinit()` drop it too.
        """
        if self._reserve is None:
            self._reserve = [bytearray(I2S_DMA_BYTES) for _ in range(I2S_DMA_BUFFERS)]
        return I2S_DMA_BUFFERS * I2S_DMA_BYTES

    def _drop_reserve(self):
        if self._reserve is not None:
            self._reserve = None
            gc.collect()

    def play(self, sample, loop=False, strict=True):
        """Play a 48 kHz sample, muting across the swap.

        `sample` is anything `audiobusio.I2SOut.play()` takes -- here a
        `RawSample` of silence and then the player's `audiomixer.Mixer`.
        Leaves the output muted or unmuted exactly as it found it.
        """
        rate = getattr(sample, "sample_rate", RATE)
        if strict and rate != RATE:
            raise ValueError(
                "this board is {} Hz only ({} Hz would play {:+.2f} % off "
                "pitch) -- resample on the host, or pass "
                "strict=False".format(RATE, rate, 100.0 * (RATE - rate) / rate)
            )

        live = not self._muted
        if live:
            self._mute_all()  # before the bus stops. Always.
        self.i2s.stop()
        self._sample = sample
        self._loop = loop

        self._drop_reserve()
        self.i2s.play(sample, loop=loop)
        if live:
            self._apply_output()

    def stop(self):
        """Mute over I2C, then stop the bus. Idempotent."""
        self._mute_all()
        self._muted = True
        if self.i2s is not None:
            self.i2s.stop()
        self._sample = None
        self._drop_reserve()

    def pause(self):
        self._mute_all()
        self._muted = True
        if self.i2s is not None and self.i2s.playing:
            self.i2s.pause()

    def resume(self):
        if self.i2s is not None and self.i2s.paused:
            self.i2s.resume()

    @property
    def playing(self):
        return self.i2s is not None and self.i2s.playing

    # -- level and routing -------------------------------------------------

    @property
    def muted(self):
        """The master mute. False routes according to `output`."""
        return self._muted

    @muted.setter
    def muted(self, value):
        value = bool(value)
        self._muted = value
        if value:
            self._mute_all()
        else:
            self._apply_output()

    @property
    def output(self):
        """Which outputs are live"""
        return self._output

    @output.setter
    def output(self, value):
        if value not in OUTPUTS:
            raise ValueError("output must be one of {}".format(OUTPUTS))
        self._output = value
        if self._muted:
            self._mute_all()
        else:
            self._apply_output()

    def update(self):
        """Re-check the jack in `output="auto"`. Returns True if it changed."""
        if self._output != "auto" or self._muted:
            return False
        if self._auto_targets() == self._live:
            return False
        self._apply_output()
        return True

    @property
    def headphones_connected(self):
        """The CS42L42's debounced tip sense. Nothing routes on it for you."""
        return self.headphone.headphone_detected

    @property
    def volume(self):
        """Headphone level, 0.0-1.0 (linear in dB). The speaker has its own."""
        return 1.0 - self.headphone.dac_volume / CS_MIN_DB

    @volume.setter
    def volume(self, value):
        self.headphone.dac_volume = _fraction_to_db(value, CS_MIN_DB)

    @property
    def minus6(self):
        """The headphone amp's -6 dB analog pad"""
        return self.headphone.full_scale_volume == -6.0

    @minus6.setter
    def minus6(self, value):
        self.headphone.full_scale_volume = -6.0 if value else 0.0

    @property
    def speaker_volume(self):
        if self.speaker_dac is None:
            return None
        return 1.0 - self.speaker_dac.dac_volume / TAS_MIN_DB

    @speaker_volume.setter
    def speaker_volume(self, value):
        if self.speaker_dac is not None:
            self.speaker_dac.dac_volume = _fraction_to_db(value, TAS_MIN_DB)

    @property
    def speaker_gain(self):
        return None if self.speaker_dac is None else self.speaker_dac.speaker_gain

    @speaker_gain.setter
    def speaker_gain(self, value):
        if self.speaker_dac is not None:
            self.speaker_dac.speaker_gain = value

    # -- the routing itself ------------------------------------------------

    @property
    def _live(self):
        hp = not self.headphone.muted
        spk = (
            self.speaker_dac is not None
            and self.speaker_dac.speaker_power
            and not self.speaker_dac.dac_mute
        )
        return hp, spk

    def _auto_targets(self):
        """(headphones, speaker) for the current `output`."""
        out = self._output
        if out == "auto":
            out = "headphones" if self.headphones_connected else "speaker"
        if out == "none":
            return False, False
        if out == "both":
            return True, True
        return out == "headphones", out == "speaker"

    def _apply_output(self):
        hp, spk = self._auto_targets()
        if self.speaker_dac is None:
            spk = False

        if spk:
            self._speaker_up()
        self.headphone.muted = not hp
        if not spk:
            self._speaker_down()

    def _mute_all(self):
        if self.headphone is not None:
            self.headphone.muted = True
        self._speaker_down()

    def _speaker_up(self):
        spk = self.speaker_dac
        if spk is None:
            return
        spk.speaker_power = True  # class-D driver, then unmute (7.1.e:
        spk.dac_mute = False  # both edges measured silent this way)

    def _speaker_down(self):
        """Mute, optionally ramp, then power the driver down."""
        spk = self.speaker_dac
        if spk is None:
            return
        was_up = spk.speaker_power
        spk.dac_mute = True
        if was_up and self.speaker_ramp:
            db = spk.dac_volume
            for i in range(RAMP_STEPS):
                spk.dac_volume = db + (TAS_MIN_DB - db) * (i + 1) / float(RAMP_STEPS)
                time.sleep(RAMP_PAUSE)
            spk.speaker_power = False
            spk.dac_volume = db
        else:
            spk.speaker_power = False

    # -- shutdown ----------------------------------------------------------

    def deinit(self):
        """Mute, stop, release the bus, then power the codecs and the
        oscillator down. Safe to call twice, and safe on a half-built object."""
        try:
            self._mute_all()
        except Exception:
            pass  # a codec that has stopped answering must not be
            # able to stop us dropping the oscillator
        self._muted = True
        if self.i2s is not None:
            self.i2s.stop()
            self.i2s.deinit()
            self.i2s = None
        self._sample = None
        self._drop_reserve()
        if self.speaker_dac is not None:
            try:
                self.speaker_dac.speaker_output = False  # what actually
            except Exception:  # quiets the chip
                pass
            self.speaker_dac = None
        if self.headphone is not None:
            try:
                self.headphone.power_down()
            except Exception:
                pass
            self.headphone = None
        for pin in ("_cs_reset", "_tas_reset"):
            p = getattr(self, pin)
            if p is not None:
                p.deinit()
                setattr(self, pin, None)
        if self._osc is not None:
            self._osc.value = False  # it draws current through SYSTEM_OFF
            self._osc.deinit()
            self._osc = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.deinit()


# --------------------------------------------------------------------------
# the demo


def poll_count(poll, nstems):
    """How many faders to sample per chunk: an int 1..nstems, or "all"/"one".

    Each one costs ~130 us of the chunk's slack and each *unsampled* one adds a
    chunk to its own update period. On the WAV player four stems leave 11-13 ms
    of a 40 ms chunk spare, the default is all of them."""
    if poll == "all":
        return nstems
    if poll == "one":
        return 1
    poll = int(poll)
    if not 1 <= poll <= nstems:
        raise ValueError("poll must be 1-%d, 'one' or 'all'" % nstems)
    return poll


def _bar(v):
    n = int(v * BAR + 0.5)
    return "#" * n + "-" * (BAR - n)


class FaderMix:
    """The four faders, wired to a `Player`'s four voices."""

    def __init__(self, player, controls, taper=TAPER, poll=FADER_POLL, measure=False):
        self.player = player
        self.controls = controls
        self.taper = taper
        self.per_chunk = poll_count(poll, player.nstems)
        self.next = 0

        self.measure = measure
        self.hook_us_max = 0.0
        self.hook_us_total = 0.0
        self.hook_calls = 0
        self.changes = 0

        self._adc = controls._faders
        if len(self._adc) < player.nstems:
            raise ValueError("need %d faders" % player.nstems)
        self._raw = [f.value for f in self._adc]
        self._deadband = sp1_controls.FADER_DEADBAND
        self._scale = sp1_controls.fader_scale

        self._voice = player.mixer.voice
        self._n = player.nstems
        self.levels = [0.0] * self._n
        for i in range(self._n):
            self._set(i, self._raw[i])

    def _set(self, i, raw):
        """One fader's raw reading -> both banks' level for that stem."""
        g = self._scale(raw)
        if self.taper != 1:
            g = g**self.taper
        self.levels[i] = g
        self._voice[i].level = g
        self._voice[self._n + i].level = g

    def poll(self, player=None, stats=None):
        """The `on_chunk` hook. Signature takes the player's two arguments so
        it can be passed straight in, and ignores both."""
        t0 = time.monotonic_ns() if self.measure else 0
        adc = self._adc
        raw = self._raw
        db = self._deadband
        n = self._n
        i = self.next
        for _ in range(self.per_chunk):
            r = adc[i].value
            if r - raw[i] >= db or raw[i] - r >= db:
                raw[i] = r
                self._set(i, r)
                self.changes += 1
            i = i + 1 if i + 1 < n else 0
        self.next = i
        if not self.measure:
            return 0.0
        us = (time.monotonic_ns() - t0) / 1000.0
        self.hook_us_total += us
        self.hook_calls += 1
        if us > self.hook_us_max:
            self.hook_us_max = us
        return us

    @property
    def hook_us_mean(self):
        return self.hook_us_total / self.hook_calls if self.hook_calls else 0.0

    def meter(self):
        return "  ".join(
            "F%d %s %.2f" % (i + 1, _bar(v), v) for i, v in enumerate(self.levels)
        )


# --------------------------------------------------------------------------
# the playlist


class Track:
    """One entry of the playlist"""

    def __init__(self, path, title=None, names=None):
        self.path = path
        self.title = title if title else path.rsplit("/", 1)[-1]
        self.names = names

    def __repr__(self):
        return "<Track %s>" % self.path


def _entry(item, root):
    """One decoded JSON entry -> a `Track`. Raises ValueError, with the entry
    in the message: a playlist that will not load should say which line."""
    names = title = None
    if isinstance(item, str):
        path = item
    elif isinstance(item, dict):
        path = item.get("path") or item.get("song") or item.get("dir")
        title = item.get("title") or item.get("name")
        names = item.get("stems") or item.get("files")
        if names is not None:
            names = [str(n) for n in names]
        if not path:
            raise ValueError("no `path` in playlist entry %r" % (item,))
    else:
        raise ValueError(
            "a playlist entry is a path or an object with one, " "not %r" % (item,)
        )
    path = str(path)
    if not path.startswith("/"):
        path = root + "/" + path
    while path.endswith("/"):
        path = path[:-1]
    return Track(path, title, names)


def load_playlist(source=None, root=None):
    """Read the playlist. Returns `(tracks, repeat, name)`, or `(None,...)`.

    `source` is a path to a JSON file, an already-decoded list of entries, or
    `None` for `PLAYLIST` on the mounted card.

    `repeat` is the file's own `"repeat"` key or `None` if it did not say.
    """
    if root is None:
        root = sp1_wavplayer.DEFAULT_MOUNT
    if isinstance(source, (list, tuple)):
        return [_entry(x, root) for x in source], None, "argument"

    name = PLAYLIST if source is None else source
    try:
        fh = open(name, "r")
    except OSError:
        if source is None:
            return None, None, None  # no playlist here; play one song
        raise
    try:
        text = fh.read(MAX_PLAYLIST_BYTES + 1)
    finally:
        fh.close()
    if len(text) > MAX_PLAYLIST_BYTES:
        raise ValueError("%s is larger than %d B" % (name, MAX_PLAYLIST_BYTES))

    import json

    try:
        data = json.loads(text)
    except (ValueError, SyntaxError) as err:
        raise ValueError("%s is not valid JSON: %s" % (name, err))
    text = None

    repeat = None
    if isinstance(data, dict):
        repeat = data.get("repeat")
        items = data.get("songs") or data.get("tracks") or data.get("playlist")
        if items is None:
            raise ValueError("%s has no `songs` list" % name)
    else:
        items = data
    if not isinstance(items, (list, tuple)):
        raise ValueError(
            "%s: the song list is a %s, not a list" % (name, type(items).__name__)
        )
    if not items:
        raise ValueError("%s lists no songs" % name)
    tracks = [_entry(x, root) for x in items]
    if repeat is not None:
        repeat = bool(repeat)
    return tracks, repeat, name


def open_track(tracks, index, need_stems):
    """`open_song()` on `tracks[index]`, stepping over the ones that will not.

    Returns `(song, index)`

    `need_stems` is the highest stem number the player is wired for, so a song
    with too few of them is refused here rather than as an IndexError inside
    the refill.
    """
    n = len(tracks)
    for _ in range(n):
        t = tracks[index]
        try:
            song = sp1_wavplayer.open_song(t.path, names=t.names)
            if song.nstems <= need_stems:
                raise sp1_wavplayer.WavError(
                    "%d stem(s), and this run plays stem %d" % (song.nstems, need_stems)
                )
            return song, index
        except (OSError, ValueError, sp1_wavplayer.WavError) as err:
            print("SKIPTRK|%s|%s" % (t.path, err))
            print("  skipping %s -- %s" % (t.path, err))
        index = index + 1 if index + 1 < n else 0
    raise sp1_wavplayer.WavError("no playable song in the playlist")


def load_track(player, song):
    """Point a built `Player` at another `Song`. The player is not rebuilt."""
    if max(player.stems) >= song.nstems:
        raise sp1_wavplayer.WavError(
            "%s has %d stem(s), and this run plays stem %d"
            % (song.path, song.nstems, max(player.stems))
        )
    player.song = song
    player._open()


# --------------------------------------------------------------------------
# the buttons


class Transport:
    """LADDER2's four buttons: VOL+/VOL- on the level, the rocker on the set.

      * **VOL+/VOL-** step the level of whichever output is live, immediately
        on the press and then every `REPEAT_INTERVAL` once it has been held
        for `HOLD_DELAY` -- so a tap is one step and a hold is a ramp.
      * **ROCKER+/ROCKER-** ask `run()` for the next or previous track. They
        never repeat: holding the rocker skips one track, not forty.

    `poll()` returns the skip request and nothing else. It cannot change the
    track itself
    """

    def __init__(
        self,
        audio,
        controls,
        step=VOLUME_STEP,
        hold_delay=HOLD_DELAY,
        interval=REPEAT_INTERVAL,
        lockout=BUTTON_LOCKOUT,
        echo=True,
    ):
        if not controls._ladders:
            raise ValueError("Transport needs Controls(buttons=True)")
        self.audio = audio
        self.step = step
        self.hold_delay = hold_delay
        self.interval = interval
        self.lockout = lockout
        self.echo = echo
        self.skip = 0  # +1 next, -1 previous; read by run()
        self.changes = 0  # volume steps written
        self.skips = 0  # rocker presses honoured

        self._adc = controls._ladders[1][0]
        self._names = sp1_controls.LADDER2_NAMES
        self._decode = sp1_controls.decode

        self._held = None

        self._changed = -lockout
        self._repeat_at = 0.0

        self.headphone_level = audio.volume
        spk = audio.speaker_volume
        self.speaker_level = 0.0 if spk is None else spk

    # -- the hook ----------------------------------------------------------

    def poll(self):
        """Sample LADDER2 once. Returns +1 (next), -1 (previous) or 0."""
        name = self._decode(self._adc.value, self._names)
        if name is None and self._held is None:
            return 0  # the idle path: no clock, no garbage
        now = time.monotonic()
        if name != self._held:
            if now - self._changed < self.lockout:
                return 0
            self._changed = now
            self._held = name
            if name is None:
                return 0  # a release arms the next press
            self._repeat_at = now + self.hold_delay
            return self._act(name, False)
        if name is not None and now >= self._repeat_at:
            self._repeat_at = now + self.interval
            return self._act(name, True)
        return 0

    def _act(self, name, repeat):
        if name == "VOL+":
            self._level(self.step, repeat)
        elif name == "VOL-":
            self._level(-self.step, repeat)
        elif repeat:
            return 0  # the rocker does not auto-repeat
        elif name == "ROCKER+":
            self.skip = 1
            self.skips += 1
            return 1
        elif name == "ROCKER-":
            self.skip = -1
            self.skips += 1
            return -1
        return 0

    def take(self):
        """The pending skip request, cleared. `run()`'s side of `poll()`."""
        s = self.skip
        self.skip = 0
        return s

    # -- the level ---------------------------------------------------------

    def targets(self):
        """`(headphones, speaker)`, which levels VOL+/VOL- are moving."""
        hp, spk = self.audio._auto_targets()
        if self.audio.speaker_dac is None:
            spk = False
        if not (hp or spk):
            hp = True
        return hp, spk

    def _level(self, delta, repeat):
        hp, spk = self.targets()
        if hp:
            self.headphone_level = _clamp01(self.headphone_level + delta)
            self.audio.volume = self.headphone_level
        if spk:
            self.speaker_level = _clamp01(self.speaker_level + delta)
            self.audio.speaker_volume = self.speaker_level
        self.changes += 1
        if self.echo and not repeat:
            print(
                "VOL|%s|%.3f|%.1f"
                % (
                    "hp" if hp else "spk",
                    self.headphone_level if hp else self.speaker_level,
                    (
                        _fraction_to_db(self.headphone_level, CS_MIN_DB)
                        if hp
                        else _fraction_to_db(self.speaker_level, TAS_MIN_DB)
                    ),
                )
            )

    def meter(self):
        hp, spk = self.targets()
        out = []
        if hp:
            out.append(
                "HP %s %.2f (%.0f dB)"
                % (
                    _bar(self.headphone_level),
                    self.headphone_level,
                    _fraction_to_db(self.headphone_level, CS_MIN_DB),
                )
            )
        if spk:
            out.append(
                "SPK %s %.2f (%.0f dB)"
                % (
                    _bar(self.speaker_level),
                    self.speaker_level,
                    _fraction_to_db(self.speaker_level, TAS_MIN_DB),
                )
            )
        return "  ".join(out)


# --------------------------------------------------------------------------
# the run


def _clamp01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def _announce(song):
    """The SONG|/STEM| lines, once per track"""
    print(
        "SONG|%s|%d|%d|%.2f|%d|%d"
        % (
            song.path,
            song.nstems,
            song.blocks,
            song.seconds,
            1 if song.aligned else 0,
            1 if song.ragged else 0,
        )
    )
    for i in range(song.nstems):
        print("STEM|%d|%s|%d|%d" % (i, song.paths[i], song.starts[i], song.sizes[i]))
    if not song.aligned:
        print(
            "  (a stem's `data` does not start on a 512 B boundary -- "
            "every read leaves f_read's fast path, at about half the "
            "rate; re-prepare it with tools/sp1_wav_prep.py)"
        )


def _aggregate(agg, st):
    """One track's `stats` into the run's. The shape stays `Player.play()`'s."""
    for k in (
        "chunks",
        "blocks",
        "underruns",
        "slips",
        "seconds",
        "audio_seconds",
        "fill_ms_sum",
    ):
        agg[k] += st[k]
    for k in ("fill_ratio", "fill_ms_max"):
        if st[k] > agg[k]:
            agg[k] = st[k]
    # A chunk boundary is a handover *between* two chunks, so a track of `n`
    # chunks has `n - 1` of them -- and the dead air is per boundary.
    agg["boundaries"] += st["chunks"] - 1 if st["chunks"] else 0
    agg["tracks"] += 1


def run(
    seconds=None,
    at=0.0,
    path=None,
    playlist=None,
    repeat=None,
    track=0,
    stems=STEMS,
    output="headphones",
    volume=0.35,
    taper=TAPER,
    poll=FADER_POLL,
    buttons=True,
    volume_step=VOLUME_STEP,
    high_speed=True,
    chunk_bytes=None,
    fade_ms=None,
    gc_every=GC_EVERY,
    mixer_pad=None,
    mixer_buffer=None,
    mount=True,
    progress=5.0,
    measure=False,
    watch=None,
    speaker=None,
):
    """Play a playlist off the card with the faders on its stems.

    Everything is built here and released on the way out, including on Ctrl-C.

    **What gets played.** `run()` with neither argument reads `PLAYLIST`
    (`/sd/playlist.json`) and plays it in order; if there is no such file it
    plays `sp1_wavplayer.DEFAULT_SONG`,

        d.run()                                   # the card's playlist
        d.run(path="/sd/songs/test_song")         # one song, playlist ignored
        d.run(playlist="/sd/set2.json")           # a different playlist
        d.run(playlist=["songs/a", "songs/b"])    # a playlist from the REPL
        d.run(playlist=False)                     # never look for one

    `repeat` starts the list again at the end; `None` takes the file's own
    `"repeat"` key, and `REPEAT` if it did not say one. It is off by default.

    `track` is where in the list to start, `at` is seconds into that first
    song, and `seconds` is a budget for the whole run.

    `buttons` enable VOL+/VOL- on the level and the rocker on the set, polled
    once a chunk out of the same hook as the faders.

    `watch(player, stats, mix)` is called once a chunk, right after the faders
    are polled

    `speaker` is the memory knob: `None` builds the TAS2505 only when `output`
    can reach it, `True` always, `False` never.

    `mixer_pad` is the silence at every chunk boundary, in frames.

    Returns one `stats` dict for the whole run, in `Player.play()`'s own shape
    -- counts summed, worst cases maximised -- plus `tracks` and `played`.
    """
    audio = controls = player = transport = None
    gc.collect()
    dev = sp1_wavplayer.mount_card(high_speed=high_speed) if mount else None
    try:
        if dev is not None:
            print("BUS|%d|%d" % (dev.frequency, 1 if dev.high_speed else 0))

        file_repeat = source = None
        tracks = None
        if playlist is False:
            pass
        elif playlist is not None:
            tracks, file_repeat, source = load_playlist(playlist)
        elif path is None:
            tracks, file_repeat, source = load_playlist(None)
        if tracks is None:
            tracks = [Track(path if path is not None else sp1_wavplayer.DEFAULT_SONG)]
            source = "path"
        if repeat is None:
            repeat = REPEAT if file_repeat is None else file_repeat
        gc.collect()

        print("LIST|%d|%s|%d" % (len(tracks), source, 1 if repeat else 0))
        for i in range(len(tracks)):
            print("TRACK|%d|%s|%s" % (i, tracks[i].path, tracks[i].title))
        if len(tracks) > 1:
            print(
                "  playlist: %d song(s) from %s%s"
                % (len(tracks), source, ", repeating" if repeat else "")
            )

        index = track % len(tracks)
        need = max(stems) if stems else 0
        song, index = open_track(tracks, index, need)
        _announce(song)
        if at and int(at / BLOCK_SECONDS) >= song.blocks:
            raise ValueError(
                "%.1f s is past the end of a %.1f s song" % (at, song.seconds)
            )

        if speaker is None:
            speaker = output in ("speaker", "both", "auto")
        audio = DriverAudio(output=output, volume=volume, speaker=speaker)

        audio.reserve()

        controls = sp1_controls.Controls(
            buttons=buttons, faders=True, battery=False, charger=False
        )
        player = sp1_wavplayer.Player(
            song,
            audio,
            stems=stems,
            chunk_bytes=chunk_bytes,
            fade_ms=fade_ms,
            gc_every=gc_every,
            mixer_pad=mixer_pad,
            mixer_buffer=mixer_buffer,
        )
        mix = FaderMix(player, controls, taper=taper, poll=poll, measure=measure)
        if buttons:
            transport = Transport(audio, controls, step=volume_step)

        mix.transport = transport
        need = max(player.stems)
        dead = player.dead_air_ms

        played = ",".join([str(x) for x in player.stems])
        print(
            "PLAY|%s|%d|%d|%d|%.3f|%d|%d|%.3f|%d|%.2f"
            % (
                played,
                int(at / BLOCK_SECONDS),
                song.blocks,
                player.chunk_bytes,
                player.chunk_seconds,
                gc.mem_free(),
                player.fade_frames,
                player.fill_ratio_predicted,
                player.mixer_buffer,
                dead,
            )
        )
        if player.chunk_shrunk:
            print(
                "  (the heap only had room for %d B chunks -- %.0f ms, so a "
                "boundary %.1f times a second)"
                % (
                    player.chunk_bytes,
                    player.chunk_seconds * 1e3,
                    1.0 / player.chunk_seconds,
                )
            )
        print(
            "  stems %s on %d voices, %d B chunks (%.0f ms)"
            % (
                played,
                2 * player.nstems,
                player.chunk_bytes,
                player.chunk_seconds * 1e3,
            )
        )
        print(
            "  faders: %s"
            % "  ".join(
                "FADER%d -> stem %d" % (i + 1, st) for i, st in enumerate(player.stems)
            )
        )
        print(
            "  poll %d fader(s) a chunk, %.0f Hz each, taper %s"
            % (
                mix.per_chunk,
                mix.per_chunk / (player.nstems * player.chunk_seconds),
                taper,
            )
        )
        if transport is not None:
            print(
                "  buttons: VOL+/VOL- step %.2f (%.1f dB), ROCKER+/- "
                "next/previous, sampled every chunk"
                % (volume_step, volume_step * -CS_MIN_DB)
            )
            print("  level: %s" % transport.meter())
        else:
            print(
                "  buttons: off (buttons=False) -- the hook is the plain "
                "fader demo's"
            )
        print(
            "  mixer %d B, %d-frame block -> %.3f ms of silence a boundary "
            "(%.2f%% of the song)"
            % (
                player.mixer_buffer,
                player.mixer_buffer // 8,
                dead,
                100.0 * dead / (dead + player.chunk_seconds * 1e3),
            )
        )
        # The line to quote when reporting how a run sounded: gap, ramp and
        # rate are the whole of what a listener is being asked to judge.
        print(
            "  boundary: gap %.3f ms (pad %d frame(s)) + ramp %.3f ms "
            "(%d frame(s)) a side, %.1f times a second"
            % (
                dead,
                player.mixer_pad,
                player.fade_frames / (RATE / 1000.0),
                player.fade_frames,
                1.0 / (player.chunk_seconds + dead / 1e3),
            )
        )
        print("MIX|%s" % ",".join("%.3f" % v for v in mix.levels))
        print("  start %s" % mix.meter())

        state = [time.monotonic()]

        def tick(p, st):
            mix.poll()
            skip = transport.poll() if transport is not None else 0
            if watch is not None:
                watch(p, st, mix)
            if progress and time.monotonic() - state[0] >= progress:
                state[0] = time.monotonic()
                print(
                    "POS|%.1f|%d|%.2f|%s|%s"
                    % (
                        st["blocks"] * BLOCK_SECONDS,
                        st["underruns"],
                        st["fill_ratio"],
                        ",".join("%.3f" % v for v in mix.levels),
                        mix.meter(),
                    )
                )
            if skip:
                audio.muted = True
                raise KeyboardInterrupt

        agg = {
            "chunks": 0,
            "blocks": 0,
            "underruns": 0,
            "slips": 0,
            "seconds": 0.0,
            "audio_seconds": 0.0,
            "fill_ratio": 0.0,
            "fill_ms_max": 0.0,
            "fill_ms_sum": 0.0,
            "fill_ratio_mean": 0.0,
            "dead_ms": 0.0,
            "boundaries": 0,
            "tracks": 0,
            "stems": tuple(player.stems),
            "interrupted": False,
            "played": [],
        }

        print("  playing -- move the faders. Ctrl-C to stop.")
        left = seconds
        skip_at = at
        wall = time.monotonic()
        first = True
        while True:
            if not first:
                _announce(song)
            first = False
            print(
                "NOW|%d|%d|%s|%s|%.1f"
                % (index, len(tracks), song.path, tracks[index].title, song.seconds)
            )
            print(
                "  [%d/%d] %s -- %.1f s"
                % (index + 1, len(tracks), tracks[index].title, song.seconds)
            )
            block = int(skip_at / BLOCK_SECONDS)
            if block >= song.blocks:
                block = 0
            skip_at = 0.0
            audio.muted = False
            st = player.play(block, song.blocks - block, seconds=left, on_chunk=tick)
            _aggregate(agg, st)
            agg["played"].append(tracks[index].path)
            print(
                "TSTAT|%d|%s|%d|%d|%d|%d|%.2f"
                % (
                    index,
                    tracks[index].path,
                    st["chunks"],
                    st["blocks"],
                    st["underruns"],
                    st["slips"],
                    st["audio_seconds"],
                )
            )

            req = transport.take() if transport is not None else 0
            if st.get("interrupted") and not req:
                agg["interrupted"] = True  # a real Ctrl-C, not the rocker
                break
            if left is not None:
                left -= st["audio_seconds"]
                if left <= 0.0:
                    break
            n = len(tracks)
            if req < 0:
                if st["blocks"] * BLOCK_SECONDS < PREV_RESTART_SECONDS:
                    index = index - 1 if index else n - 1
            elif req > 0:
                index = index + 1 if index + 1 < n else 0
            else:
                if index + 1 >= n and not repeat:
                    break  # the set played out
                index = index + 1 if index + 1 < n else 0
            song, index = open_track(tracks, index, need)
            load_track(player, song)

        if agg["boundaries"]:
            agg["fill_ratio_mean"] = (
                agg["fill_ms_sum"] / agg["boundaries"] / (player.chunk_seconds * 1e3)
            )
        gap = (agg["seconds"] - agg["audio_seconds"]) / max(1, agg["boundaries"])
        agg["dead_ms"] = gap * 1e3
        agg["frames"] = agg["blocks"] * sp1_wavplayer.BLOCK_FRAMES
        agg["wall_seconds"] = time.monotonic() - wall

        print(
            "STATS|%d|%d|%d|%.3f|%.1f|%.2f|%.2f|%d|%d|%.3f"
            % (
                agg["chunks"],
                agg["blocks"],
                agg["underruns"],
                agg["fill_ratio"],
                agg["fill_ms_max"],
                agg["audio_seconds"],
                agg["seconds"],
                gc.mem_free(),
                agg["slips"],
                agg["fill_ratio_mean"],
            )
        )
        print(
            "HOOK|%.1f|%d|%.4f|%d|%.1f|%.4f"
            % (
                mix.hook_us_max,
                mix.changes,
                mix.hook_us_max / (player.chunk_seconds * 1e6),
                1 if measure else 0,
                mix.hook_us_mean,
                mix.hook_us_mean / (player.chunk_seconds * 1e6),
            )
        )

        print("DEAD|%.3f|%.3f" % (gap * 1e3, dead))
        if transport is not None:
            print(
                "BTN|%d|%d|%.3f|%.3f"
                % (
                    transport.changes,
                    transport.skips,
                    transport.headphone_level,
                    transport.speaker_level,
                )
            )
        print(
            "  %d track(s): %.1f s played in %.1f s -- %d chunk(s), "
            "%d underrun(s), %d slip(s), worst fill %.0f%% of a chunk "
            "(%.0f%% mean)"
            % (
                agg["tracks"],
                agg["audio_seconds"],
                agg["wall_seconds"],
                agg["chunks"],
                agg["underruns"],
                agg["slips"],
                agg["fill_ratio"] * 100,
                agg["fill_ratio_mean"] * 100,
            )
        )
        print("  dead air %.2f ms a boundary (%.2f ms predicted)" % (gap * 1e3, dead))
        if measure:
            print(
                "  fader hook: %.0f us a chunk (%.1f%%), worst %.0f us, "
                "%d level change(s)"
                % (
                    mix.hook_us_mean,
                    100.0 * mix.hook_us_mean / (player.chunk_seconds * 1e6),
                    mix.hook_us_max,
                    mix.changes,
                )
            )
        else:
            print(
                "  %d fader level change(s) (hook not timed -- measure=True)"
                % mix.changes
            )
        if transport is not None:
            print(
                "  buttons: %d volume step(s), %d skip(s) -- %s"
                % (transport.changes, transport.skips, transport.meter())
            )
        print("  final %s" % mix.meter())
        return agg
    finally:
        # Mute over I2C before anything stops
        if audio is not None:
            audio.stop()
        if player is not None:
            player.deinit()
        if audio is not None:
            audio.deinit()
        if controls is not None:
            controls.deinit()
        if mount:
            sp1_wavplayer.umount_card()
        gc.collect()


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nstopped.")
