# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""ADS-B receiver: listens to 1090 MHz on the Fruit Jam or the Metro
ESP32-P4 with a NESDR SMArt v5 and decodes the aircraft's Mode S / ADS-B
messages on the board.

On the Fruit Jam the radio is read in snapshots (adsb_radio: 940 us of
2 MS/s I/Q each, about 80 a second; full-speed USB cannot carry the whole
stream). On the Metro ESP32-P4's high-speed USB host it is read as a
stream, in long chunks (adsb_radio.STREAM_CHUNK). Each snapshot or chunk
is decoded while the next one comes in (the bytes wait in the USB ring,
or the RTL2832U's FIFO), by _adsb (preamble search,
Viterbi demodulation, CRC checks); messages are decoded by adsb_parse into a table of aircraft,
printed on the serial console ('ADSB {json}' lines), shown on the screen
(adsb_ui: the aircraft on a map, or a table; DVI via picodvi on the Fruit
Jam, the TFT shield on the Metro ESP32-P4) and appended to /sd/adsb/adsb.txt
("2026-10-21 19:31:05 UTC *8DA8921D5821F582805DC7BDB69D;", one per message,
the raw hex in the AVR format that dump1090 and friends read).

Times are UTC from the ESP32-C6's clock, which nina-fw sets by SNTP when
the board is on Wi-Fi (CIRCUITPY_WIFI_SSID / _PASSWORD in settings.toml).
On boards with the wifi module (the Metro ESP32-P4) the receiver asks an
NTP server itself. Without either the log shows seconds since start-up.

Serial console (or a USB keyboard on the Fruit Jam): # status, h (or l
with the table) list the aircraft, q quiet / verbose (one line per message or not), g<gain>
then Enter: tuner gain in tenths of a dB (g alone: the tuner's AGC), v
save the screen as /sd/adsb/screen_NNNN.bmp, ? help (a page on the screen: what
it shows, the keys; ? or Esc closes it); map: i or + / o or - zoom in / out,
the arrow keys or w a s d move it, r fit the aircraft on it, k / l select the
next / previous aircraft (its details below the map), Esc deselect, j hide / show the
tags (but the selected one's), z clear the map (asks:
y forgets every aircraft, n keeps them). Esc also cancels a g command
being typed.

replay() plays the log back onto the screen instead of listening:
replay(start='19:36') from the first message at or after 19:36
UTC (or '2026-10-21 19:36:00', or a line number: start=1200), to
end= (the same forms) or the end of the log, at speed= times real time.
Gaps of more than MAX_GAP seconds in the log are skipped.
"""
# The native module and the decoder's buffers first, into internal SRAM.
# pylint: disable=wrong-import-order
import _adsb
from adsb_buffers import (state as _state, records as _records, snapshots as _snapshots,
                          MAX_RECORDS)
import time
import gc
import os
import sys
import json
import math
import struct
import board
import busio
import supervisor
import adsb_radio
import adsb_parse
from adsb_ui import Status, open_display

# pylint: disable=import-outside-toplevel, broad-except, too-many-return-statements
# pylint: disable=too-many-locals, too-many-branches, too-many-statements, too-many-nested-blocks

HOME = None                  # (lat, lon): distances and directions
GAIN = None                  # tenths of a dB, None: the tuner's AGC
DISPLAY = 'map'              # 'map', 'table' or False (adsb_ui)
UI_PAUSE_EVERY = 2.0         # s between the display's paused steps (map tile downloads)
SD_DIR = '/sd/adsb'
UI_EVERY = 1.0               # s between screen updates
LOG_EVERY = 60               # s between LIVE lines
GC_EVERY = 10.0              # s between garbage collections (a few ms each; the radio waits)
EXPIRE = 300                 # s: aircraft not heard this long are forgotten
MAX_GAP = 30                 # s: longer gaps in the log are skipped in a replay
NTP_SERVER = 'pool.ntp.org'  # (boards with the wifi module)
# Esc with nothing after it for this long: the Esc key (not an arrow key)
ESC_MS = 30
STATS = ('snapshots', 'samples', 'candidates', 'demods', 'accepted', 'df17', 'df11', 'ap', 'fixed',
         'crc_fail', 'ap_unknown', 'fixed2', 'noise_x16')


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
        if self.offset_ns is None:
            return None
        return (time.monotonic_ns() + self.offset_ns) // 1000000000

    def stamp(self):
        """'2026-10-21 19:31:05 UTC', or '+1234 s' (since start-up)."""
        t = self.utc()
        if t is None:
            return '+%d s' % (time.monotonic_ns() // 1000000000)
        day, s = divmod(t, 86400)
        y, m, d = civil(day)
        return '%04d-%02d-%02d %02d:%02d:%02d UTC' % (y, m, d, s // 3600, s // 60 % 60, s % 60)

    def hms(self):
        t = self.utc()
        if t is None:
            return '+%ds' % (time.monotonic_ns() // 1000000000)
        s = t % 86400
        return '%02d:%02d:%02dZ' % (s // 3600, s // 60 % 60, s % 60)


# -------------------------------------------------------------------- SD

def sd_card():
    """The board's SD card: the Fruit Jam's (on its own SPI bus), the Metro
    ESP32-P4's 4-bit SDIO slot, else the TFT shield's (adsb_tft)."""
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
    import adsb_tft
    return adsb_tft.sd_card()


def mount_sd():
    """True if /sd is a mounted card (mounting it if the supervisor did not)."""
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
    """adsb.txt (one message per line) in SD_DIR."""

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

    def log(self, lines, name='adsb.txt'):
        with open(self.dir + '/' + name, 'a') as f:
            for line in lines:
                f.write(line)
                f.write('\n')
        self.logged += len(lines)

    def next_name(self, prefix, ext):
        names = [n for n in os.listdir(self.dir) if n.startswith(prefix) and n.endswith(ext)]
        k = len(prefix)
        numbers = [int(n[k:k + 4]) for n in names if n[k:k + 4].isdigit()]
        return '%s/%s%04d%s' % (self.dir, prefix, max(numbers or [-1]) + 1, ext)


class Console:
    """Keys on the serial console (or a USB keyboard) -> actions: a
    letter, 'g...' (a line ended by Enter), 'esc' (the Esc key on its
    own; while a line is typed it cancels it), or for the arrow keys
    (ESC [ A..D) 'up', 'down', 'right', 'left'."""
    ARROWS = {'A': 'up', 'B': 'down', 'C': 'right', 'D': 'left'}

    def __init__(self):
        self.line = None
        self.esc = ''
        self.esc_at = 0
        self.held = ''               # a key typed straight after Esc, for the next poll()

    def _esc(self):
        """The Esc key on its own: it cancels a line being typed, else 'esc'."""
        if self.line is not None:
            self.line = None
            return None
        return 'esc'

    def poll(self):
        if self.held:
            ch, self.held = self.held, ''
        elif supervisor.runtime.serial_bytes_available:
            ch = sys.stdin.read(1)
        elif self.esc == '\x1b' and (supervisor.ticks_ms() - self.esc_at) & 0x1FFFFFFF >= ESC_MS:
            self.esc = ''
            return self._esc()
        else:
            return None
        if self.esc == '\x1b' and ch not in '[O':
            # the Esc key on its own (arrow keys send Esc [ or Esc O)
            self.esc = ''
            self.held = ch
            return self._esc()
        if self.esc:
            self.esc += ch
            if len(self.esc) == 2 and ch in '[O':
                return None
            self.esc = ''
            return self.ARROWS.get(ch)
        if ch == '\x1b':
            self.esc = ch
            self.esc_at = supervisor.ticks_ms()
        elif self.line is not None:
            if ch in '\r\n':
                action, self.line = self.line, None
                return action
            if ch in '\x08\x7f':
                self.line = self.line[:-1] if self.line else None
            else:
                self.line += ch
        elif ch in 'gG':
            self.line = 'g'
        elif ch.strip():
            return ch.lower()
        return None


def decode_slices(size, samples=4096, overlap=512, edge=8):
    """A read of size bytes in pieces for _adsb.decode() (which takes at most
    samples): [(start, end, lo, hi)], byte offsets, overlapping by overlap
    samples so that a 112-bit message (240 samples) is whole in one of them.
    A piece keeps the messages that start at lo <= sample < hi: each message
    in an overlap is taken from one piece only. One piece for a snapshot."""
    step = samples - overlap
    pieces = []
    start = 0
    while True:
        end = min(start + samples, size // 2)
        last = end == size // 2
        pieces.append((2 * start, 2 * end, 0 if start == 0 else edge,
                       65536 if last else step + edge))
        if last:
            return pieces
        start += step


def dbfs(signal_x16):
    """The fitted pulse amplitude (x16) -> dB relative to a full-scale 8-bit sample."""
    return 8.685889638 * math.log(max(signal_x16, 1) / 16 / 128)   # (no math.log10 here)


# -------------------------------------------------------------------- run

def run(seconds=0, home=HOME, gain=GAIN, display=DISPLAY, verbose=True, log_every=LOG_EVERY,
        clock_wait=10.0, commands=(), map_centre=None, map_zoom=None):
    """Run the receiver. seconds=0 runs forever.

    home: (lat, lon) of the antenna (distances, directions; also helps the
    first positions). gain: tuner gain in tenths of a dB, None for the
    tuner's AGC. display: 'map', 'table', False, or a display object
    (adsb_ui). map_centre: (lat, lon) to centre the map on without home
    (else the first position heard); map_zoom: adsb_ui_map.ZOOM.
    verbose: an 'ADSB' console line per message. commands: (seconds,
    command) pairs fed to the command handler, for unattended tests.
    """
    supervisor.runtime.autoreload = False
    store = Store(SD_DIR)
    gc.collect()
    ui = open_display(display, home, map_centre, map_zoom)
    status = Status()
    status.sd = store.ok
    clock = Clock()
    if ui:
        ui.message('Reading the time from Wi-Fi (NTP)...')
    clock.sync(clock_wait)
    status.clock = clock.source
    if ui:
        ui.prepare()
        ui.message('Starting the radio...')
    radio = adsb_radio.AdsbRadio(gain=gain)
    _adsb.reset(_state)
    # A map centre also serves as the receiver's rough position (CPR
    # decoding from one frame needs one within ~300 km).
    tracker = adsb_parse.Tracker(home, expire=EXPIRE, reference=map_centre)
    commands = sorted(commands)
    records = _records
    rv = memoryview(records)
    views = [memoryview(b) for b in _snapshots]
    slices = decode_slices(radio.snapshot)
    pending_log = []
    stats = {'messages': 0, 'positions': 0, 'timeouts': 0, 'max_handle_ms': 0, 'max_ui_ms': 0}
    recent = []                  # monotonic times of the messages in the last minute
    try:
        radio.start()
        if ui:
            ui.ready()
        start = time.monotonic()
        last_ui = last_log = last_gc = last_pause = start
        snapshots_at_log = 0
        print('LIVE_START', json.dumps({'gain': gain, 'clock': clock.source, 'sd': store.ok,
                                        'ui': ui.NAME if ui else None, 'home': home}))
        console = Console()
        running = True
        cur = 0                  # the snapshot being read
        ready = False            # the other one is waiting to be decoded
        while running:
            radio.restart_fifo()
            # The last snapshot is decoded (with all the other work) while
            # this one comes in: its bytes wait in the USB ring (streaming:
            # in the RTL2832U's FIFO).
            now = time.monotonic()
            if ready:
                view = views[cur ^ 1]
                handled = 0              # ms handling the messages (not decoding)
                for p0, p1, lo, hi in slices:
                    n = _adsb.decode(view[p0:p1], _state, records, int(now))
                    if not n:
                        continue
                    t0 = supervisor.ticks_ms()
                    stamp = clock.stamp()
                    for i in range(min(n, MAX_RECORDS)):
                        r = rv[i * 24:(i + 1) * 24]
                        if not lo <= r[6] | r[7] << 8 < hi:
                            continue         # (the slice next to this one has it)
                        msg = bytes(r[8:8 + r[0]])
                        level = dbfs(r[2] | r[3] << 8)
                        m, a, moved = tracker.add(msg, now, level)
                        stats['messages'] += 1
                        recent.append(now)
                        if moved:
                            stats['positions'] += 1
                        pending_log.append('%s *%s;' % (stamp, msg.hex().upper()))
                        if verbose:
                            m['hex'] = msg.hex()
                            m['dbfs'] = round(level, 1)
                            if r[1] & 1:
                                m['fixed'] = 1
                            if moved:
                                m['lat'] = round(a.lat, 5)
                                m['lon'] = round(a.lon, 5)
                            m.pop('cpr', None)
                            print('ADSB', json.dumps(m))
                    handled += (supervisor.ticks_ms() - t0) & 0x3FFFFFFF
                if handled > stats['max_handle_ms']:
                    stats['max_handle_ms'] = handled

            # once a second: screen, log, housekeeping
            if now - last_ui >= UI_EVERY:
                last_ui = now
                while recent and now - recent[0] > 60:
                    recent.pop(0)
                if pending_log and store.ok:
                    try:
                        store.log(pending_log)
                    except OSError as error:
                        status.note = 'SD error'
                        print('SD_ERROR', error)
                pending_log.clear()
                tracker.prune(now)
                if ui:
                    t0 = supervisor.ticks_ms()
                    status.utc = clock.hms()
                    status.messages = stats['messages']
                    status.per_minute = len(recent) * 60 / min(60, max(1, now - start))
                    status.heard = (100 * radio.snapshots * radio.snapshot / 4000000
                                    / max(1, now - start))
                    status.logged = store.logged
                    status.reference = tracker.reference
                    ui.show(status, tracker.sorted(now), now)
                    t = (supervisor.ticks_ms() - t0) & 0x3FFFFFFF
                    if t > stats['max_ui_ms']:
                        stats['max_ui_ms'] = t
                if seconds and now - start >= seconds:
                    running = False
            if ui and ui.needs_pause and now - last_pause >= UI_PAUSE_EVERY:
                # (map tiles: a download and a conversion, seconds)
                radio.stop()
                try:
                    ui.paused_step()
                finally:
                    radio.start()
                last_pause = time.monotonic()
            if now - last_gc >= GC_EVERY:
                last_gc = now
                gc.collect()
            if now - last_log >= log_every:
                a = _adsb.stats(_state)
                per_s = (radio.snapshots - snapshots_at_log) / (now - last_log)
                info = {'t': round(now - start), 'snapshots_per_s': round(per_s, 1),
                        'aircraft': len(tracker.aircraft), 'free_kb': gc.mem_free() // 1024}
                info.update(stats)
                info.update(zip(STATS, a))
                print('LIVE', json.dumps(info))
                last_log = now
                snapshots_at_log = radio.snapshots

            # console
            action = console.poll()
            if commands and now - start >= commands[0][0]:
                action = commands.pop(0)[1]
            used = ui.command(action) if action and ui else False
            if used:
                last_ui = 0
                if used == 'clear':
                    tracker.clear()
            elif action == '#':
                info = {'utc': clock.stamp(), 'aircraft': len(tracker.aircraft),
                        'snapshots': radio.snapshots, 'gain': radio.gain}
                info.update(stats)
                info.update(zip(STATS, _adsb.stats(_state)))
                print('STATUS', json.dumps(info))
            elif action in ('l', 'h'):
                for a in tracker.sorted(now):
                    print('AIRCRAFT', json.dumps(a.json(now, home)))
            elif action == 'q':
                verbose = not verbose
            elif action == 'v' and ui and store.ok:
                name = store.next_name('screen_', '.bmp')
                if ui.snapshot(name) is False:
                    print('NO_SCREENSHOT', 'this screen cannot be saved')
                else:
                    print('SCREENSHOT', name)
            elif action and action[0] == 'g':
                try:
                    g = int(action[1:]) if action[1:].strip() else None
                    radio.stop()
                    radio.set_gain(g)
                    radio.start()
                    print('GAIN', g)
                except ValueError:
                    print('BAD_COMMAND', action)

            if radio.read(views[cur]):
                ready = True
                cur ^= 1
            else:
                ready = False
                stats['timeouts'] += 1
    finally:
        radio.stop()
        if pending_log and store.ok:
            try:
                store.log(pending_log)
            except OSError:
                pass
        stats['aircraft'] = len(tracker.aircraft)
        stats.update(zip(STATS, _adsb.stats(_state)))
        print('LIVE_END', json.dumps(stats))
        for a in tracker.sorted(time.monotonic()):
            print('AIRCRAFT', json.dumps(a.json(time.monotonic(), home)))
        if ui:
            print('SCREEN', json.dumps(ui.screen()))
            ui.close()


# ----------------------------------------------------------------- replay

class ReplayClock(Clock):
    """The log's time (self.t) instead of the board's."""

    def __init__(self):
        super().__init__()
        self.t = 0

    def utc(self):
        return self.t


def stamp_seconds(stamp):
    """A log line's time ('2026-10-21 19:31:05 UTC' or '+1234 s') ->
    seconds since 1970 (or since that run's start-up)."""
    if stamp[0] == '+':
        return int(stamp[1:].split()[0])
    return (days(int(stamp[0:4]), int(stamp[5:7]), int(stamp[8:10])) * 86400
            + int(stamp[11:13]) * 3600 + int(stamp[14:16]) * 60 + int(stamp[17:19]))


def reached(line, number, mark):
    """Is the log at mark (a line number, 1 the first; or a time: '19:36',
    '19:36:30' or '2026-10-21 19:36', UTC) by this line?"""
    if isinstance(mark, int):
        return number >= mark
    if ':' in mark[:3]:
        return line[11:11 + len(mark)] >= mark
    return line[:len(mark)] >= mark


def replay(start=None, end=None, speed=1.0, home=HOME, display=DISPLAY, verbose=False,
           commands=(), map_centre=None, map_zoom=None, hold=False, path=SD_DIR + '/adsb.txt'):
    """Play the log (path) back onto the screen: the messages from start
    (None: the first; a line number or a time, see reached()) to end
    (None: the last), speed times as fast as they were heard. Nothing is
    logged. hold: at the end keep the last screen (and the console's
    keys) until Ctrl-C. The other arguments and the console as run()."""
    supervisor.runtime.autoreload = False
    store = Store(SD_DIR)
    gc.collect()
    ui = open_display(display, home, map_centre, map_zoom)
    status = Status()
    status.sd = store.ok
    status.heard = None
    clock = ReplayClock()
    f = open(path)
    try:
        if ui:
            ui.message('Replay: finding %s in the log...' % (start or 'the start'))
        number = 0
        line = None
        while True:
            line = f.readline()
            if not line:
                raise ValueError('the log has nothing at or after %r' % (start,))
            number += 1
            if ' *' in line and (start is None or reached(line, number, start)):
                break
        first = number
        stamp = line[:line.index(' *')]
        clock.source = 'NO CLOCK' if stamp[0] == '+' else 'NTP'
        status.clock = clock.source
        shift = stamp_seconds(stamp)           # log time = replay time + shift
        last = 0
        if ui:
            ui.prepare()
        tracker = adsb_parse.Tracker(home, expire=EXPIRE, reference=map_centre)
        commands = sorted(commands)
        console = Console()
        stats = {'messages': 0, 'positions': 0, 'skipped_s': 0}
        recent = []
        print('REPLAY_START', json.dumps({'line': first, 'utc': stamp, 'speed': speed,
                                          'ui': ui.NAME if ui else None}))
        if ui:
            ui.ready()
        wall0 = time.monotonic()
        last_ui = last_gc = -UI_EVERY
        done = False
        while True:
            now = last if done else (time.monotonic() - wall0) * speed
            while not done and last <= now:
                # the message in line, at log time stamp: due now (or late)
                try:
                    msg = bytes.fromhex(line[line.index(' *') + 2:line.index(';')])
                    m, a, moved = tracker.add(msg, last)
                except ValueError:
                    m = None
                if m is not None:
                    stats['messages'] += 1
                    recent.append(last)
                    if moved:
                        stats['positions'] += 1
                    if verbose:
                        m['hex'] = msg.hex()
                        if moved:
                            m['lat'] = round(a.lat, 5)
                            m['lon'] = round(a.lon, 5)
                        m.pop('cpr', None)
                        print('ADSB', json.dumps(m))
                line = f.readline()
                number += 1
                if not line or (end is not None and reached(line, number, end)):
                    done = True
                    last_ui = -UI_EVERY            # (the last screen)
                    clock.t = last + shift
                    print('REPLAY_END', json.dumps({'line': number, 'utc': clock.stamp(),
                                                    'stats': stats}))
                    if not hold:
                        break
                elif ' *' in line:
                    t = stamp_seconds(line[:line.index(' *')]) - shift
                    if t - last > MAX_GAP:
                        stats['skipped_s'] += t - last - 1
                        shift += t - last - 1
                        t = last + 1
                    last = max(t, last)
            if done and not hold:
                break
            if now - last_ui >= UI_EVERY:
                last_ui = now
                while recent and now - recent[0] > 60:
                    recent.pop(0)
                tracker.prune(now)
                clock.t = int(now) + shift
                if ui:
                    status.utc = clock.hms()
                    status.messages = stats['messages']
                    status.per_minute = len(recent) * 60 / min(60, max(1, now))
                    status.reference = tracker.reference
                    ui.show(status, tracker.sorted(now), now)
            if ui and ui.needs_pause:
                # (a map tile: the replay waits for it)
                t0 = time.monotonic()
                ui.paused_step()
                wall0 += time.monotonic() - t0
            if now - last_gc >= GC_EVERY * speed:
                last_gc = now
                gc.collect()
            action = console.poll()
            if commands and time.monotonic() - wall0 >= commands[0][0]:
                action = commands.pop(0)[1]
            used = ui.command(action) if action and ui else False
            if used:
                last_ui = -UI_EVERY
                if used == 'clear':
                    tracker.clear()
            elif action in ('l', 'h'):
                for a in tracker.sorted(now):
                    print('AIRCRAFT', json.dumps(a.json(now, home)))
            elif action == 'q':
                verbose = not verbose
            elif action == 'v' and ui and store.ok:
                name = store.next_name('screen_', '.bmp')
                if ui.snapshot(name) is False:
                    print('NO_SCREENSHOT', 'this screen cannot be saved')
                else:
                    print('SCREENSHOT', name)
            if done:
                time.sleep(0.02)
    finally:
        f.close()
        if ui:
            print('SCREEN', json.dumps(ui.screen()))
            ui.close()
