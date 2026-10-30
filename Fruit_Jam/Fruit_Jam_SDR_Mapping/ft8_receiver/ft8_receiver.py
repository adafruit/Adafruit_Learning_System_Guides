# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""FT8 receiver: listens to an FT8 frequency on the Fruit Jam or the Metro
ESP32-P4 with a NESDR SMArt v5 and decodes every 15 s slot on the board
itself.

The radio's USB audio (_ham_dsp) plays on the jack and goes through the
FT8 feed (_ft8), which builds the slot's waterfall as the audio arrives.
At each slot's end the waterfall is decoded in small steps between USB
blocks (ft8_lib's decoder, see turbo_source_files/ft8_dsp), while the
next slot fills a second waterfall. Decodes are printed, shown on the
screen (DVI via picodvi on the Fruit Jam, the TFT shield on the Metro
ESP32-P4) and appended to /sd/ft8/ALL.TXT in WSJT-X's format.

The radio is read through sdr_usb: usb_host_bulk's ring on the Fruit
Jam; on the Metro ESP32-P4's high-speed USB host, blocking reads with
one piece of the other work (a decode step...) between them, and lost
samples counted from the time. The Metro has no headphone jack and no
B1-B3 buttons: there the receiver only decodes, and the serial console
is the keyboard.

Slot timing needs UTC. It comes from the ESP32-C6's clock, which nina-fw
sets by SNTP once the board is on Wi-Fi (CIRCUITPY_WIFI_SSID and
CIRCUITPY_WIFI_PASSWORD in settings.toml, as for web workflow): the
receiver reads it before the radio starts, timing the change of second.
On boards with the wifi module (the Metro ESP32-P4) it asks an NTP
server instead (the best of NTP_TRIES requests, to the millisecond).
From then on slot edges come from counting the radio's samples (lost USB
packets included). The decodes' median DT shows any remaining offset,
and the receiver moves its slot edges once it passes DT_LIMIT.

Buttons (Fruit Jam): B1 previous preset, B2 mute, B3 next preset.
Serial console: , / . (or p / n) previous / next preset, 1-9 go to
preset 1-9 (PRESETS[0] .. [8]), x mute, c alone (then Enter) list
presets, c<number> go to a preset, f<frequency> tune anywhere (USB dial;
'f14.074', 'f14074' kHz, 'f 14074000' Hz: see parse_frequency; the
display shows it as it is typed, Backspace edits, Esc cancels), [ ]
tune 500 Hz, t read the clock again, # status, u save slot audio on/off,
? help (a page on the screen: what it shows, the keys; ? or Esc closes
it); with several views m or l shows the next; the map's keys (i or + /
o or - zoom, the arrow keys or w a s d move it, r fit, v screenshot).

decode_wav(path) decodes one saved 15 s slot (8 kHz 16-bit mono WAV).
run(replay=folder) plays 8 kHz slot WAVs (YYMMDD_HHMMSS.wav, as saved
here or cut by test/make_slots.py) through the decoder in place of the
radio's audio, one per slot, with the radio still running.

replay_log() plays the decode log (/sd/ft8/ALL.TXT) back onto the
screen instead (no radio, no decoding): replay_log(start='12:56') from
the first decode at or after 12:56 UTC (or '261020_1256', or a line
number), to end= (the same forms) or the end of the log, at speed=
times real time. With display='map' it is the map of the exchanges.
"""
# pylint: disable=wrong-import-order, wrong-import-position
import sys
# _ft8 and _ham_dsp: *.armv7emsp.mpy are the Arm builds (Fruit Jam),
# *.rv32imc.mpy the RISC-V ones (Metro ESP32-P4): `import` loads the one
# for this board.
import _ft8
# The big buffers first: they go to PSRAM, and because they are bigger
# than internal SRAM, later Python heap areas go there too. That leaves
# internal SRAM for the USB bulk ring and the audio DMA buffers. Two
# waterfalls (one fills while the other is decoded), the feed, the decode
# work, and a ring of 8 kHz audio for saving slots.
MAX_CANDIDATES = 140
RING_SECONDS = 20
_specs = (bytearray(_ft8.SPEC_BYTES), bytearray(_ft8.SPEC_BYTES))
_feed = bytearray(_ft8.FEED_BYTES)
_work = bytearray(_ft8.work_bytes(MAX_CANDIDATES))
_ring = bytearray(RING_SECONDS * 16000)
import time
import gc
import os
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
import _ham_dsp as dsp

# pylint: disable=too-many-lines, global-statement, import-outside-toplevel
# pylint: disable=too-many-locals, too-many-branches, too-many-statements
# pylint: disable=too-many-return-statements, unsubscriptable-object, broad-except
# pylint: disable=no-self-use

USB = 2                      # _ham_dsp mode
RATE32 = 32000
SLOT = 15                    # seconds
SLOT_SAMPLES = SLOT * RATE32

# (label, USB dial frequency in Hz). FT8 signals are 200-3000 Hz above it.
PRESETS = (
    ('10m', 28074000),
    ('6m', 50313000),
    ('20m', 14074000),
    ('40m', 7074000),
    ('80m', 3573000),
    ('30m', 10136000),
    ('17m', 18100000),
    ('15m', 21074000),
    ('12m', 24915000),
)
DEFAULT_PRESET = 0
STEP = 500                   # Hz per [ / ]

MIN_SCORE = 10               # sync score a candidate needs (ft8_lib's default)
LDPC_ITERATIONS = 25
DT_LIMIT = 0.3               # s: move the slot edges once the decodes' median DT passes this
DT_SLOTS = 4                 # ... measured over this many slots (with DT_MIN_DECODES or more)
DT_MIN_DECODES = 3
MY_CALL = ''                 # messages with this call are marked on the screen
DISPLAY = 'dvi'              # a DISPLAYS name: 'dvi' (plain text), 'color' (callsigns in colors)
                             # or 'map' (the exchanges on a map); or several, ('color', 'map'):
                             # the m or l key shows the next (ft8_display_views)
DISPLAYS = {
    'dvi': ('ft8_display_dvi', 'DviDisplay'),
    'color': ('ft8_display_color', 'ColorDisplay'),
    'map': ('ft8_display_map', 'MapDisplay'),
}
SAVE_AUDIO = False           # save each slot's 8 kHz audio as /sd/ft8/YYMMDD_HHMMSS.wav
GC_EVERY = 4                 # slots between garbage collections...
GC_AT = 14.0                 # ...done this far into a slot (s), after FT8 transmissions end
UI_PAUSE_BY = 14.3           # s: the display's paused step (the map) starts between GC_AT and this

# VHF (6 m): tuner gain in tenths of a dB.
VHF_MIN = 30000000
VHF_GAIN = 496
# The hardware centre sits above the dial so the signal is away from DC;
# tuning inside the window only moves the DSP oscillator.
CENTRE_OFFSET = 56000
WINDOW = (12000, 100000)
BLOCK = 8192                 # I/Q bytes per DSP call -> 512 PCM samples (16 ms)
PCM_BLOCK = BLOCK // 8       # bytes of 32 kHz PCM per block
SAMPLES = PCM_BLOCK // 2     # 32 kHz samples per block
PACKET_SAMPLES = 4           # 32 kHz samples per lost 64-byte USB packet (32 I/Q pairs)
LATENCY_MS = 20              # from the antenna to a block's arrival, at stream start

SD_DIR = '/sd/ft8'
MIN_FREE = 8 * 1024 * 1024
NTP_SERVER = 'pool.ntp.org'  # (boards with the wifi module)
NTP_TRIES = 3                # requests; the one with the shortest round trip is kept
# Esc with nothing after it for this long: the Esc key (not an arrow key)
ESC_MS = 30
ARROW_KEYS = {'[A': 'up', 'OA': 'up', '[B': 'down', 'OB': 'down', '[C': 'right', 'OC': 'right',
              '[D': 'left', 'OD': 'left'}   # (the map's)
I2C_FREQUENCY = 400000
RTL_AGC = False              # the RTL2832U's digital AGC in direct sampling (HF)
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


def open_display(display=True, options=None):
    """The display, or None. display: True for DISPLAY, a DISPLAYS name,
    a tuple or list of them (views on one screen; m or l shows the next),
    False for none, or a display object (the methods ft8_display_dvi's
    DviDisplay has). options: keyword arguments for the DISPLAYS classes
    that take them (OPTIONS = True: the map's home, centre, zoom, keep)."""
    if display is True:
        display = DISPLAY
    if not display:
        return None
    if not isinstance(display, (str, tuple, list)):
        return display

    def make(name, screen=None, views=False):
        module, cls = DISPLAYS[name]
        cls = getattr(__import__(module), cls)
        kwargs = dict(options) if options and getattr(cls, 'OPTIONS', False) else {}
        if screen:
            kwargs['screen'] = screen
        if views:
            kwargs['views'] = True       # (its help page lists m / l)
        return cls(**kwargs)

    try:
        if isinstance(display, str):
            return make(display)
        from ft8_display_views import Views
        views = [make(display[0], views=True)]
        for name in display[1:]:
            views.append(make(name, (views[0].fb, views[0].display), True))
        return Views(views)
    except Exception as error:
        print('DISPLAY_ERROR', type(error).__name__, error)
        return None


# ------------------------------------------------------------------ time

def civil(days):
    """Days since 1970-01-01 -> (year, month, day)."""
    z = days + 719468
    era = z // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + 3 if mp < 10 else mp - 9
    return yoe + era * 400 + (1 if m <= 2 else 0), m, d


def stamp(day, sec):
    """'261018_143015' (WSJT-X's slot stamp) for a day number and second of day."""
    y, m, d = civil(day)
    return '%02d%02d%02d_%02d%02d%02d' % (y % 100, m, d, sec // 3600, sec // 60 % 60, sec % 60)


class Clock:
    """UTC as time.monotonic_ns() + offset. The offset comes from the
    ESP32-C6's clock (nina-fw's GET_TIME, set by SNTP), read at the moment
    its second changes; or on boards with the wifi module from an NTP
    server."""

    def __init__(self):
        self.offset_ns = None
        self.source = 'NO CLOCK'
        self.adjusted_ms = 0         # moved by DT corrections since the last sync

    @staticmethod
    def _esp_time():
        import _airlift
        if not _airlift.active():
            raise RuntimeError('no Wi-Fi: set CIRCUITPY_WIFI_SSID/PASSWORD in settings.toml')
        r = _airlift.transact(0x3B)[0]
        return struct.unpack('<q' if len(r) == 8 else '<i', r)[0]

    @staticmethod
    def _ntp(address):
        """One SNTP request: (UTC in ms, the time.monotonic_ns() it was then
        (the middle of the round trip), the round trip in ms)."""
        import wifi
        import socketpool
        pool = socketpool.SocketPool(wifi.radio)
        packet = bytearray(48)
        packet[0] = 0x1B         # version 3, client
        with pool.socket(pool.AF_INET, pool.SOCK_DGRAM) as s:
            s.settimeout(2)
            a = time.monotonic_ns()
            s.sendto(packet, address)
            s.recv_into(packet)
            b = time.monotonic_ns()
        secs, frac = struct.unpack_from('>II', packet, 40)
        ms = (secs - 2208988800) * 1000 + (frac * 1000 >> 32)       # (from 1900)
        return ms, (a + b) // 2, (b - a) // 1000000

    def _sync_ntp(self, wait):
        """Set the clock from NTP_SERVER (boards with the wifi module)."""
        end = time.monotonic() + wait
        best = None
        problem = None
        tries = 0
        while tries < NTP_TRIES:
            try:
                if not os.getenv('CIRCUITPY_WIFI_SSID'):
                    # (and leave wifi alone: on the Metro ESP32-P4 the board
                    # crashes at the next soft reset once wifi has been imported)
                    raise RuntimeError('no Wi-Fi: set CIRCUITPY_WIFI_SSID/PASSWORD '
                                       'in settings.toml')
                import wifi
                import socketpool
                if not wifi.radio.connected:
                    raise RuntimeError('Wi-Fi is not connected')
                address = socketpool.SocketPool(wifi.radio).getaddrinfo(NTP_SERVER, 123)[0][4]
                got = self._ntp(address)
                tries += 1
                if best is None or got[2] < best[2]:
                    best = got
            except Exception as error:
                problem = '%s %s' % (type(error).__name__, error)
                if time.monotonic() > end:
                    break
            time.sleep(0.5)
        if best is None:
            print('CLOCK_ERROR', problem)
            return False
        ms, at, rtt = best
        self.offset_ns = ms * 1000000 - at
        self.source = 'NTP'
        self.adjusted_ms = 0
        print('CLOCK', json.dumps({'utc': ms // 1000, 'uncertainty_ms': rtt // 2 + 1}))
        return True

    def sync(self, wait=20.0):
        """Read UTC from the ESP32-C6 (waiting up to `wait` s for it to
        have the time), or from NTP. Returns True when set."""
        try:
            import _airlift  # pylint: disable=unused-import
        except ImportError:
            return self._sync_ntp(wait)
        end = time.monotonic() + wait
        while True:
            try:
                last = self._esp_time()
                if last > 1700000000:
                    break
                problem = 'its clock is not set yet'
            except Exception as error:
                problem = '%s %s' % (type(error).__name__, error)
            if time.monotonic() > end:
                print('CLOCK_ERROR', problem)
                return False
            time.sleep(0.5)
        before = time.monotonic_ns()
        limit = before + 2500000000
        while True:
            a = time.monotonic_ns()
            now = self._esp_time()
            b = time.monotonic_ns()
            if now != last:
                # The second began between the two readings.
                self.offset_ns = now * 1000000000 - (before + b) // 2
                self.source = 'NTP'
                self.adjusted_ms = 0
                print('CLOCK', json.dumps({'utc': now, 'uncertainty_ms': (b - before) // 1000000}))
                return True
            last, before = now, a
            if a > limit:
                print('CLOCK_ERROR', 'second did not change')
                return False

    def utc_ms(self):
        """Milliseconds since 1970 (monotonic clock if never set)."""
        return (time.monotonic_ns() + (self.offset_ns or 0)) // 1000000

    def adjust(self, ms):
        if self.offset_ns is not None:
            self.offset_ns += ms * 1000000
        self.adjusted_ms += ms


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


def open_radio(direct_input='Q'):
    """The NESDR on the USB host port, configured."""
    d = sdr_usb.find_device()
    return d, open_ham_receiver(sdr_usb.control(d), max_packet=sdr_usb.max_packet(d),
                                direct_input=direct_input)


def parse_frequency(text):
    """A typed frequency -> Hz, without single-precision floats, which
    cannot hold every frequency to the hertz: '14.074' or '14.074 MHz',
    '14074' or '14074khz', '14074000' or '14074000hz'. Without a unit the
    whole part says which: MHz below 1000, kHz below 1000000, else Hz."""
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


def format_mhz(hz):
    return '%d.%06d' % (hz // 1000000, hz % 1000000)


def wav_header(nbytes, rate=8000):
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
    ESP32-P4's 4-bit SDIO slot, else the TFT shield's (ft8_tft)."""
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
    import ft8_tft
    return ft8_tft.sd_card()


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
    """ALL.TXT (WSJT-X's decode log format) and saved slot audio in SD_DIR."""

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
        self.wav = None              # [file, ring position, bytes left] while a slot is being saved

    def free(self):
        try:
            s = os.statvfs(self.dir)
            return s[0] * s[3]
        except OSError:
            return 0

    def log(self, lines, name='ALL.TXT'):
        with open(self.dir + '/' + name, 'a') as f:
            for line in lines:
                f.write(line)
                f.write('\n')
        self.logged += len(lines)

    def save_begin(self, name, ring_pos, nbytes):
        if self.wav or self.free() < nbytes + MIN_FREE:
            return False
        f = open('%s/%s.wav' % (self.dir, name), 'wb')
        f.write(wav_header(nbytes))
        self.wav = [f, ring_pos, nbytes]
        return True

    def save_step(self, ring, chunk=8192):
        """Write the next chunk of a slot being saved; False when done."""
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


class Status:
    """What the display shows. The receiver keeps it up to date and calls
    ui.show(status); the display module formats it."""

    def __init__(self):
        self.dial = 0
        self.label = ''
        self.utc = ''               # 'HH:MM:SSZ'
        self.utc_s = 0              # seconds since 1970 (UTC)
        self.clock = 'NO CLOCK'     # 'NTP', 'NTP DT+0.4' ...
        self.level = -99.0
        self.slot_decodes = None    # decodes in the last decoded slot
        self.decoding = None        # units of decoding work left, or None
        self.muted = False
        self.sd = False
        self.logged = 0
        self.note = None


# ---------------------------------------------------------------- decoding

def results(work, text_buf, day, sec, dial):
    """The decodes in work as dicts."""
    out = []
    for i in range(_ft8.result_count(work)):
        snr, dt_ms, hz, n = _ft8.result(work, i, text_buf)
        out.append({'t': stamp(day, sec), 'snr': snr, 'dt': dt_ms / 1000, 'freq': hz,
                    'text': bytes(text_buf[:n]).decode(), 'dial': dial})
    return out


def all_txt(d):
    """One line of WSJT-X's ALL.TXT."""
    return '%s %9s Rx FT8 %6d %4.1f %4d %s' % (d['t'], '%.3f' % (d['dial'] / 1000000), d['snr'],
                                               d['dt'], d['freq'], d['text'])


def parse_all_txt(line):
    """One line of ALL.TXT -> a decode dict (as results() makes them), or
    None if it is not a decode."""
    f = line.split()
    if len(f) < 8 or f[2] != 'Rx' or len(f[0]) != 13 or f[0][6] != '_':
        return None
    try:
        return {'t': f[0], 'snr': int(f[4]), 'dt': float(f[5]), 'freq': int(f[6]),
                'text': ' '.join(f[7:]), 'dial': parse_frequency(f[1])}
    except ValueError:
        return None


def decode_wav(path, max_candidates=MAX_CANDIDATES, dial=0):
    """Decode a saved 15 s slot (16-bit mono WAV, 8 kHz or 32 kHz);
    returns and prints the decodes."""
    feed, spec, work = _feed, _specs[0], _work
    with open(path, 'rb') as f:
        head = f.read(64)
        rate = int.from_bytes(head[24:28], 'little')
        if rate not in (8000, 32000) or head[34] != 16:
            raise ValueError('decode_wav needs a 16-bit 8 or 32 kHz WAV')
        at = head.find(b'data')
        f.seek(at + 8 if at >= 0 else 44)
        _ft8.feed_init(feed, 1 if rate == 8000 else 4)
        _ft8.slot_reset(feed, spec, 0)
        buf = bytearray(4096)
        while True:
            k = f.readinto(buf)
            if not k:
                break
            _ft8.feed(feed, memoryview(buf)[:k & ~1], spec)
    _ft8.work_init(work, max_candidates)
    t = time.monotonic()
    _ft8.decode_begin(work, spec, MIN_SCORE, LDPC_ITERATIONS)
    while _ft8.decode_step(work, spec, 4):
        pass
    name = path.split('/')[-1]
    day, sec = 0, 0
    if len(name) >= 13 and name[6] == '_':
        sec = int(name[7:9]) * 3600 + int(name[9:11]) * 60 + int(name[11:13])
    res = results(work, bytearray(40), day, sec, dial)
    for d in res:
        print('DECODE', json.dumps(d))
    print('DECODE_WAV', json.dumps({'file': path, 'decodes': len(res),
                                    'seconds': round(time.monotonic() - t, 2),
                                    'stats': _ft8.stats(work)}))
    return res


# ------------------------------------------------------------------ main

def paused_step_due(ui, pos, ui_by, ui_slot, sec):
    """The display's paused step (the map's slow work) is due: it has one,
    wants it, and it has not run this slot and can start before ui_by."""
    return (getattr(ui, 'paused_step', None) is not None and pos < ui_by and ui_slot != sec
            and ui.needs_pause)


def run(seconds=0, preset=DEFAULT_PRESET, frequency=None, presets=PRESETS, volume=-10.0,
        monitor=True, display=True, commands=(), log_every=60, direct_input='Q', rtl_agc=RTL_AGC,
        vhf_gain=VHF_GAIN, save_audio=SAVE_AUDIO, my_call=MY_CALL, clock_wait=20.0, replay=None,
        display_options=None):
    """Run the receiver. seconds=0 runs forever.

    preset: the PRESETS entry to start on; frequency (Hz, USB dial) tunes
    there instead. monitor plays the audio on the jack. commands is a list
    of (seconds, command) pairs fed to the command handler, for unattended
    tests. display: True (DISPLAY), a DISPLAYS name ('dvi', 'color'), a
    display object, or False. rtl_agc turns the RTL2832U's digital AGC
    on (HF). save_audio saves each decoded slot's audio. clock_wait:
    seconds to wait for the ESP32-C6 to have the time. replay: a folder
    of 8 kHz slot WAVs to decode in place of the radio's audio (one per
    slot, then it stops). display_options: keyword arguments for the
    display ({'home': 'EM28', 'zoom': 3} for the map).

    A display with paused_step() (the map) gets it once a slot, late in
    the slot (GC_AT) with the stream stopped, while its needs_pause is
    true: for drawing that takes longer than the USB ring holds; and at
    once, also with the stream stopped, after a key that makes its
    switching true (the views' m / l). Keys go to its command(action)
    first; the receiver gets the ones it does not use. Its step(), if it
    has one, is called when the stream is idle (the help page, a strip at
    a time).
    """
    supervisor.runtime.autoreload = False
    presets = tuple(presets)
    index = preset % len(presets)
    muted = not monitor
    commands = sorted(commands)
    specs, feed, work, ring = _specs, _feed, _work, _ring
    store = Store(SD_DIR)

    gc.collect()
    try:
        i2c = shared_i2c()
    except RuntimeError as error:
        print('I2C_ERROR', error)
        i2c = None
    ui = open_display(display, display_options)
    ui_paused = getattr(ui, 'paused_step', None)
    ui_command = getattr(ui, 'command', None)
    ui_entry = getattr(ui, 'entry', None)
    ui_step = getattr(ui, 'step', None)
    status = Status()

    clock = Clock()
    if ui:
        ui.message('Reading the time from Wi-Fi (NTP)...')
    clock.sync(clock_wait)
    status.clock = clock.source

    if ui and hasattr(ui, 'prepare'):
        ui.prepare()                 # (the map's tiles, before the radio starts)
    if ui:
        ui.connecting()
    d, radio = open_radio(direct_input)

    def clamp(f):
        return max(radio.min_frequency + WINDOW[1], min(radio.max_frequency - WINDOW[1], f))

    if frequency is not None:
        label, dial = 'manual', frequency
    else:
        label, dial = presets[index]
    dial = clamp(dial)
    vhf = dial >= VHF_MIN
    centre = dial + CENTRE_OFFSET
    radio.initialize(frequency=centre, sample_rate=256000, gain=vhf_gain if vhf else None)
    radio.hold_buffer()

    def set_rtl_agc():
        # Direct sampling only; entering it (again) turns the AGC on.
        if radio.direct:
            radio.demod(0, 0x19, 0x25 if rtl_agc else 0x05)

    set_rtl_agc()
    state = bytearray(8192)
    text_buf = bytearray(40)

    def configure():
        dsp.configure(state, USB, dial - centre, 0, 1 if radio.conjugate else 0)

    _ft8.feed_init(feed, 1 if replay else 4)
    _ft8.work_init(work, MAX_CANDIDATES)
    replays = sorted(n for n in os.listdir(replay) if n.endswith('.wav')) if replay else []
    rfile = None
    replay_end = False
    rbuf = bytearray(PCM_BLOCK // 4)     # one block of 8 kHz audio
    rzero = bytes(len(rbuf))             # (silence, copied in without a Python loop)

    # The slot clock. `pos` counts 32 kHz samples since the start of the
    # current slot, which began `sec` seconds into UTC day `day`. `fill`
    # is the waterfall being filled; `valid` once it started at a slot
    # edge on this frequency. A finished waterfall is decoded (in steps)
    # while the next one fills: `decoding` is its index, `dslot` its slot.
    pos = 0
    day = sec = 0
    fill = 0
    valid = False
    decoding = None
    dslot = None
    slot_start_ring = 0
    audio = keys = stream = None
    lost_seen = 0
    dt_meds = []                 # median DT of recent slots
    slots_since_gc = 0
    pending_rows = []            # decodes waiting to be drawn
    pending_log = []             # ALL.TXT lines waiting to be written
    stats = {'slots': 0, 'decoded_slots': 0, 'decodes': 0, 'max_step_ms': 0, 'max_feed_ms': 0,
             'max_dsp_ms': 0, 'late': 0, 'max_pause_ms': 0}
    ui_slot = None               # the slot (its sec) of the display's last paused step

    def anchor():
        """Set the slot clock from UTC, for a stream that has just started."""
        nonlocal pos, day, sec
        ms = clock.utc_ms() - LATENCY_MS
        day, rem = divmod(ms, 86400000)  # pylint: disable=unused-variable
        sec = rem // 15000 * 15
        pos = ((rem - sec * 1000) * 32) & ~3

    try:
        audio = open_audio(volume, i2c) if i2c is not None else NoAudio()
        if hasattr(board, 'BUTTON3'):        # (none on the Metro ESP32-P4)
            keys = keypad.Keys((board.BUTTON1, board.BUTTON2, board.BUTTON3),
                               value_when_pressed=False, pull=True)
        configure()
        gc.collect()
        radio.reset_buffer()
        stream, usb_ring = start_stream(d, audio, radio.sample_rate)
        iq = bytearray(BLOCK)
        iqv = memoryview(iq)
        filled = 0
        anchor()
        max_loop = max_ui = 0
        lost_total = 0
        stalls = []
        start = time.monotonic()
        last_log = start
        pressed_at = [None, None, None]
        line = None
        esc = None           # what came after an Esc, while it may be an arrow key
        esc_at = 0
        held = ''            # a key typed straight after Esc, for the next read_controls()
        print('LIVE_START', json.dumps({'ring_size': usb_ring, 'tuner': radio.tuner_name,
                                        'dial': dial, 'clock': clock.source, 'sd': store.ok,
                                        'utc': stamp(day, sec), 'pos': pos}))

        paused = 0           # pause_stream() calls not yet resumed (they nest)

        def pause_stream():
            nonlocal lost_total, paused, lost_seen
            paused += 1
            if paused > 1:
                return
            lost_total += stream.lost_packets
            lost_seen = 0
            stream.deinit()
            audio.stop()
            audio.clear()
            radio.hold_buffer()

        def resume_stream(keep_slot):  # pylint: disable=unused-variable
            """Restart the stream; the slot clock is set again from UTC.
            keep_slot: the waterfall being filled stays valid (the gap was
            short and after the slot's transmissions)."""
            nonlocal stream, usb_ring, filled, paused, valid
            paused -= 1
            if paused:
                return
            radio.reset_buffer()
            filled = 0
            stream, usb_ring = start_stream(d, audio, radio.sample_rate)
            old = (day, sec)
            anchor()
            if (day, sec) != old:
                # The pause crossed a slot edge.
                end_slot(old, keep_slot)
                valid = False
            elif not keep_slot:
                valid = False

        def end_slot(slot, complete):
            """The waterfall being filled ends here (slot = its (day, sec)):
            decode it if it is a whole slot, and start the next one."""
            nonlocal fill, valid, decoding, dslot, slot_start_ring, slots_since_gc
            if decoding is not None:
                # Not finished in a whole slot: report what was found.
                stats['late'] += 1
                finish_decode(late=True)
            done = fill
            fill ^= 1
            rows = _ft8.spec_info(specs[done])[0]
            stats['slots'] += 1
            slots_since_gc += 1
            if valid and complete and rows >= _ft8.ROWS - 4:
                _ft8.decode_begin(work, specs[done], MIN_SCORE, LDPC_ITERATIONS)
                decoding = done
                dslot = (slot[0], slot[1], dial)
                status.decoding = 0
                if save_audio and store.ok:
                    n = SLOT * 16000
                    if store.save_begin(stamp(*slot), slot_start_ring, n):
                        print('SAVING', stamp(*slot))
            _ft8.slot_reset(feed, specs[fill], 0)
            slot_start_ring = _ft8.ring_pos(feed)
            valid = True
            if replay:
                next_replay()

        def next_replay():
            nonlocal rfile, replay_end
            if rfile:
                rfile.close()
                rfile = None
            if not replays:
                replay_end = True        # stop once the last one is decoded
                return
            name = replays.pop(0)
            rfile = open('%s/%s' % (replay, name), 'rb')
            rfile.seek(44)
            print('REPLAY', name)

        def next_slot():
            nonlocal day, sec
            sec += SLOT
            if sec >= 86400:
                sec -= 86400
                day += 1

        def finish_decode(late=False):
            nonlocal decoding
            res = results(work, text_buf, dslot[0], dslot[1], dslot[2])
            st = _ft8.stats(work)
            decoding = None
            status.decoding = None
            status.slot_decodes = len(res)
            stats['decoded_slots'] += 1
            stats['decodes'] += len(res)
            for r in res:
                print('FT8', json.dumps(r))
                pending_rows.append(r)
                pending_log.append(all_txt(r))
            print('SLOT', json.dumps({'t': stamp(dslot[0], dslot[1]), 'decodes': len(res),
                                      'late': late, 'candidates': st[0], 'ldpc_fail': st[2],
                                      'noise_v': st[6], 'hashes': st[7]}))
            if len(res) >= DT_MIN_DECODES:
                dts = sorted(r['dt'] for r in res)
                dt_meds.append(dts[len(dts) // 2])
                if len(dt_meds) > DT_SLOTS:
                    dt_meds.pop(0)
                check_dt()

        def check_dt():
            """Move the slot edges when the decodes keep arriving early or
            late (a clock error)."""
            nonlocal pos
            if len(dt_meds) < DT_SLOTS:
                return
            m = sorted(dt_meds)[len(dt_meds) // 2]
            if abs(m) < DT_LIMIT:
                return
            # Signals late in the waterfall: this slot started too early.
            shift = int(m * RATE32) & ~3
            pos -= shift
            clock.adjust(-int(m * 1000))
            dt_meds.clear()
            print('CLOCK_ADJUST', json.dumps({'dt': m, 'total_ms': clock.adjusted_ms}))

        def tune(f):
            """Retune (pausing the stream if the hardware has to move). The
            slot being filled is dropped."""
            nonlocal dial, centre, vhf, valid
            dial = clamp(f)
            band = dial >= VHF_MIN
            if band != vhf or not WINDOW[0] <= centre - dial <= WINDOW[1]:
                centre = dial + CENTRE_OFFSET
                pause_stream()
                try:
                    if band != vhf:
                        radio.set_gain(vhf_gain if band else None)
                    radio.tune(centre)
                    set_rtl_agc()
                finally:
                    vhf = band
                    resume_stream(False)
            vhf = band
            configure()
            valid = False
            print('TUNE', json.dumps({'label': label, 'dial': dial}))

        def show_status(now_ms):
            if not ui:
                return
            status.dial = dial
            status.label = label
            status.utc_s = now_ms // 1000
            s = status.utc_s % 86400
            status.utc = '%02d:%02d:%02dZ' % (s // 3600, s // 60 % 60, s % 60)
            if clock.offset_ns is None:
                status.clock = 'NO CLOCK'
            elif clock.adjusted_ms:
                status.clock = '%s %+.1fs' % (clock.source, clock.adjusted_ms / 1000)
            else:
                status.clock = clock.source
            status.level = level_db(dsp.status(state)[0])
            status.muted = muted
            status.sd = store.ok
            status.logged = store.logged
            ui.show(status)

        def read_controls():
            """The next action from the buttons or the serial console, or
            None. Buttons: B1 previous preset, B2 mute, B3 next preset."""
            nonlocal line, esc, esc_at, held
            action = None
            typed = line
            event = keys.events.get() if keys else None
            if event:
                k = event.key_number
                if event.pressed:
                    pressed_at[k] = event.timestamp
                elif pressed_at[k] is not None:
                    pressed_at[k] = None
                    action = ('p', 'x', 'n')[k]
            ch = ''
            if held:
                ch, held = held, ''
            elif supervisor.runtime.serial_bytes_available:
                ch = sys.stdin.read(1)
            elif esc == '' and (supervisor.ticks_ms() - esc_at) & 0x1fffffff >= ESC_MS:
                ch = '\x00'           # (Esc on its own)
            if ch:
                if ch == '\x1b':
                    esc, ch = '', ''
                    esc_at = supervisor.ticks_ms()
                elif esc == '' and ch not in '[O':
                    # The Esc key on its own (arrow keys send Esc [ or Esc O):
                    # it cancels a command being typed, else it is an action.
                    # A key typed straight after it is kept for the next call.
                    esc = None
                    if ch != '\x00':
                        held = ch
                    ch = ''
                    if line is not None:
                        line = None
                    elif action is None:
                        action = 'esc'
                elif esc is not None:
                    esc += ch
                    if len(esc) > 1 and '@' <= ch <= '~' or esc[0] not in '[O' or len(esc) > 8:
                        if line is None:
                            action = ARROW_KEYS.get(esc, action)
                        esc = None
                    ch = ''
                if not ch:
                    pass
                elif line is not None:
                    if ch in '\r\n':
                        action, line = line, None
                    elif ch in '\x08\x7f':
                        line = line[:-1] if line else None
                    else:
                        line += ch
                elif ch in 'fFcC':
                    line = ch.lower()
                else:
                    action = ch.lower()
                if line != typed and ui_entry:
                    ui.entry(line)
            return action

        if ui:
            ui.ready()
        # The loop below must not allocate in the per-block path (a garbage
        # collection scans the heap and stalls for longer than the USB ring
        # holds); gc.collect() runs with the stream paused, late in a slot.
        views = [iqv[k:] for k in range(0, BLOCK, 64)]
        tick = supervisor.ticks_ms
        last_tick = last_ui = tick()
        blocks = 0
        running = True
        gc_at = int(GC_AT * RATE32)
        ui_by = int(UI_PAUSE_BY * RATE32)
        step_units = 0
        while running:
            t = tick()
            dt = (t - last_tick) & 0x1fffffff
            last_tick = t
            max_loop = max(max_loop, dt)
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
                src = out
                if replay:
                    # (8 kHz audio from the file; silence before the first)
                    src = rbuf
                    if not rfile or rfile.readinto(rbuf) < len(rbuf):
                        rbuf[:] = rzero
                if pos + SAMPLES >= SLOT_SAMPLES:
                    # A slot edge in this block: the samples before it end
                    # the slot, the rest start the next one.
                    k = max(0, SLOT_SAMPLES - pos)
                    b = (2 * k) // (4 if replay else 1)
                    if b:
                        _ft8.feed(feed, src[:b], specs[fill], ring)
                    end_slot((day, sec), True)
                    next_slot()
                    pos = pos + SAMPLES - SLOT_SAMPLES
                    if b < len(src):
                        if replay and rfile:
                            # The new slot's file starts at its edge.
                            rfile.readinto(rbuf)
                            b = 0
                        _ft8.feed(feed, src[b:], specs[fill], ring)
                else:
                    _ft8.feed(feed, src, specs[fill], ring)
                    pos += SAMPLES
                t3 = tick()
                if (t2 - t) & 0x1fffffff > stats['max_dsp_ms']:
                    stats['max_dsp_ms'] = (t2 - t) & 0x1fffffff
                if (t3 - t2) & 0x1fffffff > stats['max_feed_ms']:
                    stats['max_feed_ms'] = (t3 - t2) & 0x1fffffff
                if not muted:
                    audio.commit(SAMPLES)
                audio.service()
                blocks = (blocks + 1) & 0xffff
                if blocks & 15:
                    continue
                # Every 16th block (256 ms): lost packets move the clock on
                # (not when the stream filled them in with silence: sdr_usb).
                lost = stream.lost_packets
                if lost != lost_seen:
                    if not getattr(stream, 'fills_gaps', False):
                        pos += (lost - lost_seen) * PACKET_SAMPLES
                    lost_seen = lost
                now = time.monotonic()
                if seconds and now - start >= seconds:
                    running = False
                if now - last_log >= log_every:
                    last_log = now
                    info = {'t': round(now - start), 'lost': lost_total + lost_seen,
                            'loop_max_ms': max_loop, 'ui_max_ms': max_ui, 'stalls': stalls,
                            'audio': audio.stats(), 'dial': dial, 'clock': status.clock}
                    info.update(stats)
                    print('LIVE', json.dumps(info))
                    max_loop = 0
                    stalls = []
            elif not n:
                # Idle until the next USB data: one piece of other work.
                t = tick()
                if ui and (t - last_ui) & 0x1fffffff >= 1000:
                    # (this and the last slot's decodes before the decode
                    # steps: on a busy band a decode can run all of the
                    # next slot, and they would wait until one is early)
                    last_ui = t
                    show_status(clock.utc_ms())
                    t = (tick() - t) & 0x1fffffff
                    max_ui = max(max_ui, t)
                elif pending_log and store.ok:
                    try:
                        # (replayed slots carry live times: kept apart)
                        store.log(pending_log, 'REPLAY.TXT' if replay else 'ALL.TXT')
                    except OSError as error:
                        status.note = 'SD error'
                        print('SD_ERROR', error)
                    pending_log.clear()
                elif pending_rows and ui:
                    ui.add_decode(pending_rows.pop(0), my_call)
                    t = (tick() - t) & 0x1fffffff
                    max_ui = max(max_ui, t)
                elif ui_step and ui.step():
                    # (a strip of the help page)
                    t = (tick() - t) & 0x1fffffff
                    max_ui = max(max_ui, t)
                elif decoding is not None:
                    left = _ft8.decode_step(work, specs[int(decoding)], 1)
                    step_units += 1
                    if not left:
                        finish_decode()
                    elif not step_units & 15:
                        status.decoding = left
                    t = (tick() - t) & 0x1fffffff
                    if t > stats['max_step_ms']:
                        stats['max_step_ms'] = t
                elif store.wav:
                    try:
                        store.save_step(ring)
                    except OSError as error:
                        print('SAVE_ERROR', error)
                        store.wav = None
                elif replay_end:
                    running = False
                elif pos >= gc_at and decoding is None and (
                        slots_since_gc >= GC_EVERY
                        or paused_step_due(ui, pos, ui_by, ui_slot, sec)):
                    # Late in the slot, after its transmissions: the garbage
                    # collection, and the display's slow work (the map).
                    t = tick()
                    pause_stream()
                    try:
                        if paused_step_due(ui, pos, ui_by, ui_slot, sec):
                            ui_slot = sec
                            ui.paused_step()
                        if slots_since_gc >= GC_EVERY:
                            gc.collect()
                            slots_since_gc = 0
                    finally:
                        resume_stream(True)
                    t = (tick() - t) & 0x1fffffff
                    if t > stats['max_pause_ms']:
                        stats['max_pause_ms'] = t
                else:
                    time.sleep(.0005)
            if pending_rows and not ui:
                pending_rows.clear()

            action = read_controls()
            if (commands and block and not blocks & 15
                    and time.monotonic() - start >= commands[0][0]):
                action = commands.pop(0)[1]
            if action:
                if ui_command and ui.command(action):
                    if ui_paused and getattr(ui, 'switching', False):
                        # Another view (the m / l key): shown now, not at the
                        # slot's end. Before the slot's transmissions end the
                        # gap loses the slot being received.
                        pause_stream()
                        try:
                            ui.paused_step()
                        finally:
                            resume_stream(pos >= gc_at)
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
                    save_audio = not save_audio
                    print('SAVE_AUDIO', save_audio)
                elif action == 'c':
                    for k, e in enumerate(presets):
                        print('PRESET %d %s %s MHz' % (k, e[0], format_mhz(e[1])))
                elif action == '#':
                    info = {'dial': dial, 'utc': stamp(day, sec), 'pos': pos, 'valid': valid,
                            'decoding': decoding, 'clock': status.clock, 'dt_meds': dt_meds}
                    info.update(stats)
                    print('STATUS', json.dumps(info))
                elif action == 't':
                    pause_stream()
                    try:
                        clock.sync(2.0)
                    finally:
                        resume_stream(False)
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
    finally:
        if stream is not None:
            try:
                lost_total += stream.lost_packets
                stream.deinit()
            except Exception:
                pass
        if rfile:
            rfile.close()
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
        print('LIVE_END', json.dumps(stats))
        if ui:
            print('SCREEN', json.dumps(ui.screen()))


# ----------------------------------------------------------- log replay

MAX_GAP = 60                 # s: longer gaps between decodes are skipped in a log replay


class Console:
    """Keys on the serial console -> actions: a letter, 'esc' (the Esc
    key on its own), or for the arrow keys (ESC [ A..D) 'up', 'down',
    'right', 'left'."""
    ARROWS = {'A': 'up', 'B': 'down', 'C': 'right', 'D': 'left'}

    def __init__(self):
        self.esc = ''
        self.esc_at = 0
        self.held = ''               # a key typed straight after Esc, for the next poll()

    def poll(self):
        if self.held:
            ch, self.held = self.held, ''
        elif supervisor.runtime.serial_bytes_available:
            ch = sys.stdin.read(1)
        elif self.esc == '\x1b' and (supervisor.ticks_ms() - self.esc_at) & 0x1fffffff >= ESC_MS:
            self.esc = ''
            return 'esc'
        else:
            return None
        if self.esc:
            if self.esc == '\x1b' and ch not in '[O':
                # the Esc key on its own (arrow keys send Esc [ or Esc O)
                self.esc = ''
                self.held = ch
                return 'esc'
            self.esc += ch
            if len(self.esc) == 2:
                return None
            self.esc = ''
            return self.ARROWS.get(ch)
        if ch == '\x1b':
            self.esc = ch
            self.esc_at = supervisor.ticks_ms()
            return None
        return ch.lower()


def replay_mark(mark, ref):
    """A replay's start or end -> seconds since 1970: 'HH:MM' or
    'HH:MM:SS' (UTC: the first such time at or after ref, seconds since
    1970), or a slot stamp 'YYMMDD_HHMMSS' or the start of one
    ('261020_1256', '261020')."""
    from ft8_exchanges import stamp_seconds
    if ':' in mark:
        parts = [int(x) for x in mark.split(':')]
        t = (ref - ref % 86400 + parts[0] * 3600 + parts[1] * 60
             + (parts[2] if len(parts) > 2 else 0))
        return t if t >= ref else t + 86400
    return stamp_seconds((mark + ('_000000' if len(mark) == 6 else '000000'))[:13])


def replay_log(start=None, end=None, speed=1.0, display=True, display_options=None, my_call=MY_CALL,
               verbose=False, hold=False, commands=(), path=SD_DIR + '/ALL.TXT'):
    """Play the decode log (path, ALL.TXT) back onto the screen: the
    decodes from start to end, speed times as fast as they were heard.
    Each slot's decodes come at the slot's end, as when listening.

    start: None (the first decode), a line number (1: the first line),
    'HH:MM' / 'HH:MM:SS' (UTC: the first decode at or after that time of
    day) or a slot stamp or the start of one ('261020_1256', '261020').
    end: the same forms (a time of day: the first at or after start), or
    None for the end of the log. Gaps of more than MAX_GAP seconds
    between decodes are skipped (the exchanges on the screen age through
    them at once). Nothing is logged and the radio is not used. A display
    with learn() (the map) is given the decodes of the hour before start
    first, so it knows the grids a listener would have heard by then.

    display, display_options and my_call as for run(). verbose prints each
    decode ('FT8 {json}'). hold: at the end keep the last screen (and the
    keys) until Ctrl-C. commands: (seconds, key) pairs, for tests.

    Serial console: # status; ? help (on the screen; ? or Esc closes it);
    m or l the next view (with several); the map's keys (i or + / o or -
    zoom, r fit, v screenshot, the arrow keys or w a s d move the map).
    """
    from ft8_exchanges import stamp_seconds, GRID_SECONDS
    supervisor.runtime.autoreload = False
    mount_sd()
    gc.collect()
    ui = open_display(display, display_options)
    ui_paused = getattr(ui, 'paused_step', None)
    ui_command = getattr(ui, 'command', None)
    ui_learn = getattr(ui, 'learn', None)
    ui_step = getattr(ui, 'step', None)
    status = Status()
    status.clock = 'REPLAY' if speed == 1 else 'REPLAY x%g' % speed
    status.sd = True
    commands = sorted(commands)
    f = open(path)
    try:
        if ui:
            ui.message('Replay: finding %s in %s...' % (start or 'the start', path))
        number = 0
        start_s = None
        while True:
            line = f.readline()
            if not line:
                raise ValueError('%s has no decodes at or after %r' % (path, start))
            number += 1
            d = parse_all_txt(line)
            if d is None:
                continue
            t = stamp_seconds(d['t'])
            if start is None or isinstance(start, int) and number >= start:
                break
            if isinstance(start, str):
                if start_s is None:
                    start_s = replay_mark(start, t)
                if t >= start_s:
                    break
            if ui_learn and (start_s is None or t >= start_s - GRID_SECONDS):
                ui.learn(d, my_call)
        end_s = replay_mark(end, t) if isinstance(end, str) else None
        if ui and hasattr(ui, 'prepare'):
            ui.prepare()
        if ui:
            ui.ready()
        print('REPLAY_START', json.dumps({'line': number, 't': d['t'], 'speed': speed,
                                          'ui': getattr(ui, 'NAME', None)}))
        stats = {'decodes': 0, 'slots': 0, 'skipped_s': 0}
        # Log times are whole seconds since 1970, kept as integers (too
        # big for CircuitPython's floats); only the time since the start
        # is a float.
        due = t + SLOT               # when the next decode (d) comes, in the log's time
        last_due = None
        shift = due                  # log time = replay time * speed + shift
        console = Console()
        wall0 = time.monotonic_ns()
        last_ui = None
        done = False
        while True:
            now = last_due if done else shift + int((time.monotonic_ns() - wall0) * speed / 1e9)
            if not done and now < due and last_due is not None and now - last_due >= MAX_GAP:
                stats['skipped_s'] += due - now
                shift += due - now
                now = due
            while not done and due <= now:
                if due != last_due:
                    stats['slots'] += 1
                    status.slot_decodes = 0
                last_due = due
                stats['decodes'] += 1
                status.slot_decodes += 1
                status.logged = stats['decodes']
                status.dial = d['dial']
                if verbose:
                    print('FT8', json.dumps(d))
                if ui:
                    ui.add_decode(d, my_call)
                d = None
                while d is None:
                    line = f.readline()
                    if not line:
                        break
                    number += 1
                    d = parse_all_txt(line)
                if (d is None or isinstance(end, int) and number >= end
                        or end_s is not None and stamp_seconds(d['t']) >= end_s):
                    done = True
                    now = last_due
                    last_ui = None           # (the last screen)
                    print('REPLAY_END', json.dumps({'line': number, 'stats': stats}))
                else:
                    due = max(last_due, stamp_seconds(d['t']) + SLOT)
            w = time.monotonic_ns()
            if ui and (last_ui is None or w - last_ui >= 1000000000):
                last_ui = w
                status.utc_s = now
                s = status.utc_s % 86400
                status.utc = '%02d:%02d:%02dZ' % (s // 3600, s // 60 % 60, s % 60)
                status.label = ''
                for label, hz in PRESETS:
                    if hz == status.dial:
                        status.label = label
                ui.show(status)
            if ui_paused and ui.needs_pause:
                ui.paused_step()
                w = time.monotonic_ns() - w
                if w > 500000000:
                    wall0 += w           # (a map tile: the replay waits for it)
            if done and not hold:
                break
            action = console.poll()
            if commands and (time.monotonic_ns() - wall0) / 1e9 >= commands[0][0]:
                action = commands.pop(0)[1]
            if action and ui_command and ui.command(action):
                last_ui = None
            elif action == '#':
                print('STATUS', json.dumps({'line': number, 'utc': status.utc, 'done': done,
                                            'stats': stats}))
            if ui_step:
                while ui.step():         # (the help page: no radio to wait for)
                    pass
            time.sleep(0.02 if done else 0.005)
    finally:
        f.close()
        if ui:
            print('SCREEN', json.dumps(ui.screen()))
            if hasattr(ui, 'close'):
                ui.close()
