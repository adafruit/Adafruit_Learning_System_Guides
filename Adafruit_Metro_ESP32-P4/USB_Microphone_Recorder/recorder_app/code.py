# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""A USB microphone recorder with waveform visualizer.

Metro ESP32-P4 with a Raspberry Pi Touch Display 2, a USB microphone on the
USB host port and a microSD card.

Tap the screen to start recording and tap again to stop. The recording is
saved as a WAV file in /sd/recordings. Between recordings the waveform keeps
showing the microphone in grey; what is recorded is drawn in blue.

To see refreshed files on a computer the Metro P4 is connected to: first
eject the SD card drive, then press the sync button in the lower left of
the touch UI. The SD card drive will re-connect to the computer after a
few seconds with the latest files listed.

By default a recording is kept in RAM and written to the card after it stops,
which limits its length to about a minute. WRITE_WHILE_RECORDING = True
writes as it records instead, with no limit but with dropouts.
"""

import array
import gc
import math
import os
import struct
import time

import adafruit_gt911
import adafruit_ili9881
import adafruit_usb_host_descriptors
import audiotap
import bitmaptools
import board
import busio
import digitalio
import displayio
import framebufferio
import mipidsi
import sdioio
import storage
import supervisor
import terminalio
import usb_host
import usb_host_audio
import vectorio
from audiofilewriter import AudioFileWriter

# _audiograph.rv32imc.mpy: `import` loads it on the Metro ESP32-P4. Its source
# and build script are in turbo_source_files/audiograph.
import _audiograph

# pylint: disable=too-many-lines, too-many-locals, too-many-branches, too-many-statements
# pylint: disable=too-many-nested-blocks, attribute-defined-outside-init

CURSOR = 5  # palette index of the sweep cursor, after _audiograph's first five
WAVE_PALETTE_SIZE = 8  # _audiograph's MONITOR_WAVE and MONITOR_RMS are 6 and 7

# Recording.
SD_MOUNT = "/sd"
RECORD_DIRECTORY = SD_MOUNT + "/recordings"
SD_FREQUENCY = 40_000_000
# The computer caches the SD card's drive and doesn't see files the board
# writes. The Sync SD button unmounts the card, which makes its USB drive report
# "medium not present", so the computer drops the drive; mounting it again
# brings it back with the new files. It has to stay out long enough for the
# computer's media poll to see it (Linux polls every 2 s).
SD_EJECT_MS = 3000
# False keeps the recording in RAM until it stops, then writes it to the card:
# no dropouts from the card, but at most about a minute (see the docstring).
WRITE_WHILE_RECORDING = False
RAM_RESERVE = 2_000_000  # heap left free beside the recording buffer
SD_BLOCK = 512
SAVE_CHUNK = 128 * 1024  # bytes written to the card per write while saving
SAVE_WRITES_PER_FRAME = 2  # about 40 ms of writing per frame
STREAM_CHUNK = 64 * 1024  # bytes per write when WRITE_WHILE_RECORDING
TAP_LOCKOUT_MS = 400  # ignore a second tap this soon after the first
TOUCH_I2C_FREQUENCY = 400_000  # the board I2C bus's 100 kHz costs dropouts; 1 MHz fails
# The touch controller keeps a touch's report until it's read, so a short tap
# isn't missed between polls.
TOUCH_POLL_MS = 100

STOPPED = 0
RECORDING = 1
SAVING = 2

# True shows the dropout count in the track panel, for testing.
DEBUG_UI = False

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
# The 5" panel's pixels are small: terminalio's 6x12 font needs scale 2 or
# more to be readable, so all text is at least SMALL_TEXT.
SMALL_TEXT = 2  # 12x24 pixel characters
LARGE_TEXT = 3  # 18x36
CLOCK_TEXT = 4  # 24x48
TOOLBAR_HEIGHT = 96
RULER_Y = TOOLBAR_HEIGHT
RULER_HEIGHT = 40
TRACK_Y = RULER_Y + RULER_HEIGHT
PANEL_WIDTH = 110  # 8 characters of SMALL_TEXT
AMPLITUDE_WIDTH = 70
WAVE_X = PANEL_WIDTH + AMPLITUDE_WIDTH
WAVE_HEIGHT = SCREEN_HEIGHT - TRACK_Y - 8
CHANNEL_GAP = 6
# The Sync SD button, at the bottom of the track's control panel.
SYNC_X = 6
SYNC_WIDTH = PANEL_WIDTH - 14
SYNC_HEIGHT = 56
SYNC_Y = TRACK_Y + WAVE_HEIGHT - 6 - SYNC_HEIGHT
# Taps up to a button's height above it or right of it still count, as do taps
# between it and the screen's left and bottom edges.
SYNC_PADDING = SYNC_HEIGHT
COLUMNS_PER_SECOND = 100
PAGE_COLUMNS = SCREEN_WIDTH - WAVE_X  # 1100 columns, 11 seconds a page
# At the right edge the waveform starts again at the left.
WIPE_PAGE = False
# Blank columns kept ahead of the sweep cursor, so that the newest audio is
# always drawn next to blank space rather than the previous pass.
BLANK_AHEAD_COLUMNS = 30
ERASE_COLUMNS = 40  # old page columns wiped per refresh, about 20 ms of redraw
# Columns per arrayblit of the wipe. Background tasks, which must queue the
# microphone's next USB packet every millisecond, don't run during one call.
ERASE_BLIT_COLUMNS = 8
FRAME_MS = 33  # at most about 30 refreshes a second
# The toolbar's two lines of text, between the clock and the level meter.
TEXT_X = 470
HINT_LENGTH = 18  # characters of LARGE_TEXT
INFO_LENGTH = 28  # characters of SMALL_TEXT
METER_X = 850
METER_WIDTH = 410
METER_BAR_HEIGHT = 20  # each of two; a single channel's bar is taller
MONO_BAR_HEIGHT = 34
METER_BAR_GAP = 6
METER_DB = 60  # the meter shows -60 dB to 0 dB
PEAK_HOLD_MS = 1500
DB_PER_LOG = 20 / math.log(10)  # this build's math has no log10
SAMPLE_RATE = 48000

# Theme colors: slate grey around a darker waveform, with light text.
TOOLBAR_COLOUR = 0x535B68
RULER_COLOUR = 0x626B79
TRACK_BACKGROUND = 0x434A56
PANEL_COLOUR = 0x5C6472
TEXT_COLOUR = 0xF2F4F7
MUTED_COLOUR = 0xC2C8D1
WAVE_BACKGROUND = 0x343A44
WAVE_COLOUR = 0x34D27A  # green while recording
RMS_COLOUR = 0xA6F2C4
MONITOR_WAVE_COLOUR = 0x6C7480  # dim grey while not recording
MONITOR_RMS_COLOUR = 0x8C949F
CLIP_COLOUR = 0xFF4A4A
CURSOR_COLOUR = 0xF2F4F7
RECORD_COLOUR = 0xFF4A4A
STOPPED_COLOUR = 0xAEB5C0
SAVING_COLOUR = 0xD89418
BUTTON_COLOUR = 0x737C8A
BUTTON_BORDER = 0xA4ACB8
METER_UNLIT = 0x3E4550
METER_PEAK = 0xF2F4F7
METER_RAMP = ((0.0, 0x20B040), (0.7, 0x40D860), (0.85, 0xF0D030), (1.0, 0xFF4A4A))

FONT = terminalio.FONT
GLYPH_WIDTH, GLYPH_HEIGHT = FONT.get_bounding_box()[:2]
DIGIT_TILES = [FONT.get_glyph(ord("0") + d).tile_index for d in range(10)]


def ticks_diff(end, start):
    """end - start in ms. supervisor.ticks_ms() wraps at 2**29, 65 s after boot the first time."""
    return ((end - start + 0x10000000) & 0x1FFFFFFF) - 0x10000000


def solid(colour):
    palette = displayio.Palette(1)
    palette[0] = colour
    return palette


def rectangle(colour, x, y, width, height):
    return vectorio.Rectangle(
        pixel_shader=solid(colour), x=x, y=y, width=width, height=height
    )


def make_text(string, colour, scale, x, y, length=None):
    shader = displayio.Palette(2)
    shader.make_transparent(0)
    shader[1] = colour
    grid = displayio.TileGrid(
        FONT.bitmap,
        pixel_shader=shader,
        width=length or len(string),
        height=1,
        tile_width=GLYPH_WIDTH,
        tile_height=GLYPH_HEIGHT,
    )
    set_text(grid, string)
    group = displayio.Group(scale=scale, x=x, y=y)
    group.append(grid)
    return group, grid


def set_text(grid, string):
    for i in range(grid.width):
        tile = FONT.get_glyph(ord(string[i]) if i < len(string) else 32).tile_index
        if grid[i, 0] != tile:
            grid[i, 0] = tile


def set_digits(grid, start, value, count):
    """Show value in count digits from tile start, without allocating."""
    for i in range(count):
        tile = DIGIT_TILES[value % 10]
        value //= 10
        if grid[start + count - 1 - i, 0] != tile:
            grid[start + count - 1 - i, 0] = tile


def mix(first, second, amount):
    result = 0
    for shift in (16, 8, 0):
        a = (first >> shift) & 0xFF
        b = (second >> shift) & 0xFF
        result |= int(a + (b - a) * amount) << shift
    return result


def ramp_colour(level):
    for i in range(len(METER_RAMP) - 1):
        low, low_colour = METER_RAMP[i]
        high, high_colour = METER_RAMP[i + 1]
        if level <= high:
            return mix(low_colour, high_colour, (level - low) / (high - low))
    return METER_RAMP[-1][1]


def start_display():
    if supervisor.runtime.display is not None:
        display = supervisor.runtime.display
    else:
        bus = mipidsi.Bus(
            minimum_frequency=adafruit_ili9881.RaspberryPiTouchDisplay2.MINIMUM_BUS_FREQUENCY,
            num_lanes=2,
        )
        panel = adafruit_ili9881.RaspberryPiTouchDisplay2(bus, board.I2C())
        display = framebufferio.FramebufferDisplay(panel, rotation=90)
        supervisor.runtime.display = display
    display.auto_refresh = False
    return display


def start_microphone():
    # The Metro's USB host port isn't started by the board: power it and start it.
    power = digitalio.DigitalInOut(board.USB_HOST_POWER)
    power.switch_to_output(value=True)
    port = usb_host.Port(board.USB_HOST_DP, board.USB_HOST_DM)

    # Give a device that was plugged in at power-up time to enumerate.
    device = None
    deadline = time.monotonic() + 3
    while device is None and time.monotonic() < deadline:
        device = adafruit_usb_host_descriptors.find_microphone()
        if device is None:
            time.sleep(0.1)
    if device is None:
        raise RuntimeError("Plug a USB microphone or webcam into the USB host port")
    formats = adafruit_usb_host_descriptors.find_microphone_formats(device)
    mic_format = adafruit_usb_host_descriptors.choose_microphone_format(
        formats, sample_rate=SAMPLE_RATE
    )
    sample_rate = mic_format.nearest_rate(SAMPLE_RATE)

    device.set_configuration()
    # SET_INTERFACE to the format's alternate setting starts the stream, then
    # SET_CUR of the endpoint's sampling frequency picks the rate.
    device.ctrl_transfer(0x01, 11, mic_format.alternate, mic_format.interface, None)
    if mic_format.rate_control:
        device.ctrl_transfer(
            0x22, 0x01, 0x0100, mic_format.endpoint, sample_rate.to_bytes(3, "little")
        )
    mic = usb_host_audio.USBIn(
        device,
        mic_format.endpoint,
        sample_rate=sample_rate,
        channel_count=mic_format.channel_count,
        bit_depth=8 * mic_format.bytes_per_sample,
        samples_signed=mic_format.samples_signed,
        max_packet_size=mic_format.max_packet_size,
    )
    return mic, (power, port, device)


def mount_sd():
    """Mount the microSD card at SD_MOUNT. Returns the SDCard, or None if there is none."""
    try:
        card = sdioio.SDCard(
            clock=board.SD_CLK,
            command=board.SD_CMD,
            data=(board.SD_DATA0, board.SD_DATA1, board.SD_DATA2, board.SD_DATA3),
            frequency=SD_FREQUENCY,
        )
        storage.mount(storage.VfsFat(card), SD_MOUNT)
    except OSError as error:
        print("No SD card:", error)
        return None
    try:
        os.mkdir(RECORD_DIRECTORY)
    except OSError:
        pass  # it's there already
    return card


def eject_sd():
    """Unmount the SD card so that the computer drops its cached copy of the drive."""
    try:
        storage.umount(SD_MOUNT)
    except OSError as error:
        print("Couldn't unmount the SD card:", error)
        return False
    return True


def reinsert_sd(card):
    """Mount the SD card again after eject_sd()."""
    storage.mount(storage.VfsFat(card), SD_MOUNT)


class Touch:
    """Taps on the Touch Display 2's touch screen, read with the adafruit_gt911 library.

    The GT911 is polled: the display has no interrupt line. Each poll reads the
    controller's status over I2C, and while a finger is down the touch points
    too and a write to clear the status. The microphone's USB packets aren't
    collected during those transfers. The bus runs at TOUCH_I2C_FREQUENCY
    and is polled every TOUCH_POLL_MS.
    """

    def __init__(self, i2c, rotation):
        # rotation matches the display's, so touches come in screen coordinates.
        self.touchscreen = adafruit_gt911.GT911(i2c, rotation=rotation)
        self.x = 0  # where the last tap was, in screen coordinates
        self.y = 0
        self.down = False
        self.last_tap = None  # the time of a tap less than TAP_LOCKOUT_MS ago

    def tapped(self, now):
        """True once each time a finger touches the screen. x and y are then where."""
        # Forget the last tap once it's old, rather than comparing with it later:
        # ticks_ms() starts 65 s before it wraps, and a difference with an old
        # time wraps too.
        if (
            self.last_tap is not None
            and ticks_diff(now, self.last_tap) > TAP_LOCKOUT_MS
        ):
            self.last_tap = None
        touches = self.touchscreen.touch
        down = len(touches) > 0
        tap = down and not self.down and self.last_tap is None
        self.down = down
        if tap:
            self.last_tap = now
            self.x = touches[0]["x"]
            self.y = touches[0]["y"]
        return tap


def wav_header(rate, channels, data_bytes):
    """A 44 byte header of a 16-bit PCM WAV file."""
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_bytes,
        b"WAVE",
        b"fmt ",
        16,
        1,
        channels,
        rate,
        rate * channels * 2,
        channels * 2,
        16,
        b"data",
        data_bytes,
    )


class Recorder:
    """Keeps a recording in a RAM buffer and writes it to a WAV file on the SD card.

    The buffer is a ring of whole columns of audio. Each column has its own
    memoryview, made in advance, that the tap reads into and the waveform is
    drawn from: copying a column in viper instead took 0.2 ms, enough to
    double the dropouts, and assigning to a memoryview slice moves the rest of
    the buffer as well. The file is opened by the first write, and its header
    gets the length when it's closed.
    """

    def __init__(self, rate, channels, column_bytes):
        self.rate = rate
        self.channels = channels
        self.column_bytes = column_bytes
        self.bytes_per_second = rate * channels * 2
        self.number = 1
        for name in os.listdir(RECORD_DIRECTORY):
            if name.startswith("rec_") and name.endswith(".wav"):
                try:
                    self.number = max(self.number, int(name[4:-4]) + 1)
                except ValueError:
                    pass
        # Whole columns, and whole SD blocks so that the card's writes stay aligned.
        unit = column_bytes
        while unit % SD_BLOCK:
            unit += column_bytes
        gc.collect()
        size = (gc.mem_free() - RAM_RESERVE) // unit * unit
        self.buffer = None
        while self.buffer is None and size > 0:
            try:
                self.buffer = bytearray(size)
            except MemoryError:  # the free memory isn't all in one piece
                size = (size * 9 // 10) // unit * unit
        self.capacity = size
        self.view = memoryview(self.buffer)
        self.columns = [
            self.view[i : i + column_bytes] for i in range(0, size, column_bytes)
        ]
        self.file = None
        self.path = None
        self.start()

    @property
    def seconds(self):
        """The longest recording that fits in RAM."""
        return self.capacity // self.bytes_per_second

    def start(self):
        """Start a new recording and give it the next file name."""
        self.path = "%s/rec_%04d.wav" % (RECORD_DIRECTORY, self.number)
        self.name = self.path[len(RECORD_DIRECTORY) + 1 :]
        self.write_at = 0
        self.read_at = 0
        self.pending = 0  # bytes in the buffer, not yet written
        self.recorded = 0
        self.written = 0

    def next_column(self):
        """The buffer for the next column's samples, or None if the buffer is full."""
        size = self.column_bytes
        if self.pending + size > self.capacity:
            return None
        column = self.columns[self.write_at // size]
        self.write_at += size
        if self.write_at == self.capacity:
            self.write_at = 0
        self.pending += size
        self.recorded += size
        return column

    def write(self, limit):
        """Write up to limit bytes of the buffer to the card."""
        if self.file is None:
            self.file = open(self.path, "wb")
            self.file.write(wav_header(self.rate, self.channels, 0))
        size = min(limit, self.pending, self.capacity - self.read_at)
        if size:
            self.file.write(self.view[self.read_at : self.read_at + size])
            self.read_at += size
            if self.read_at == self.capacity:
                self.read_at = 0
            self.pending -= size
            self.written += size
        return size

    def finish(self):
        """Write the length into the header and close the file. Returns its length in seconds."""
        if self.file is None:
            return 0
        self.file.seek(0)
        self.file.write(wav_header(self.rate, self.channels, self.written))
        self.file.close()
        self.file = None
        self.number += 1
        return self.written / self.bytes_per_second

    def abandon(self):
        """Close the file after an error, keeping what was written."""
        if self.file is not None:
            try:
                self.file.close()
            except OSError:
                pass
            self.file = None
        self.number += 1
        self.pending = 0


class Meter:
    """A level meter: one bar per channel, in dB, with a peak hold."""

    def __init__(self, channels, x, y):
        self.group = displayio.Group(x=x, y=y)
        self.bar_height = height = METER_BAR_HEIGHT if channels > 1 else MONO_BAR_HEIGHT
        palette = displayio.Palette(66)
        for i in range(64):
            palette[i] = ramp_colour(i / 63)
        palette[64] = METER_UNLIT
        palette[65] = METER_PEAK
        self.lit = displayio.Bitmap(METER_WIDTH, height, 66)
        for i in range(METER_WIDTH):
            bitmaptools.fill_region(
                self.lit, i, 0, i + 1, height, i * 64 // METER_WIDTH
            )
        self.bars = []
        names = "LR" if channels == 2 else "M"
        letter_height = GLYPH_HEIGHT * SMALL_TEXT
        for ch in range(channels):
            level_bar = displayio.Bitmap(METER_WIDTH, height, 66)
            level_bar.fill(64)
            top = ch * (height + METER_BAR_GAP)
            self.group.append(
                displayio.TileGrid(level_bar, pixel_shader=palette, x=0, y=top)
            )
            label, _ = make_text(
                names[ch],
                TEXT_COLOUR,
                SMALL_TEXT,
                -GLYPH_WIDTH * SMALL_TEXT - 8,
                top + (height - letter_height) // 2,
            )
            self.group.append(label)
            self.bars.append(level_bar)
        scale_y = channels * (height + METER_BAR_GAP) - 2
        for db in range(-METER_DB, 1, 12):
            x = (db + METER_DB) * METER_WIDTH // METER_DB
            text = str(db)
            label, _ = make_text(
                text,
                MUTED_COLOUR,
                SMALL_TEXT,
                x - len(text) * GLYPH_WIDTH * SMALL_TEXT // 2,
                scale_y,
            )
            self.group.append(label)
        self.length = [0] * channels
        self.hold = [0] * channels
        self.hold_until = [supervisor.ticks_ms()] * channels

    def _restore(self, level_bar, start, end, length):
        """Redraw level_bar's columns start..end as lit up to length."""
        if start < length:
            bitmaptools.blit(
                level_bar,
                self.lit,
                start,
                0,
                x1=start,
                y1=0,
                x2=min(end, length),
                y2=self.bar_height,
            )
        if end > length:
            bitmaptools.fill_region(
                level_bar, max(start, length), 0, end, self.bar_height, 64
            )

    def update(self, ch, peak, now):
        """Show channel ch's peak sample (0 to 32768). Touches only what changed."""
        if peak > 0:
            level = (DB_PER_LOG * math.log(peak / 32768) + METER_DB) / METER_DB
            length = int(max(0.0, min(1.0, level)) * METER_WIDTH)
        else:
            length = 0
        level_bar = self.bars[ch]
        old = self.length[ch]
        hold = self.hold[ch]
        if length >= hold or ticks_diff(now, self.hold_until[ch]) > 0:
            new_hold = length
            self.hold_until[ch] = (now + PEAK_HOLD_MS) & 0x1FFFFFFF
        else:
            new_hold = hold
        if length != old:
            self._restore(level_bar, min(old, length), max(old, length), length)
        if new_hold != hold or length != old:
            if hold > 0:
                self._restore(level_bar, max(0, hold - 2), hold, length)
            if new_hold > 0:
                bitmaptools.fill_region(
                    level_bar, max(0, new_hold - 2), 0, new_hold, self.bar_height, 65
                )
        self.length[ch] = length
        self.hold[ch] = new_hold


def make_ruler():
    """The time ruler: a tick every 0.1 s, a label every second of the page."""
    group = displayio.Group(y=RULER_Y)
    group.append(rectangle(RULER_COLOUR, 0, 0, SCREEN_WIDTH, RULER_HEIGHT))
    ticks = displayio.Bitmap(SCREEN_WIDTH, RULER_HEIGHT, 2)
    shader = displayio.Palette(2)
    shader.make_transparent(0)
    shader[1] = MUTED_COLOUR
    for column in range(0, PAGE_COLUMNS, COLUMNS_PER_SECOND // 10):
        x = WAVE_X + column
        tall = column % COLUMNS_PER_SECOND == 0
        bitmaptools.fill_region(
            ticks, x, RULER_HEIGHT - (12 if tall else 5), x + 1, RULER_HEIGHT, 1
        )
    bitmaptools.fill_region(ticks, 0, RULER_HEIGHT - 1, SCREEN_WIDTH, RULER_HEIGHT, 1)
    group.append(displayio.TileGrid(ticks, pixel_shader=shader))
    labels = []
    for second in range(PAGE_COLUMNS // COLUMNS_PER_SECOND):
        label, grid = make_text(
            "",
            TEXT_COLOUR,
            SMALL_TEXT,
            WAVE_X + second * COLUMNS_PER_SECOND + 3,
            3,
            length=5,
        )
        group.append(label)
        labels.append(grid)
    return group, labels


def blank_columns(wave, blank_slice, height, start, end):
    """Blank page columns start to end, a few at a time so that background tasks keep up."""
    while start < end:
        last = min(end, start + ERASE_BLIT_COLUMNS)
        bitmaptools.arrayblit(wave, blank_slice, 0, start, height, last)
        start = last


def label_second(labels, page, index):
    seconds = page * PAGE_COLUMNS // COLUMNS_PER_SECOND + index
    set_text(
        labels[index],
        (
            "%d:%02d" % (seconds // 60, seconds % 60)
            if seconds >= 60
            else "%d.0" % seconds
        ),
    )


def label_page(labels, page):
    for index in range(len(labels)):
        label_second(labels, page, index)


def make_track(channels, band, info):
    """The track's control panel and the amplitude ruler of each channel.

    Returns the group and, with DEBUG_UI, the text grid of the dropout count."""
    group = displayio.Group(y=TRACK_Y)
    group.append(rectangle(PANEL_COLOUR, 0, 0, PANEL_WIDTH - 2, WAVE_HEIGHT))
    group.append(
        rectangle(RULER_COLOUR, PANEL_WIDTH, 0, AMPLITUDE_WIDTH - 2, WAVE_HEIGHT)
    )
    line_height = GLYPH_HEIGHT * SMALL_TEXT + 8
    title, _ = make_text("Audio 1", TEXT_COLOUR, SMALL_TEXT, 6, 10)
    group.append(title)
    y = 10 + line_height + 12
    for line in info:
        text, _ = make_text(line, MUTED_COLOUR, SMALL_TEXT, 6, y)
        group.append(text)
        y += line_height
    dropouts = None
    if DEBUG_UI:
        y += 12
        text, _ = make_text("Drops", MUTED_COLOUR, SMALL_TEXT, 6, y)
        group.append(text)
        text, dropouts = make_text("0000", TEXT_COLOUR, SMALL_TEXT, 6, y + line_height)
        group.append(text)
    ticks = displayio.Bitmap(AMPLITUDE_WIDTH, WAVE_HEIGHT, 2)
    shader = displayio.Palette(2)
    shader.make_transparent(0)
    shader[1] = MUTED_COLOUR
    half = (band - 1) // 2
    for ch in range(channels):
        base = ch * (band + CHANNEL_GAP)
        for tenth in range(-10, 11):
            y = base + half - tenth * half // 10
            length = 10 if tenth % 5 == 0 else 4
            bitmaptools.fill_region(
                ticks, AMPLITUDE_WIDTH - 2 - length, y, AMPLITUDE_WIDTH - 2, y + 1, 1
            )
        text_height = GLYPH_HEIGHT * SMALL_TEXT
        for value, text in (
            (1, "1"),
            (0.5, "0.5"),
            (0, "0"),
            (-0.5, "-0.5"),
            (-1, "-1"),
        ):
            y = base + half - int(value * half)
            y = max(base, min(base + band - text_height, y - text_height // 2))
            label, _ = make_text(
                text,
                TEXT_COLOUR,
                SMALL_TEXT,
                PANEL_WIDTH
                + AMPLITUDE_WIDTH
                - 14
                - len(text) * GLYPH_WIDTH * SMALL_TEXT,
                y,
            )
            group.append(label)
    group.append(displayio.TileGrid(ticks, pixel_shader=shader, x=PANEL_WIDTH))
    return group, dropouts


class Toolbar:
    """The record dot, the state, the recording's clock and two lines of info.

    The hint is the big line, at most HINT_LENGTH characters; the info line
    below it holds INFO_LENGTH."""

    def __init__(self, root):
        middle = TOOLBAR_HEIGHT // 2
        self.dot = solid(STOPPED_COLOUR)
        root.append(vectorio.Circle(pixel_shader=self.dot, radius=18, x=32, y=middle))
        status, self.status = make_text(
            "Stopped",
            TEXT_COLOUR,
            LARGE_TEXT,
            62,
            middle - GLYPH_HEIGHT * LARGE_TEXT // 2,
            length=9,
        )
        root.append(status)
        clock, self.clock = make_text(
            "00:00:00",
            TEXT_COLOUR,
            CLOCK_TEXT,
            248,
            middle - GLYPH_HEIGHT * CLOCK_TEXT // 2,
        )
        root.append(clock)
        hint, self.hint = make_text(
            "", TEXT_COLOUR, LARGE_TEXT, TEXT_X, 8, length=HINT_LENGTH
        )
        root.append(hint)
        info, self.info = make_text(
            "",
            MUTED_COLOUR,
            SMALL_TEXT,
            TEXT_X,
            8 + GLYPH_HEIGHT * LARGE_TEXT + 6,
            length=INFO_LENGTH,
        )
        root.append(info)
        self.dropouts = None  # the track panel's count, with DEBUG_UI

    def show(self, colour, status, hint, info=None):
        self.dot[0] = colour
        set_text(self.status, status)
        set_text(self.hint, hint)
        if info is not None:
            set_text(self.info, info)

    def set_clock(self, seconds):
        set_digits(self.clock, 0, seconds // 3600, 2)
        set_digits(self.clock, 3, seconds // 60 % 60, 2)
        set_digits(self.clock, 6, seconds % 60, 2)

    def set_dropouts(self, count):
        if self.dropouts is not None:
            set_digits(self.dropouts, 0, min(count, 9999), 4)


class SyncButton:
    """The Sync SD button. It turns SAVING_COLOUR while the card is out."""

    def __init__(self, root):
        self.fill = solid(BUTTON_COLOUR)
        root.append(rectangle(BUTTON_BORDER, SYNC_X, SYNC_Y, SYNC_WIDTH, SYNC_HEIGHT))
        root.append(
            vectorio.Rectangle(
                pixel_shader=self.fill,
                x=SYNC_X + 2,
                y=SYNC_Y + 2,
                width=SYNC_WIDTH - 4,
                height=SYNC_HEIGHT - 4,
            )
        )
        label = "Sync SD"
        text, _ = make_text(
            label,
            TEXT_COLOUR,
            SMALL_TEXT,
            SYNC_X + (SYNC_WIDTH - len(label) * GLYPH_WIDTH * SMALL_TEXT) // 2,
            SYNC_Y + (SYNC_HEIGHT - GLYPH_HEIGHT * SMALL_TEXT) // 2,
        )
        root.append(text)

    @staticmethod
    def hit(x, y):
        return x < SYNC_X + SYNC_WIDTH + SYNC_PADDING and y >= SYNC_Y - SYNC_PADDING

    def show_busy(self, busy):
        self.fill[0] = SAVING_COLOUR if busy else BUTTON_COLOUR


def minutes(seconds):
    return "%d:%02d" % (seconds // 60, seconds % 60)


def ready_info(recorder):
    """The info line while stopped: the next file and how long it can be."""
    if recorder is None:
        return "Recording is off"
    if WRITE_WHILE_RECORDING:
        return "Next: %s" % recorder.name
    return "Next: %s  %s max" % (recorder.name, minutes(recorder.seconds))


def main():
    card = mount_sd()
    display = start_display()
    try:
        # The display is set up over the board's I2C bus at 100 kHz. Only the
        # touch controller uses I2C from here on, so run the bus faster.
        board.I2C().deinit()
        touch = Touch(
            busio.I2C(board.SCL, board.SDA, frequency=TOUCH_I2C_FREQUENCY),
            display.rotation,
        )
    except (OSError, RuntimeError, ValueError) as error:
        print("No touch screen:", error)
        touch = None
    mic, _keep = start_microphone()  # _keep holds the USB host port and device
    channels = mic.channel_count
    rate = mic.sample_rate
    frames = rate // COLUMNS_PER_SECOND
    band = (WAVE_HEIGHT - CHANNEL_GAP * (channels - 1)) // channels
    band -= 1 - band % 2  # odd, so that zero is a pixel row
    height = channels * band + (channels - 1) * CHANNEL_GAP

    # Bitmap rows are screen columns, so that each column is one row and a cheap blit.
    palette = displayio.Palette(WAVE_PALETTE_SIZE)
    palette[_audiograph.BACKGROUND] = WAVE_BACKGROUND
    palette[_audiograph.WAVE] = WAVE_COLOUR
    palette[_audiograph.RMS] = RMS_COLOUR
    palette[_audiograph.CLIP] = CLIP_COLOUR
    palette[_audiograph.GAP] = TRACK_BACKGROUND
    palette[CURSOR] = CURSOR_COLOUR
    palette[_audiograph.MONITOR_WAVE] = MONITOR_WAVE_COLOUR
    palette[_audiograph.MONITOR_RMS] = MONITOR_RMS_COLOUR
    wave = displayio.Bitmap(height, PAGE_COLUMNS, WAVE_PALETTE_SIZE)
    blank = bytearray(height)
    for ch in range(1, channels):
        start = ch * (band + CHANNEL_GAP) - CHANNEL_GAP
        for y in range(start, start + CHANNEL_GAP):
            blank[y] = _audiograph.GAP
    blank_slice = blank * ERASE_BLIT_COLUMNS
    for column in range(0, PAGE_COLUMNS, ERASE_BLIT_COLUMNS):
        last = min(PAGE_COLUMNS, column + ERASE_BLIT_COLUMNS)
        bitmaptools.arrayblit(wave, blank_slice, 0, column, height, last)
    cursor = bytes([CURSOR]) * height
    grid = displayio.TileGrid(wave, pixel_shader=palette, x=WAVE_X, y=TRACK_Y)
    grid.transpose_xy = True

    root = displayio.Group()
    root.append(rectangle(TRACK_BACKGROUND, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))
    root.append(rectangle(TOOLBAR_COLOUR, 0, 0, SCREEN_WIDTH, TOOLBAR_HEIGHT))
    toolbar = Toolbar(root)
    ruler, ruler_labels = make_ruler()
    root.append(ruler)
    label_page(ruler_labels, 0)
    info = ("Stereo" if channels == 2 else "Mono", "%g kHz" % (rate / 1000), "16-bit")
    track, toolbar.dropouts = make_track(channels, band, info)
    root.append(track)
    root.append(grid)
    meter = Meter(channels, METER_X, 8 if channels == 2 else 16)
    root.append(meter.group)
    sync_button = None
    if card is not None and touch is not None:
        sync_button = SyncButton(root)

    samples = array.array("h", [0] * (frames * channels))
    tap = audiotap.Tap(capacity=0.5)
    sink = AudioFileWriter(None)
    # The rest of the heap, less a reserve, holds the recording.
    recorder = None
    if card is not None:
        recorder = Recorder(rate, channels, len(samples) * 2)
    if recorder is None:
        ready = "No SD card"
    elif touch is None:
        ready = "No touch screen"
    else:
        ready = "Tap to record"
    toolbar.show(STOPPED_COLOUR, "Stopped", ready, ready_info(recorder))
    display.root_group = root
    display.refresh(target_frames_per_second=None)

    sink.play(tap.play(mic))

    row = bytearray(height)
    # The last entry is _audiograph's monitor flag: grey while not recording.
    config = array.array("i", [frames, channels, band, CHANNEL_GAP, 1])
    peaks = array.array("i", [0] * channels)
    frame_peaks = array.array("i", [0] * channels)
    column = 0
    page = 0
    erase_from = PAGE_COLUMNS  # nothing to wipe until the first page is full
    total_columns = 0
    # Columns are counted from the start here: the first page starts out
    # blank, and from there on the gap is blanked ahead of the cursor.
    blanked = PAGE_COLUMNS
    state = STOPPED
    stop_reason = None  # set to stop the recording
    recorded_columns = 0
    shown_seconds = -1
    dropout_count = 0
    mic_drops = 0
    tap_drops = 0
    buffer_drops = (
        0  # columns that didn't fit in the buffer, when WRITE_WHILE_RECORDING
    )
    saved = []
    ejected_at = None  # when eject_sd() unmounted the card, until it's mounted again
    touch_due = False
    tapped = False
    last_touch = supervisor.ticks_ms()
    last_frame = supervisor.ticks_ms()
    started = last_frame

    def stop_message(seconds):
        return "Saved %s %s" % (recorder.name, minutes(int(seconds)))

    try:
        while True:
            drew = False
            while tap.available >= len(samples):
                audio = samples
                if state == RECORDING:
                    audio = recorder.next_column()
                    if audio is not None:
                        recorded_columns += 1
                    else:
                        audio = samples
                        if WRITE_WHILE_RECORDING:
                            buffer_drops += 1  # the card fell behind
                        elif stop_reason is None:
                            stop_reason = "RAM full"
                tap.readinto(audio)
                _audiograph.column(audio, row, config, peaks)
                bitmaptools.arrayblit(wave, row, 0, column, height, column + 1)
                for ch in range(channels):
                    if peaks[ch] > frame_peaks[ch]:
                        frame_peaks[ch] = peaks[ch]
                column += 1
                total_columns += 1
                drew = True
                if column == PAGE_COLUMNS:
                    # Refresh this page's last columns before starting the next, so that
                    # one refresh never spans the whole page.
                    display.refresh(target_frames_per_second=None)
                    column = 0
                    page += 1
                    if WIPE_PAGE:
                        erase_from = 0
                        label_page(ruler_labels, page)
                if not WIPE_PAGE:
                    bitmaptools.arrayblit(wave, cursor, 0, column, height, column + 1)
                    if column % COLUMNS_PER_SECOND == 0:
                        # The cursor reached a second's tick: label it with this page's time.
                        label_second(ruler_labels, page, column // COLUMNS_PER_SECOND)

            now = supervisor.ticks_ms()
            if ticks_diff(now, last_frame) < FRAME_MS:
                if not drew:
                    time.sleep(0.002)
                    if touch_due:
                        # Poll straight after the sleep has run the
                        # background tasks: right after other C calls, the I2C
                        # read would add to their time without USB being serviced.
                        touch_due = False
                        if touch.tapped(now):
                            tapped = True
                continue
            last_frame = now
            if touch is not None and ticks_diff(now, last_touch) >= TOUCH_POLL_MS:
                touch_due = True
                last_touch = now

            # Read both: reading a flag clears it. Only a recording's dropouts count.
            lost = False
            if mic.overflow:
                lost = True
                mic_drops += 1
            if tap.overflow:
                lost = True
                tap_drops += 1
            if lost and state == RECORDING:
                dropout_count += 1
                toolbar.set_dropouts(dropout_count)  # shown only with DEBUG_UI
            for ch in range(channels):
                meter.update(ch, frame_peaks[ch], now)
                frame_peaks[ch] = 0

            if tapped and sync_button is not None and sync_button.hit(touch.x, touch.y):
                # The Sync SD button. It does nothing while recording or saving.
                tapped = False
                if state == STOPPED and ejected_at is None and eject_sd():
                    ejected_at = now
                    sync_button.show_busy(True)
                    toolbar.show(
                        STOPPED_COLOUR,
                        "Stopped",
                        "Syncing SD card",
                        "The card is out for %d s" % (SD_EJECT_MS // 1000),
                    )

            if ejected_at is not None and (
                tapped or ticks_diff(now, ejected_at) >= SD_EJECT_MS
            ):
                # A tap to record mounts the card straight away.
                ejected_at = None
                sync_button.show_busy(False)
                try:
                    reinsert_sd(card)
                    if not tapped:
                        toolbar.show(STOPPED_COLOUR, "Stopped", ready, "SD card synced")
                except OSError as error:
                    toolbar.show(STOPPED_COLOUR, "Stopped", "SD card gone", str(error))

            if tapped:
                tapped = False
                if state == STOPPED and recorder is not None:
                    recorder.start()
                    state = RECORDING
                    config[4] = 0
                    recorded_columns = 0
                    shown_seconds = -1
                    dropout_count = 0
                    buffer_drops = 0
                    toolbar.set_dropouts(0)
                    toolbar.show(
                        RECORD_COLOUR, "Recording", "Tap to stop", recorder.name
                    )
                elif state == RECORDING and stop_reason is None:
                    stop_reason = "stopped"

            if state == RECORDING:
                if stop_reason is not None:
                    state = SAVING
                    config[4] = 1
                    toolbar.show(
                        SAVING_COLOUR,
                        "Saving",
                        (
                            "Saving to SD card"
                            if stop_reason == "stopped"
                            else "Stop: %s" % stop_reason
                        ),
                    )
                    stop_reason = None
                else:
                    seconds = recorded_columns // COLUMNS_PER_SECOND
                    if seconds != shown_seconds:
                        shown_seconds = seconds
                        toolbar.set_clock(seconds)
                        if not WRITE_WHILE_RECORDING:
                            set_text(
                                toolbar.info,
                                "%s  %s left"
                                % (recorder.name, minutes(recorder.seconds - seconds)),
                            )
                    if WRITE_WHILE_RECORDING and recorder.pending >= STREAM_CHUNK:
                        try:
                            recorder.write(STREAM_CHUNK)
                        except OSError as error:
                            recorder.abandon()
                            state = STOPPED
                            config[4] = 1
                            toolbar.show(
                                STOPPED_COLOUR, "Stopped", "Write failed", str(error)
                            )
            elif state == SAVING:
                try:
                    for _ in range(SAVE_WRITES_PER_FRAME):
                        recorder.write(SAVE_CHUNK)
                    if recorder.pending:
                        set_text(
                            toolbar.info,
                            "%s  %d%%"
                            % (
                                recorder.name,
                                100 * recorder.written // max(1, recorder.recorded),
                            ),
                        )
                    else:
                        seconds = recorder.finish()
                        saved.append(recorder.path)
                        message = stop_message(seconds)
                        print(
                            "%s, %d dropouts, %d columns lost"
                            % (message, dropout_count, buffer_drops)
                        )
                        state = STOPPED
                        toolbar.show(STOPPED_COLOUR, "Stopped", ready, message)
                        # Collect now rather than during the next recording.
                        gc.collect()
                except OSError as error:
                    recorder.abandon()
                    state = STOPPED
                    toolbar.show(STOPPED_COLOUR, "Stopped", "Save failed", str(error))

            # Extend the blank gap ahead of the cursor. Up to the page's right edge it
            # joins the new columns' refresh; past the edge it's at the left of the
            # next page, so it gets a refresh of its own rather than one spanning the
            # whole page.
            wrapped_start = wrapped_end = 0
            if not WIPE_PAGE:
                blanked = max(blanked, total_columns + 1)  # never blank drawn columns
                target = total_columns + 1 + BLANK_AHEAD_COLUMNS
                page_end = total_columns - column + PAGE_COLUMNS
                if blanked < min(target, page_end):
                    blank_columns(
                        wave,
                        blank_slice,
                        height,
                        blanked - page_end + PAGE_COLUMNS,
                        min(target, page_end) - page_end + PAGE_COLUMNS,
                    )
                    blanked = min(target, page_end)
                if blanked < target:
                    wrapped_start = blanked - page_end
                    wrapped_end = target - page_end
                    blanked = target
            display.refresh(target_frames_per_second=None)
            if wrapped_end > wrapped_start:
                blank_columns(wave, blank_slice, height, wrapped_start, wrapped_end)
                display.refresh(target_frames_per_second=None)

            # Wipe a slice of the old page ahead of the new waveform, in a refresh
            # of its own so that its area doesn't join the new columns'.
            start = max(erase_from, column + 1)
            if start < PAGE_COLUMNS:
                end = min(PAGE_COLUMNS, start + ERASE_COLUMNS)
                blank_columns(wave, blank_slice, height, start, end)
                erase_from = end
                display.refresh(target_frames_per_second=None)
    except KeyboardInterrupt:
        if state != STOPPED:
            # Save what was recorded before stopping.
            recorder.write(SAVE_CHUNK)
            while recorder.pending:
                recorder.write(SAVE_CHUNK)
            seconds = recorder.finish()
            saved.append(recorder.path)
            print("%s, %d dropouts" % (stop_message(seconds), dropout_count))
        elapsed = ticks_diff(supervisor.ticks_ms(), started) / 1000
        print(
            "Showed %.1f s of audio in %.1f s; %d recordings saved: %s"
            % (
                total_columns / COLUMNS_PER_SECOND,
                elapsed,
                len(saved),
                ", ".join(saved),
            )
        )
        print("Overflows since start: microphone %d, tap %d" % (mic_drops, tap_drops))
        raise


main()
