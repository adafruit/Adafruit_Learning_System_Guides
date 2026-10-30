# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""APRS receiver: listens to an APRS frequency (144.390 MHz in North
America) on the Fruit Jam or the Metro ESP32-P4 with a NESDR SMArt v5
and decodes the packets on the board itself.

The radio's FM audio (_ham_dsp NFM, no squelch) goes through the APRS
decoder (_aprs: Bell 202 AFSK, 1200 baud, several slicers; AX.25 frames
with a good FCS come out) and, while a signal is there, to the jack.
Packets are decoded by aprs_parse, printed on the serial console
('APRS {json}' lines), shown on the screen (aprs_ui: the stations on a
map, or lines of text; DVI via picodvi on the Fruit Jam, the TFT shield
on the Metro ESP32-P4) and appended to /sd/aprs/aprs.txt
("2026-10-18 20:31:05 UTC: SRC>DST,PATH:info", one per packet).

The radio is read through sdr_usb: usb_host_bulk's ring on the Fruit
Jam; on the Metro ESP32-P4's high-speed USB host, blocking reads with
one piece of the other work between them. The Metro has no headphone
jack and no B1-B3 buttons: there the receiver only decodes, and the
serial console is the keyboard.

Times are UTC from the ESP32-C6's clock, which nina-fw sets by SNTP when
the board is on Wi-Fi (CIRCUITPY_WIFI_SSID / _PASSWORD in settings.toml,
as for web workflow). On boards with the wifi module (the Metro
ESP32-P4) the receiver asks an NTP server itself. Without either the log
shows seconds since start-up.

Buttons (Fruit Jam): B1 previous preset, B2 mute, B3 next preset; held
down (map): B1 zoom out, B2 fit the stations on the map, B3 zoom in.
Serial console: , / . (or p / n) previous / next preset, 1-9 go to
preset 1-9 (PRESETS[0] .. [8]), x mute, l (text screen) or c alone
(then Enter) list presets, c<number> go to a preset, f<frequency> tune
anywhere ('f144.39', 'f144390' kHz, 'f 144390000' Hz: see
parse_frequency; the display shows it as it is typed, Backspace edits),
[ ] tune 5 kHz, # status, ? help (a page on the screen: the map's
colours, the keys; ? or Esc closes it), h list the stations heard, u save
the last RING_SECONDS of audio as /sd/aprs/audio_NNNN.wav (32 kHz, for
the decoder tests), v save the screen as /sd/aprs/screen_NNNN.bmp (not
on the TFT: its pixels cannot be read back); map:
i or + / o or - zoom in / out, the arrow keys or w a s d move it, r fit
the stations on it, k / l select the next / previous station on the
map, Esc deselect it, z clear the map (asks: y forgets every station, n
keeps them). Esc on its own also cancels an f / c command being typed.
The display gets the keys it uses first.

decode_wav(path) decodes a saved recording (32 kHz 16-bit mono WAV).

replay() plays the log back onto the screen instead of listening (no
radio): replay(start='19:36') from the first packet at or after 19:36
UTC (or '2026-10-24 19:36:00', or a line number: start=120), to end=
(the same forms) or the end of the log, at speed= times real time. Gaps
of more than MAX_GAP seconds in the log are cut short; the map's stations
still age (and fall off) by the log's time.
"""
# pylint: disable=wrong-import-order, wrong-import-position
import _aprs
import _ham_dsp as dsp
# The DSP's buffers (see aprs_buffers.py: code.py imports it first, so that
# they are in internal SRAM).
from aprs_buffers import (BLOCK, dsp_state as _dsp_state, aprs_state as _aprs_state,
                          iq as _iq)
# Then the big buffer: it goes to PSRAM, and because it is bigger than
# internal SRAM, later Python heap areas go there too. That leaves internal
# SRAM for the USB bulk ring and the audio DMA buffers. It is a ring of the
# radio's 32 kHz audio, for saving ('u').
RING_SECONDS = 20
_ring = bytearray(RING_SECONDS * 64000)
import time
import gc
import os
import sys
import json
import math
import struct
import board
import busio
import displayio
import keypad
import supervisor
from ham_tuner import open_ham_receiver
import sdr_usb
try:
    from jack_audio import JackAudio
except ImportError:          # (no adafruit_tlv320: the Metro ESP32-P4 has no jack)
    JackAudio = None
import aprs_parse
from aprs_ui import Status, open_display, packet_row

# pylint: disable=too-many-lines, global-statement, import-outside-toplevel, broad-except
# pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-nested-blocks
# pylint: disable=no-self-use

NFM = 0                      # _ham_dsp mode
RATE32 = 32000

# (label, FM channel in Hz).
PRESETS = (
    ('APRS NA', 144390000),      # North America
    ('ISS APRS', 145825000),     # ISS and satellite digipeaters (+-3.5 kHz Doppler)
    ('APRS EU', 144800000),      # Europe, Africa
    ('APRS AU', 145175000),      # Australia
    ('APRS NZ', 144575000),      # New Zealand
    ('APRS JP', 144640000),      # Japan
)
DEFAULT_PRESET = 0
STEP = 5000                  # Hz per [ / ]

# (lat, lon) in degrees: show distance and direction instead of positions
HOME = None
DISPLAY = 'map'              # 'map', 'text' or False (see aprs_ui)
LONG_PRESS_MS = 600          # buttons held this long: the display's LONG_PRESS actions
# seconds between the display's paused steps (map tile downloads)
UI_PAUSE_EVERY = 2.0
# jack: play while _ham_dsp's noise (Q16) is below this (1.0 = its FM_SQUELCH 1000)
SQUELCH = 65536
# without a USB ring (sdr_usb's blocking reads): the other work waits this
# long at most while a signal is there (squelch open)
HOLD_MS = 2000
# the same packet again (another digipeater's copy) within this: not shown again
REPEAT_SECONDS = 30
# seconds between garbage collections, done while no packet is coming in
GC_EVERY = 30.0
LOG_EVERY = 60               # seconds between LIVE lines
UI_EVERY = 1.0               # seconds between status updates in a replay
MAX_GAP = 60                 # seconds: longer gaps in the log are cut to 1 s in a replay

VHF_GAIN = 496               # tuner gain, tenths of a dB
# The hardware centre sits above the channel so the signal is away from DC;
# tuning inside the window only moves the DSP oscillator.
CENTRE_OFFSET = 56000
WINDOW = (12000, 100000)
PCM_BLOCK = BLOCK // 8       # bytes of 32 kHz PCM per block
SAMPLES = PCM_BLOCK // 2     # 32 kHz samples per block

SD_DIR = '/sd/aprs'
MIN_FREE = 8 * 1024 * 1024
NTP_SERVER = 'pool.ntp.org'  # (boards with the wifi module)
# Esc with nothing after it for this long: the Esc key (not an arrow key)
ESC_MS = 30
ARROW_KEYS = {'[A': 'up', 'OA': 'up', '[B': 'down', 'OB': 'down', '[C': 'right', 'OC': 'right',
              '[D': 'left', 'OD': 'left'}   # (the map's)
I2C_FREQUENCY = 400000
_i2c = None


def shared_i2c():
    """The I2C bus of the STEMMA QT port and the jack's codec, at 400 kHz.
    Created once and kept, so a restarted receiver can use it again."""
    global _i2c
    if _i2c is None:
        displayio.release_displays()
        try:
            _i2c = busio.I2C(board.SCL, board.SDA, frequency=I2C_FREQUENCY)
        except ValueError:
            _i2c = board.I2C()
    return _i2c


# ------------------------------------------------------------------ time

def civil(day_number):
    """Days since 1970-01-01 -> (year, month, day)."""
    z = day_number + 719468
    era = z // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + 3 if mp < 10 else mp - 9
    return yoe + era * 400 + (1 if m <= 2 else 0), m, d


def days(y, m, d):
    """(year, month, day) -> days since 1970-01-01 (civil()'s inverse)."""
    y -= m <= 2
    era = y // 400
    yoe = y - era * 400
    doy = (153 * (m - 3 if m > 2 else m + 9) + 2) // 5 + d - 1
    return era * 146097 + yoe * 365 + yoe // 4 - yoe // 100 + doy - 719468


class Clock:
    """UTC as time.monotonic_ns() + offset, from the ESP32-C6's clock
    (nina-fw's GET_TIME, set by SNTP), or from an NTP server on boards
    with the wifi module."""

    def __init__(self):
        self.offset_ns = None
        self.source = 'NO CLOCK'

    @staticmethod
    def _esp_time():
        try:
            import _airlift
        except ImportError:
            return Clock._ntp_time()
        if not _airlift.active():
            raise RuntimeError('no Wi-Fi: set CIRCUITPY_WIFI_SSID/PASSWORD in settings.toml')
        r = _airlift.transact(0x3B)[0]
        return struct.unpack('<q' if len(r) == 8 else '<i', r)[0]

    @staticmethod
    def _ntp_time():
        """Seconds since 1970 from NTP_SERVER (one SNTP request)."""
        if not os.getenv('CIRCUITPY_WIFI_SSID'):
            # (and leave wifi alone: on the Metro ESP32-P4 the board crashes
            # at the next soft reset once wifi has been imported)
            raise RuntimeError('no Wi-Fi: set CIRCUITPY_WIFI_SSID/PASSWORD in settings.toml')
        import wifi
        import socketpool
        if not wifi.radio.connected:
            raise RuntimeError('no Wi-Fi: set CIRCUITPY_WIFI_SSID/PASSWORD in settings.toml')
        pool = socketpool.SocketPool(wifi.radio)
        address = pool.getaddrinfo(NTP_SERVER, 123)[0][4]
        packet = bytearray(48)
        packet[0] = 0x1B         # version 3, client
        with pool.socket(pool.AF_INET, pool.SOCK_DGRAM) as s:
            s.settimeout(2)
            s.sendto(packet, address)
            s.recv_into(packet)
        return struct.unpack_from('>I', packet, 40)[0] - 2208988800   # (from 1900)

    def sync(self, wait=10.0):
        """Read UTC from the ESP32-C6 or NTP (waiting up to `wait` s for
        it to have the time). Returns True when set. To the second is
        plenty here."""
        end = time.monotonic() + wait
        while True:
            try:
                now = self._esp_time()
                if now > 1700000000:
                    break
                problem = 'its clock is not set yet'
            except Exception as error:
                problem = '%s %s' % (type(error).__name__, error)
            if time.monotonic() > end:
                print('CLOCK_ERROR', problem)
                return False
            time.sleep(0.5)
        self.offset_ns = now * 1000000000 - time.monotonic_ns()
        self.source = 'NTP'
        print('CLOCK', json.dumps({'utc': now}))
        return True

    def utc(self):
        """Seconds since 1970, or None if the clock was never set."""
        if self.offset_ns is None:
            return None
        return (time.monotonic_ns() + self.offset_ns) // 1000000000

    def stamp(self):
        """'2026-10-18 20:31:05 UTC', or '+1234 s' (since start-up)."""
        t = self.utc()
        if t is None:
            return '+%d s' % (time.monotonic_ns() // 1000000000)
        day, s = divmod(t, 86400)
        y, m, d = civil(day)
        return '%04d-%02d-%02d %02d:%02d:%02d UTC' % (y, m, d, s // 3600, s // 60 % 60, s % 60)

    def hhmm(self):
        t = self.utc()
        if t is None:
            t = time.monotonic_ns() // 1000000000
        return '%02d:%02d' % (t // 3600 % 24, t // 60 % 60)


# ----------------------------------------------------------- audio, radio

class NoAudio:
    """Stands in for JackAudio when the jack's DAC does not start (the
    receiver decodes and logs just the same)."""

    def __init__(self):
        self._pcm = memoryview(bytearray(PCM_BLOCK))

    def write_view_bytes(self, count):
        return self._pcm[:2 * count]

    def start(self):
        pass

    stop = clear = service = deinit = start

    def commit(self, count):
        pass

    def stats(self):
        return None


def open_audio(volume, i2c):
    """The headphone jack, or NoAudio if the board has none (the Metro
    ESP32-P4) or its DAC does not answer."""
    if JackAudio is None or i2c is None or not hasattr(board, 'I2S_MCLK'):
        return NoAudio()
    try:
        return JackAudio(volume=volume, i2c=i2c)
    except Exception as error:
        print('AUDIO_ERROR', type(error).__name__, error, '(no jack audio)')
        return NoAudio()


def start_stream(d, audio, rate):
    # Audio first (its FIFO is allocated later, on first write), then the
    # stream: the largest USB ring that fits, or blocking reads (sdr_usb).
    audio.start()
    try:
        return sdr_usb.open_stream(d, rate)
    except MemoryError:
        audio.stop()
        raise


def open_radio():
    """The NESDR on the USB host port, configured."""
    d = sdr_usb.find_device()
    return d, open_ham_receiver(sdr_usb.control(d), max_packet=sdr_usb.max_packet(d))


def parse_frequency(text):
    """A typed frequency -> Hz, without single-precision floats, which
    cannot hold every frequency to the hertz: '144.39' or '144.39 MHz',
    '144390' or '144390khz', '144390000' or '144390000hz'. Without a unit
    the whole part says which: MHz below 1000, kHz below 1000000, else Hz."""
    text = text.strip().lower().replace(' ', '')
    scale = None
    for unit, factor in (('mhz', 1000000), ('khz', 1000), ('hz', 1)):
        if text.endswith(unit):
            text, scale = text[:-len(unit)], factor
            break
    whole, frac = text.split('.', 1) if '.' in text else (text, '')
    if not (whole + frac).isdigit():
        raise ValueError(text)
    value = int(whole or '0')
    if scale is None:
        scale = 1000000 if value < 1000 else 1000 if value < 1000000 else 1
    digits = len(str(scale)) - 1
    return value * scale + (int((frac + '000000')[:digits]) if frac and digits else 0)


def level_db(power_q16):
    """Mean channel power (Q16 from _ham_dsp.status), dB relative to a
    full-scale 8-bit sine."""
    return 4.342944819 * math.log(power_q16 / 65536 / 16256.25 + 1e-12)


def memory_place(obj):
    """'SRAM' or 'PSRAM': where a buffer's data is (functions: their object)."""
    try:
        a = _aprs.address(obj)
    except TypeError:
        a = id(obj)
    if 0x20000000 <= a < 0x20100000:
        return 'SRAM'
    return 'PSRAM' if 0x11000000 <= a < 0x12000000 else hex(a)


def format_mhz(hz):
    return '%d.%06d' % (hz // 1000000, hz % 1000000)


def wav_header(nbytes, rate=RATE32):
    h = bytearray(44)
    h[0:4] = b'RIFF'
    h[4:8] = (36 + nbytes).to_bytes(4, 'little')
    h[8:16] = b'WAVEfmt '
    h[16:20] = (16).to_bytes(4, 'little')
    h[20:22] = (1).to_bytes(2, 'little')            # PCM
    h[22:24] = (1).to_bytes(2, 'little')            # mono
    h[24:28] = rate.to_bytes(4, 'little')
    h[28:32] = (rate * 2).to_bytes(4, 'little')
    h[32:34] = (2).to_bytes(2, 'little')
    h[34:36] = (16).to_bytes(2, 'little')
    h[36:40] = b'data'
    h[40:44] = nbytes.to_bytes(4, 'little')
    return h


def sd_card():
    """The board's SD card: the Fruit Jam's (on its own SPI bus), the Metro
    ESP32-P4's 4-bit SDIO slot, else the TFT shield's (aprs_tft)."""
    if hasattr(board, 'SD_SCK'):
        import sdcardio
        return sdcardio.SDCard(busio.SPI(board.SD_SCK, board.SD_MOSI, board.SD_MISO), board.SD_CS)
    if hasattr(board, 'SD_CLK'):
        import sdioio
        try:
            return sdioio.SDCard(clock=board.SD_CLK, command=board.SD_CMD,
                                 data=[board.SD_DATA0, board.SD_DATA1,
                                       board.SD_DATA2, board.SD_DATA3],
                                 frequency=25000000)
        except Exception as error:
            print('SD_SLOT', type(error).__name__, error, '(empty?), trying the TFT shield')
    import aprs_tft
    return aprs_tft.sd_card()


def mount_sd():
    """True if /sd is a mounted card. The supervisor mounts it at start-up;
    if that failed, /sd is only the empty folder on CIRCUITPY, and writing
    there would fill the internal flash, so try mounting the card here."""
    try:
        if os.statvfs('/sd') != os.statvfs('/'):
            return True
    except OSError:
        pass
    try:
        import storage
        storage.mount(storage.VfsFat(sd_card()), '/sd')
        return os.statvfs('/sd') != os.statvfs('/')
    except Exception as error:
        print('SD_MOUNT_ERROR', error)
        return False


class Store:
    """aprs.txt (one packet per line) and saved audio in SD_DIR."""

    def __init__(self, directory=SD_DIR):
        self.dir = directory
        self.ok = mount_sd()
        if self.ok:
            try:
                os.mkdir(directory)
            except OSError:
                pass
            try:
                os.listdir(directory)
            except OSError as error:
                print('SD_ERROR', error)
                self.ok = False
        self.logged = 0
        self.wav = None              # [file, ring position, bytes left] while audio is being saved

    def free(self):
        try:
            s = os.statvfs(self.dir)
            return s[0] * s[3]
        except OSError:
            return 0

    def log(self, lines, name='aprs.txt'):
        with open(self.dir + '/' + name, 'a') as f:
            for line in lines:
                f.write(line)
                f.write('\n')
        self.logged += len(lines)

    def next_name(self, prefix, suffix):
        """The path for the next numbered file (prefix NNNN suffix)."""
        names = [n for n in os.listdir(self.dir) if n.startswith(prefix) and n.endswith(suffix)]
        k = len(prefix)
        return '%s/%s%04d%s' % (self.dir, prefix, max(
            [int(n[k:k + 4]) for n in names if n[k:k + 4].isdigit()] or [-1]) + 1, suffix)

    def save_begin(self, ring_pos, nbytes):
        """Start saving nbytes of the ring from ring_pos; the file name, or None."""
        if self.wav or self.free() < nbytes + MIN_FREE:
            return None
        names = [n for n in os.listdir(self.dir) if n.startswith('audio_') and n.endswith('.wav')]
        numbers = [int(n[6:10]) for n in names if n[6:10].isdigit()]
        name = 'audio_%04d.wav' % (max(numbers or [-1]) + 1)
        f = open('%s/%s' % (self.dir, name), 'wb')
        f.write(wav_header(nbytes))
        self.wav = [f, ring_pos, nbytes]
        return name

    def save_step(self, ring, chunk=8192):
        """Write the next chunk being saved; False when done."""
        if not self.wav:
            return False
        f, pos, left = self.wav
        n = min(left, chunk, len(ring) - pos)
        f.write(memoryview(ring)[pos:pos + n])
        pos = (pos + n) % len(ring)
        left -= n
        if left:
            self.wav[1], self.wav[2] = pos, left
            return True
        f.close()
        self.wav = None
        return False


# ---------------------------------------------------------------- packets

def decode_wav(path):
    """Decode a saved recording (32 kHz 16-bit mono WAV): prints and
    returns the packets."""
    state = bytearray(_aprs.STATE_BYTES)
    _aprs.reset(state)
    buf = bytearray(8192)
    frame = bytearray(400)
    found = []
    with open(path, 'rb') as f:
        f.seek(44)
        while True:
            n = f.readinto(buf)
            if not n:
                break
            k = _aprs.feed(memoryview(buf)[:n & ~1], state)
            while k:
                ln = _aprs.pop(state, frame)
                k -= 1
                p = aprs_parse.decode(bytes(frame[:ln]))
                if p:
                    print(p['raw'])
                    found.append(p)
    print('DECODE_WAV', json.dumps({'path': path, 'packets': len(found),
                                    'stats': _aprs.stats(state)}))
    return found


class Heard:
    """The stations heard (h lists them), and the packets of the last
    REPEAT_SECONDS: the same packet again (another digipeater's copy) is a
    repeat, logged but not shown again."""

    def __init__(self):
        self.stations = {}           # call -> [packets, last hh:mm, last summary]
        self.recent = {}             # source + info -> when last heard (s)

    def repeat(self, p, now):
        """Is p (heard at now, seconds) a repeat?"""
        key = p['src'] + p['raw'][p['raw'].find(':'):]
        repeat = now - self.recent.get(key, -REPEAT_SECONDS) < REPEAT_SECONDS
        self.recent[key] = now
        if len(self.recent) > 64:
            for k in [k for k, v in self.recent.items() if now - v >= REPEAT_SECONDS]:
                del self.recent[k]
        return repeat

    def add(self, p, hhmm, home):
        s = self.stations.get(p['src'])
        if s is None:
            s = self.stations[p['src']] = [0, '', '']
        s[0] += 1
        s[1] = hhmm
        s[2] = packet_row(p, hhmm, home, 80)[2]

    def report(self):
        for call in sorted(self.stations):
            s = self.stations[call]
            print('HEARD %-9s %3d %s %s' % (call, s[0], s[1], s[2]))


# --------------------------------------------------------------- controls

def open_keys():
    """The buttons B1-B3 (a keypad.Keys), or None on boards without them
    (the Metro ESP32-P4)."""
    if not hasattr(board, 'BUTTON3'):
        return None
    return keypad.Keys((board.BUTTON1, board.BUTTON2, board.BUTTON3),
                       value_when_pressed=False, pull=True)


class Controls:
    """The buttons and the serial console -> actions (see the module's
    docstring): a key ('n', '#', ...), 'esc', an arrow key ('up', ...), a
    typed command ('f144.39', 'c2'; Enter ends it), or a button's: B1 'p',
    B2 'x', B3 'n', or held down, the display's LONG_PRESS. keys: None
    without buttons."""

    def __init__(self, keys, ui):
        self.keys = keys
        self.ui = ui
        self.pressed_at = [None, None, None]
        self.line = None             # a command being typed
        self.esc = None              # what came after an Esc, while it may be an arrow key
        self.esc_at = 0
        self.held_ch = ''            # a key typed straight after Esc, for the next poll()

    def poll(self):
        """The next action, or None."""
        ui = self.ui
        action = None
        typed = self.line
        event = self.keys.events.get() if self.keys else None
        if event:
            k = event.key_number
            if event.pressed:
                self.pressed_at[k] = event.timestamp
            elif self.pressed_at[k] is not None:
                held = (event.timestamp - self.pressed_at[k]) & 0x1fffffff
                self.pressed_at[k] = None
                if held >= LONG_PRESS_MS and ui and ui.LONG_PRESS:
                    action = ui.LONG_PRESS[k]
                else:
                    action = ('p', 'x', 'n')[k]
        ch = ''
        if self.held_ch:
            ch, self.held_ch = self.held_ch, ''
        elif supervisor.runtime.serial_bytes_available:
            ch = sys.stdin.read(1)
        elif self.esc == '' and (supervisor.ticks_ms() - self.esc_at) & 0x1fffffff >= ESC_MS:
            ch = '\x00'           # (Esc on its own)
        if ch:
            if ch == '\x1b':
                self.esc, ch = '', ''
                self.esc_at = supervisor.ticks_ms()
            elif self.esc == '' and ch not in '[O':
                # The Esc key on its own (arrow keys send Esc [ or Esc O):
                # it cancels a command being typed, else it is an action.
                # A key typed straight after it is kept for the next call.
                self.esc = None
                if ch != '\x00':
                    self.held_ch = ch
                ch = ''
                if self.line is not None:
                    self.line = None
                elif action is None:
                    action = 'esc'
            elif self.esc is not None:
                self.esc += ch
                if (len(self.esc) > 1 and '@' <= ch <= '~' or self.esc[0] not in '[O'
                        or len(self.esc) > 8):
                    if self.line is None:
                        action = ARROW_KEYS.get(self.esc, action)
                    self.esc = None
                ch = ''
            if not ch:
                pass
            elif self.line is not None:
                if ch in '\r\n':
                    action, self.line = self.line, None
                elif ch in '\x08\x7f':
                    self.line = self.line[:-1] if self.line else None
                else:
                    self.line += ch
            elif ch in 'fFcC':
                self.line = ch.lower()
            else:
                action = ch.lower()
            if self.line != typed and ui:
                ui.entry(self.line)
        return action


# -------------------------------------------------------------------- run

def run(seconds=0, preset=DEFAULT_PRESET, frequency=None, presets=PRESETS, volume=-10.0,
        monitor=True, display=DISPLAY, commands=(), log_every=LOG_EVERY, vhf_gain=VHF_GAIN,
        home=HOME, clock_wait=10.0, map_centre=None, map_zoom=None):
    """Run the receiver. seconds=0 runs forever.

    preset: the PRESETS entry to start on; frequency (Hz) tunes there
    instead. monitor plays the channel on the jack while a signal is
    there. commands is a list of (seconds, command) pairs fed to the
    command handler, for unattended tests. display: 'map', 'text',
    False, or a display object (see aprs_ui). home: (lat, lon) to show
    distance and direction (and the map's centre). map_centre: (lat,
    lon) to centre the map on instead; without either the map centres on
    the first position heard. map_zoom: the map's zoom (aprs_ui_map.ZOOM).
    clock_wait: seconds to wait for the ESP32-C6 to have the time.
    """
    supervisor.runtime.autoreload = False
    presets = tuple(presets)
    index = preset % len(presets)
    muted = not monitor
    commands = sorted(commands)
    ring = _ring
    store = Store(SD_DIR)

    gc.collect()
    try:
        i2c = shared_i2c()
    except RuntimeError as error:
        print('I2C_ERROR', error)
        i2c = None
    ui = open_display(display, home, map_centre, map_zoom)
    status = Status()

    clock = Clock()
    if ui:
        ui.message('Reading the time from Wi-Fi (NTP)...')
    clock.sync(clock_wait)
    status.clock = clock.source
    if ui:
        ui.prepare()

    if ui:
        ui.connecting()
    d, radio = open_radio()

    def clamp(f):
        return max(radio.min_frequency + WINDOW[1], min(radio.max_frequency - WINDOW[1], f))

    if frequency is not None:
        label, dial = 'manual', frequency
    else:
        label, dial = presets[index]
    dial = clamp(dial)
    centre = dial + CENTRE_OFFSET
    radio.initialize(frequency=centre, sample_rate=256000, gain=vhf_gain)
    radio.hold_buffer()
    state = _dsp_state
    state[:] = bytes(len(state))     # (a fresh _ham_dsp state)
    astate = _aprs_state
    _aprs.reset(astate)
    frame = bytearray(400)
    silence = bytes(PCM_BLOCK)

    def configure():
        dsp.configure(state, NFM, dial - centre, 0, 1 if radio.conjugate else 0)

    heard = Heard()
    pending = []                 # frames waiting to be decoded
    pending_log = []             # aprs.txt lines waiting to be written
    pending_rows = []            # (packet, hh:mm) waiting to be drawn
    stats = {'packets': 0, 'repeats': 0, 'not_aprs': 0, 'max_dsp_ms': 0, 'max_feed_ms': 0,
             'max_parse_ms': 0}
    audio = keys = stream = None

    try:
        audio = open_audio(volume, i2c) if i2c is not None else NoAudio()
        keys = open_keys()
        controls = Controls(keys, ui)
        configure()
        gc.collect()
        radio.reset_buffer()
        stream, usb_ring = start_stream(d, audio, radio.sample_rate)
        iq = _iq
        iqv = memoryview(iq)
        filled = 0
        max_loop = max_ui = 0
        lost_total = 0
        stalls = []
        start = time.monotonic()
        last_log = last_gc = last_packet = last_ui_pause = start
        print('LIVE_START', json.dumps({
            'ring_size': usb_ring, 'tuner': radio.tuner_name, 'dial': dial, 'label': label,
            'clock': clock.source, 'sd': store.ok, 'ui': ui.NAME if ui else None,
            'memory': {'dsp_state': memory_place(state), 'aprs_state': memory_place(astate),
                       'iq': memory_place(iq), 'ring': memory_place(ring)}}))

        paused = 0           # pause_stream() calls not yet resumed (they nest)

        def pause_stream():
            nonlocal lost_total, paused
            paused += 1
            if paused > 1:
                return
            lost_total += stream.lost_packets
            stream.deinit()
            audio.stop()
            audio.clear()
            radio.hold_buffer()

        def resume_stream():
            nonlocal stream, usb_ring, filled, paused
            paused -= 1
            if paused:
                return
            radio.reset_buffer()
            filled = 0
            stream, usb_ring = start_stream(d, audio, radio.sample_rate)

        def tune(f):
            """Retune (pausing the stream if the hardware has to move)."""
            nonlocal dial, centre
            dial = clamp(f)
            if not WINDOW[0] <= centre - dial <= WINDOW[1]:
                centre = dial + CENTRE_OFFSET
                pause_stream()
                try:
                    radio.tune(centre)
                finally:
                    resume_stream()
            configure()
            _aprs.reset(astate)
            print('TUNE', json.dumps({'label': label, 'dial': dial}))

        def handle(raw):
            """One frame: decode, print, queue for the log and the screen."""
            p = aprs_parse.decode(raw)
            if p is None:
                stats['not_aprs'] += 1
                print('AX25_OTHER', raw.hex())
                return
            stats['packets'] += 1
            p['t'] = clock.stamp()
            p['dial'] = dial
            # A copy through another digipeater: logged, not shown again.
            repeat = heard.repeat(p, time.monotonic())
            if repeat:
                p['repeat'] = True
                stats['repeats'] += 1
            print('APRS', json.dumps(p))
            pending_log.append('%s: %s' % (p['t'], p['raw']))
            if repeat:
                return
            hhmm = clock.hhmm()
            heard.add(p, hhmm, home)
            if ui:
                pending_rows.append((p, hhmm))

        def show_status():
            if not ui:
                return
            status.dial = dial
            status.label = label
            t = clock.utc()
            if t is None:
                status.utc = '+%ds' % int(time.monotonic() - start)
            else:
                s = t % 86400
                status.utc = '%02d:%02d:%02dZ' % (s // 3600, s // 60 % 60, s % 60)
            status.clock = clock.source
            status.level = level_db(dsp.status(state)[0])
            status.dcd = _aprs.stats(astate)[5] > 0
            status.packets = stats['packets']
            status.stations = len(heard.stations)
            status.muted = muted
            status.sd = store.ok
            status.logged = store.logged
            ui.show(status)

        if ui:
            ui.ready()
        # The per-block path below must not allocate (a garbage collection
        # scans the heap and stalls for longer than the USB ring holds);
        # gc.collect() runs with the stream paused while the channel is quiet.
        views = [iqv[k:] for k in range(0, BLOCK, 64)]
        # The ring is written through one small view per block: assigning
        # to a slice of the big bytearray itself moves its whole tail
        # (~160 ms).
        rv = memoryview(ring)
        ring_views = [rv[k:k + PCM_BLOCK] for k in range(0, len(ring), PCM_BLOCK)]
        rk = 0
        tick = supervisor.ticks_ms
        last_tick = last_ui = tick()
        blocks = 0
        carrier = False
        quiet_at = tick()            # when the squelch was last closed
        ring_n = len(ring)
        running = True
        while running:
            t = tick()
            dt = (t - last_tick) & 0x1fffffff
            last_tick = t
            if dt > max_loop:
                max_loop = dt
            if dt > 80 and len(stalls) < 8:
                stalls.append((round(time.monotonic() - start, 1), dt))
            n = stream.readinto(views[filled >> 6] if not filled & 63 else iqv[filled:])
            if n == 0:
                raise RuntimeError('USB stream ended')
            if n:
                filled += n
            block = filled == BLOCK
            if block:
                filled = 0
                audio.service()
                out = audio.write_view_bytes(SAMPLES)
                t = tick()
                dsp.process(iq, out, state)
                t2 = tick()
                q = _aprs.feed(out, astate)
                t3 = tick()
                ring_views[rk][:] = out
                rk += 1
                if rk == len(ring_views):
                    rk = 0
                while q:
                    ln = _aprs.pop(astate, frame)
                    pending.append(bytes(frame[:ln]))
                    q -= 1
                if (t2 - t) & 0x1fffffff > stats['max_dsp_ms']:
                    stats['max_dsp_ms'] = (t2 - t) & 0x1fffffff
                if (t3 - t2) & 0x1fffffff > stats['max_feed_ms']:
                    stats['max_feed_ms'] = (t3 - t2) & 0x1fffffff
                if not muted:
                    if not carrier:
                        out[:] = silence
                    audio.commit(SAMPLES)
                audio.service()
                blocks = (blocks + 1) & 0xffff
                if blocks & 3:
                    continue
                # Every 4th block (64 ms): the jack's squelch.
                carrier = dsp.status(state)[1] < SQUELCH
                if not carrier:
                    quiet_at = tick()
                if blocks & 15:
                    continue
                now = time.monotonic()
                if seconds and now - start >= seconds:
                    running = False
                if now - last_log >= log_every:
                    last_log = now
                    a = _aprs.stats(astate)
                    info = {'t': round(now - start), 'lost': lost_total + stream.lost_packets,
                            'loop_max_ms': max_loop, 'ui_max_ms': max_ui, 'stalls': stalls,
                            'audio': audio.stats(), 'dial': dial, 'stations': len(heard.stations),
                            'frames': a[0], 'dupes': a[1], 'crc_fail': a[2], 'dropped': a[3],
                            'free_kb': gc.mem_free() // 1024}
                    info.update(stats)
                    print('LIVE', json.dumps(info))
                    max_loop = 0
                    stalls = []
            elif not n:
                # Idle until the next USB data: one piece of other work.
                # Without a USB ring, not while a signal is there (for
                # HOLD_MS at most): work for longer than the RTL2832U's
                # FIFO holds (~7 ms) would leave a gap in the packet.
                t = tick()
                if not usb_ring and carrier and (t - quiet_at) & 0x1fffffff < HOLD_MS:
                    pass
                elif pending:
                    handle(pending.pop(0))
                    last_packet = time.monotonic()
                    t = (tick() - t) & 0x1fffffff
                    if t > stats['max_parse_ms']:
                        stats['max_parse_ms'] = t
                elif store.wav:
                    try:
                        store.save_step(ring)
                    except OSError as error:
                        print('SAVE_ERROR', error)
                        store.wav = None
                elif pending_log and store.ok:
                    try:
                        store.log(pending_log)
                    except OSError as error:
                        status.note = 'SD error'
                        print('SD_ERROR', error)
                    pending_log.clear()
                elif pending_rows and ui:
                    ui.add_packet(*pending_rows.pop(0))
                    t = (tick() - t) & 0x1fffffff
                    if t > max_ui:
                        max_ui = t
                elif ui and (t - last_ui) & 0x1fffffff >= 1000:
                    last_ui = t
                    show_status()
                    t = (tick() - t) & 0x1fffffff
                    if t > max_ui:
                        max_ui = t
                elif ui and ui.step():
                    t = (tick() - t) & 0x1fffffff
                    if t > max_ui:
                        max_ui = t
                elif (ui and ui.needs_pause and time.monotonic() - last_ui_pause >= UI_PAUSE_EVERY
                      and not _aprs.stats(astate)[5] and time.monotonic() - last_packet > 1.0):
                    # (map tiles: downloads, conversions; seconds each)
                    pause_stream()
                    try:
                        ui.paused_step()
                    finally:
                        resume_stream()
                    last_ui_pause = time.monotonic()
                elif (time.monotonic() - last_gc >= GC_EVERY and not _aprs.stats(astate)[5]
                      and time.monotonic() - last_packet > 1.0):
                    pause_stream()
                    try:
                        gc.collect()
                    finally:
                        resume_stream()
                    last_gc = time.monotonic()
                else:
                    time.sleep(.0005)
            if pending_rows and not ui:
                pending_rows.clear()
            if pending_log and not store.ok:
                pending_log.clear()

            action = controls.poll()
            if (commands and block and not blocks & 15
                    and time.monotonic() - start >= commands[0][0]):
                action = commands.pop(0)[1]
            if action:
                if ui and ui.command(action):
                    pass
                elif action in ('n', 'p', '.', ','):
                    index = (index + (1 if action in ('n', '.') else -1)) % len(presets)
                    label, f = presets[index]
                    tune(f)
                elif len(action) == 1 and '1' <= action <= '9':
                    if int(action) <= len(presets):
                        index = int(action) - 1
                        label, f = presets[index]
                        tune(f)
                    else:
                        print('BAD_COMMAND', action)
                elif action in ('[', ']'):
                    label = 'manual'
                    tune(dial + (STEP if action == ']' else -STEP))
                elif action == 'x':
                    muted = not muted
                    audio.clear()
                elif action == 'u':
                    if store.ok:
                        name = store.save_begin(rk * PCM_BLOCK, ring_n)
                        print('SAVING', name)
                elif action in ('l', 'c'):
                    for k, e in enumerate(presets):
                        print('PRESET %d %s %s MHz' % (k, e[0], format_mhz(e[1])))
                elif action == 'h':
                    heard.report()
                elif action == '#':
                    a = _aprs.stats(astate)
                    info = {'dial': dial, 'label': label, 'utc': clock.stamp(),
                            'stations': len(heard.stations), 'frames': a[0], 'dupes': a[1],
                            'crc_fail': a[2], 'dropped': a[3], 'flags': a[4], 'dcd': a[5],
                            'lost': lost_total + stream.lost_packets}
                    info.update(stats)
                    print('STATUS', json.dumps(info))
                elif action[0] == 'c':
                    try:
                        index = int(action[1:]) % len(presets)
                        label, f = presets[index]
                        tune(f)
                    except ValueError:
                        print('BAD_COMMAND', action)
                elif action[0] == 'f':
                    try:
                        f = parse_frequency(action[1:])
                        label = 'manual'
                        tune(f)
                    except ValueError:
                        print('BAD_COMMAND', action)
                elif action == 'v':
                    if ui and store.ok:
                        name = store.next_name('screen_', '.bmp')
                        pause_stream()
                        try:
                            saved = ui.snapshot(name)
                        finally:
                            resume_stream()
                        if saved is False:
                            print('NO_SCREENSHOT', 'this screen cannot be saved')
                        else:
                            print('SCREENSHOT', name)
    finally:
        if stream is not None:
            try:
                lost_total += stream.lost_packets
                stream.deinit()
            except Exception:
                pass
        if store.wav:
            try:
                store.wav[0].close()
            except Exception:
                pass
            store.wav = None
        if audio is not None:
            audio.deinit()
        if keys is not None:
            keys.deinit()
        try:
            radio.hold_buffer()
        except Exception:
            pass
        stats['lost'] = lost_total
        stats['stations'] = len(heard.stations)
        print('LIVE_END', json.dumps(stats))
        if ui:
            print('SCREEN', json.dumps(ui.screen()))
            ui.close()


# ----------------------------------------------------------------- replay

class ReplayClock(Clock):
    """The log's time (self.t: seconds since 1970, or since that run's
    start-up) instead of the board's."""

    def __init__(self):
        super().__init__()
        self.t = 0
        self.elapsed = 0.0           # log seconds since the replay's first packet

    def utc(self):
        return self.t

    def seconds(self):
        """The map's clock: its stations age by the log's time."""
        return self.elapsed


def stamp_seconds(stamp):
    """A log line's time ('2026-10-24 19:31:05 UTC' or '+1234 s') ->
    seconds since 1970 (or since that run's start-up)."""
    if stamp[0] == '+':
        return int(stamp[1:].split()[0])
    return (days(int(stamp[0:4]), int(stamp[5:7]), int(stamp[8:10])) * 86400
            + int(stamp[11:13]) * 3600 + int(stamp[14:16]) * 60 + int(stamp[17:19]))


def reached(line, number, mark):
    """Is the log at mark (a line number, 1 the first; or a time: '19:36',
    '19:36:30' or '2026-10-24 19:36', UTC) by this line?"""
    if isinstance(mark, int):
        return number >= mark
    if ':' in mark[:3]:
        return line[11:11 + len(mark)] >= mark
    return line[:len(mark)] >= mark


def replay(start=None, end=None, speed=1.0, home=HOME, display=DISPLAY, verbose=False,
           commands=(), map_centre=None, map_zoom=None, hold=False, path=SD_DIR + '/aprs.txt'):
    """Play the log (path) back onto the screen: the packets from start
    (None: the first; a line number or a time, see reached()) to end
    (None: the last), speed times as fast as they were heard. Repeats are
    found again (by the log's times) and not shown twice. Nothing is
    logged. verbose: an 'APRS' console line per packet. hold: at the end
    keep the last screen (and the keys) until Ctrl-C. commands: (seconds,
    command) pairs, as run(). The keys and buttons as run(): h, #, v, ?
    and the map's work; the radio's do nothing."""
    supervisor.runtime.autoreload = False
    store = Store(SD_DIR)
    gc.collect()
    try:
        shared_i2c()
    except RuntimeError as error:
        print('I2C_ERROR', error)
    ui = open_display(display, home, map_centre, map_zoom)
    clock = ReplayClock()
    if ui:
        ui.now = clock.seconds
    status = Status()
    status.label = 'REPLAY'
    status.dial = status.level = None
    status.sd = store.ok
    heard = Heard()
    keys = None
    f = open(path)
    number = 0

    def read():
        """The next packet line and its log time, or (None, None) at the
        end of the log or at end."""
        nonlocal number
        while True:
            line = f.readline()
            number += 1
            if not line or (end is not None and reached(line, number, end)):
                return None, None
            at = line.find(': ')
            if at > 0:
                try:
                    return line, stamp_seconds(line[:at])
                except ValueError:
                    pass

    try:
        if ui:
            ui.message('Replay: finding %s in the log...' % (start or 'the start'))
        while True:
            line = f.readline()
            if not line:
                raise ValueError('the log has nothing at or after %r' % (start,))
            number += 1
            at = line.find(': ')
            if at > 0 and (start is None or reached(line, number, start)):
                try:
                    shift = stamp_seconds(line[:at])       # log time = replay time + shift
                    break
                except ValueError:
                    pass
        first = number
        clock.t = shift
        clock.source = 'NO CLOCK' if line[0] == '+' else 'NTP'
        status.clock = clock.source
        last = 0
        if ui:
            ui.prepare()
        keys = open_keys()
        controls = Controls(keys, ui)
        commands = sorted(commands)
        stats = {'packets': 0, 'repeats': 0, 'skipped_s': 0}
        print('REPLAY_START', json.dumps({'line': first, 'utc': clock.stamp(), 'speed': speed,
                                          'ui': ui.NAME if ui else None}))
        if ui:
            ui.ready()
        wall0 = time.monotonic_ns()
        last_ui = last_gc = -UI_EVERY
        done = False
        while True:
            wall = (time.monotonic_ns() - wall0) / 1e9
            now = last if done else wall * speed
            while not done and last <= now:
                # the packet in line, at log time last + shift: due now (or late)
                p = aprs_parse.from_tnc2(line[line.find(': ') + 2:].rstrip('\r\n'))
                if p:
                    clock.t = last + shift
                    clock.elapsed = last + stats['skipped_s']
                    stats['packets'] += 1
                    p['t'] = clock.stamp()
                    if heard.repeat(p, clock.t):
                        p['repeat'] = True
                        stats['repeats'] += 1
                    else:
                        hhmm = clock.hhmm()
                        heard.add(p, hhmm, home)
                        if ui:
                            ui.add_packet(p, hhmm)
                    if verbose:
                        print('APRS', json.dumps(p))
                line, t = read()
                if line is None:
                    done = True
                    last_ui = -UI_EVERY            # (the last screen)
                    clock.t = last + shift
                    print('REPLAY_END', json.dumps({'line': number, 'utc': clock.stamp(),
                                                    'stats': stats}))
                    if not hold:
                        break
                else:
                    t -= shift
                    if t - last > MAX_GAP or t < last:
                        # (the receiver was off; or, going back, the log of
                        # a later run without the time)
                        if t > last:
                            stats['skipped_s'] += t - last - 1
                        shift += t - last - 1
                        t = last + 1
                    last = t
            if wall - last_ui >= UI_EVERY:
                last_ui = wall
                clock.t = int(now) + shift
                clock.elapsed = now + stats['skipped_s']
                if ui:
                    t = clock.t
                    if clock.source == 'NTP':
                        status.utc = '%02d:%02d:%02dZ' % (t // 3600 % 24, t // 60 % 60, t % 60)
                    else:
                        status.utc = '+%ds' % t
                    status.packets = stats['packets']
                    status.stations = len(heard.stations)
                    ui.show(status)
            if done and not hold:
                # (the last screen, drawn in full)
                while ui and ui.step():
                    pass
                break
            if ui and ui.needs_pause:
                # (a map tile: the replay waits for it)
                t0 = time.monotonic_ns()
                ui.paused_step()
                wall0 += time.monotonic_ns() - t0
            elif ui and ui.step():
                pass
            elif wall - last_gc >= GC_EVERY:
                last_gc = wall
                gc.collect()
            else:
                time.sleep(0.005)
            action = controls.poll()
            if commands and wall >= commands[0][0]:
                action = commands.pop(0)[1]
            if not action or ui and ui.command(action):
                pass
            elif action == 'h':
                heard.report()
            elif action == '#':
                info = {'utc': clock.stamp(), 'line': number, 'stations': len(heard.stations),
                        'done': done}
                info.update(stats)
                print('STATUS', json.dumps(info))
            elif action == 'v' and ui and store.ok:
                name = store.next_name('screen_', '.bmp')
                if ui.snapshot(name) is False:
                    print('NO_SCREENSHOT', 'this screen cannot be saved')
                else:
                    print('SCREENSHOT', name)
    finally:
        f.close()
        if keys is not None:
            keys.deinit()
        if ui:
            print('SCREEN', json.dumps(ui.screen()))
            ui.close()
