# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import array
import gc
import math
import os
import time
import random

import board
import audiobusio
import audiofilters
import audiomixer
import audiomp3
import audiotap
import displayio
import sdioio
import storage
import synthio
import framebufferio
import mipidsi
import adafruit_ili9881
import adafruit_gt911
import ulab.numpy as np
from ulab.utils import spectrogram

from winamp_skin import Skin, MainWindow, EqWindow, PlaylistWindow, EQ_SLIDERS, mmss

displayio.release_displays()

# display setup
i2c = board.I2C()
bus = mipidsi.Bus(
    minimum_frequency=adafruit_ili9881.RaspberryPiTouchDisplay2.MINIMUM_BUS_FREQUENCY,
    num_lanes=2,
)
panel = adafruit_ili9881.RaspberryPiTouchDisplay2(bus, i2c, color_depth=16)
display = framebufferio.FramebufferDisplay(panel)
display.auto_refresh = False
ts = adafruit_gt911.GT911(i2c)
W, H = display.width, display.height

# sd card
sd = sdioio.SDCard(
    clock=board.SD_CLK,
    command=board.SD_CMD,
    data=(board.SD_DATA0, board.SD_DATA1, board.SD_DATA2, board.SD_DATA3),
    frequency=25000000)
storage.mount(storage.VfsFat(sd), "/sd")

# asset locations
SKIN_DIRS = ("/sd/skins", "/skins")      # .wsz files and/or extracted folders
BASE_NAME = "base-2.91.wsz"              # fallback for sheets a skin lacks
MUSIC_ROOT = "/sd"                       # scanned recursively for .mp3 files

# I2S wiring
I2S_BIT_CLOCK = board.A0    # BCLK
I2S_WORD_SELECT = board.A1  # LRC
I2S_DATA = board.A2         # DIN
MAX_LEVEL = 0.5     # mixer level at 100% volume

# display and touch performance settings
REFRESH_FPS = 15      # screen updates per second (the main loop calls display.refresh())
VIS_FPS = 10          # visualizer frames per second; more than REFRESH_FPS would be wasted
VIS_FFT_SIZE = 128    # samples per FFT (power of 2): ~6 ms at 44.1 kHz, 172 Hz per bin
TOUCH_HZ = 8         # touch polls per second; each is an I2C read
SCROLL_FPS = 2        # playlist updates per second while dragging its scrollbar
                      # (each one redraws the whole list); the final spot shows on release
FOCUS_FOLLOWS_TOUCH = False  # True: a tapped window's title bar lights up, like Winamp.
                             # Off saves redrawing two full-width title bars per tap.
VIS_RANGE_DB = 50     # dB from full scale down to an empty bar
VIS_TILT_DB = 3       # dB per octave added toward treble, as music has less energy there

SCALE = W / 275  # full width: 720 / 275 = 2.618. Use 2 for crisp, even pixels.

# Equalizer: Winamp's 10 bands, each a peaking filter of +/-12 dB
EQ_FREQS = (60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000)
EQ_Q = 1.0  # band width of a single band's filter; higher = narrower
EQ_MAX_FILTERS = 4        # most biquads the EQ may use: each one costs CPU on every sample
EQ_MERGE_DB = 1.0         # neighbouring bands within this many dB share one filter
EQ_CORRECTION_STEPS = 6   # passes that fit the filters' combined curve to the sliders

# Winamp's built-in EQ presets, as stored in its winamp.q1 file (values 1..64,
# 33 = flat), via Webamp's presets/builtin.json: (name, preamp, 10 bands).
EQ_PRESETS = (
    ("Classical", 33, (33, 33, 33, 33, 33, 33, 20, 20, 20, 16)),
    ("Club", 33, (33, 33, 38, 42, 42, 42, 38, 33, 33, 33)),
    ("Dance", 33, (48, 44, 36, 32, 32, 22, 20, 20, 32, 32)),
    ("Laptop speakers/headphones", 33, (40, 50, 41, 26, 28, 35, 40, 48, 53, 56)),
    ("Large hall", 33, (49, 49, 42, 42, 33, 24, 24, 24, 33, 33)),
    ("Party", 33, (44, 44, 33, 33, 33, 33, 33, 33, 44, 44)),
    ("Pop", 33, (29, 40, 44, 45, 41, 30, 28, 28, 29, 29)),
    ("Reggae", 33, (33, 33, 31, 22, 33, 43, 43, 33, 33, 33)),
    ("Rock", 33, (45, 40, 23, 19, 26, 39, 47, 50, 50, 50)),
    ("Soft", 33, (40, 35, 30, 28, 30, 39, 46, 48, 50, 52)),
    ("Ska", 33, (28, 24, 25, 31, 39, 42, 47, 48, 50, 48)),
    ("Full Bass", 33, (48, 48, 48, 42, 35, 25, 18, 15, 14, 14)),
    ("Soft Rock", 33, (39, 39, 36, 31, 25, 23, 26, 31, 37, 47)),
    ("Full Treble", 33, (16, 16, 16, 25, 37, 50, 58, 58, 58, 60)),
    ("Full Bass & Treble", 33, (44, 42, 33, 20, 24, 35, 46, 50, 52, 52)),
    ("Live", 33, (24, 33, 39, 41, 42, 42, 39, 37, 37, 36)),
    ("Techno", 33, (45, 42, 33, 23, 24, 33, 45, 48, 48, 47)),
)

def px(v):
    return int(v * SCALE + 0.5)

# Stack main + EQ + playlist like classic Winamp
PL_HEIGHT = 116 + max(0, (int((H - px(232)) / SCALE) - 116) // 29) * 29
TOTAL_H = px(232 + PL_HEIGHT)
X0 = (W - px(275)) // 2
Y0 = max(0, (H - TOTAL_H) // 2)

# player state classes
class UI:
    def __init__(self):
        self.main = None          # the three windows, rebuilt when the skin changes
        self.eq = None
        self.pl = None
        self.skin_index = 0
        self.title_until = 0.0    # the title display shows a message (a preset name) until then
        self.held_win = None      # window and control under the finger since touch-down
        self.held_name = None
        self.last_xy = (0, 0)
        self.pending_drag = None  # (control, fx, fy): latest slider spot, applied per refresh
        self.last_scroll_drag = 0.0

class Player:
    def __init__(self):
        self.state = "stop"       # "play", "pause" or "stop"
        self.elapsed = 0.0
        self.scan_next = 0        # next playlist entry whose duration to read
        self.scan_start = 0.0
        self.preset_index = -1    # last preset loaded with the Presets button

class AudioChain:
    def __init__(self):
        self.decoder = None       # one MP3Decoder, reused for every track (saves memory)
        self.mixer = None         # mixer, tap and filter are rebuilt when the audio format changes
        self.fmt = None           # (sample rate, channels) they were built for
        self.tap = None           # audiotap.Tap between decoder and mixer (before volume)
        self.effect = None        # audiofilters.Filter running the EQ
        self.filters = []         # [(kind, synthio.Biquad)] currently in the filter chain

class Vis:
    def __init__(self):
        self.mode = "bars"        # tapping the visualizer cycles "bars" -> "scope" -> "off"
        self.buf = None           # one FFT's worth of samples, all channels
        self.window = None        # Hann window, so a pure tone shows as one bar, not a smear
        self.bands = []           # (first_bin, end_bin, tilt_db) for each of the 19 bars
        self.ref = 1.0            # FFT magnitude of a full-scale sine: the top of the scale
        self.channels = 1
        self.levels = [0.0] * 19

ui = UI()
player = Player()
chain = AudioChain()
vis = Vis()

# winamp skins
def list_skins():
    out = []
    for d in SKIN_DIRS:
        try:
            names = sorted(os.listdir(d))
        except OSError:
            continue
        for name in names:
            if name.startswith("."):
                continue
            path = d + "/" + name
            ext = name.lower()[-4:]
            if ext in (".wsz", ".zip") or os.stat(path)[0] & 0x4000:
                out.append(path)
    return out

skins = list_skins()
base_paths = [p for p in skins if p.endswith("/" + BASE_NAME)]
if not base_paths:
    raise RuntimeError("%s not found in %s" % (BASE_NAME, " or ".join(SKIN_DIRS)))
BASE_SKIN = base_paths[0]
print("Found %d skins; base: %s" % (len(skins), BASE_SKIN))
base = Skin(BASE_SKIN)
root = displayio.Group()
display.root_group = root

def save_settings():
    """The current windows' settings, to carry over to a new skin."""
    main, eq, pl = ui.main, ui.eq, ui.pl
    return {
        "volume": main.volume,
        "balance": main.balance,
        "main_toggles": [(n, main.toggled(n)) for n in ("shuffle", "repeat", "eq", "playlist")],
        "eq_toggles": [(n, eq.toggled(n)) for n in ("eq_on", "eq_auto")],
        "bands": [eq.values["band%d" % i] for i in range(10)],
        "preamp": eq.values["preamp"],
        "playlist": (pl.tracks, pl.current, pl.selected, pl.offset),
        "hidden": (eq.hidden, pl.hidden),
    }

def restore_settings(keep):
    """Apply what save_settings() returned to newly built windows."""
    main, eq, pl = ui.main, ui.eq, ui.pl
    main.set_volume(keep["volume"])
    main.set_balance(keep["balance"])
    for n, on in keep["main_toggles"]:
        main.set_toggle(n, on)
    for n, on in keep["eq_toggles"]:
        eq.set_toggle(n, on)
    eq.set_bands(keep["bands"], keep["preamp"])
    pl.tracks, pl.current, pl.selected, pl.offset = keep["playlist"]
    pl.refresh()
    eq.hidden, pl.hidden = keep["hidden"]

def load_skin(index):
    """Build all three windows from a skin, carrying settings across."""
    path = skins[index % len(skins)]
    keep = None
    if ui.main is not None:
        keep = save_settings()
        while len(root):
            root.pop()
        ui.main = ui.eq = ui.pl = None
        gc.collect()
    t0 = time.monotonic()
    skin = base if path == BASE_SKIN else Skin(path, fallback=base)
    ui.main = MainWindow(skin, X0, Y0, SCALE)
    ui.eq = EqWindow(skin, X0, Y0 + px(116), SCALE)
    ui.pl = PlaylistWindow(skin, X0, Y0 + px(232), SCALE, height=PL_HEIGHT)
    skin.release_sheets()
    if keep:
        restore_settings(keep)
    else:
        ui.main.set_toggle("eq", True)
        ui.main.set_toggle("playlist", True)
    root.append(ui.main)
    root.append(ui.eq)
    root.append(ui.pl)
    gc.collect()
    print("Loaded %s in %.2fs, free mem %d" % (path, time.monotonic() - t0, gc.mem_free()))
    show_state()

# music files
# Playlist tracks are (title, seconds, path). Titles come from file names;
# seconds start at 0 (shown blank) and are filled in a file at a time.
BITRATES = (
    (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320),  # MPEG1 layer III
    (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),      # MPEG2/2.5 layer III
)
SAMPLE_RATES = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000), 0: (11025, 12000, 8000)}
info = {}

def find_mp3s(folder):
    """All .mp3 files under folder (including subfolders), sorted by path."""
    found = []
    for name in os.listdir(folder):
        if name.startswith("."):
            continue
        path = folder + "/" + name
        if os.stat(path)[0] & 0x4000:
            found.extend(find_mp3s(path))
        elif name.lower().endswith(".mp3"):
            found.append(path)
    return sorted(found, key=lambda p: p.lower())

def title_from_path(path):
    """'/sd/Music/Artist_-_Song.mp3' -> 'Artist - Song'."""
    return path.rsplit("/", 1)[-1][:-4].replace("_", " ")

def read_mp3_start(path):
    """(bytes of audio after the ID3 tag, the first 4 KB of that audio)."""
    size = os.stat(path)[6]
    with open(path, "rb") as f:
        head = f.read(10)
        start = 0
        if head[:3] == b"ID3":  # skip the tag block (album art etc.)
            start = 10 + ((head[6] << 21) | (head[7] << 14) | (head[8] << 7) | head[9])
        f.seek(start)
        return size - start, f.read(4096)

def frame_header(buf, i):
    """(version, kbps, rate, samples_per_frame, stereo)"""
    b1, b2 = buf[i + 1], buf[i + 2]
    version = (b1 >> 3) & 3  # 3 = MPEG1, 2 = MPEG2, 0 = MPEG2.5
    # frame sync + layer III, valid bitrate and sample rate
    if (b1 & 0xE6) != 0xE2 or version == 1 or not 0 < b2 >> 4 < 15 or (b2 >> 2) & 3 == 3:
        return None
    kbps = BITRATES[version != 3][b2 >> 4]
    rate = SAMPLE_RATES[version][(b2 >> 2) & 3]
    spf = 1152 if version == 3 else 576  # samples per frame
    nxt = i + spf // 8 * kbps * 1000 // rate + ((b2 >> 1) & 1)
    if nxt < len(buf) and buf[nxt] != 0xFF:  # no next frame where expected
        return None
    return version, kbps, rate, spf, (buf[i + 3] >> 6) != 3

def mp3_info(path):
    """(seconds, kbps, khz, stereo) read from the start of an MP3"""
    audio_bytes, buf = read_mp3_start(path)
    i = buf.find(b"\xff")
    while 0 <= i < len(buf) - 48:
        header = frame_header(buf, i)
        if header is not None:
            version, kbps, rate, spf, stereo = header
            x = i + 4 + ((32 if stereo else 17) if version == 3 else (17 if stereo else 9))
            if buf[x:x + 4] in (b"Xing", b"Info") and buf[x + 7] & 1:
                seconds = int.from_bytes(buf[x + 8:x + 12], "big") * spf / rate
                kbps = int(audio_bytes * 8 / seconds / 1000 + 0.5) if seconds else kbps
            else:
                seconds = audio_bytes * 8 / (kbps * 1000)
            return int(seconds + 0.5), kbps, rate // 1000, stereo
        i = buf.find(b"\xff", i + 1)
    return None

def read_info(index):
    """Fill in one playlist track's duration (and bitrate etc.) if needed."""
    title, _, path = ui.pl.tracks[index]
    if path in info:
        return
    try:
        info[path] = mp3_info(path)
    except OSError as err:
        print("Can't read %s: %s" % (path, err))
        info[path] = None
        return
    if info[path] is None:
        print("No MP3 audio found in", path)
    else:
        ui.pl.update_track(index, (title, info[path][0], path))

def start_scan():
    """List the card's MP3s (names only, so this is quick)."""
    stop_playback()
    player.state, player.elapsed, player.scan_next = "stop", 0.0, 0
    player.scan_start = time.monotonic()
    info.clear()
    paths = find_mp3s(MUSIC_ROOT)
    ui.pl.set_tracks([(title_from_path(p), 0, p) for p in paths])
    print("Found %d MP3 files in %.1fs" % (len(paths), time.monotonic() - player.scan_start))

# I2S and filters
audio = audiobusio.I2SOut(I2S_BIT_CLOCK, I2S_WORD_SELECT, I2S_DATA)
FILTER_MODES = {"peak": synthio.FilterMode.PEAKING_EQ, "low": synthio.FilterMode.LOW_SHELF,
                "high": synthio.FilterMode.HIGH_SHELF}

# audio visualizer
def setup_vis(rate, channels):
    """Sizes and band edges for the visualizer at this sample rate."""
    n = VIS_FFT_SIZE
    vis.channels = channels
    vis.buf = array.array("h", [0] * (n * channels))
    vis.window = 0.5 - 0.5 * np.cos(np.arange(n) * (2 * math.pi / n))
    vis.ref = 32768 * n / 4  # full-scale sine through a Hann window
    # 19 bars spaced evenly on a log scale, like Winamp, 40 Hz .. 16 kHz
    lo, hi = 40.0, min(16000.0, rate * 0.45)
    edges = [lo * (hi / lo) ** (k / 19) for k in range(20)]
    bins = [max(1, int(f * n / rate + 0.5)) for f in edges]
    vis.bands = []
    for k in range(19):
        a = bins[k]
        b = max(a + 1, bins[k + 1])  # every bar gets at least one bin
        center = math.sqrt(edges[k] * edges[k + 1])
        vis.bands.append((a, b, VIS_TILT_DB * math.log(center / 1000) / math.log(2)))

def read_tap():
    """Newest audio as a mono float array, or None if not enough has played."""
    if chain.tap.available < len(vis.buf):
        return None
    chain.tap.readinto(vis.buf)
    chain.tap.clear()  # drop older audio so the next frame shows what's playing now
    x = np.array(np.frombuffer(vis.buf, dtype=np.int16), dtype=np.float)
    if vis.channels == 2:
        x = (x[0::2] + x[1::2]) * 0.5
    return x

def spectrum_levels(x):
    """19 bar heights (0..1) from one block of samples."""
    mags = spectrogram(x * vis.window)
    out = []
    for a, b, tilt in vis.bands:
        m = np.max(mags[a:b]) / vis.ref
        db = 8.685889638 * math.log(m + 1e-9) + tilt  # 20 * log10(m)
        out.append(max(0.0, min(1.0, (db + VIS_RANGE_DB) / VIS_RANGE_DB)))
    return out

def update_vis():
    if vis.mode == "off" or player.state != "play":
        return
    x = read_tap()
    if x is None:
        return
    if vis.mode == "bars":
        levels = vis.levels
        for i, target in enumerate(spectrum_levels(x)):
            # jump up, fall gradually, like Winamp's analyzer
            levels[i] = target if target > levels[i] else levels[i] * 0.85
        ui.main.vis.draw_bars(levels)
    else:
        ui.main.vis.draw_scope(list(x[::4] * (1 / 32768)))

def cycle_vis():
    vis.mode = {"bars": "scope", "scope": "off"}.get(vis.mode, "bars")
    for i in range(19):
        vis.levels[i] = 0.0
    ui.main.vis.peaks = [0.0] * 19
    ui.main.vis.clear()

# EQ
def slider_db(value):
    """EQ slider 0..100 -> -12..+12 dB."""
    return (value - 50) * 12 / 50

def apply_volume():
    """Volume (squared, for a natural feel), EQ preamp and balance -> mixer."""
    if chain.mixer is None:  # nothing has played yet
        return
    voice = chain.mixer.voice[0]
    level = (ui.main.volume / 100) ** 2 * MAX_LEVEL
    if ui.eq.toggled("eq_on"):
        level *= 10 ** (slider_db(ui.eq.values["preamp"]) / 20)
    voice.level = min(1.0, level)
    voice.panning = ui.main.balance / 100

def biquad_coefs(kind, f0, q, db, rate):
    """RBJ Audio EQ Cookbook biquad: (b0, b1, b2, a0, a1, a2). kind: "peak", "low" or "high"."""
    a = 10 ** (db / 40)
    w0 = 2 * math.pi * f0 / rate
    s, c = math.sin(w0), math.cos(w0)
    alpha = s / (2 * q)
    if kind == "peak":
        return (1 + alpha * a, -2 * c, 1 - alpha * a, 1 + alpha / a, -2 * c, 1 - alpha / a)
    sq = 2 * math.sqrt(a) * alpha
    if kind == "low":
        return (a * ((a + 1) - (a - 1) * c + sq), 2 * a * ((a - 1) - (a + 1) * c),
                a * ((a + 1) - (a - 1) * c - sq), (a + 1) + (a - 1) * c + sq,
                -2 * ((a - 1) + (a + 1) * c), (a + 1) + (a - 1) * c - sq)
    return (a * ((a + 1) + (a - 1) * c + sq), -2 * a * ((a - 1) + (a + 1) * c),
            a * ((a + 1) + (a - 1) * c - sq), (a + 1) - (a - 1) * c + sq,
            2 * ((a - 1) - (a + 1) * c), (a + 1) - (a - 1) * c - sq)

_band_trig = {}

def band_trig(rate):
    """cos/sin of w and 2w at each band centre, for this sample rate (cached)."""
    if rate not in _band_trig:
        t = []
        for f in EQ_FREQS:
            w = 2 * math.pi * f / rate
            t.append((math.cos(w), math.sin(w), math.cos(2 * w), math.sin(2 * w)))
        _band_trig[rate] = t
    return _band_trig[rate]

def magnitude_sq(p0, p1, p2, trig):
    """|p0 + p1 e^-jw + p2 e^-2jw| squared at one frequency.
    trig: (cos w, sin w, cos 2w, sin 2w) for that frequency."""
    c1, s1, c2, s2 = trig
    real = p0 + p1 * c1 + p2 * c2
    imag = p1 * s1 + p2 * s2
    return real * real + imag * imag

def response_db(coefs, trig):
    """A biquad's gain in dB at one frequency."""
    num = magnitude_sq(coefs[0], coefs[1], coefs[2], trig)
    den = magnitude_sq(coefs[3], coefs[4], coefs[5], trig)
    return 4.342944819 * math.log(num / den)  # 10 * log10

def bands_below_limit(rate):
    """How many EQ bands lie below 0.45 x the sample rate"""
    n = 0
    while n < len(EQ_FREQS) and EQ_FREQS[n] < rate * 0.45:
        n += 1
    return n

def group_spread(dbs, group):
    return max(dbs[k] for k in group) - min(dbs[k] for k in group)

def group_mean(dbs, group):
    return sum(dbs[k] for k in group) / len(group)

def group_bands(dbs, n):
    """Lists of neighbouring band indexes that will share one filter each."""
    groups = [[i] for i in range(n)]
    while len(groups) > 1:
        best = min(range(len(groups) - 1),
                   key=lambda k: group_spread(dbs, groups[k] + groups[k + 1]))
        n_active = sum(1 for g in groups if abs(group_mean(dbs, g)) >= 0.25)
        if (group_spread(dbs, groups[best] + groups[best + 1]) > EQ_MERGE_DB
                and n_active <= EQ_MAX_FILTERS):
            break
        groups[best:best + 2] = [groups[best] + groups[best + 1]]
    return groups

def group_filter(group, gain, n):
    """The filter for one group of bands: [kind, f0, Q, dB, bands]."""
    i, j = group[0], group[-1]
    if i == j:
        return ["peak", EQ_FREQS[i], EQ_Q, gain, group]
    if i == 0:  # run from the bottom band: low shelf, corner above the run
        above = EQ_FREQS[j + 1] if j + 1 < len(EQ_FREQS) else EQ_FREQS[j]
        return ["low", math.sqrt(EQ_FREQS[j] * above), 0.7071, gain, group]
    if j == n - 1:  # run to the top band: high shelf, corner below the run
        return ["high", math.sqrt(EQ_FREQS[i - 1] * EQ_FREQS[i]), 0.7071, gain, group]
    lo = math.sqrt(EQ_FREQS[i - 1] * EQ_FREQS[i])
    hi = math.sqrt(EQ_FREQS[j] * EQ_FREQS[j + 1])
    bw = 2 ** (math.log(hi / lo) / math.log(2))  # 2 ** octaves
    return ["peak", math.sqrt(lo * hi), math.sqrt(bw) / (bw - 1), gain, group]

def correct_gains(filters, dbs, n, rate):
    """Move each filter's gain toward the sliders it covers, a few times over."""
    trig = band_trig(rate)
    for _ in range(EQ_CORRECTION_STEPS):
        coefs = [biquad_coefs(k, f0, q, d, rate) for k, f0, q, d, _ in filters]
        got = [sum(response_db(c, trig[b]) for c in coefs) for b in range(n)]
        for flt in filters:
            err = sum(dbs[b] - got[b] for b in flt[4]) / len(flt[4])
            flt[3] = max(-18.0, min(18.0, flt[3] + 0.8 * err))

def plan_eq(dbs, rate):
    """Turn 10 slider settings into at most EQ_MAX_FILTERS biquads: [(kind, f0, Q, dB)]"""
    n = bands_below_limit(rate)
    filters = []  # [kind, f0, Q, dB, bands]
    for group in group_bands(dbs, n):
        gain = group_mean(dbs, group)
        if abs(gain) >= 0.25:
            filters.append(group_filter(group, gain, n))
    correct_gains(filters, dbs, n, rate)
    # a filter corrected to almost nothing would cost CPU for no audible change
    return [(k, f0, q, d) for k, f0, q, d, _ in filters if abs(d) >= 0.25]

def apply_eq():
    """EQ window -> filter chain and preamp"""
    on = ui.eq.toggled("eq_on")
    rate = chain.fmt[0] if chain.fmt else 44100
    plan = []
    if on:
        plan = plan_eq([slider_db(ui.eq.values["band%d" % i]) for i in range(10)], rate)
    effect = chain.effect
    if effect is not None:
        same = len(plan) == len(chain.filters) and all(
            p[0] == k for p, (k, _) in zip(plan, chain.filters))
        if plan and same:
            for (_, f0, q, db), (_, bq) in zip(plan, chain.filters):
                bq.frequency = f0
                bq.Q = q
                bq.A = 10 ** (db / 40)
        else:
            chain.filters = [(kind, synthio.Biquad(FILTER_MODES[kind], frequency=f0, Q=q,
                                                   A=10 ** (db / 40)))
                             for kind, f0, q, db in plan]
            effect.filter = tuple(bq for _, bq in chain.filters) if chain.filters else None
        effect.mix = 1.0 if plan else 0.0
    apply_volume()  # the preamp
    print("EQ %s: %d filter(s) for the curve" % ("on" if on else "off", len(plan)))

# audio playback
def rebuild_chain(fmt):
    """A Mixer, Tap and Filter only accept audio in their own format, so build
    them for this one (decoder -> tap -> mixer for volume -> EQ filter -> I2S)."""
    if chain.tap is not None:
        chain.tap.deinit()
    if chain.effect is not None:
        chain.effect.deinit()
    if chain.mixer is not None:
        chain.mixer.deinit()
    chain.mixer = audiomixer.Mixer(voice_count=1, sample_rate=fmt[0], channel_count=fmt[1],
                                   bits_per_sample=16, samples_signed=True)
    chain.tap = audiotap.Tap(capacity=0.1)
    chain.effect = audiofilters.Filter(sample_rate=fmt[0], channel_count=fmt[1], mix=0.0)
    chain.fmt = fmt
    chain.filters = []  # new filter: apply_eq() builds its chain
    setup_vis(*fmt)
    print("Audio: %d Hz, %d channel(s)" % fmt)

def start_track(index):
    """Start playing playlist entry `index` from the beginning."""
    path = ui.pl.tracks[index][2]
    stop_playback()
    try:
        # The decoder opens the file by name and keeps it open while it plays.
        if chain.decoder is None:
            chain.decoder = audiomp3.MP3Decoder(path)
        else:
            chain.decoder.file.close()  # the previous track's file
            chain.decoder.open(path)
        fmt = (chain.decoder.sample_rate, chain.decoder.channel_count)
        if fmt != chain.fmt:
            rebuild_chain(fmt)
        apply_eq()
        chain.tap.play(chain.decoder)
        chain.mixer.voice[0].play(chain.tap)
        chain.effect.play(chain.mixer)
        audio.play(chain.effect)
    except (OSError, ValueError, RuntimeError) as err:
        print("Can't play %s: %s" % (path, err))
        return False
    player.elapsed = 0.0
    return True

def stop_playback():
    """Stop the I2S output"""
    audio.stop()
    if chain.tap is not None:
        chain.tap.stop()
    if chain.mixer is not None:
        chain.mixer.voice[0].stop()

def show_state():
    pl = ui.pl
    track = pl.tracks[pl.current] if pl.current is not None and pl.tracks else None
    playing = player.state != "stop" and track is not None
    ui.main.set_state(player.state)
    if time.monotonic() < ui.title_until:
        pass  # a message (a preset name) is showing; the main loop restores the title
    elif track is not None:
        secs = " (%s)" % mmss(track[1]) if track[1] else ""
        ui.main.set_title("%d. %s%s" % (pl.current + 1, track[0], secs))
    else:
        ui.main.set_title("")
    data = info.get(track[2]) if playing else None
    if data:
        ui.main.set_info(data[1], data[2], data[3])
    else:  # stopped, or not known (yet)
        ui.main.set_info(None, None, None)
    ui.main.set_time(player.elapsed if playing else None)
    pl.set_mini_time(player.elapsed if playing else None)
    if not playing:
        ui.main.vis.clear()

def show_progress():
    """Clock, mini clock and seek bar while a track plays."""
    ui.main.set_time(player.elapsed)
    ui.pl.set_mini_time(player.elapsed)
    secs = ui.pl.tracks[ui.pl.current][1]
    if secs:  # length known: move the seek bar
        ui.main.set_position(min(1.0, player.elapsed / secs))

def go_to(index, play=True):
    """Make `index` the current track; play it, or just select it."""
    if not ui.pl.tracks:
        return
    ui.pl.set_current(index % len(ui.pl.tracks))
    read_info(ui.pl.current)  # make sure the playing track's length is known
    player.elapsed = 0.0
    if play:
        player.state = "play" if start_track(ui.pl.current) else "stop"
    elif player.state != "stop":
        stop_playback()
        player.state = "stop"
    show_state()

def next_track(step=1):
    if ui.main.toggled("shuffle") and len(ui.pl.tracks) > 1:
        go_to(random.randrange(len(ui.pl.tracks)))
    else:
        go_to(ui.pl.current + step)

def track_finished():
    """Called when the decoder runs out: advance, repeat, or stop."""
    if ui.main.toggled("repeat") or ui.pl.current < len(ui.pl.tracks) - 1:
        next_track()
    else:
        stop_playback()
        player.state, player.elapsed = "stop", 0.0
        show_state()

def set_window(name, visible):
    """Show/hide the EQ or playlist window and sync the main toggle."""
    win = ui.eq if name == "eq" else ui.pl
    win.hidden = not visible
    ui.main.set_toggle(name, visible)

def focus(win):
    for w in (ui.main, ui.eq, ui.pl):
        w.set_focused(w is win)

# buttons
def press_play():
    if player.state == "pause":
        audio.resume()
        player.state = "play"
    else:  # from stop, or restart the track if already playing (Winamp)
        player.state = "play" if start_track(ui.pl.current) else "stop"

def press_pause():
    if player.state == "play":
        audio.pause()
        player.state = "pause"
    elif player.state == "pause":
        audio.resume()
        player.state = "play"

def press_stop():
    stop_playback()
    player.state, player.elapsed = "stop", 0.0

def press_previous():
    go_to(ui.pl.current - 1, play=player.state == "play")

def eqf_to_slider(value):
    """A Winamp preset value (1..64) as an EQ slider position (0..100), as Webamp does."""
    return (value - 1) * 100 / 63

def next_preset():
    """Each tap of Presets loads the next of Winamp's presets."""
    player.preset_index = (player.preset_index + 1) % len(EQ_PRESETS)
    label, preamp, values = EQ_PRESETS[player.preset_index]
    ui.eq.set_bands([eqf_to_slider(v) for v in values], eqf_to_slider(preamp))
    apply_eq()
    ui.main.set_title("EQ: " + label)
    ui.title_until = time.monotonic() + 2.0

def next_skin():
    """For now, eject cycles through the skins."""
    ui.skin_index += 1
    load_skin(ui.skin_index)

def tap_row(name):
    """A tap on a playlist row selects it; a second tap plays it."""
    idx = ui.pl.row_index(name)
    if idx is not None and idx in ui.pl.selected:
        go_to(idx)
    else:
        ui.pl.select(idx)

TRANSPORT = ("play", "pause", "previous", "next")
BUTTON_ACTIONS = {
    "play": press_play,
    "pause": press_pause,
    "stop": press_stop,
    "previous": press_previous,
    "next": next_track,
    "eq_presets": next_preset,
    "visualizer": cycle_vis,
    "eject": next_skin,
    "pl_add": start_scan,  # "Add" re-reads the SD card for now
}
TODO_BUTTONS = ("options", "minimize", "shade", "close", "eq_shade", "eq_auto")

def on_release(win, name):
    """A button was released over itself."""
    if name in TRANSPORT and ui.pl.current is None:
        return  # nothing in the playlist yet
    if name in BUTTON_ACTIONS:
        BUTTON_ACTIONS[name]()
    elif name in ("shuffle", "repeat", "eq_on"):
        win.set_toggle(name, not win.toggled(name))
        if name == "eq_on":
            apply_eq()
    elif name in ("eq", "playlist"):
        set_window(name, not ui.main.toggled(name))
    elif name in ("eq_close", "pl_close"):
        set_window("eq" if name == "eq_close" else "playlist", False)
    elif name.startswith("row"):
        tap_row(name)
    elif name.startswith("pl_") or name in TODO_BUTTONS:
        print("todo:", name)
    show_state()

# touch
SLIDERS = {"volume", "balance", "position", "pl_scroll"} | set(EQ_SLIDERS)

def on_drag(name, fx, fy):
    """A slider moved to (fx, fy), as fractions across and down it."""
    if name == "volume":
        ui.main.set_volume(fx * 100)
        apply_volume()
    elif name == "balance":
        ui.main.set_balance(fx * 200 - 100)
        apply_volume()
    elif name in EQ_SLIDERS:
        ui.eq.set_slider(name, EqWindow.value_from_fy(fy), redraw=False)
    elif name == "pl_scroll":
        ui.pl.scroll_to_fraction(fy)

def apply_drag(final=False):
    """Act on the latest slider position"""
    if ui.pending_drag is None:
        return
    if ui.pending_drag[0] == "pl_scroll" and not final:
        t = time.monotonic()
        if t - ui.last_scroll_drag < 1 / SCROLL_FPS:
            return  # keep it pending
        ui.last_scroll_drag = t
    on_drag(*ui.pending_drag)
    ui.pending_drag = None

def touch_down(tx, ty):
    """A new touch: find the control under it and show it pressed."""
    for win in (ui.main, ui.eq, ui.pl):
        if win.contains(tx, ty):
            if FOCUS_FOLLOWS_TOUCH:
                focus(win)
            name = win.hit_test(*win.to_skin(tx, ty))[0]
            if name is not None:
                ui.held_win, ui.held_name = win, name
                win.press(name, True)
            break

def touch_up():
    """The finger lifted: finish a slider, or fire the button it was on."""
    apply_drag(final=True)  # the slider's final position
    win, name = ui.held_win, ui.held_name
    ui.held_win = ui.held_name = None
    win.press(name, False)
    if name in EQ_SLIDERS:
        ui.eq.set_bands([ui.eq.values["band%d" % i] for i in range(10)], ui.eq.values["preamp"])
        apply_eq()
    elif name not in SLIDERS and win.hit_test(*win.to_skin(*ui.last_xy))[0] == name:
        on_release(win, name)

def handle_touch():
    touches = ts.touch
    if touches:
        tx, ty = touches[0]["x"], touches[0]["y"]
        ui.last_xy = (tx, ty)
        if ui.held_name is None:
            touch_down(tx, ty)
        if ui.held_name in SLIDERS:
            win, name = ui.held_win, ui.held_name
            ui.pending_drag = (name,) + win.fraction(name, *win.to_skin(tx, ty))
    elif ui.held_name is not None:
        touch_up()

ui.skin_index = skins.index(BASE_SKIN)
load_skin(ui.skin_index)
start_scan()
show_state()

last_scroll = last_vis = last_tick = last_touch = last_info = last_refresh = time.monotonic()
while True:
    now = time.monotonic()
    if now - last_touch >= 1 / TOUCH_HZ:
        handle_touch()
        last_touch = now
    # fill in one track's duration at a time; while music plays, only every
    # half second so we don't compete with the decoder for the SD card
    if player.scan_next < len(ui.pl.tracks) and (
            player.state != "play" or now - last_info >= 0.5):
        last_info = now
        read_info(player.scan_next)
        player.scan_next += 1
        if player.scan_next == len(ui.pl.tracks):
            print("All durations read in %.1fs" % (time.monotonic() - player.scan_start))
    if player.state == "play":
        player.elapsed += now - last_tick
        if not chain.tap.playing:  # the file has finished (a tap plays silence after)
            track_finished()
        else:
            show_progress()
    last_tick = now
    if now - last_vis >= 1 / VIS_FPS:
        last_vis = now
        update_vis()
    if now - last_scroll >= 0.25:
        if ui.title_until and now >= ui.title_until:  # message done: back to the title
            ui.title_until = 0.0
            show_state()
        ui.main.scroll_title()
        last_scroll = now
    if now - last_refresh >= 1 / REFRESH_FPS:
        apply_drag()  # a slider being dragged moves once per refresh
        display.refresh()  # no target_frames_per_second: draws now, never waits
        last_refresh = now
