# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
# Live 2.4 GHz waterfall: ESP-SDR on the on-board ESP32-C6, Pi Touch Display 2 on the DSI connector.
"""
import binascii
import gc
import struct
import time

import bitmaptools
import board
import busio
import digitalio
import displayio
import framebufferio
import mipidsi
import terminalio
import ulab.numpy as np

import adafruit_ili9881

CENTRE_MHZ = 2442
SPAN_MHZ = 80
BINS = 1024
FRAMES_PER_LINE = 3  # max-held into each line
# The C6's FFT runs from high to low frequency
INVERT_SPECTRUM = True
DC_MASK_BINS = 4  # bins either side of the LO replaced for display
RANGE_CODES = 60  # colour range above the floor. One code is 0.5 dB.
BACKLIGHT = 20  # 0 to 31
STALL_SECONDS = 3
LOG_SECONDS = 60

ROTATION = 90
SCREEN_WIDTH = 1280
STATUS_HEIGHT = 38
FREQ_PIXELS = 682  # 2 pixels for every 3 bins, see make_line()
GUTTER_WIDTH = 110
TIME_LINES = SCREEN_WIDTH - GUTTER_WIDTH

HEADER = 28
FRAME_SIZE = HEADER + BINS + 4
OFFSET_SEQUENCE = 4
OFFSET_DROPS = 24
CURSOR_INDEX = 255
CURSOR_COLOUR = 0xFFB000
TEXT_COLOUR = 0xE8EEF2
MUTED_COLOUR = 0x8A97A3
RAMP = (
    (0.0, 0x000000),
    (0.3, 0x0B3C5D),
    (0.6, 0x1E88B6),
    (0.85, 0x8FD8F0),
    (1.0, 0xFFFFFF),
)


class Stream:
    """Assembles CRC-checked SPC1 frames from the UART without allocating on the good path."""
    # pylint: disable=attribute-defined-outside-init
    def __init__(self, uart):
        self.uart = uart
        self.buffer = bytearray(FRAME_SIZE)
        self.view = memoryview(self.buffer)
        self.bins = np.frombuffer(
            self.buffer, dtype=np.uint8, offset=HEADER, count=BINS
        )
        self.clear()

    def clear(self):

        self.fill = 0
        self.good = 0
        self.bad = 0
        self.resync = 0
        self.lost = 0
        self.drops = 0
        self.sequence = None

    def poll(self):
        """Read what's waiting. Returns True when buffer holds a new good frame."""
        got = self.uart.readinto(self.view[self.fill :])
        if not got:
            return False
        self.fill += got
        if self.fill < FRAME_SIZE:
            return False
        self.fill = 0
        if bytes(self.view[:4]) == b"SPC1":
            expected = struct.unpack_from("<I", self.buffer, HEADER + BINS)[0]
            if binascii.crc32(self.view[: HEADER + BINS]) == expected:
                self._account()
                return True
            self.bad += 1
        self._resynchronise()
        return False

    def _account(self):
        sequence = struct.unpack_from("<I", self.buffer, OFFSET_SEQUENCE)[0]
        if self.sequence is not None:
            self.lost += (sequence - self.sequence - 1) & 0xFFFFFFFF
        self.sequence = sequence
        self.drops = struct.unpack_from("<H", self.buffer, OFFSET_DROPS)[0]
        self.good += 1

    def _resynchronise(self):
        if self.good:
            self.resync += 1
        start = self.buffer.find(b"SPC1", 1)
        if start < 0:
            start = FRAME_SIZE - 3
        tail = bytes(self.view[start:])
        self.buffer[: len(tail)] = tail
        self.fill = len(tail)


def make_text(string, colour, scale, x, y):
    font = terminalio.FONT
    width, height = font.get_bounding_box()[:2]
    shader = displayio.Palette(2)
    shader.make_transparent(0)
    shader[1] = colour
    grid = displayio.TileGrid(
        font.bitmap,
        pixel_shader=shader,
        width=len(string),
        height=1,
        tile_width=width,
        tile_height=height,
    )
    set_text(grid, string)
    group = displayio.Group(scale=scale, x=x, y=y)
    group.append(grid)
    return group, grid


def set_text(grid, string):
    font = terminalio.FONT
    for i in range(grid.width):
        tile = font.get_glyph(ord(string[i]) if i < len(string) else 32).tile_index
        if grid[i, 0] != tile:
            grid[i, 0] = tile


def mix(first, second, amount):
    result = 0
    for shift in (16, 8, 0):
        a = (first >> shift) & 0xFF
        b = (second >> shift) & 0xFF
        result |= int(a + (b - a) * amount) << shift
    return result


def make_palette(floor):
    palette = displayio.Palette(256)
    for code in range(256):
        level = max(0.0, min(1.0, (code - floor) / RANGE_CODES))
        for i in range(len(RAMP) - 1):
            low, low_colour = RAMP[i]
            high, high_colour = RAMP[i + 1]
            if level <= high:
                palette[code] = mix(
                    low_colour, high_colour, (level - low) / (high - low)
                )
                break
    palette[CURSOR_INDEX] = CURSOR_COLOUR
    return palette


def frequency_y(mhz):
    low = CENTRE_MHZ - SPAN_MHZ / 2
    return STATUS_HEIGHT + FREQ_PIXELS - 1 - int((mhz - low) * FREQ_PIXELS / SPAN_MHZ)


def make_axis():
    group = displayio.Group()
    bitmap = displayio.Bitmap(GUTTER_WIDTH, FREQ_PIXELS + STATUS_HEIGHT, 2)
    shader = displayio.Palette(2)
    shader.make_transparent(0)
    shader[1] = MUTED_COLOUR
    bitmaptools.fill_region(
        bitmap,
        GUTTER_WIDTH - 2,
        STATUS_HEIGHT,
        GUTTER_WIDTH,
        STATUS_HEIGHT + FREQ_PIXELS,
        1,
    )
    for channel in range(1, 14):
        y = frequency_y(2407 + 5 * channel)
        bitmaptools.fill_region(bitmap, GUTTER_WIDTH - 8, y, GUTTER_WIDTH, y + 1, 1)
    group.append(displayio.TileGrid(bitmap, pixel_shader=shader))
    for mhz, name in (
        (2404, "   2404"),
        (2412, " 1 2412"),
        (2437, " 6 2437"),
        (2462, "11 2462"),
        (2480, "   2480"),
    ):
        y = frequency_y(mhz)
        text, _ = make_text(name, TEXT_COLOUR, 2, 4, y - 12)
        group.append(text)
    bitmaptools.fill_region(
        bitmap, 0, STATUS_HEIGHT - 1, GUTTER_WIDTH, STATUS_HEIGHT, 1
    )
    return group


def make_line(held):
    """One line of screen pixels from a held spectrum in natural FFT order."""
    swapped = np.concatenate((held[BINS // 2 :], held[: BINS // 2]))
    swapped[BINS // 2 - DC_MASK_BINS : BINS // 2 + DC_MASK_BINS] = swapped[
        BINS // 2 - DC_MASK_BINS - 1
    ]
    # 3 bins to 2 pixels. Taking the maximum keeps a narrow signal from falling between pixels.
    line = np.zeros(FREQ_PIXELS, dtype=np.uint8)
    line[0::2] = np.maximum(swapped[0:1023:3], swapped[1:1023:3])
    line[1::2] = np.maximum(swapped[1:1023:3], swapped[2:1023:3])
    line = np.clip(line, 0, CURSOR_INDEX - 1)
    if INVERT_SPECTRUM:
        return line  # bitmap column 0 is the top of the screen
    return line[::-1].copy()


def command(uart, text, expected=b"OK", timeout=1.5):
    uart.reset_input_buffer()
    uart.write(text.encode() + b"\n")
    received = b""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        waiting = uart.in_waiting
        data = uart.read(waiting) if waiting else None
        if data:  # read() can return None even when in_waiting isn't 0
            received += data
            if expected in received:
                return received
    raise RuntimeError("no %s from %s: %s" % (expected, text, received[-60:]))


def start_c6(uart):
    reset = digitalio.DigitalInOut(board.C6_RESET)
    reset.switch_to_output(False)
    time.sleep(0.05)
    reset.deinit()
    end = time.monotonic() + 10
    while True:
        try:
            command(uart, "INFO", b"C6SDR", 0.4)
            break
        except RuntimeError:
            if time.monotonic() > end:
                raise
    command(uart, "FREQ %d" % CENTRE_MHZ)
    command(uart, "BANDWIDTH 0")
    command(uart, "DC 1")


def start_spectrum(uart, stream, milliseconds):
    uart.reset_input_buffer()
    stream.clear()
    uart.write(b"SPEC %d 1 1 0 0 %d\n" % (milliseconds, BINS))


def measure_floor(uart, stream):
    """Median level of a held line, with the panel on, so its own noise is included."""
    start_spectrum(uart, stream, 1000)
    held = None
    frames = 0
    lines = []
    end = time.monotonic() + 2
    while len(lines) < 8 and time.monotonic() < end:
        if stream.poll():
            held = stream.bins.copy() if held is None else np.maximum(held, stream.bins)
            frames += 1
            if frames == FRAMES_PER_LINE:
                lines.append(int(sorted(make_line(held))[FREQ_PIXELS // 2]))
                held = None
                frames = 0
    time.sleep(0.5)  # let the stream end before the slow first redraw
    if not lines:
        raise RuntimeError("no spectrum frames from the C6")
    return sorted(lines)[len(lines) // 2]


def main():
    # pylint: disable=too-many-locals, too-many-statements
    displayio.release_displays()
    bus = mipidsi.Bus(
        minimum_frequency=adafruit_ili9881.RaspberryPiTouchDisplay2.MINIMUM_BUS_FREQUENCY,
        num_lanes=2,
    )
    panel = adafruit_ili9881.RaspberryPiTouchDisplay2(
        bus, board.I2C(), color_depth=16, brightness=BACKLIGHT
    )
    display = framebufferio.FramebufferDisplay(
        panel, rotation=ROTATION, auto_refresh=False
    )

    uart = busio.UART(
        tx=board.C6_TX,
        rx=board.C6_RX,
        baudrate=2000000,
        receiver_buffer_size=32768,
        timeout=0,
    )
    stream = Stream(uart)
    try:
        start_c6(uart)
    except ValueError as e:
        raise ValueError("ESP32-C6 must be running esp-sdr firmware.") from e
    floor = measure_floor(uart, stream)
    print("noise floor code", floor)

    # Bitmap rows are screen columns, so that each line is one row and a cheap blit.
    bitmap = displayio.Bitmap(FREQ_PIXELS, TIME_LINES, 256)
    bitmap.fill(0)
    waterfall = displayio.TileGrid(bitmap, pixel_shader=make_palette(floor))
    waterfall.transpose_xy = True
    waterfall.x = GUTTER_WIDTH
    waterfall.y = STATUS_HEIGHT
    status, status_grid = make_text(" " * 100, TEXT_COLOUR, 2, 8, 7)
    root = displayio.Group()
    root.append(waterfall)
    root.append(make_axis())
    root.append(status)
    display.root_group = root
    display.refresh(minimum_frames_per_second=0)

    cursor = np.full(FREQ_PIXELS, CURSOR_INDEX, dtype=np.uint8)
    start_spectrum(uart, stream, 0)
    row = 0
    held = None
    frames = 0
    lines = 0
    restarts = 0
    began = time.monotonic()
    last_frame = began
    next_status = began + 2
    next_log = began + LOG_SECONDS
    window_start = began
    window_lines = 0

    while True:
        if stream.poll():
            last_frame = time.monotonic()
            held = stream.bins.copy() if held is None else np.maximum(held, stream.bins)
            frames += 1
            if frames == FRAMES_PER_LINE:
                bitmaptools.arrayblit(
                    bitmap, make_line(held), 0, row, FREQ_PIXELS, row + 1
                )
                row = (row + 1) % TIME_LINES
                if row == 0:
                    # Refresh before the cursor wraps to row 0. Otherwise the dirty area spans every
                    # row, and the 0.5 s full redraw overflows the UART buffer and loses ~26 frames.
                    display.refresh(minimum_frames_per_second=0)
                bitmaptools.arrayblit(bitmap, cursor, 0, row, FREQ_PIXELS, row + 1)
                display.refresh(minimum_frames_per_second=0)
                held = None
                frames = 0
                lines += 1
                window_lines += 1
            continue

        now = time.monotonic()
        if now - last_frame > STALL_SECONDS:
            restarts += 1
            print("stalled, restarting the C6:", restarts)
            start_c6(uart)
            start_spectrum(uart, stream, 0)
            last_frame = time.monotonic()
        if now >= next_status:
            rate = window_lines / (now - window_start)
            window_start = now
            window_lines = 0
            next_status = now + 2
            set_text(
                status_grid,
                "%d MHz  %d lines/s  frames %d  crc %d  resync %d  lost %d  drops %d  restarts %d"
                % (
                    CENTRE_MHZ,
                    round(rate),
                    stream.good,
                    stream.bad,
                    stream.resync,
                    stream.lost,
                    stream.drops,
                    restarts,
                ),
            )
            display.refresh(minimum_frames_per_second=0)
        if now >= next_log:
            next_log = now + LOG_SECONDS
            print(
                "t %d lines %d frames %d crc %d resync %d lost %d drops %d restarts %d mem %d"
                % (
                    now - began,
                    lines,
                    stream.good,
                    stream.bad,
                    stream.resync,
                    stream.lost,
                    stream.drops,
                    restarts,
                    gc.mem_free(),
                )
            )


if __name__ == "__main__":
    main()
