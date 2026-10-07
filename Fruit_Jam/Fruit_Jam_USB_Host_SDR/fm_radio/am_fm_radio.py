# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""RTL-SDR AM/FM/NOAA weather receiver with audio on the 3.5 mm jack.

FM (88-108 MHz) and NOAA Weather Radio (162.400-162.550 MHz) work with any
supported dongle. AM (530-1700 kHz) uses the RTL2832U's direct sampling input,
which the Nooelec NESDR SMArt v5 wires and FC0013 dongles do not. AM may also
require longer or outdoor antenna.
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
from radio_ui_am_fm import RadioUI, format_frequency
from radio_presets import Presets, SAVE_PATH
from jack_audio import JackAudio

# pylint: disable=too-many-locals, too-many-branches, too-many-statements
# pylint: disable=too-many-arguments

# Built-in presets, in Hz. Stations saved on the radio (hold B2, or s and x)
# go in /saves/am_fm_radio.json, which can also take these out.
FM_PRESETS = (93900000, 93100000, 97100000, 101100000, 104300000, 107500000, 88500000)
# Add your local AM stations here, in Hz.
AM_PRESETS = (610000,)

# FM dial: B1/B2 and the arrow keys step 200 kHz and wrap at the band edges.
FM_STEP, FM_MIN, FM_MAX = 200000, 88100000, 107900000
# AM dial for the Americas: 10 kHz channels, 530-1700 kHz. For Europe, Africa,
# Asia and Australia use 9 kHz channels instead:
#   AM_STEP, AM_MIN, AM_MAX = 9000, 531000, 1602000
AM_STEP, AM_MIN, AM_MAX = 10000, 530000, 1700000
# NOAA Weather Radio (US and Canada): seven narrowband FM channels 25 kHz
# apart, listed here as WX1..WX7, the usual channel numbering.
WX_CHANNELS = (
    162550000,
    162400000,
    162475000,
    162425000,
    162450000,
    162500000,
    162525000,
)
WX_STEP, WX_MIN, WX_MAX = 25000, 162400000, 162550000
# Typed frequencies are accepted over these slightly wider ranges. Typed
# weather frequencies snap to the nearest channel.
FM_LIMITS = (87500000, 108000000)
AM_LIMITS = (520000, 1710000)
WX_LIMITS = (162387500, 162562500)

# Signal bar range in dB for each band. FM shows the wideband I/Q power, AM
# and weather the power in the channel filter. Indoors, on a NESDR SMArt v5,
# empty AM channels read about -40 dB, empty weather channels about -32 dB
# and a local weather station about -15 dB.
FM_LEVEL_DB = (-30, 0)
AM_LEVEL_DB = (-45, -10)
WX_LEVEL_DB = (-35, -10)
# Added to the headphone volume on AM and weather, so switching bands does
# not jump in loudness (the AM demodulator has its own AGC; weather voice
# measured about 6 dB louder than FM music).
AM_VOLUME_OFFSET = 0.0
WX_VOLUME_OFFSET = -6.0

# The AM demodulator has no DC removal, so the hardware centre sits above the
# dial frequency, away from the receiver's DC offset. Tuning inside the window
# only moves the DSP oscillator, which is instant and gapless; leaving it
# retunes the hardware.
AM_CENTRE_OFFSET = 56000  # centre - dial after a hardware retune
AM_WINDOW = (12000, 100000)  # allowed centre - dial
# Weather uses the same demodulator in NFM mode. With the hardware centre
# between the channels, all seven are 12.5-87.5 kHz from it, so changing
# channel never retunes the hardware.
WX_CENTRE = 162487500
HAM_NFM, HAM_AM = 0, 1  # _ham_dsp mode numbers

HOLD_MS = 650  # a button held this long is a hold, not a press
# Serial console escape sequences (after ESC) for the up and down arrow keys,
# in normal and application cursor mode, and the tuning action they map to.
ARROW_KEYS = {"[A": "+", "OA": "+", "[B": "-", "OB": "-"}
NO_AM = "AM needs a direct-sampling dongle (NESDR SMArt v5)"


def wx_channel(hz):
    """Return the NOAA weather channel nearest to hz."""
    hz = (hz - WX_MIN + WX_STEP // 2) // WX_STEP * WX_STEP + WX_MIN
    return min(WX_MAX, max(WX_MIN, hz))


def parse_frequency(text):
    """Return (band, Hz) for a typed frequency, without single-precision floats.

    '101.1', '101.1mhz', '88.5' -> FM; '610', '610khz', '1190' (whole numbers
    in AM_LIMITS are kHz) and '0.61' (MHz below 2) -> AM; '162.55', '162.4'
    -> WX (snapped to a channel). A number with no unit and no point is
    otherwise MHz below 2000 and Hz above.
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
    if WX_LIMITS[0] <= hz <= WX_LIMITS[1]:
        return "WX", wx_channel(hz)
    raise ValueError(text)


def fm_level_db(iq):
    # Power of the whole 256 kHz I/Q block with its DC offset removed, in dB
    # relative to a full-scale 8-bit sine. The demodulator's digital AGC is off
    # and the tuner gain is fixed, so this follows the antenna signal.
    n, sum_i, sum_q, sumsq = _fm_turbo.signal_stats(iq)[:4]
    power = (n * sumsq - sum_i * sum_i - sum_q * sum_q) / (n * n)
    return 4.342944819 * math.log(power / 16256.25 + 1e-12)


def ham_level_db(power_q16):
    # Mean AM or weather channel power (Q16, from _ham_dsp.status), in dB
    # relative to a full-scale 8-bit sine.
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
    wx_frequency=WX_CHANNELS[0],
    gain=400,
    controls=True,
    volume=-10.0,
    display=True,
    direct_input="Q",
    commands=(),
    log_every=5,
    presets_file=SAVE_PATH,
):
    """Run the receiver. seconds=0 runs forever.

    band ('FM', 'AM' or 'WX' for NOAA weather) picks the starting band; each
    band starts on its own frequency (Hz). commands is a list of (seconds,
    command) pairs, such as (5, 'b') or (8, 'f610'), fed to the command
    handler for unattended tests. Presets are saved in presets_file (None
    keeps them in memory only).
    """
    supervisor.runtime.autoreload = False
    # Free the garbage left by compiling ham_tuner.py first, so where the
    # display bitmaps land (and so how long a redraw takes) is repeatable.
    gc.collect()
    ui = RadioUI() if display else None
    freq = {"FM": fm_frequency, "AM": am_frequency, "WX": wx_channel(wx_frequency)}
    presets = Presets(
        {"FM": FM_PRESETS, "AM": AM_PRESETS, "WX": WX_CHANNELS},
        parse_frequency,
        presets_file,
    )
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
            footer = "AM needs an outdoor antenna"
        elif band == "WX":
            line1 = "NOAA weather channel WX%d, narrowband FM" % (
                WX_CHANNELS.index(freq["WX"]) + 1
            )
            footer = "NOAA WEATHER RADIO (US / CANADA)"
        else:
            line1 = "256 ksample/s -> 32 kHz mono"
            footer = "RTL-SDR RECEIVER"
        ui.draw(
            notice or status,
            freq[band],
            line1,
            "receiving directly from the antenna",
            footer,
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

    def centre_for(b, hz):
        # Hardware centre frequency for station hz on band b.
        if b == "AM":
            return hz + AM_CENTRE_OFFSET
        return WX_CENTRE if b == "WX" else hz

    def band_volume():
        return volume + {"AM": AM_VOLUME_OFFSET, "WX": WX_VOLUME_OFFSET}.get(band, 0)

    centre = centre_for(band, freq[band])
    radio.initialize(frequency=centre, sample_rate=256000, gain=gain)
    radio.hold_buffer()
    fm_state = bytearray(512)
    ham_state = bytearray(8192)  # AM and weather

    def configure_ham():
        _ham_dsp.configure(
            ham_state,
            HAM_AM if band == "AM" else HAM_NFM,
            freq[band] - centre,
            0,
            1 if radio.conjugate else 0,
        )

    try:
        audio = JackAudio(volume=band_volume())
        if band != "FM":
            configure_ham()
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
                    "presets": {b: presets.stations(b) for b in freq},
                }
            ),
        )

        def stop_stream():
            nonlocal lost_before
            lost_before += stream.lost_packets
            stream.deinit()
            audio.stop()
            audio.clear()
            radio.hold_buffer()

        def restart_stream():
            nonlocal stream, ring, filled, last_ns
            radio.reset_buffer()
            filled = 0
            stream, ring = start_stream(d, audio)
            # loop_max_ms tracks stalls while receiving, not this stop.
            last_ns = time.monotonic_ns()

        def tune(new_band, hz):
            # Tune to hz, switching band if needed. Returns the redraw time.
            nonlocal band, centre, fm_state, ham_state, notice, retunes, level
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
            if not switching and (
                band == "WX"  # every channel is within reach of WX_CENTRE
                or (band == "AM" and AM_WINDOW[0] <= centre - hz <= AM_WINDOW[1])
            ):
                configure_ham()
                return 0
            # Stop, retune and restart without pausing in between: in testing,
            # a retune after the FIFO was held for several seconds failed with
            # a USB pipe error. Leaving AM fully re-initializes the tuner
            # (gain included) inside radio.tune().
            stop_stream()
            centre = centre_for(band, hz)
            radio.tune(centre)
            radio.hold_buffer()
            retunes += 1
            if band == "FM":
                fm_state = bytearray(512)
            else:
                if switching:
                    ham_state = bytearray(8192)
                configure_ham()
            if switching:
                audio.dac.dac_volume = band_volume()
            # A full redraw outlasts the USB ring, so do it while stopped.
            dt = draw()
            restart_stream()
            return dt

        def store(add):
            # Save (add=True) or remove the station on the dial as a preset.
            # Returns the redraw time.
            nonlocal notice
            hz = freq[band]
            name = "%s %s" % (band, format_frequency(hz))
            if not (presets.add(band, hz) if add else presets.remove(band, hz)):
                notice = "%s IS %s A PRESET" % (name, "ALREADY" if add else "NOT")
                return 0
            notice = "%s PRESET %s" % ("SAVED" if add else "REMOVED", name)
            if not presets_file:
                return 0
            # Writing flash stalls the chip for longer than the USB ring
            # lasts, so stop the stream around it, as for a retune.
            stop_stream()
            try:
                presets.save()
            except OSError as error:
                # The change still holds until the radio restarts.
                print("PRESETS_NOT_SAVED", error)
                notice = "NOT SAVED: %s" % error
            dt = draw()
            restart_stream()
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
                    count = _ham_dsp.process(iq, out, ham_state) // 2
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
                        level = ham_level_db(_ham_dsp.status(ham_state)[0])
                        low, high = AM_LEVEL_DB if band == "AM" else WX_LEVEL_DB
                    if ui:
                        ui.level((level - low) / (high - low))
                    last_level = now
                filled = 0
                audio.service()
            elif not n:
                time.sleep(0.0005)

            # Buttons act on release, so a hold can be told from a press:
            # B1 lower / hold: next band, B2 higher / hold: save or remove
            # this preset, B3 mute / hold: next preset.
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
                        ("t" if held else "+"),
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
                        # pylint: disable=unsubscriptable-object
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
                    elif band == "WX":
                        f += WX_STEP if action == "+" else -WX_STEP
                        low, high = WX_MIN, WX_MAX
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
                    stations = presets.stations(band)
                    f = freq[band]
                    if stations:
                        idx = stations.index(f) if f in stations else -1
                        dt = tune(band, stations[(idx + 1) % len(stations)])
                    else:
                        notice = "NO %s PRESETS: HOLD B2 OR PRESS s TO SAVE" % band
                elif action in ("s", "x", "t"):
                    # s save, x remove, t (B2 hold) whichever applies.
                    if action == "t":
                        action = "x" if freq[band] in presets.stations(band) else "s"
                    dt = store(action == "s")
                elif action in ("b", "a", "n", "w"):
                    if action == "b":
                        # FM -> AM -> weather -> FM, without AM if not possible.
                        order = ("FM", "AM", "WX") if has_am else ("FM", "WX")
                        new_band = order[(order.index(band) + 1) % len(order)]
                    else:
                        new_band = {"a": "AM", "n": "FM", "w": "WX"}[action]
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
                                "presets": presets.stations(band),
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
                    "wx_frequency": freq["WX"],
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
