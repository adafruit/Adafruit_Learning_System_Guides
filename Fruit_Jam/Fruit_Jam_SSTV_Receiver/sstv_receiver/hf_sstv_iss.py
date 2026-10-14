# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""HF SSTV receiver: amateur slow-scan TV pictures on 20 m (14.230 MHz USB)
and the other SSTV calling frequencies, received, decoded and saved on the
Fruit Jam. Also receives the ISS (ARISS) SSTV events on
145.800 and 437.550 MHz FM.

If a 128x64 SH1107 OLED answers on the STEMMA QT port (I2C address 0x3C),
the pictures and status go to it (hf_sstv_display_oled.py); if not, to HDMI
(hf_sstv_display_hdmi.py). Only the module of the display used is
imported, so HDMI alone does not need adafruit_displayio_sh1107. With
neither working (or display=False) it runs without a display and still
saves the pictures.

A NESDR SMArt v5 (R820T2 tuner, HF through its direct-sampling input) on
the Fruit Jam's USB host port receives upper sideband; The 32 kHz audio
goes to the headphone jack, and _hf_sstv cuts it to 8 kHz into
a ring buffer in PSRAM while watching it for pictures:

- a VIS header (the 1.1 s of tones before each picture) gives the mode, the
  start of the picture and the sender's tuning error;
- failing that (the header lost in a fade or under another station), a
  train of line syncs at one mode's line rate starts a recording too.

The picture is drawn as it comes in: line by line on HDMI, or on the OLED
dithered to black and white (a row of the 64-row thumbnail every few
lines). When it ends, the recording is decoded on the Fruit Jam in
short steps while reception continues, which fixes slant from the sender's
clock error and removes the tuning error. Then, with the USB stream paused
briefly, it is saved to /sd/hf_sstv/ as an 8 kHz WAV and a full-size
colour BMP, with a line in log.txt, and the decoded picture replaces the
live one. If the next picture is already coming in, the save waits for it
to end.

ISS / ARISS: at and above FM_MIN (30 MHz) the receiver demodulates narrowband
FM with _sstv_dsp in place of _ham_dsp's upper sideband. Its automatic
frequency control (AFC) follows the satellite's Doppler shift
(about +-3.5 kHz on 2 m, +-11 kHz on 70 cm), the tuner gain
is fixed (FM_GAIN), and the jack plays the audio only
while the noise squelch hears a carrier. Everything after the demodulator
is the same: the VIS header or line syncs start a recording, and ISS
events send Robot 36 or PD120, both decoded here. On the ISS frequencies
(ISS_FREQUENCIES +-ISS_WINDOW) the carrier also starts a recording, since
a weak pass may never give a VIS header or a train of line syncs: it ends
when the carrier has been gone for HANG seconds, but not before the
picture's end (MIN_RECORD while its mode is unknown), recordings with less
than MIN_CARRIER seconds of carrier are dropped, and the rest are saved even
with no picture in them. Until the VIS header or the line syncs give the
mode, the recording counts as Robot 36. The presets after the HF ones are
ISS 2 m, ISS 70 cm and a NOAA weather station (an FM carrier to
test with, not SSTV).

Modes: Martin 1 and 2, Scottie 1, 2 and DX, PD90, PD120, PD180, Robot 36.
Scottie DX (270 s) is longer than the ring: only its first ~235 s are kept.

Buttons: B1/B2 tune down/up 100 Hz, B3 next preset; hold B1 to record now
(or end the recording), (OLED) B2 to switch between the picture and the
details view, and B3 to switch to the picture viewer and back. Serial
console: f<MHz>, + -, p, m (mute), d, r, g (viewer), and (OLED) v for the
view.

Picture viewer: shows the pictures saved in /sd/hf_sstv/, newest first;
B1 (or -) goes to the previous one, B2 (or +) to the next. Reception stops
while it is open (the receiver first decodes and saves any recording still
waiting), and starts again when it closes. It does not open while a
picture is coming in.
"""
# pylint: disable=wrong-import-position, global-statement, import-outside-toplevel, too-many-lines
# pylint: disable=too-many-locals, broad-except
# pylint: disable=unsupported-assignment-operation, unsubscriptable-object, too-many-nested-blocks
# pylint: disable=too-many-branches, too-many-statements, wrong-import-order, unused-variable
# Ring buffer of the 8 kHz audio. Allocated before anything else: it goes to
# PSRAM, and because it is bigger than all of internal SRAM, every later
# Python heap area is at least as big and also goes to PSRAM. That leaves
# internal SRAM for the USB bulk ring and the audio DMA buffers.
# 240 s holds the longest common mode (PD180, 188 s) with its pre-roll,
# plus time to decode it before new audio overwrites its start.
RING_SECONDS = 240
_ring = bytearray(RING_SECONDS * 16000)
import time
import gc
import os
import sys
import json
import math
import board
import busio
import displayio
import keypad
import supervisor
import usb.core
import usb_host_bulk
from ham_tuner import open_ham_receiver
from jack_audio import JackAudio
import _ham_dsp as dsp
import _hf_sstv as hf
import _sstv_dsp as fm

USB_MODE = 2  # _ham_dsp mode: upper sideband
RATE8 = 8000

# (label, dial frequency in Hz). SSTV is sent on upper sideband everywhere.
PRESETS = (
    ("20m SSTV", 14230000),
    ("20m SSTV (overflow)", 14227000),
    ("20m SSTV (overflow)", 14233000),
    ("40m SSTV", 7171000),
    ("80m SSTV (US, nights)", 3845000),
    ("15m SSTV", 21340000),
    ("10m SSTV", 28680000),
    ("ISS SSTV 2 m", 145800000),
    ("ISS SSTV 70 cm", 437550000),
    ("NOAA weather (FM test)", 162550000),
)
DEFAULT_PRESET = 0
STEP = 100  # Hz per +/- or arrow key
FM_STEP = 1000  # ... on FM

# FM (ISS) at and above FM_MIN, with _sstv_dsp: noise squelch (for the jack
# only: recordings start on the VIS header or line syncs, as on HF), tuner
# gain in tenths of a dB (None = tuner AGC) and the AFC's range around the
# dial.
FM_MIN = 30000000
FM_SQUELCH = 1500
FM_GAIN = 496
AFC_RANGE = 15000
FM_FLAG_AFC = 4

# ISS: on these frequencies (+-ISS_WINDOW, which covers tuning around them)
# a carrier starts a recording, by these rules:
ISS_FREQUENCIES = (145800000, 437550000)
ISS_WINDOW = 25000
CARRIER_START = 2  # carrier in this many readings (64 ms apart) starts a recording
HANG = 6.0  # carrier gone this long ends it (rides out fades)...
MIN_RECORD = 42.0  # ...but not before this long (a Robot 36 picture with its header
# and the pre-roll), or the picture's end once its mode is known
MIN_CARRIER = 5.0  # recordings with less carrier than this are dropped (bursts)

# The hardware centre sits above the dial so the signal is away from DC;
# tuning inside the window only moves the DSP oscillator.
CENTRE_OFFSET = 56000
WINDOW = (12000, 100000)
BLOCK = 8192  # I/Q bytes per DSP call -> 512 PCM samples (16 ms)
PCM_BLOCK = BLOCK // 8  # bytes of 32 kHz PCM per block
SAMPLES8 = PCM_BLOCK // 8  # 8 kHz samples per block (128)

PRE_ROLL = 2.0  # seconds kept before the VIS header or first sync
END_MARGIN = 3.0  # seconds kept after a picture's nominal end
SYNC_LOST = 12.0  # no line sync for this long ends a picture (HF fades
# last up to a few seconds)
MIN_SYNCS = 20  # line syncs needed to keep a recording (a VIS header
# with nothing after it is a false alarm)
MIN_FREE = 8 * 1024 * 1024  # keep this much of the card free
GC_IDLE = 120.0  # seconds between garbage collections while idle
SD_DIR = "/sd/hf_sstv"
ARROW_KEYS = {"[A": "+", "OA": "+", "[B": "-", "OB": "-", "[C": "p", "OC": "p"}
OLED_ADDRESS = 0x3C  # SH1107 OLED on the STEMMA QT port
I2C_FREQUENCY = 400000  # board.I2C() runs at 100 kHz, too slow for the OLED
# The RTL2832U's digital AGC in direct sampling (ham_tuner turns it on). It
# lifts a weak antenna's output above the 8-bit quantization floor, but with
# a strong amplified antenna (such as an active loop) it drives the I/Q
# output into clipping. Off, the level reads about 15 dB lower.
RTL_AGC = False

MODES = [
    hf.mode_info(i) for i in range(hf.N_MODES)
]  # (name, vis, w, h, lines, line_us, seconds_ms, vis_to_sync0_us)
ISS_MODE = [m[0] for m in MODES].index(
    "Robot 36"
)  # a carrier recording's mode until it is known

_i2c = None


def shared_i2c():
    """The I2C bus of the STEMMA QT port and the jack's codec, at 400 kHz.
    Created once and kept, so a restarted receiver can use it again."""
    global _i2c
    if _i2c is None:
        # A display from before a soft reload still holds the bus (and the
        # board starts with an HDMI framebuffer): release them first.
        displayio.release_displays()
        try:
            _i2c = busio.I2C(board.SCL, board.SDA, frequency=I2C_FREQUENCY)
        except ValueError:
            # Pins already in use by board.I2C(): share that (100 kHz) one.
            _i2c = board.I2C()
    return _i2c


def open_display(kind=True):
    """The display to use: the OLED if it answers at OLED_ADDRESS, else
    HDMI; None if neither works. kind 'oled' or 'hdmi' tries only that one.
    Only the module of the display used is imported."""
    ui = None
    if kind in (True, "oled"):
        i2c = shared_i2c()
        while not i2c.try_lock():
            pass
        try:
            found = OLED_ADDRESS in i2c.scan()
        finally:
            i2c.unlock()
        if found:
            try:
                from hf_sstv_display_oled import OledDisplay

                ui = OledDisplay(i2c, OLED_ADDRESS)
            except Exception as error:
                # For example adafruit_displayio_sh1107 missing from lib/.
                print("OLED_ERROR", type(error).__name__, error)
    if ui is None and kind in (True, "hdmi"):
        try:
            from hf_sstv_display_hdmi import HdmiDisplay

            ui = HdmiDisplay()
        except Exception as error:
            print("HDMI_ERROR", type(error).__name__, error)
    print("DISPLAY", ui.NAME if ui else None)
    return ui


class Status:
    """What the display shows. The receiver keeps it up to date and calls
    ui.show(status); the display module formats it."""

    def __init__(self):
        self.dial = 0
        self.label = ""
        self.demod = "USB"  # 'USB' or 'FM'
        self.level = -99  # dB
        self.muted = False
        self.record_all = False
        self.state = "listen"  # 'listen', 'rx', 'decode' or 'save'
        self.mode = None  # MODES entry being received, decoded or saved
        self.line = 0  # line coming in
        self.trigger = ""  # what started the recording: 'vis', 'sync' or 'manual'
        self.offset = None  # sender's tuning error (Hz), if known
        self.progress = 0  # decoding, percent
        self.sd = False  # card mounted
        self.saved = 0  # files saved since start
        self.pictures = 0  # pictures saved since start
        self.free_mb = 0  # free on the card (after the last save)
        self.last = (
            None  # last saved: (file name, mode name or None if no picture, lines)
        )
        self.note = None  # (long, short) text in place of the last saved


def start_stream(d, audio):
    # Audio first (its FIFO is allocated later, on first write), then the
    # largest USB ring that fits: 128 ms of buffering, or 64 ms.
    audio.start()
    for size in (65536, 32768):
        try:
            return usb_host_bulk.InStream(d, 0x81, buffer_size=size), size
        except MemoryError:
            pass
    audio.stop()
    raise MemoryError("no SRAM for the USB bulk ring")


def parse_frequency(text):
    """'14.23' (MHz) or '14230000' (Hz) -> Hz, without single-precision
    floats, which cannot hold every frequency to the hertz."""
    text = text.strip().lower().replace("mhz", "")
    if "." in text:
        whole, frac = text.split(".", 1)
        if not frac.isdigit() or (whole and not whole.isdigit()):
            raise ValueError(text)
        return int(whole or "0") * 1000000 + int((frac + "000000")[:6])
    value = int(text)
    return value * 1000000 if value < 2000 else value


def level_db(power_q16):
    """Mean channel power (Q16 from _ham_dsp.status), dB relative to a
    full-scale 8-bit sine."""
    return 4.342944819 * math.log(power_q16 / 65536 / 16256.25 + 1e-12)


def wav_header(nbytes, rate=RATE8):
    h = bytearray(44)
    h[0:4] = b"RIFF"
    h[4:8] = (36 + nbytes).to_bytes(4, "little")
    h[8:16] = b"WAVEfmt "
    h[16:20] = (16).to_bytes(4, "little")
    h[20:22] = (1).to_bytes(2, "little")  # PCM
    h[22:24] = (1).to_bytes(2, "little")  # mono
    h[24:28] = rate.to_bytes(4, "little")
    h[28:32] = (rate * 2).to_bytes(4, "little")
    h[32:34] = (2).to_bytes(2, "little")
    h[34:36] = (16).to_bytes(2, "little")
    h[36:40] = b"data"
    h[40:44] = nbytes.to_bytes(4, "little")
    return h


def bmp_header(width, height):
    """24-bit uncompressed BMP header (rows bottom-up, BGR)."""
    size = width * height * 3
    h = bytearray(54)
    h[0:2] = b"BM"
    h[2:6] = (54 + size).to_bytes(4, "little")
    h[10:14] = (54).to_bytes(4, "little")
    h[14:18] = (40).to_bytes(4, "little")
    h[18:22] = width.to_bytes(4, "little")
    h[22:26] = height.to_bytes(4, "little")
    h[26:28] = (1).to_bytes(2, "little")
    h[28:30] = (24).to_bytes(2, "little")
    h[34:38] = size.to_bytes(4, "little")
    return h


def uptime():
    """Whole seconds since the board started."""
    return time.monotonic_ns() // 1000000000


def mount_sd():
    """True if /sd is a mounted card. The supervisor mounts it at start-up;
    if that failed, /sd is only the empty folder on CIRCUITPY, and writing
    there would fill the internal flash, so try mounting the card here."""
    try:
        if os.statvfs("/sd") != os.statvfs("/"):
            return True
    except OSError:
        pass
    try:
        import sdcardio
        import storage

        spi = busio.SPI(board.SD_SCK, board.SD_MOSI, board.SD_MISO)
        storage.mount(storage.VfsFat(sdcardio.SDCard(spi, board.SD_CS)), "/sd")
        return os.statvfs("/sd") != os.statvfs("/")
    except Exception as error:
        print("SD_MOUNT_ERROR", error)
        return False


class Store:
    """Numbered WAV and BMP files and a log in SD_DIR."""

    def __init__(self, directory=SD_DIR):
        self.dir = directory
        self.ok = mount_sd()
        names = []
        if self.ok:
            try:
                try:
                    os.mkdir(directory)
                except OSError:
                    pass
                names = os.listdir(directory)
            except OSError as error:
                print("SD_ERROR", error)
                self.ok = False
        self.next = 1
        for name in names:
            if name.startswith("hfsstv_") and name.endswith(".wav"):
                try:
                    self.next = max(self.next, int(name[7:-4]) + 1)
                except ValueError:
                    pass
        self.saved = 0
        self.images = 0

    def free(self):
        try:
            s = os.statvfs(self.dir)
            return s[0] * s[3]
        except OSError:
            return 0

    def write_wav(self, ring, start, length):
        """Write ring[start:start+length] (bytes, wrapping) as the next WAV
        file; returns its path without the extension."""
        base = "%s/hfsstv_%04d" % (self.dir, self.next)
        view = memoryview(ring)
        size = len(ring)
        with open(base + ".wav", "wb") as f:
            f.write(wav_header(length))
            pos, left = start % size, length
            while left:
                n = min(left, size - pos, 32768)
                f.write(view[pos : pos + n])
                pos = (pos + n) % size
                left -= n
        self.next += 1
        self.saved += 1
        return base

    def write_bmp(self, base, bgr, width, height):
        with open(base + ".bmp", "wb") as f:
            f.write(bmp_header(width, height))
            view = memoryview(bgr)
            n = width * height * 3
            for p in range(0, n, 32768):
                f.write(view[p : min(n, p + 32768)])
        self.images += 1

    def log(self, info):
        with open(self.dir + "/log.txt", "a") as f:
            f.write(json.dumps(info) + "\n")


class Decoder:
    """Work memory for the decoder, the live preview and the BMP image, all
    allocated once (PSRAM) for the largest mode."""

    def __init__(self, ring_len):
        self.work = bytearray(
            max(hf.decode_work_bytes(i, ring_len) for i in range(hf.N_MODES))
        )
        self.preview = bytearray(
            max(hf.preview_work_bytes(i) for i in range(hf.N_MODES))
        )
        self.bgr = bytearray(max(m[2] * m[3] for m in MODES) * 3)

    def result(self):
        r = hf.decode_result(self.work)
        return {
            "mode": MODES[r[0]][0],
            "lines": r[1],
            "first_line": r[2],
            "vis": r[3],
            "period_us": r[4],
            "align": ("none", "vis", "first sync", "last sync")[r[5]],
            "syncs": r[6],
            "offset_hz": r[7],
        }


def draw_picture(ui, bgr, width, height):
    """Show the decoded picture (in bgr, the BMP buffer) on the display."""
    ui.picture_begin(width, height)
    while not ui.picture_row(bgr):
        pass
    ui.picture_show()


def load_bmp(path, bgr):
    """Read a 24-bit uncompressed BMP (as this receiver saves) into bgr in
    the decoder's layout: BGR, rows bottom-up, unpadded. Returns (width,
    height)."""
    with open(path, "rb") as f:
        head = f.read(54)
        if len(head) < 54 or head[0:2] != b"BM":
            raise ValueError("not a BMP")
        width = int.from_bytes(head[18:22], "little")
        height = int.from_bytes(head[22:26], "little")
        top_down = height >= 1 << 31
        if top_down:
            height = (1 << 32) - height
        if head[28] != 24 or head[30:34] != b"\0\0\0\0":
            raise ValueError("not a 24-bit uncompressed BMP")
        if not 0 < width * height * 3 <= len(bgr):
            raise ValueError("%d x %d is too big" % (width, height))
        f.seek(int.from_bytes(head[10:14], "little"))
        view = memoryview(bgr)
        row = width * 3
        pad = (-row) & 3
        if not pad and not top_down:
            # In pieces: one huge read from the SD card hangs and fails.
            n, p = row * height, 0
            while p < n:
                k = f.readinto(view[p : min(n, p + 32768)])
                if not k:
                    break
                p += k
        else:
            skip = bytearray(pad)
            for i in range(height):
                y = height - 1 - i if top_down else i
                f.readinto(view[y * row : (y + 1) * row])
                if pad:
                    f.readinto(skip)
    return width, height


def picture_info(directory):
    """{'hfsstv_NNNN': (mode, lines)} from the log in directory."""
    info = {}
    try:
        with open(directory + "/log.txt") as f:
            while True:
                text = f.readline()
                if not text:
                    break
                if '"file"' not in text:
                    continue
                try:
                    entry = json.loads(text)
                    decoded = entry.get("decode") or {}
                    name = entry["file"].split("/")[-1][:-4]
                    info[name] = (
                        decoded.get("mode") or entry.get("mode"),
                        decoded.get("lines", 0),
                    )
                except (ValueError, KeyError, TypeError, AttributeError):
                    pass
    except OSError:
        pass
    return info


def picture(result):
    """Whether the decoder found a picture in the recording."""
    return result is not None and (
        result["vis"] and result["syncs"] >= 5 or result["syncs"] >= MIN_SYNCS
    )


class Replay:
    """Stands in for the USB stream and the demodulator: plays a WAV file
    (16-bit mono, 32 kHz, or 8 kHz which is zero-stuffed to 32 kHz and
    filtered by the decimator) through the receiver in real time, so the
    whole chain can be tested without a signal on the air."""

    def __init__(self, path):
        self.f = open(path, "rb")
        head = self.f.read(64)
        self.rate = int.from_bytes(head[24:28], "little")
        if self.rate not in (8000, 32000) or head[34] != 16:
            raise ValueError("replay needs a 16-bit 8 or 32 kHz WAV")
        at = head.find(b"data")
        self.f.seek(at + 8 if at >= 0 else 44)
        self.small = bytearray(PCM_BLOCK // 4)
        self.next = time.monotonic_ns()
        self.lost_packets = 0
        self.done = False

    def readinto(self, buf):
        """A whole block every 16 ms, like the USB stream."""
        if time.monotonic_ns() < self.next:
            return None
        self.next += 16000000
        return len(buf)

    def fill(self, out):
        """The next 32 kHz PCM block into out (a byte view)."""
        if self.rate == 32000:
            k = self.f.readinto(out)
        else:
            k = 4 * self.f.readinto(self.small)
            s = self.small
            for i in range(0, len(s) - 1, 2):
                # x4 in level, then three zero samples
                v = s[i] | s[i + 1] << 8
                v = (v - 65536 if v & 32768 else v) * 4
                v = max(-32768, min(32767, v)) & 65535
                j = 4 * i
                out[j] = v & 255
                out[j + 1] = v >> 8
                out[j + 2] = out[j + 3] = out[j + 4] = out[j + 5] = out[j + 6] = out[
                    j + 7
                ] = 0
        if not k or k < len(out):
            self.done = True
            for i in range(k or 0, len(out)):
                out[i] = 0

    def deinit(self):
        self.f.close()


def decode_wav(path, mode=None, display=True):
    """Decode a saved recording (8 kHz WAV from this receiver, or a 32 kHz
    16-bit mono WAV, e.g. from a PC) on the Fruit Jam,
    write the BMP next to it and show it. The VIS header gives the mode,
    else a sync train does, else `mode` (an index into MODES)."""
    ring = _ring
    det = bytearray(hf.STATE_BYTES)
    with open(path, "rb") as f:
        head = f.read(64)
        rate = int.from_bytes(head[24:28], "little")
        data_at = head.find(b"data")
        f.seek(data_at + 8 if data_at >= 0 else 44)
        view = memoryview(ring)
        n = 0
        if rate == 8000:
            # In pieces: one huge read from the SD card hangs and fails.
            while n < len(ring):
                k = f.readinto(view[n : n + 65536])
                if not k:
                    break
                n += k
            n -= n & 1
            for p in range(0, n, 65536):
                hf.scan(det, ring, p, min(65536, n - p))
        elif rate == 32000:
            buf = bytearray(65536)
            while n < len(ring) - 16384:
                k = f.readinto(buf)
                if not k:
                    break
                n = hf.feed(det, memoryview(buf)[: k & ~1], ring, n)
        else:
            raise ValueError("8 or 32 kHz WAV needed, not %d Hz" % rate)
    events = []
    while True:
        e = hf.event(det)
        if e is None:
            break
        events.append(e)
    vis = [
        e for e in events if e[0] == 1 and e[1] >= 0 and (mode is None or e[1] == mode)
    ]
    sync = [e for e in events if e[0] == 2]
    vis_pos = offset = None
    if vis:
        e = max(vis, key=lambda v: v[4])
        mode, offset, vis_pos = e[1], e[3], n // 2 - e[5]
    elif sync and mode is None:
        mode = sync[0][1]
    if mode is None:
        print("DECODED", json.dumps({"file": path, "image": False, "events": events}))
        return None
    del det
    gc.collect()
    ui = open_display(display) if display else None
    if ui:
        ui.file_begin(path)
    decoder = Decoder(len(ring))
    dw, dh = ui.DECODE_SIZE if ui else (320, 240)
    image = ui.decode_image if ui else None
    t = time.monotonic_ns()
    ok = hf.decode_begin(decoder.work, ring, 0, n, mode, offset, vis_pos, dw, dh)
    p = 0
    while ok and p < 100:
        p = hf.decode_step(decoder.work, ring, image, decoder.bgr)
    info = (
        decoder.result() if ok else {"mode": MODES[mode][0], "syncs": 0, "vis": False}
    )
    info["ms"] = (time.monotonic_ns() - t) // 1000000
    info["file"] = path
    print("DECODED", json.dumps(info))
    if ok and (info["vis"] or info["syncs"] >= MIN_SYNCS):
        base = path[:-4] if path.lower().endswith(".wav") else path
        w, h = MODES[mode][2], MODES[mode][3]
        with open(base + ".bmp", "wb") as f:
            f.write(bmp_header(w, h))
            f.write(memoryview(decoder.bgr)[: w * h * 3])
        if ui:
            draw_picture(ui, decoder.bgr, w, h)
            ui.file_done(info)
    elif ui:
        ui.file_done(None)
    return info


def run(
    seconds=0,
    preset=DEFAULT_PRESET,
    frequency=None,
    volume=-10.0,
    monitor=True,
    display=True,
    record_all=False,
    commands=(),
    log_every=10,
    direct_input="Q",
    replay=None,
    rtl_agc=RTL_AGC,
    fm_gain=FM_GAIN,
    squelch=FM_SQUELCH,
):
    """Run the receiver. seconds=0 runs forever.

    frequency (Hz) overrides the preset. monitor plays the audio on the jack.
    record_all keeps recordings even when the decoder finds no picture.
    commands is a list of (seconds, command) pairs fed to the command
    handler, for unattended tests. replay: a WAV file to play through the
    receiver instead of the radio (see Replay); it stops at the file's end.
    display: True uses the OLED if one is found, else HDMI; 'oled' or
    'hdmi' only that one; False none.
    rtl_agc turns the RTL2832U's digital AGC on (see RTL_AGC).
    fm_gain and squelch: the tuner gain and noise squelch on FM (FM_MIN and
    up).
    """
    supervisor.runtime.autoreload = False
    preset_index = preset % len(PRESETS)
    label, dial = PRESETS[preset_index]
    if frequency is not None:
        dial, label = frequency, "manual"
    muted = not monitor
    commands = sorted(commands)
    ring = _ring
    ring_len = len(ring)
    ring_n = ring_len // 2  # samples
    store = Store(SD_DIR)
    decoder = Decoder(ring_len)
    det = bytearray(hf.STATE_BYTES)
    if store.ok:
        # The board has no clock: times in the log are seconds since start-up.
        try:
            store.log(
                {
                    "event": "start",
                    "uptime_s": uptime(),
                    "frequency": dial,
                    "rtl_agc": rtl_agc,
                    "fm_gain": fm_gain,
                }
            )
        except OSError as error:
            print("SD_ERROR", error)

    gc.collect()
    i2c = shared_i2c()
    ui = open_display(display) if display else None
    # Sizes the live preview and the decoder fit the picture into.
    pw, ph = (ui.W, ui.H) if ui else (320, 240)
    dw, dh = ui.DECODE_SIZE if ui else (320, 240)
    status = Status()

    audio = keys = d = stream = radio = None
    if replay is None:
        if ui:
            ui.connecting()
        for _ in range(20):
            d = usb.core.find(idVendor=0x0BDA, idProduct=0x2838)
            if d:
                break
            time.sleep(0.1)
        if not d:
            raise RuntimeError("No RTL-SDR receiver found on Fruit Jam USB")
        time.sleep(0.5)
        d.set_configuration()
        radio = open_ham_receiver(d, direct_input=direct_input)

    def clamp(f):
        if radio is None:
            return f
        return max(
            radio.min_frequency + WINDOW[1], min(radio.max_frequency - WINDOW[1], f)
        )

    def on_iss(f):
        return f >= FM_MIN and any(
            abs(f - iss_f) <= ISS_WINDOW for iss_f in ISS_FREQUENCIES
        )

    dial = clamp(dial)
    fm_band = dial >= FM_MIN
    iss = on_iss(dial)
    centre = dial + CENTRE_OFFSET
    if radio is not None:
        radio.initialize(
            frequency=centre, sample_rate=256000, gain=fm_gain if fm_band else None
        )
        radio.hold_buffer()

    def set_rtl_agc():
        # Direct sampling only; entering it (again) turns the AGC on.
        if radio is not None and radio.direct:
            radio.demod(0, 0x19, 0x25 if rtl_agc else 0x05)

    set_rtl_agc()
    state = bytearray(8192)
    fm_state = bytearray(4096)

    def configure():
        conjugate = 1 if radio is not None and radio.conjugate else 0
        if fm_band:
            fm.configure(
                fm_state, dial - centre, squelch, FM_FLAG_AFC | conjugate, AFC_RANGE
            )
        else:
            dsp.configure(state, USB_MODE, dial - centre, 0, conjugate)

    def channel_power():
        return (fm.status(fm_state) if fm_band else dsp.status(state))[0]

    def band_note():
        if radio is not None and radio.tuner_name != "R82xx" and not fm_band:
            return ("no HF: use a NESDR SMArt v5", "NO HF")
        return None

    # Positions are in 8 kHz samples of the stream since start (total); the
    # ring holds the last ring_n of them, sample s at byte 2 * (s % ring_n).
    total = 0
    wp = 0
    barrier = 0  # no pre-roll from before this point (a pause)
    rec = None  # [start, mode, trigger, vis_end or None, offset or None, end_by, peak power,
    #  lowest AFC (Hz), highest AFC (None on HF), on the ISS (kept even with
    #  no picture), carrier readings, carrier lost at (sample) or None,
    #  mode known]. trigger 'carrier': end_by is the earliest end.
    jobs = []  # recordings waiting for (or in) decoding
    job = None  # [start, length, mode, offset, vis_pos, info, stage, result] being decoded
    preview = None  # [line, sync sample] being drawn
    next_line = 0
    track = (-1, 0, 0, 0, 0, 0)
    track_total = 0
    rec_rows = None  # display rows (y0, y1) or None for each line of the picture
    job_p = 0  # decoding progress, percent
    # note: (long text, short text) in place of the last picture saved
    note = band_note()
    # FM: whether the squelch hears a carrier (the jack plays only then),
    # read every fourth block. A replay has no squelch: always played.
    carrier = replay is not None
    quarter = 0
    open_reads = 0  # readings in a row with carrier, before a carrier recording

    try:
        audio = JackAudio(volume=volume, i2c=i2c)
        keys = keypad.Keys(
            (board.BUTTON1, board.BUTTON2, board.BUTTON3),
            value_when_pressed=False,
            pull=True,
        )
        configure()
        gc.collect()
        if replay is None:
            radio.reset_buffer()
            stream, usb_ring = start_stream(d, audio)
        else:
            audio.start()
            stream, usb_ring = Replay(replay), 0
        if ui:
            ui.set_live(True)
        iq = bytearray(BLOCK)
        iqv = memoryview(iq)
        filled = 0
        max_dsp = max_feed = max_loop = max_ui = 0
        lost_total = 0
        stalls = []
        decode_steps = 0
        max_step = 0
        start = time.monotonic()
        last_log = start
        last_ui = start
        last_gc = start
        last_track = start
        pressed_at = [None, None, None]
        line = None
        esc = None
        print(
            "LIVE_START",
            json.dumps(
                {
                    "ring_size": usb_ring,
                    "dial": dial,
                    "centre": centre,
                    "tuner": radio.tuner_name if radio else "replay",
                    "direct": radio.direct if radio else None,
                    "rtl_agc": rtl_agc,
                    "fm": fm_band,
                    "record_ring_s": ring_n / RATE8,
                }
            ),
        )

        paused = 0  # pause_stream() calls not yet resumed (they nest)

        def pause_stream():
            nonlocal lost_total, paused
            paused += 1
            if paused > 1:
                return
            if replay is None:
                lost_total += stream.lost_packets
                stream.deinit()
                audio.stop()
                audio.clear()
                radio.hold_buffer()
            if ui:
                ui.set_live(False)

        def resume_stream():
            nonlocal stream, usb_ring, filled, barrier, paused
            paused -= 1
            if paused:
                return
            if replay is None:
                barrier = total
                radio.reset_buffer()
                filled = 0
                stream, usb_ring = start_stream(d, audio)
            if ui:
                ui.set_live(True)

        def sd_info():
            """The saved counts and free space (statvfs can be slow: not live)."""
            status.sd = store.ok
            status.saved = store.saved
            status.pictures = store.images
            status.free_mb = store.free() // (1024 * 1024) if store.ok else 0

        def show():
            if not ui:
                return
            status.dial = dial
            status.label = label
            status.demod = "FM" if fm_band else "USB"
            status.level = level
            status.muted = muted
            status.record_all = record_all
            status.note = note
            if rec is not None:
                status.state = "rx"
                status.mode = MODES[rec[1]]
                status.line = max(0, track[1] if track[0] == rec[1] else 0)
                status.trigger = rec[2]
                status.offset = rec[4]
            elif job is not None:
                status.state = "decode"
                status.mode = MODES[job[2]]
                status.progress = job_p
                status.trigger = job[5]["trigger"]
                status.offset = job[3]
            else:
                status.state = "listen"
                status.mode = None
            ui.show(status)

        def start_rec(mode, trigger, t_event, offset):
            """t_event: VIS end (vis) or earliest matched sync (sync)."""
            nonlocal rec, next_line, preview, rec_rows
            m = MODES[mode]
            line_n = m[5] * RATE8 // 1000000
            if ui:
                # (PD modes send two picture rows per line.)
                rows = 2 if m[0].startswith("PD") else 1
                rec_rows = [
                    ui.rows(m[2], m[3], k * rows, (k + 1) * rows) for k in range(m[4])
                ]
                ui.new_picture()
            if trigger == "vis":
                begin = t_event - int((0.91 + PRE_ROLL) * RATE8)
                end_by = (
                    t_event + (m[6] - 910) * RATE8 // 1000 + int(END_MARGIN * RATE8)
                )
            elif trigger == "carrier":
                # (t_event: when the carrier was first heard)
                begin = t_event - int(PRE_ROLL * RATE8)
            else:
                begin = t_event - 4 * line_n - int(PRE_ROLL * RATE8)
                end_by = t_event + m[4] * line_n + int(END_MARGIN * RATE8)
            begin = max(begin, total - ring_n + 8 * SAMPLES8, barrier)
            if trigger == "carrier":
                end_by = begin + int(MIN_RECORD * RATE8)
            rec = [
                begin,
                mode,
                trigger,
                t_event if trigger == "vis" else None,
                offset,
                end_by,
                0,
                None,
                None,
                iss,
                0,
                None,
                trigger != "carrier",
            ]
            next_line = 0
            preview = None
            print(
                "RECORD_START",
                json.dumps(
                    {
                        "mode": m[0],
                        "trigger": trigger,
                        "offset_hz": offset,
                        "seconds_back": (total - begin) / RATE8,
                    }
                ),
            )

        def set_mode(mode, t_event, offset, vis):
            """A carrier recording learns its mode, from the VIS header (vis:
            t_event is its end) or a train of line syncs (t_event: the
            earliest sync), and then lasts at least to the picture's end."""
            nonlocal next_line, preview, rec_rows
            m = MODES[mode]
            if vis:
                rec[3] = t_event
                rec[4] = offset
                end = t_event + (m[6] - 910) * RATE8 // 1000
            else:
                end = t_event + m[4] * (m[5] * RATE8 // 1000000)
            rec[5] = end + int(END_MARGIN * RATE8)
            rec[12] = True
            if mode != rec[1]:
                rec[1] = mode
                if ui:
                    rows = 2 if m[0].startswith("PD") else 1
                    rec_rows = [
                        ui.rows(m[2], m[3], k * rows, (k + 1) * rows)
                        for k in range(m[4])
                    ]
                    ui.new_picture()
                next_line = 0
                preview = None
            print(
                "RECORD_MODE",
                json.dumps(
                    {
                        "mode": m[0],
                        "from": "vis" if vis else "sync",
                        "offset_hz": offset,
                    }
                ),
            )

        def finish(reason):
            nonlocal rec, preview
            (
                begin,
                mode,
                trigger,
                vis_end,
                offset,
                end_by,
                peak,
                afc_lo,
                afc_hi,
                keep,
                carrier_reads,
            ) = rec[:11]
            rec = None
            preview = None
            hf.track(det, -1)
            length = total - begin
            carrier_s = round(carrier_reads * 4 * SAMPLES8 / RATE8, 1)
            if trigger == "carrier" and carrier_s < MIN_CARRIER and reason != "manual":
                print(
                    "RECORD_DROPPED",
                    json.dumps({"seconds": length / RATE8, "carrier_s": carrier_s}),
                )
                return
            info = {
                "uptime_s": uptime(),
                "seconds": round(length / RATE8, 1),
                "mode": MODES[mode][0],
                "trigger": trigger,
                "reason": reason,
                "dial": dial,
                "offset_hz": offset,
                "peak_level_db": round(level_db(peak), 1) if peak else None,
            }
            if fm_band:
                info["demod"] = "FM"
                info["afc_hz"] = [afc_lo, afc_hi]
            if keep:
                info["iss"] = True
            if trigger == "carrier":
                info["carrier_s"] = carrier_s
            print("RECORD_END", json.dumps(info))
            jobs.append(
                [
                    begin,
                    length,
                    mode,
                    offset,
                    None if vis_end is None else vis_end - begin,
                    info,
                    0,
                    None,
                ]
            )

        def save(j, result):
            """Write the WAV, BMP and log line (stream paused)."""
            nonlocal note
            begin, length, mode, offset, vis_pos, info = j[:6]
            info["decode"] = result
            image = picture(result)
            if not image and not record_all and not info.get("iss"):
                info["saved"] = False
                note = ("no picture in last recording", "no pic")
            elif not store.ok:
                note = ("not saved: no SD card", "NO SD")
            elif store.free() < 2 * length + 2 * 1024 * 1024 + MIN_FREE:
                note = ("not saved: SD card full", "SD FULL")
            else:
                t = time.monotonic_ns()
                try:
                    base = store.write_wav(ring, 2 * (begin % ring_n), 2 * length)
                    info["file"] = base + ".wav"
                    name = base.split("/")[-1]
                    if image:
                        m = MODES[mode]
                        store.write_bmp(base, decoder.bgr, m[2], m[3])
                        status.last = (name, m[0], result["lines"])
                    else:
                        status.last = (name, None, 0)
                    note = None
                    info["write_ms"] = (time.monotonic_ns() - t) // 1000000
                except OSError as error:
                    note = ("save failed: %s" % error, "SD ERR")
                    print("SAVE_ERROR", error)
                sd_info()
            try:
                if store.ok:
                    store.log(info)
            except OSError as error:
                print("SAVE_ERROR", error)
            print("SAVED", json.dumps(info))

        def complete_job(result):
            nonlocal job, last_gc
            pause_stream()
            try:
                if ui:
                    status.state = "save"
                    status.mode = MODES[job[2]]
                    ui.show(status)
                save(job, result)
                if ui and picture(result) and rec is None and job[6] != 4:
                    # The decoded picture replaces the live one (unless the
                    # next picture came in meanwhile).
                    if job[6] == 3:
                        ui.picture_show()
                    else:
                        m = MODES[job[2]]
                        draw_picture(ui, decoder.bgr, m[2], m[3])
                gc.collect()
                last_gc = time.monotonic()
            finally:
                job = None
                resume_stream()

        def set_dial(f):
            nonlocal dial, centre, barrier, fm_band, note, carrier, iss
            dial = clamp(f)
            iss = on_iss(dial)
            band = dial >= FM_MIN
            # On FM the AFC moves the DSP oscillator up to AFC_RANGE further.
            low, high = (
                (WINDOW[0] + AFC_RANGE, WINDOW[1] - AFC_RANGE) if band else WINDOW
            )
            if radio is not None and (
                band != fm_band or not low <= centre - dial <= high
            ):
                centre = dial + CENTRE_OFFSET
                pause_stream()
                try:
                    if band != fm_band:
                        # Remembered while in direct sampling, and applied
                        # when tune() leaves it.
                        radio.set_gain(fm_gain if band else None)
                    radio.tune(centre)
                    set_rtl_agc()
                finally:
                    resume_stream()
            if band != fm_band:
                fm_band = band
                note = band_note()
                carrier = replay is not None
            configure()

        def finish_jobs():
            """Decode and save every recording still waiting, now."""
            nonlocal job
            while jobs or job is not None:
                if job is None:
                    job = jobs.pop(0)
                if job[6] >= 2:
                    complete_job(job[7])
                    continue
                begin, length, mode, offset, vis_pos = job[:5]
                ok = hf.decode_begin(
                    decoder.work,
                    ring,
                    2 * (begin % ring_n),
                    2 * length,
                    mode,
                    offset,
                    vis_pos,
                    dw,
                    dh,
                )
                p = 0 if ok else 100
                image = ui.decode_image if ui and rec is None else None
                while p < 100:
                    p = hf.decode_step(decoder.work, ring, image, decoder.bgr)
                complete_job(decoder.result() if ok else None)

        def read_controls():
            """The next action from the buttons or the serial console, or
            None. Buttons: B1 down, B2 up, B3 next preset; hold B1 record now
            (or end the recording), hold B2 switch the view (OLED; on HDMI
            it tunes up), hold B3 the picture viewer. Serial mirrors them."""
            nonlocal line, esc
            action = None
            event = keys.events.get()
            if event:
                k = event.key_number
                if event.pressed:
                    pressed_at[k] = event.timestamp
                elif pressed_at[k] is not None:
                    held = ((event.timestamp - pressed_at[k]) & 0x1FFFFFFF) >= 650
                    pressed_at[k] = None
                    views = ui is not None and ui.VIEWS > 1
                    action = (
                        ("r" if held else "-"),
                        ("v" if held and views else "+"),
                        ("g" if held else "p"),
                    )[k]
            if supervisor.runtime.serial_bytes_available:
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    esc, ch = "", ""
                elif esc is not None:
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
                if not ch:
                    pass
                elif line is not None:
                    if ch in "\r\n":
                        action, line = "f" + line, None
                    elif ch in "\x08\x7f":
                        line = line[:-1] if line else None
                    else:
                        line += ch
                elif ch in "fF":
                    line = ""
                else:
                    action = ch.lower()
            return action

        def picture_viewer():
            """The saved pictures, one at a time (B1/B2 previous/next), until
            hold B3 (g) again. Reception stops meanwhile."""
            nonlocal last_gc, muted
            pause_stream()
            try:
                finish_jobs()
                names = []
                if store.ok:
                    try:
                        names = sorted(
                            n[:-4] for n in os.listdir(store.dir) if n.endswith(".bmp")
                        )
                    except OSError as error:
                        print("SD_ERROR", error)
                info = picture_info(store.dir) if names else {}
                k = len(names) - 1
                show_at = k
                print("VIEWER", json.dumps({"pictures": len(names)}))
                ui.viewer_begin()
                ui.viewer_text(
                    k, len(names), names[k] if names else None, None, 0, store.ok
                )
                while True:
                    if show_at is not None:
                        k, show_at = show_at, None
                        if names:
                            name = names[k]
                            mode, lines = info.get(name, (None, 0))
                            ui.viewer_text(k, len(names), name, "loading", 0, True)
                            t = supervisor.ticks_ms()
                            try:
                                w, h = load_bmp(
                                    "%s/%s.bmp" % (store.dir, name), decoder.bgr
                                )
                                ui.viewer_picture(decoder.bgr, w, h)
                                if not mode:
                                    mode = "%dx%d" % (w, h)
                            except (OSError, ValueError) as error:
                                print("VIEW_ERROR", name, error)
                                ui.viewer_picture(None, 0, 0)
                                mode, lines = "cannot read", 0
                            ui.viewer_text(k, len(names), name, mode, lines, True)
                            print(
                                "VIEW",
                                json.dumps(
                                    {
                                        "picture": name,
                                        "index": k,
                                        "mode": mode,
                                        "ms": (supervisor.ticks_ms() - t) & 0x1FFFFFFF,
                                    }
                                ),
                            )
                    action = read_controls()
                    if (
                        not action
                        and commands
                        and time.monotonic() - start >= commands[0][0]
                    ):
                        action = commands.pop(0)[1]
                    if action == "g":
                        break
                    if action in ("+", "-") and names:
                        show_at = (k + (1 if action == "+" else -1)) % len(names)
                    elif action == "v" and ui.VIEWS > 1:
                        ui.set_view(1 - ui.view)
                    elif action == "m":
                        muted = not muted
                    elif not action:
                        time.sleep(0.01)
                ui.viewer_end()
                gc.collect()
                last_gc = time.monotonic()
            finally:
                resume_stream()
            print("VIEWER_END")

        sd_info()

        # The loop below must not allocate in the per-block path (a garbage
        # collection scans the heap and stalls for longer than the USB ring
        # holds); gc.collect() runs while idle instead.
        views = [iqv[k:] for k in range(0, BLOCK, 64)]
        hang_n = int(HANG * RATE8)
        min_reads = int(MIN_CARRIER * RATE8) // (4 * SAMPLES8)
        tick = supervisor.ticks_ms
        last_tick = tick()
        now = start
        level = -99
        running = True
        while running:
            t = tick()
            dt = (t - last_tick) & 0x1FFFFFFF
            last_tick = t
            max_loop = max(max_loop, dt)
            if dt > 60 and len(stalls) < 8:
                stalls.append((round(now - start, 1), dt))
            n = stream.readinto(views[filled >> 6] if not filled & 63 else iqv[filled:])
            if n == 0:
                raise RuntimeError("USB stream ended")
            if n:
                filled += n
            block = filled == BLOCK
            if block:
                filled = 0
                now = time.monotonic()
                if seconds and now - start >= seconds:
                    running = False
                audio.service()
                out = audio.write_view_bytes(PCM_BLOCK // 2)
                t = tick()
                if replay is not None:
                    stream.fill(out)
                    if stream.done:
                        running = False
                elif fm_band:
                    fm.process(iq, out, fm_state)
                else:
                    dsp.process(iq, out, state)
                t2 = tick()
                wp = hf.feed(det, out, ring, wp)
                t3 = tick()
                total += SAMPLES8
                quarter = (quarter + 1) & 3
                if not quarter:
                    # (Not every block: each call builds a tuple.)
                    if fm_band and replay is None:
                        carrier = fm.status(fm_state)[2]
                    # ISS: the carrier starts and ends recordings.
                    if rec is None:
                        open_reads = open_reads + 1 if iss and carrier else 0
                        if open_reads >= CARRIER_START:
                            open_reads = 0
                            start_rec(
                                ISS_MODE,
                                "carrier",
                                total - CARRIER_START * 4 * SAMPLES8,
                                None,
                            )
                            rec[10] = CARRIER_START
                    elif rec[2] == "carrier":
                        if not iss:
                            finish("retuned")
                        else:
                            if carrier:
                                rec[10] += 1
                                rec[11] = None
                            elif rec[11] is None:
                                rec[11] = total
                            # (A burst, too short to keep, ends without waiting.)
                            if (
                                rec[11] is not None
                                and total - rec[11] >= hang_n
                                and (total >= rec[5] or rec[10] < min_reads)
                            ):
                                finish("carrier lost")
                if not muted and (carrier or not fm_band):
                    audio.commit(PCM_BLOCK // 2)
                audio.service()
                t2, t3 = (t2 - t) & 0x1FFFFFFF, (t3 - t2) & 0x1FFFFFFF
                max_dsp = max(max_dsp, t2)
                max_feed = max(max_feed, t3)
                e = hf.event(det)
                while e is not None:
                    kind, mode, code, offset, extra, age = e
                    t_event = total - age
                    print(
                        "EVENT",
                        json.dumps(
                            {
                                "kind": ("", "vis", "sync")[kind],
                                "mode": MODES[mode][0] if mode >= 0 else None,
                                "vis_code": code,
                                "offset_hz": offset,
                                "extra": extra,
                                "seconds_ago": age / RATE8,
                            }
                        ),
                    )
                    if kind == 1 and mode >= 0:
                        if rec is not None and rec[2] == "carrier" and rec[3] is None:
                            # The header of the picture this carrier brings.
                            set_mode(mode, t_event, offset, True)
                        else:
                            if rec is not None:
                                finish("new VIS")
                            start_rec(mode, "vis", t_event, offset)
                    elif kind == 2 and rec is None:
                        start_rec(mode, "sync", t_event, None)
                    elif kind == 2 and rec[2] == "carrier" and not rec[12]:
                        set_mode(mode, t_event, None, False)
                    e = hf.event(det)
                if rec is not None:
                    # (A carrier recording ends when the carrier does, above.)
                    if total >= rec[5] and rec[2] != "carrier":
                        finish("end")
                    elif total - rec[0] >= ring_n - 2 * RATE8:
                        finish("ring full")
                    elif now - last_track >= 0.25:
                        track = hf.status(det)
                        track_total = total
                        last_track = now
                        # Peak level: read here, not every block (each call
                        # builds a tuple, and the heap fills with them).
                        if fm_band:
                            power, _, _, afc_hz = fm.status(fm_state)
                            if rec[7] is None or afc_hz < rec[7]:
                                rec[7] = afc_hz
                            if rec[8] is None or afc_hz > rec[8]:
                                rec[8] = afc_hz
                        else:
                            power = dsp.status(state)[0]
                        if power > rec[6]:
                            rec[6] = power
                        if (
                            rec[2] != "carrier"
                            and track[0] == rec[1]
                            and track[3] > SYNC_LOST * RATE8
                            and total - rec[0] > SYNC_LOST * RATE8
                        ):
                            finish("syncs lost")
                        elif ui and track[0] == rec[1] and preview is None:
                            # Live picture: the next whole line not yet drawn.
                            m = MODES[rec[1]]
                            line_n = m[5] * RATE8 / 1000000
                            anchor = track_total - track[4]
                            # (floor division: a line not yet complete gives
                            # -1 here, which int() would round up to 0)
                            newest = (
                                int((total - anchor - line_n - 0.02 * RATE8) // line_n)
                                + track[1]
                            )
                            if newest >= next_line:
                                if newest - next_line > 2:
                                    next_line = newest
                                # Only lines that land on a display row
                                # are drawn (on the OLED, about one in four).
                                while (
                                    next_line < newest
                                    and 0 <= next_line < m[4]
                                    and rec_rows[next_line] is None
                                ):
                                    next_line += 1
                                if (
                                    0 <= next_line < m[4]
                                    and rec_rows[next_line] is not None
                                ):
                                    s = int(anchor + (next_line - track[1]) * line_n)
                                    if s > total - ring_n:
                                        hf.preview_begin(
                                            decoder.preview,
                                            ring,
                                            2 * (s % ring_n),
                                            rec[1],
                                            next_line,
                                            rec[4] or 0,
                                            pw,
                                            ph,
                                        )
                                        preview = next_line
                                next_line += 1
                if job is not None and total - job[0] >= ring_n - 2 * RATE8:
                    # New audio is about to overwrite the recording being
                    # decoded (or waiting to be saved): finish it now, with
                    # the stream paused, even in the middle of a recording.
                    if job[6] >= 2:
                        result = job[7]
                    else:
                        pause_stream()
                        ok = job[6] == 1 or hf.decode_begin(
                            decoder.work,
                            ring,
                            2 * (job[0] % ring_n),
                            2 * job[1],
                            job[2],
                            job[3],
                            job[4],
                            dw,
                            dh,
                        )
                        image = ui.decode_image if ui and rec is None else None
                        p = 0 if ok else 100
                        while p < 100:
                            p = hf.decode_step(decoder.work, ring, image, decoder.bgr)
                        resume_stream()
                        result = decoder.result() if ok else None
                    complete_job(result)
                if (
                    rec is None
                    and job is None
                    and not jobs
                    and now - last_gc >= GC_IDLE
                ):
                    # A collection takes ~125 ms with the ring in the heap:
                    # longer than the loop can catch up on (the demodulator
                    # and detector use ~14 of every 16 ms), so pause the
                    # stream for it.
                    pause_stream()
                    try:
                        gc.collect()
                    finally:
                        resume_stream()
                    last_gc = now
                    if total > 1 << 29:
                        # Keep the counters small ints: move them back by
                        # whole rings (the ring position is unchanged).
                        shift = (total // ring_n - 2) * ring_n
                        total -= shift
                        barrier = max(0, barrier - shift)
            elif not n:
                # Idle until the next USB data: one short piece of work.
                # The display first: an I2C refresh busy-waits, so it is
                # only sent while the USB ring is empty.
                t = tick()
                if ui and ui.service():
                    t = (tick() - t) & 0x1FFFFFFF
                    max_ui = max(max_ui, t)
                else:
                    if preview is not None and ui:
                        if hf.preview_step(decoder.preview, ring, ui.image):
                            if rec is not None and rec_rows[preview] is not None:
                                ui.image_rows(*rec_rows[preview])
                            preview = None
                    elif job is not None:
                        # Stages: 0 begin, 1 decode, 2 display rows (OLED
                        # thumbnail), 3 done, 4 done but a newer picture came
                        # in (not shown).
                        if job[6] == 0:
                            begin, length, mode, offset, vis_pos = job[:5]
                            job_p = 0
                            if hf.decode_begin(
                                decoder.work,
                                ring,
                                2 * (begin % ring_n),
                                2 * length,
                                mode,
                                offset,
                                vis_pos,
                                dw,
                                dh,
                            ):
                                job[6] = 1
                            else:
                                job[6] = 3
                        elif job[6] == 1:
                            # (HDMI: the decoder draws the picture, unless
                            # the next one is coming in.)
                            job_p = hf.decode_step(
                                decoder.work,
                                ring,
                                ui.decode_image if ui and rec is None else None,
                                decoder.bgr,
                            )
                            decode_steps += 1
                            if job_p >= 100:
                                job[7] = decoder.result()
                                if ui and rec is None and picture(job[7]):
                                    m = MODES[job[2]]
                                    ui.picture_begin(m[2], m[3])
                                    job[6] = 2
                                else:
                                    job[6] = 4 if rec is not None else 3
                        elif job[6] == 2:
                            if ui.picture_row(decoder.bgr):
                                job[6] = 3
                        elif rec is None:
                            complete_job(job[7])
                        else:
                            # Saving pauses the stream (about 1 s, all lost),
                            # so it waits for the picture coming in to end: a
                            # gap inside a recording shifts its line syncs,
                            # the receiver then loses them and splits the
                            # picture.
                            job[6] = 4
                            time.sleep(0.0005)
                    elif jobs:
                        job = jobs.pop(0)
                    else:
                        time.sleep(0.0005)
                    t = (tick() - t) & 0x1FFFFFFF
                    max_step = max(max_step, t)

            action = read_controls()
            if commands and block and now - start >= commands[0][0]:
                action = commands.pop(0)[1]
            if action:
                if action in ("+", "-"):
                    step = FM_STEP if fm_band else STEP
                    set_dial(dial + (step if action == "+" else -step))
                    label = "manual"
                elif action == "p":
                    preset_index = (preset_index + 1) % len(PRESETS)
                    label, f = PRESETS[preset_index]
                    set_dial(f)
                elif action == "m":
                    muted = not muted
                    audio.clear()
                elif action == "d":
                    record_all = not record_all
                elif action == "v":
                    # A whole-screen redraw is longer than the USB ring
                    # holds: with the stream paused, and not while a
                    # picture is coming in.
                    if ui and ui.VIEWS > 1 and rec is None:
                        pause_stream()
                        try:
                            ui.set_view(1 - ui.view)
                        finally:
                            resume_stream()
                elif action == "g":
                    # The picture viewer: not while a picture is coming in.
                    if ui and rec is None:
                        picture_viewer()
                    else:
                        print("VIEWER_BUSY" if ui else "VIEWER_NO_DISPLAY")
                        action = None
                elif action == "r":
                    # Record now (as Martin 1 unless the decoder finds the
                    # header), or end the recording.
                    if rec is None:
                        start_rec(0, "manual", total, None)
                        rec[5] = total + int((MODES[0][6] / 1000 + END_MARGIN) * RATE8)
                    else:
                        finish("manual")
                elif action[0] == "f":
                    try:
                        set_dial(parse_frequency(action[1:]))
                        label = "manual"
                    except ValueError:
                        print("BAD_FREQUENCY", action[1:])
                else:
                    action = None
                if action:
                    show()
                    print(
                        "SET",
                        json.dumps(
                            {
                                "dial": dial,
                                "centre": centre,
                                "label": label,
                                "muted": muted,
                                "record_all": record_all,
                                "fm": fm_band,
                            }
                        ),
                    )
            if block and ui and now - last_ui >= 0.5 and preview is None:
                level = int(level_db(channel_power()))
                show()
                last_ui = now
            if block and now - last_log >= log_every:
                fs = fm.status(fm_state) if fm_band else None
                power = fs[0] if fm_band else dsp.status(state)[0]
                st = hf.status(det)
                print(
                    "LIVE",
                    json.dumps(
                        {
                            "seconds": round(now - start, 1),
                            "dial": dial,
                            "level_db": round(level_db(power), 1),
                            "sync_score": st[5] / 1000,
                            "fm": (
                                {
                                    "sq_noise": round(fs[1] / 65536, 3),
                                    "carrier": fs[2],
                                    "afc_hz": fs[3],
                                }
                                if fs
                                else None
                            ),
                            "recording_s": (
                                (total - rec[0]) / RATE8 if rec is not None else None
                            ),
                            "iss": iss,
                            "track": st[:3],
                            "jobs": len(jobs) + (job is not None),
                            "saved": store.saved,
                            "dsp_max_ms": max_dsp,
                            "feed_max_ms": max_feed,
                            "step_max_ms": max_step,
                            "ui_max_ms": max_ui,
                            "loop_max_ms": max_loop,
                            "decode_steps": decode_steps,
                            "lost_packets": lost_total + stream.lost_packets,
                            "stalls": stalls,
                            "audio": audio.stats(),
                        }
                    ),
                )
                last_log = now
                max_loop = max_dsp = max_feed = max_step = max_ui = 0
                stalls = []
        if rec is not None:
            finish("stopped")
        finish_jobs()
        print(
            "RESULT",
            json.dumps(
                {
                    "seconds": time.monotonic() - start,
                    "saved": store.saved,
                    "lost_packets": lost_total + stream.lost_packets,
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
