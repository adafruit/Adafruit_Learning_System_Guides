# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""RTL-SDR AM/FM receiver with audio on the 3.5 mm jack.

FM (88-108 MHz) works with any supported dongle. AM (530-1700 kHz) uses the
RTL2832U's direct sampling input, which the Nooelec NESDR SMArt v5 wires and
FC0013 dongles do not. AM may also require longer or outdoor antenna.
"""

# The USB bulk ring and the audio DMA buffers can only use internal SRAM, but
# CircuitPython also grows its Python heap there, in areas as large as the
# heap already is, whenever such an area still fits. Holding a block bigger
# than all of SRAM puts it in PSRAM and makes every later area at least that
# big, so the heap stops taking SRAM. Keep this before the other imports.
# pylint: disable=wrong-import-position
_heap_ballast = bytearray(1024 * 1024)
import time
import gc
import sys
import json
import math

import board
import keypad
import supervisor
import usb.core
import usb_host_bulk

import _fm_turbo95 as _fm_turbo
import _ham_dsp
from ham_tuner import open_ham_receiver
from radio_ui_am_fm import RadioUI
from jack_audio import JackAudio

# pylint: disable=too-many-locals, too-many-branches, too-many-statements
# pylint: disable=too-many-arguments

FM_PRESETS = (93900000, 93100000, 97100000, 101100000, 104300000, 107500000, 88500000)
# Add your local AM stations here, in Hz.
AM_PRESETS = (610000,)

# FM dial: B1/B2 and the arrow keys step 200 kHz and wrap at the band edges.
FM_STEP, FM_MIN, FM_MAX = 200000, 88100000, 107900000
# AM dial for the Americas: 10 kHz channels, 530-1700 kHz. For Europe, Africa,
# Asia and Australia use 9 kHz channels instead:
#   AM_STEP, AM_MIN, AM_MAX = 9000, 531000, 1602000
AM_STEP, AM_MIN, AM_MAX = 10000, 530000, 1700000
# Typed frequencies are accepted over these slightly wider ranges.
FM_LIMITS = (87500000, 108000000)
AM_LIMITS = (520000, 1710000)

# Signal bar range in dB for each band. FM shows the wideband I/Q power, AM
# the power in the AM channel filter. Indoors, empty AM channels read about
# -40 dB on a NESDR SMArt v5.
FM_LEVEL_DB = (-30, 0)
AM_LEVEL_DB = (-45, -10)
# Added to the headphone volume on AM, so switching bands does not jump in
# loudness (the AM demodulator has its own AGC).
AM_VOLUME_OFFSET = 0.0

# The AM demodulator has no DC removal, so the hardware centre sits above the
# dial frequency, away from the receiver's DC offset. Tuning inside the window
# only moves the DSP oscillator, which is instant and gapless; leaving it
# retunes the hardware.
AM_CENTRE_OFFSET = 56000  # centre - dial after a hardware retune
AM_WINDOW = (12000, 100000)  # allowed centre - dial
HAM_AM = 1  # _ham_dsp mode number

HOLD_MS = 650  # a button held this long is a hold, not a press
# Serial console escape sequences (after ESC) for the up and down arrow keys,
# in normal and application cursor mode, and the tuning action they map to.
ARROW_KEYS = {"[A": "+", "OA": "+", "[B": "-", "OB": "-"}
NO_AM = "AM needs a direct-sampling dongle (NESDR SMArt v5)"


def parse_frequency(text):
    """Return (band, Hz) for a typed frequency, without single-precision floats.

    '101.1', '101.1mhz', '88.5' -> FM; '610', '610khz', '1190' (whole numbers
    in AM_LIMITS are kHz) and '0.61' (MHz below 2) -> AM. A number with no
    unit and no point is otherwise MHz below 2000 and Hz above.
    """
    text = text.strip().lower().replace(" ", "")
    scale = None
    for unit, factor in (("mhz", 1000000), ("khz", 1000), ("hz", 1)):
        if text.endswith(unit):
            text = text[: -len(unit)]
            scale = factor
            break
    whole, frac = text.split(".", 1) if "." in text else (text, "")
    if not (whole + frac).isdigit():
        raise ValueError(text)
    value = int(whole or "0")
    if scale is None:
        if frac:
            scale = 1000000
        elif AM_LIMITS[0] // 1000 <= value <= AM_LIMITS[1] // 1000:
            scale = 1000
        elif value < 2000:
            scale = 1000000
        else:
            scale = 1
    digits = len(str(scale)) - 1
    hz = value * scale
    if frac and digits:
        hz += int((frac + "000000")[:digits])
    if FM_LIMITS[0] <= hz <= FM_LIMITS[1]:
        return "FM", hz
    if AM_LIMITS[0] <= hz <= AM_LIMITS[1]:
        return "AM", hz
    raise ValueError(text)


def fm_level_db(iq):
    # Power of the whole 256 kHz I/Q block with its DC offset removed, in dB
    # relative to a full-scale 8-bit sine. The demodulator's digital AGC is off
    # and the tuner gain is fixed, so this follows the antenna signal.
    n, sum_i, sum_q, sumsq = _fm_turbo.signal_stats(iq)[:4]
    power = (n * sumsq - sum_i * sum_i - sum_q * sum_q) / (n * n)
    return 4.342944819 * math.log(power / 16256.25 + 1e-12)


def am_level_db(power_q16):
    # Mean AM channel power (Q16, from _ham_dsp.status), in dB relative to a
    # full-scale 8-bit sine.
    return 4.342944819 * math.log(power_q16 / 65536 / 16256.25 + 1e-12)


def start_stream(d, audio):
    # The audio DMA buffers and the bulk ring must both be in internal SRAM.
    # Start the audio first (its FIFO is allocated later, on first write),
    # then take the largest ring that fits: 64 ms of USB buffering, or 32 ms.
    audio.start()
    for size in (32768, 16384):
        try:
            return usb_host_bulk.InStream(d, 0x81, buffer_size=size), size
        except MemoryError:
            pass
    audio.stop()
    raise MemoryError("no SRAM for the USB bulk ring")


def run(
    seconds=0,
    band="FM",
    fm_frequency=93900000,
    am_frequency=AM_PRESETS[0],
    gain=400,
    controls=True,
    volume=-10.0,
    display=True,
    direct_input="Q",
    commands=(),
    log_every=5,
):
    """Run the receiver. seconds=0 runs forever.

    band ('FM' or 'AM') picks the starting band; each band starts on its own
    frequency (Hz). commands is a list of (seconds, command) pairs, such as
    (5, 'b') or (8, 'f610'), fed to the command handler for unattended tests.
    """
    supervisor.runtime.autoreload = False
    # Free the garbage left by compiling ham_tuner.py first, so where the
    # display bitmaps land (and so how long a redraw takes) is repeatable.
    gc.collect()
    ui = RadioUI() if display else None
    freq = {"FM": fm_frequency, "AM": am_frequency}
    muted = False
    notice = None
    commands = sorted(commands)

    def draw():
        if not ui:
            return 0
        t = time.monotonic_ns()
        status = "LIVE %s / 3.5MM JACK" % band
        if muted:
            status += " / MUTED"
        if band == "AM":
            line1 = "AM, direct sampling, %d kHz steps" % (AM_STEP // 1000)
        else:
            line1 = "256 ksample/s -> 32 kHz mono"
        ui.draw(
            notice or status,
            freq[band],
            line1,
            "receiving directly from the antenna",
            band == "AM",
        )
        return time.monotonic_ns() - t

    audio = None
    keys = None
    d = None
    stream = None
    if ui:
        ui.draw("CONNECTING", freq[band], "looking for the USB receiver", "")
    for _ in range(20):
        d = usb.core.find(idVendor=0x0BDA, idProduct=0x2838)
        if d:
            break
        time.sleep(0.1)
    if not d:
        raise RuntimeError("No RTL-SDR receiver found on Fruit Jam USB")
    # Let USB enumeration and receiver power settle after a full MCU reset.
    time.sleep(0.5)
    d.set_configuration()
    radio = open_ham_receiver(d, direct_input=direct_input)
    # Only a dongle with direct sampling (R82xx here) tunes below 25 MHz.
    has_am = radio.min_frequency <= AM_LIMITS[0]
    if band == "AM" and not has_am:
        band = "FM"
        notice = NO_AM
    centre = freq[band] + (AM_CENTRE_OFFSET if band == "AM" else 0)
    radio.initialize(frequency=centre, sample_rate=256000, gain=gain)
    radio.hold_buffer()
    fm_state = bytearray(512)
    am_state = bytearray(8192)

    def configure_am():
        _ham_dsp.configure(
            am_state, HAM_AM, freq["AM"] - centre, 0, 1 if radio.conjugate else 0
        )

    try:
        audio = JackAudio(volume=volume + (AM_VOLUME_OFFSET if band == "AM" else 0))
        if band == "AM":
            configure_am()
        total = output = 0
        lost_before = 0  # packets lost by streams already stopped
        retunes = 0
        max_dsp = 0
        dsp_total = 0
        dsp_calls = 0
        max_loop = 0
        max_draw = 0  # redraws while the stream runs
        max_redraw = 0  # full redraws while it is stopped
        pressed_at = [None, None, None]
        line = None
        esc = None  # partial escape sequence from the serial console
        keys = keypad.Keys(
            (board.BUTTON1, board.BUTTON2, board.BUTTON3),
            value_when_pressed=False,
            pull=True,
        )
        draw()
        gc.collect()
        radio.reset_buffer()
        stream, ring = start_stream(d, audio)
        iq = bytearray(8192)
        iqv = memoryview(iq)
        filled = 0
        start = time.monotonic()
        last_log = start
        last_level = start
        level = None
        last_ns = time.monotonic_ns()
        print(
            "LIVE_START",
            json.dumps(
                {
                    "ring_size": ring,
                    "band": band,
                    "frequency": freq[band],
                    "centre": centre,
                    "sample_rate": radio.sample_rate,
                    "gain": gain,
                    "tuner": radio.tuner_name,
                    "direct": radio.direct,
                }
            ),
        )

        def tune(new_band, hz):
            # Tune to hz, switching band if needed. Returns the redraw time.
            nonlocal band, centre, stream, ring, filled, fm_state, am_state
            nonlocal notice, retunes, level, lost_before, last_ns
            if new_band == "AM" and not has_am:
                notice = NO_AM
                print("NO_AM", radio.tuner_name)
                return 0
            notice = None
            switching = new_band != band
            if switching:
                level = None  # the other band's reading means nothing here
            band = new_band
            freq[band] = hz
            if (
                band == "AM"
                and not switching
                and AM_WINDOW[0] <= centre - hz <= AM_WINDOW[1]
            ):
                configure_am()
                return 0
            # Stop, retune and restart without pausing in between: in testing,
            # a retune after the FIFO was held for several seconds failed with
            # a USB pipe error. Leaving AM fully re-initializes the tuner
            # (gain included) inside radio.tune().
            lost_before += stream.lost_packets
            stream.deinit()
            audio.stop()
            audio.clear()
            radio.hold_buffer()
            centre = hz + (AM_CENTRE_OFFSET if band == "AM" else 0)
            radio.tune(centre)
            radio.hold_buffer()
            retunes += 1
            if band == "FM":
                fm_state = bytearray(512)
            else:
                if switching:
                    am_state = bytearray(8192)
                configure_am()
            if switching:
                audio.dac.dac_volume = volume + (
                    AM_VOLUME_OFFSET if band == "AM" else 0
                )
            # A full redraw outlasts the USB ring, so do it while stopped.
            dt = draw()
            radio.reset_buffer()
            filled = 0
            stream, ring = start_stream(d, audio)
            # loop_max_ms tracks stalls while receiving, not this stop.
            last_ns = time.monotonic_ns()
            return dt

        while not seconds or time.monotonic() - start < seconds:
            now = time.monotonic()
            t = time.monotonic_ns()
            max_loop = max(max_loop, t - last_ns)
            last_ns = t
            audio.service()
            n = stream.readinto(iqv[filled:])
            if n == 0:
                raise RuntimeError("USB stream ended")
            n = n or 0
            filled += n
            total += n
            if filled == len(iq):
                # One block of 4096 I/Q samples gives 512 PCM samples.
                out = audio.write_view_bytes(512)
                t = time.monotonic_ns()
                if band == "FM":
                    count = _fm_turbo.process(iq, out, fm_state) // 2
                else:
                    count = _ham_dsp.process(iq, out, am_state) // 2
                dt = time.monotonic_ns() - t
                dsp_total += dt
                dsp_calls += 1
                max_dsp = max(max_dsp, dt)
                if not muted:
                    audio.commit(count)
                    output += count
                if now - last_level >= 0.25:
                    if band == "FM":
                        level = fm_level_db(iq)
                        low, high = FM_LEVEL_DB
                    else:
                        level = am_level_db(_ham_dsp.status(am_state)[0])
                        low, high = AM_LEVEL_DB
                    if ui:
                        ui.level((level - low) / (high - low))
                    last_level = now
                filled = 0
                audio.service()
            elif not n:
                time.sleep(0.0005)

            # Buttons act on release, so a hold can be told from a press:
            # B1 lower / hold: AM <-> FM, B2 higher, B3 mute / hold: preset.
            action = None
            event = keys.events.get()
            if event:
                k = event.key_number
                if event.pressed:
                    pressed_at[k] = event.timestamp
                elif pressed_at[k] is not None:
                    held = ((event.timestamp - pressed_at[k]) & 0x1FFFFFFF) >= HOLD_MS
                    pressed_at[k] = None
                    action = (
                        ("b" if held else "-"),
                        (None if held else "+"),
                        ("p" if held else "m"),
                    )[k]
            if supervisor.runtime.serial_bytes_available:
                # 'f 101.1' or 'f610' + Enter tunes directly; other characters
                # are single-key commands. Backspace edits the entry, and
                # cancels it once it is empty.
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    esc, ch = "", ""
                elif esc is not None:
                    # Inside an escape sequence: up/down arrows tune like
                    # + and -. Swallow any other sequence up to its final byte.
                    esc += ch
                    if (
                        len(esc) > 1
                        and "@" <= ch <= "~"
                        or esc[0] not in "[O"
                        or len(esc) > 8
                    ):
                        if line is None:
                            action = ARROW_KEYS.get(esc, action)
                        esc = None
                    ch = ""
                if not ch:  # consumed by an escape sequence
                    pass
                elif line is not None:
                    if ch in "\r\n":
                        action = "f" + line
                        line = None
                    elif ch in "\x08\x7f":
                        line = line[:-1] if line else None
                    else:
                        line += ch
                    if not action and controls and ui:
                        t = time.monotonic_ns()
                        ui.entry(None if line is None else "f" + line)
                        max_draw = max(max_draw, time.monotonic_ns() - t)
                elif ch in "fF":
                    line = ""
                    if controls and ui:
                        t = time.monotonic_ns()
                        ui.entry("f")
                        max_draw = max(max_draw, time.monotonic_ns() - t)
                else:
                    action = ch.lower()
            if commands and now - start >= commands[0][0]:
                action = commands.pop(0)[1]
            if not controls:
                action = None
            if action:
                dt = 0
                if action in ("+", "-"):
                    f = freq[band]
                    if band == "FM":
                        f += FM_STEP if action == "+" else -FM_STEP
                        low, high = FM_MIN, FM_MAX
                    else:
                        # Step to the next channel on the AM_STEP grid.
                        if action == "+":
                            f = (f // AM_STEP + 1) * AM_STEP
                        else:
                            f = (f - 1) // AM_STEP * AM_STEP
                        low, high = AM_MIN, AM_MAX
                    if f > high:
                        f = low
                    if f < low:
                        f = high
                    dt = tune(band, f)
                elif action == "p":
                    presets = FM_PRESETS if band == "FM" else AM_PRESETS
                    f = freq[band]
                    idx = presets.index(f) if f in presets else -1
                    dt = tune(band, presets[(idx + 1) % len(presets)])
                elif action in ("b", "a", "n"):
                    new_band = {"b": "AM" if band == "FM" else "FM", "a": "AM"}.get(
                        action, "FM"
                    )
                    if new_band != band:
                        dt = tune(new_band, freq[new_band])
                elif action == "m":
                    muted = not muted
                    notice = None
                    audio.clear()
                    print("MUTE", muted)
                elif action[0] == "f":
                    try:
                        dt = tune(*parse_frequency(action[1:]))
                    except ValueError:
                        print("BAD_FREQUENCY", action[1:].strip())
                        if ui:
                            ui.entry(None)
                        action = None
                else:
                    action = None
                if action:
                    max_redraw = max(max_redraw, dt)
                    max_draw = max(max_draw, draw())
                    print(
                        "TUNED",
                        json.dumps(
                            {
                                "band": band,
                                "frequency": freq[band],
                                "centre": centre,
                                "muted": muted,
                                "notice": notice,
                                "retunes": retunes,
                            }
                        ),
                    )
            if now - last_log >= log_every:
                # Lost packets are a short audio gap, not a reason to stop.
                lost = lost_before + stream.lost_packets
                print(
                    "LIVE",
                    json.dumps(
                        {
                            "band": band,
                            "frequency": freq[band],
                            "muted": muted,
                            "level_db": level,
                            "seconds": now - start,
                            "bytes": total,
                            "pcm_samples": output,
                            "ring_size": ring,
                            "retunes": retunes,
                            "dsp_max_ms": max_dsp / 1000000,
                            "loop_max_ms": max_loop / 1000000,
                            "draw_max_ms": max_draw / 1000000,
                            "redraw_max_ms": max_redraw / 1000000,
                            "audio": audio.stats(),
                            "lost_packets": lost,
                        }
                    ),
                )
                last_log = now
        lost = lost_before + stream.lost_packets
        print(
            "RESULT",
            json.dumps(
                {
                    "band": band,
                    "fm_frequency": freq["FM"],
                    "am_frequency": freq["AM"],
                    "seconds": time.monotonic() - start,
                    "bytes": total,
                    "pcm_samples": output,
                    "level_db": level,
                    "retunes": retunes,
                    "dsp_max_ms": max_dsp / 1000000,
                    "dsp_mean_ms": dsp_total / max(1, dsp_calls) / 1000000,
                    "loop_max_ms": max_loop / 1000000,
                    "draw_max_ms": max_draw / 1000000,
                    "redraw_max_ms": max_redraw / 1000000,
                    "demod_read_retries": radio.demod_read_retries,
                    "audio": audio.stats(),
                    "lost_packets": lost,
                }
            ),
        )
    finally:
        try:
            if stream is not None:
                stream.deinit()
        finally:
            try:
                if audio is not None:
                    audio.deinit()
            finally:
                if keys is not None:
                    keys.deinit()
    print("~~END~~")
