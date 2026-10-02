# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Experimental direct RTL-SDR FM receiver with audio on the 3.5 mm jack."""
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

import board
import keypad
import supervisor
import usb.core
import usb_host_bulk

import _fm_turbo95 as _fm_turbo
from fc0013_fm import open_receiver
from radio_ui_jack import RadioUI
from jack_audio import JackAudio


# pylint: disable=too-many-locals, too-many-branches, too-many-statements

PRESETS = (93900000, 93100000, 97100000, 101100000, 104300000, 107500000, 88500000)
LABEL = "LIVE FM / 3.5MM JACK"


def parse_frequency(text):
    # '101.1' (MHz) or '101100000' (Hz) -> Hz, without single-precision floats.
    text = text.strip().lower().replace("mhz", "")
    if "." in text:
        whole, frac = text.split(".", 1)
        if not frac.isdigit() or (whole and not whole.isdigit()):
            raise ValueError(text)
        return int(whole or "0") * 1000000 + int((frac + "000000")[:6])
    value = int(text)
    return value * 1000000 if value < 2000 else value


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
    test_mode=False,
    frequency=93900000,
    gain=400,
    controls=True,
    volume=-10.0,
    display=True,
):
    supervisor.runtime.autoreload = False
    ui = RadioUI() if display else None

    def draw(*a):
        if ui:
            ui.draw(*a)

    audio = None
    keys = None
    d = None
    stream = None
    draw("CONNECTING", frequency, "looking for the USB receiver", "")
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
    radio = open_receiver(d)
    radio.initialize(frequency=frequency, sample_rate=256000, gain=gain)
    radio.hold_buffer()
    if test_mode:
        radio.set_test_mode(True)
    try:
        audio = JackAudio(volume=volume)
        state = bytearray(512)
        silence = memoryview(bytes(1024))
        total = output = 0
        gaps = missing = 0
        previous = -1
        max_dsp = 0
        dsp_total = 0
        dsp_calls = 0
        max_loop = 0
        muted = False
        button3 = None
        line = None
        input_label = (
            "USB hardware counter / transport test"
            if test_mode
            else "receiving directly from the antenna"
        )
        keys = keypad.Keys(
            (board.BUTTON1, board.BUTTON2, board.BUTTON3),
            value_when_pressed=False,
            pull=True,
        )
        draw(
            "COUNTER TEST" if test_mode else LABEL,
            frequency,
            "256 ksample/s -> 32 kHz mono",
            input_label,
        )
        gc.collect()
        radio.reset_buffer()
        stream, ring = start_stream(d, audio)
        iq = bytearray(8192)
        iqv = memoryview(iq)
        filled = 0
        start = time.monotonic()
        last_log = start
        last_ns = time.monotonic_ns()
        print(
            "LIVE_START",
            json.dumps(
                {
                    "ring_size": ring,
                    "test_mode": test_mode,
                    "frequency": frequency,
                    "sample_rate": radio.sample_rate,
                    "gain": gain,
                }
            ),
        )
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
                if test_mode:
                    previous, ng, nm = _fm_turbo.test_counter(iq, previous)
                    gaps += ng
                    missing += nm
                # One block of 4096 I/Q samples gives 512 PCM samples.
                out = audio.write_view_bytes(512)
                t = time.monotonic_ns()
                count = _fm_turbo.process(iq, out, state) // 2
                dt = time.monotonic_ns() - t
                dsp_total += dt
                dsp_calls += 1
                max_dsp = max(max_dsp, dt)
                if test_mode:
                    out[: 2 * count] = silence[: 2 * count]
                if not muted:
                    audio.commit(count)
                    output += count
                filled = 0
                audio.service()
            elif not n:
                time.sleep(0.0005)
            action = None
            event = keys.events.get()
            if event:
                if event.key_number == 2:
                    if event.pressed:
                        button3 = event.timestamp
                    elif button3 is not None:
                        action = (
                            "p"
                            if ((event.timestamp - button3) & 0x1FFFFFFF) >= 650
                            else "m"
                        )
                        button3 = None
                elif event.pressed:
                    action = "-" if event.key_number == 0 else "+"
            if supervisor.runtime.serial_bytes_available:
                # 'f 101.1' + Enter tunes directly; other characters are single-key commands.
                # Backspace edits the entry, and cancels it once it is empty.
                ch = sys.stdin.read(1)
                if line is not None:
                    if ch in "\r\n":
                        action = "f" + line
                        line = None
                    elif ch in "\x08\x7f":
                        line = line[:-1] if line else None
                    else:
                        line += ch
                    if not action and controls and ui:
                        ui.entry(None if line is None else "f" + line)
                elif ch in "fF":
                    line = ""
                    if controls and ui:
                        ui.entry("f")
                else:
                    action = ch.lower()
            if not controls:
                action = None
            if action and action[0] == "f":
                try:
                    tuned = parse_frequency(action[1:])
                    if not 87500000 <= tuned <= 108000000:
                        raise ValueError(action[1:])
                    frequency = tuned
                    action = "f"
                except ValueError:
                    print("BAD_FREQUENCY", action[1:].strip())
                    action = None
                    if ui:
                        ui.entry(None)
            if action == "m":
                stream.deinit()
                audio.stop()
                radio.hold_buffer()
                muted = not muted
                audio.clear()
                draw(
                    "LIVE FM / MUTED" if muted else LABEL,
                    frequency,
                    "256 ksample/s -> 32 kHz mono",
                    input_label,
                )
                radio.reset_buffer()
                filled = 0
                state = bytearray(512)
                previous = -1
                stream, ring = start_stream(d, audio)
                print("MUTE", muted)
            elif action in ("+", "-", "p", "f"):
                stream.deinit()
                audio.stop()
                audio.clear()
                radio.hold_buffer()
                if action == "p":
                    idx = PRESETS.index(frequency) if frequency in PRESETS else -1
                    frequency = PRESETS[(idx + 1) % len(PRESETS)]
                elif action != "f":
                    frequency += 200000 if action == "+" else -200000
                    if frequency > 107900000:
                        frequency = 88100000
                    if frequency < 88100000:
                        frequency = 107900000
                radio.tune(frequency)
                draw(
                    "LIVE FM / MUTED" if muted else LABEL,
                    frequency,
                    "256 ksample/s -> 32 kHz mono",
                    input_label,
                )
                radio.reset_buffer()
                state = bytearray(512)
                filled = 0
                previous = -1
                stream, ring = start_stream(d, audio)
                print("TUNED", frequency)
            if now - last_log >= 5:
                lost = stream.lost_packets
                if lost:
                    raise RuntimeError("USB stream lost samples")
                print(
                    "LIVE",
                    json.dumps(
                        {
                            "frequency": frequency,
                            "muted": muted,
                            "seconds": now - start,
                            "bytes": total,
                            "pcm_samples": output,
                            "ring_size": ring,
                            "dsp_max_ms": max_dsp / 1000000,
                            "loop_max_ms": max_loop / 1000000,
                            "audio": audio.stats(),
                            "lost_packets": lost,
                        }
                    ),
                )
                last_log = now
        lost = stream.lost_packets
        print(
            "RESULT",
            json.dumps(
                {
                    "test_mode": test_mode,
                    "frequency": frequency,
                    "seconds": time.monotonic() - start,
                    "bytes": total,
                    "pcm_samples": output,
                    "counter_gaps": gaps if test_mode else None,
                    "min_missing_mod256": missing if test_mode else None,
                    "dsp_max_ms": max_dsp / 1000000,
                    "dsp_mean_ms": dsp_total / max(1, dsp_calls) / 1000000,
                    "loop_max_ms": max_loop / 1000000,
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
