# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# pylint: disable=global-statement,invalid-name,redefined-outer-name,too-many-lines

"""Star Trek TNG Data Dispenser Prop - Environmental Monitor.

Displays CO2, humidity, temperature and battery level as
shaped colored bars on the ESP32-S3 Reverse TFT Feather.

Button map:
  D0 short: rescan animation (bars) / return to bars
  D0 double: demo mode (auto-cycle all screens)
  D0 long:  CO2 offset calibration
  D1 short: toggle Fahrenheit / Celsius
  D1 long:  toggle LCARS name badge
  D2 short: cycle views (bars -> stats -> CO2 graph)
  D2 long:  toggle display brightness
  D0+D2 long: sleep mode (any button wakes)
  5min idle: auto sleep"""

import time
import struct
import alarm
import board
import busio
import digitalio
import displayio
import vectorio
import terminalio
from adafruit_display_text import label

# ============================================================
#  TUNABLES
# ============================================================
CO2_MIN = 400
CO2_MAX = 2000
CO2_WARN = 700
CO2_FLOOR_PCT = 8
TEMP_MIN = 15.0
TEMP_MAX = 40.0
UPDATE_INTERVAL = 2
HAPTIC_COOLDOWN = 30
I2C_RETRIES = 10
LONG_PRESS_MS = 2000    # hold time for long press
IDLE_SLEEP_S = 300      # 5 min idle -> deep sleep
DIM_BRIGHTNESS = 0.15   # dimmed display brightness
FULL_BRIGHTNESS = 1.0

# ============================================================
#  NAME BADGE - edit these to personalise your prop
# ============================================================
BADGE_NAME = "P. RUIZ"           # your name (2x scale)
BADGE_TITLE = "ENGINEERING"      # department / role
BADGE_ID = "NCC-1701-D"          # registry / ID number
BADGE_PROJECT = "TNG DATA DISPENSER"  # project name
BADGE_QR_URL = "https://learn.adafruit.com/u/pixil3d"

# ============================================================
#  COLORS
# ============================================================
COLOR_CO2 = 0x4466FF
COLOR_HUMIDITY = 0x44FF66
COLOR_TEMP = 0xFFCC00
COLOR_BATTERY = 0xFF4444
BG_COLOR = 0x000000
BAR_COLORS = (
    COLOR_CO2, COLOR_HUMIDITY, COLOR_TEMP, COLOR_BATTERY
)

DIM_FACTOR = 5
GRAD_DIM_FACTOR = 20
SOFT_DIM_FACTOR = 4
MID_DIM_FACTOR = 10


def dim_color(color, factor=DIM_FACTOR):
    """Return a dimmed version of a 24-bit color."""
    r = ((color >> 16) & 0xFF) // factor
    g = ((color >> 8) & 0xFF) // factor
    b = (color & 0xFF) // factor
    return (r << 16) | (g << 8) | b


TRACK_COLORS = tuple(
    dim_color(c, DIM_FACTOR) for c in BAR_COLORS
)
GRAD_COLORS = tuple(
    dim_color(c, GRAD_DIM_FACTOR) for c in BAR_COLORS
)
SOFT_COLORS = tuple(
    dim_color(c, SOFT_DIM_FACTOR) for c in BAR_COLORS
)
OUTLINE_COLORS = tuple(
    dim_color(c, MID_DIM_FACTOR) for c in BAR_COLORS
)

# ============================================================
#  LAYOUT - 240 x 135 display
# ============================================================
DISPLAY_W = 240
DISPLAY_H = 135
NUM_BARS = 4
BAR_W = 45
BAR_GAP = 10
BAR_H = 90
BAR_Y = 8
LABEL_Y = BAR_Y + BAR_H + 16
TOTAL_BAR_W = NUM_BARS * BAR_W + (NUM_BARS - 1) * BAR_GAP
X_OFFSET = (DISPLAY_W - TOTAL_BAR_W) // 2

# ============================================================
#  BAR SHAPE
# ============================================================
PEAK_L = 11
PEAK_R = 13
TAPER_L = 2
TAPER_R = 19
SHELF_L_Y = 57
SHELF_R_Y = 56
NUM_PTS = 8
OUTLINE_PX = 1


def bar_shape():
    """Full bar outline as 8 points."""
    return [
        (PEAK_L, 0), (PEAK_R, 0),
        (TAPER_R, SHELF_R_Y), (BAR_W, SHELF_R_Y),
        (BAR_W, BAR_H), (0, BAR_H),
        (0, SHELF_L_Y), (TAPER_L, SHELF_L_Y),
    ]


def outline_shape():
    """Bar outline expanded by OUTLINE_PX."""
    o = OUTLINE_PX
    return [
        (PEAK_L - o, 0), (PEAK_R + o, 0),
        (TAPER_R + o, SHELF_R_Y),
        (BAR_W + o, SHELF_R_Y - o),
        (BAR_W + o, BAR_H + o),
        (0 - o, BAR_H + o),
        (0 - o, SHELF_L_Y - o),
        (TAPER_L - o, SHELF_L_Y),
    ]


def mask_shape(pct):
    """Mask polygon covering unfilled portion."""
    fill_y = max(int(BAR_H * (100 - pct) / 100), 1)
    if fill_y <= SHELF_R_Y:
        frac = fill_y / SHELF_R_Y
        ml = int(PEAK_L + (TAPER_L - PEAK_L) * frac)
        mr = int(PEAK_R + (TAPER_R - PEAK_R) * frac)
        return [
            (PEAK_L, 0), (PEAK_R, 0),
            (mr, fill_y), (mr, fill_y),
            (mr, fill_y), (ml, fill_y),
            (ml, fill_y), (ml, fill_y),
        ]
    return [
        (PEAK_L, 0), (PEAK_R, 0),
        (TAPER_R, SHELF_R_Y), (BAR_W, SHELF_R_Y),
        (BAR_W, fill_y), (0, fill_y),
        (0, SHELF_L_Y), (TAPER_L, SHELF_L_Y),
    ]


def soft_mask_shape(pct):
    """Soft anti-alias mask expanded 1px into fill."""
    o = 1
    fill_y = max(int(BAR_H * (100 - pct) / 100), 1)
    if fill_y <= SHELF_R_Y:
        frac = fill_y / SHELF_R_Y
        ml = int(PEAK_L + (TAPER_L - PEAK_L) * frac)
        mr = int(PEAK_R + (TAPER_R - PEAK_R) * frac)
        fy = min(fill_y + o, BAR_H)
        return [
            (PEAK_L, 0), (PEAK_R, 0),
            (mr + o, fy), (mr + o, fy),
            (mr + o, fy), (ml - o, fy),
            (ml - o, fy), (ml - o, fy),
        ]
    fy = min(fill_y + o, BAR_H)
    return [
        (PEAK_L, 0), (PEAK_R, 0),
        (TAPER_R + o, SHELF_R_Y),
        (BAR_W + o, SHELF_R_Y),
        (BAR_W + o, fy), (0, fy),
        (0, SHELF_L_Y), (TAPER_L - o, SHELF_L_Y),
    ]


# ============================================================
#  GRADIENT BACKGROUND
# ============================================================
GRAD_STEPS = 64


def lerp_color(c1, c2, t):
    """Linearly interpolate two 24-bit colours."""
    r1 = (c1 >> 16) & 0xFF
    g1 = (c1 >> 8) & 0xFF
    b1 = c1 & 0xFF
    r2 = (c2 >> 16) & 0xFF
    g2 = (c2 >> 8) & 0xFF
    b2 = c2 & 0xFF
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return (r << 16) | (g << 8) | b


def build_gradient():
    """Build a 1-row gradient bitmap."""
    bmp = displayio.Bitmap(
        TOTAL_BAR_W, 1, GRAD_STEPS
    )
    pal = displayio.Palette(GRAD_STEPS)
    centres = []
    for i in range(NUM_BARS):
        centres.append(
            i * (BAR_W + BAR_GAP) + BAR_W // 2
        )
    for i in range(GRAD_STEPS):
        t = i / (GRAD_STEPS - 1)
        pal[i] = _grad_at(t, centres)
    for x_pos in range(TOTAL_BAR_W):
        t = x_pos / (TOTAL_BAR_W - 1)
        idx = int(t * (GRAD_STEPS - 1))
        bmp[x_pos, 0] = idx
    return bmp, pal


def _grad_at(t, centres):
    """Gradient colour at position t."""
    x_pos = t * (TOTAL_BAR_W - 1)
    for i in range(NUM_BARS - 1):
        if x_pos <= centres[i + 1]:
            span = centres[i + 1] - centres[i]
            local_t = (x_pos - centres[i]) / span
            local_t = max(0.0, min(1.0, local_t))
            return lerp_color(
                GRAD_COLORS[i], GRAD_COLORS[i + 1],
                local_t
            )
    return GRAD_COLORS[-1]


# ============================================================
#  SLEEP MEMORY - persist CO2 offset across deep sleep
# ============================================================
# Bytes 0-3: CO2 offset as signed int (big-endian)
co2_offset = 0
try:
    raw = bytes(alarm.sleep_memory[0:4])
    co2_offset = struct.unpack('>i', raw)[0]
    if abs(co2_offset) > 1000:
        co2_offset = 0
    if co2_offset != 0:
        print("Restored CO2 offset: {}".format(
            co2_offset
        ))
except (IndexError, ValueError, TypeError):
    co2_offset = 0


def save_co2_offset():
    """Write co2_offset to alarm.sleep_memory."""
    try:
        packed = struct.pack('>i', co2_offset)
        for i in range(4):
            alarm.sleep_memory[i] = packed[i]
    except (IndexError, TypeError):
        pass

# ============================================================
#  DISPLAY INIT
# ============================================================
display = board.DISPLAY
display.brightness = FULL_BRIGHTNESS
is_dimmed = False
root = displayio.Group()

bg_pal = displayio.Palette(1)
bg_pal[0] = BG_COLOR
root.append(
    vectorio.Rectangle(
        pixel_shader=bg_pal,
        width=DISPLAY_W,
        height=DISPLAY_H,
        x=0, y=0,
    )
)

status_lbl = label.Label(
    terminalio.FONT,
    text="SCANNING I2C...",
    color=0xFFFFFF,
    anchor_point=(0.5, 0.5),
    anchored_position=(
        DISPLAY_W // 2, DISPLAY_H // 2
    ),
)
root.append(status_lbl)
display.root_group = root

# ============================================================
#  BUTTON SETUP
# ============================================================
btn_d0 = digitalio.DigitalInOut(board.D0)
btn_d0.direction = digitalio.Direction.INPUT
btn_d0.pull = digitalio.Pull.UP

btn_d1 = digitalio.DigitalInOut(board.D1)
btn_d1.direction = digitalio.Direction.INPUT
btn_d1.pull = digitalio.Pull.DOWN

btn_d2 = digitalio.DigitalInOut(board.D2)
btn_d2.direction = digitalio.Direction.INPUT
btn_d2.pull = digitalio.Pull.DOWN


# ============================================================
#  I2C BUS
# ============================================================
def try_i2c():
    """Attempt to create I2C bus."""
    methods = []
    if hasattr(board, "STEMMA_I2C"):
        methods.append(("STEMMA_I2C", board.STEMMA_I2C))
    if hasattr(board, "I2C"):
        methods.append(("I2C", board.I2C))
    for method_name, method in methods:
        try:
            bus = method()
            print("I2C via board.{}".format(
                method_name
            ))
            return bus
        except RuntimeError:
            pass
    try:
        bus = busio.I2C(board.SCL, board.SDA)
        print("I2C via busio.I2C")
        return bus
    except RuntimeError:
        pass
    return None


i2c = None
for attempt in range(I2C_RETRIES):
    i2c = try_i2c()
    if i2c is not None:
        break
    status_lbl.text = "I2C retry {}/{}".format(
        attempt + 1, I2C_RETRIES
    )
    time.sleep(2)

if i2c is None:
    status_lbl.text = "NO I2C - CHECK WIRING"
    while True:
        time.sleep(10)

# ============================================================
#  SENSOR + BATTERY INIT
# ============================================================
import adafruit_stcc4  # pylint: disable=import-outside-toplevel,wrong-import-position
import adafruit_max1704x  # pylint: disable=import-outside-toplevel,wrong-import-position

sensor = None
batt = None

try:
    sensor = adafruit_stcc4.STCC4(i2c)
    sensor.continuous_measurement = True
    print("STCC4 detected.")
except (ValueError, RuntimeError, OSError) as err:
    print("STCC4 not found: {}".format(err))

try:
    batt = adafruit_max1704x.MAX17048(i2c)
    print("MAX17048 detected.")
except (ValueError, RuntimeError, OSError) as err:
    print("MAX17048 not found: {}".format(err))

haptic = None
drv_effect = None
try:
    import adafruit_drv2605  # pylint: disable=import-outside-toplevel,wrong-import-position
    haptic = adafruit_drv2605.DRV2605(i2c)
    drv_effect = adafruit_drv2605.Effect
    print("DRV2605 detected.")
except (ImportError, ValueError, RuntimeError, OSError):
    print("No haptic motor found.")

# ============================================================
#  BUILD BAR GRAPH UI
# ============================================================
root.pop()  # remove status label

# Gradient background
grad_bmp, grad_pal = build_gradient()
grad_grid = displayio.TileGrid(
    grad_bmp,
    pixel_shader=grad_pal,
    width=1,
    height=BAR_H,
    tile_width=TOTAL_BAR_W,
    tile_height=1,
    x=X_OFFSET,
    y=BAR_Y,
)
root.append(grad_grid)

bar_masks = []
soft_masks = []
pct_labels = []

for i in range(NUM_BARS):
    bx = X_OFFSET + i * (BAR_W + BAR_GAP)

    out_pal = displayio.Palette(1)
    out_pal[0] = OUTLINE_COLORS[i]
    root.append(
        vectorio.Polygon(
            pixel_shader=out_pal,
            points=outline_shape(),
            x=bx, y=BAR_Y,
        )
    )

    trk_pal = displayio.Palette(1)
    trk_pal[0] = TRACK_COLORS[i]
    root.append(
        vectorio.Polygon(
            pixel_shader=trk_pal,
            points=bar_shape(),
            x=bx, y=BAR_Y,
        )
    )

    fill_pal = displayio.Palette(1)
    fill_pal[0] = BAR_COLORS[i]
    root.append(
        vectorio.Polygon(
            pixel_shader=fill_pal,
            points=bar_shape(),
            x=bx, y=BAR_Y,
        )
    )

    soft_pal = displayio.Palette(1)
    soft_pal[0] = SOFT_COLORS[i]
    soft = vectorio.Polygon(
        pixel_shader=soft_pal,
        points=bar_shape(),
        x=bx, y=BAR_Y,
    )
    root.append(soft)
    soft_masks.append(soft)

    mask = vectorio.Polygon(
        pixel_shader=trk_pal,
        points=bar_shape(),
        x=bx, y=BAR_Y,
    )
    root.append(mask)
    bar_masks.append(mask)

    lbl = label.Label(
        terminalio.FONT,
        text="---",
        color=BAR_COLORS[i],
        anchor_point=(0.5, 0.0),
        anchored_position=(
            bx + BAR_W // 2, LABEL_Y
        ),
    )
    root.append(lbl)
    pct_labels.append(lbl)

# ============================================================
#  CHARGING INDICATOR
# ============================================================
BOLT_POINTS = [
    (4, 0), (7, 0), (3, 5),
    (6, 5), (1, 12), (4, 6), (1, 6),
]
BATT_BAR_X = X_OFFSET + 3 * (BAR_W + BAR_GAP)
BATT_BASE_MID = BAR_Y + SHELF_R_Y + (
    BAR_H - SHELF_R_Y
) // 2
BOLT_X = BATT_BAR_X + 3
BOLT_Y = BATT_BASE_MID - 6  # center 12px bolt

bolt_pal = displayio.Palette(1)
bolt_pal[0] = 0xFFFFFF
bolt_shape_obj = vectorio.Polygon(
    pixel_shader=bolt_pal,
    points=BOLT_POINTS,
    x=BOLT_X, y=BOLT_Y,
)
bolt_visible = False
is_charging = False
charge_blink = False

# In-bar voltage label (right of bolt)
volt_lbl = label.Label(
    terminalio.FONT,
    text="",
    color=0xFFFFFF,
    anchor_point=(0.5, 0.5),
    anchored_position=(
        BATT_BAR_X + 28, BATT_BASE_MID
    ),
)
volt_visible = False

# ============================================================
#  STATE
# ============================================================
last_haptic = 0.0
use_fahrenheit = True
co2_min = 9999
co2_max = 0
last_activity = time.monotonic()

SCAN_STEPS = 20
SCAN_DELAY = 0.03
SCAN_STAGGER = 3

# CO2 history for LCARS graph
HISTORY_SIZE = 120     # 2 hours of data
SAMPLE_INTERVAL = 60   # seconds between samples
co2_history = []
hum_history = []
temp_history = []
last_sample = 0.0

# View modes
VIEW_BARS = 0
VIEW_STATS = 1
VIEW_CO2 = 2
VIEW_HUM = 3
VIEW_TEMP = 4
VIEW_ABOUT = 5
NUM_CYCLE_VIEWS = 5    # bars->stats->co2->hum->temp
current_view = VIEW_BARS

# Graph layout constants
GRAPH_X = 56           # left edge of graph area
GRAPH_Y = 10
GRAPH_W = 180          # pixels wide
GRAPH_H = 100          # pixels tall
GRAPH_MIN_BAR = 1      # minimum bar width
GRAPH_MAX_BAR = 12     # maximum bar width (few samples)
GRAPH_GAP_PX = 1       # gap between bars
GRAPH_CO2_LO = 300     # CO2 graph floor (below 400)
GRAPH_CO2_HI = 1200    # CO2 graph ceiling
GRAPH_HUM_LO = 0       # humidity floor
GRAPH_HUM_HI = 100     # humidity ceiling
GRAPH_TEMP_LO = 50     # temp floor (F)
GRAPH_TEMP_HI = 100    # temp ceiling (F)
GRAPH_TEMP_LO_C = 10   # temp floor (C)
GRAPH_TEMP_HI_C = 38   # temp ceiling (C)


def graph_layout(n_samples, zoomed=False):
    """Compute bar width, slot, offset for n samples.

    Normal: starts at half width, grows to full.
    Zoomed: always fills full width with last
    ZOOM_SAMPLES readings.
    Returns (bar_px, slot, x_start, count)."""
    if zoomed:
        count = min(n_samples, ZOOM_SAMPLES)
    else:
        count = n_samples

    if count <= 0:
        return GRAPH_MAX_BAR, GRAPH_MAX_BAR + 1, 0, 0

    if zoomed:
        avail_w = GRAPH_W
    else:
        fill_frac = min(
            0.5 + 0.5 * count / HISTORY_SIZE, 1.0
        )
        avail_w = int(GRAPH_W * fill_frac)

    bar_px = max(
        (avail_w - (count - 1) * GRAPH_GAP_PX)
        // count,
        GRAPH_MIN_BAR,
    )
    bar_px = min(bar_px, GRAPH_MAX_BAR)
    slot = bar_px + GRAPH_GAP_PX
    total_w = count * slot - GRAPH_GAP_PX

    x_start = (GRAPH_W - total_w) // 2
    x_start = max(x_start, 0)

    return bar_px, slot, x_start, count

# LCARS colors
LCARS_GOLD = 0xFFCC66
LCARS_BLUE = 0x6688CC
LCARS_ORANGE = 0xFF9944
LCARS_GREEN = 0x44CC66
LCARS_YELLOW = 0xCCCC44
LCARS_RED = 0xCC4444

# Min/max for all sensors
hum_min = 999
hum_max = 0
temp_min_val = 999.0
temp_max_val = -999.0

# CO2 graph display group
graph_group = None
graph_bmp = None
graph_pal = None
graph_co2_lbl = None
graph_minmax_lbl = None

# Humidity graph display group
hum_graph_group = None
hum_graph_bmp = None
hum_graph_pal = None
hum_graph_lbl = None
hum_minmax_lbl = None

# Temperature graph display group
temp_graph_group = None
temp_graph_bmp = None
temp_graph_pal = None
temp_graph_lbl = None
temp_minmax_lbl = None

# Stats display group (built on first show)
stats_group = None
stats_uptime_lbl = None
stats_samples_lbl = None
stats_co2_lbl = None
stats_hum_lbl = None
stats_temp_lbl = None
stats_batt_lbl = None

# About display group (built on first show)
about_group = None
boot_time = time.monotonic()

# Graph zoom
ZOOM_SAMPLES = 15      # 15 minutes of data when zoomed
graph_zoomed = False


# ============================================================
#  HELPERS
# ============================================================
def clamp(val, lo, hi):
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, val))


def to_pct(val, lo, hi):
    """Map val from [lo..hi] to 0-100."""
    return int(
        clamp((val - lo) / (hi - lo) * 100, 0, 100)
    )


def update_bar(idx, pct, txt):
    """Set bar fill height and label text."""
    soft_masks[idx].points = soft_mask_shape(pct)
    bar_masks[idx].points = mask_shape(pct)
    pct_labels[idx].text = txt


def scan_buzz():
    """Three quick haptic pulses for scan events."""
    if haptic is None:
        return
    for pulse in range(3):  # pylint: disable=unused-variable
        haptic.sequence[0] = drv_effect(47)
        haptic.play()
        time.sleep(0.15)
        haptic.stop()
        if pulse < 2:
            time.sleep(0.1)


def buzz_alert(force=False):
    """Double-pulse haptic warning."""
    global last_haptic
    if haptic is None:
        return
    now = time.monotonic()
    if not force:
        if now - last_haptic < HAPTIC_COOLDOWN:
            return
    last_haptic = now
    for pulse in range(2):  # pylint: disable=unused-variable
        haptic.sequence[0] = drv_effect(47)
        haptic.play()
        time.sleep(0.3)
        haptic.stop()
        if pulse == 0:
            time.sleep(0.15)


def scan_animation(targets):
    """Tricorder-style sweep with staggered text."""
    scan_buzz()
    for i in range(NUM_BARS):
        pct_labels[i].text = ""
        time.sleep(0.08)
    total = SCAN_STEPS + SCAN_STAGGER * 3
    for frame in range(total):
        for i in range(NUM_BARS):
            local = frame - i * SCAN_STAGGER
            if local < 0:
                pct = 0
            elif local >= SCAN_STEPS:
                pct = 100
            else:
                pct = int(local * 100 / SCAN_STEPS)
            soft_masks[i].points = soft_mask_shape(
                pct
            )
            bar_masks[i].points = mask_shape(pct)
        time.sleep(SCAN_DELAY)
    time.sleep(0.3)
    for frame in range(total):
        for i in range(NUM_BARS):
            local = frame - i * SCAN_STAGGER
            t_pct, t_txt = targets[i]
            if local < 0:
                pct = 100
            elif local >= SCAN_STEPS:
                pct = t_pct
            else:
                frac = local / SCAN_STEPS
                pct = int(
                    100 + (t_pct - 100) * frac
                )
            soft_masks[i].points = soft_mask_shape(
                pct
            )
            bar_masks[i].points = mask_shape(pct)
            if local >= SCAN_STEPS:
                pct_labels[i].text = t_txt
        time.sleep(SCAN_DELAY)


def rescan_animation(current, targets):
    """Rescan: current -> 100% -> 0% -> targets.

    Labels stay on screen throughout. current is a list
    of current pct values, targets is (pct, txt) pairs.
    """
    scan_buzz()

    # Capture starting percentages
    starts = list(current)

    # Phase 1: fill from current to 100% (no stagger)
    for frame in range(SCAN_STEPS):
        frac = frame / SCAN_STEPS
        for i in range(NUM_BARS):
            pct = int(starts[i] + (
                100 - starts[i]) * frac)
            soft_masks[i].points = soft_mask_shape(
                pct
            )
            bar_masks[i].points = mask_shape(pct)
        time.sleep(SCAN_DELAY)

    # Brief hold at peak
    for i in range(NUM_BARS):
        soft_masks[i].points = soft_mask_shape(100)
        bar_masks[i].points = mask_shape(100)
    time.sleep(0.15)

    # Phase 2: drain 100% -> 0% (no stagger)
    for frame in range(SCAN_STEPS):
        frac = frame / SCAN_STEPS
        pct = int(100 - 100 * frac)
        for i in range(NUM_BARS):
            soft_masks[i].points = soft_mask_shape(
                pct
            )
            bar_masks[i].points = mask_shape(pct)
        time.sleep(SCAN_DELAY)

    time.sleep(0.15)

    # Phase 3: fill 0% -> targets with stagger
    total = SCAN_STEPS + SCAN_STAGGER * 3
    for frame in range(total):
        for i in range(NUM_BARS):
            local = frame - i * SCAN_STAGGER
            t_pct, t_txt = targets[i]
            if local < 0:
                pct = 0
            elif local >= SCAN_STEPS:
                pct = t_pct
            else:
                frac = local / SCAN_STEPS
                pct = int(t_pct * frac)
            soft_masks[i].points = soft_mask_shape(
                pct
            )
            bar_masks[i].points = mask_shape(pct)
            if local >= SCAN_STEPS:
                pct_labels[i].text = t_txt
        time.sleep(SCAN_DELAY)


def solo_scan(idx, current_pct, target_pct, target_txt):
    """Rescan a single bar: current -> 100% -> 0% -> target.

    Label stays visible throughout."""
    scan_buzz()
    start = current_pct

    # Phase 1: fill from current to 100%
    for frame in range(SCAN_STEPS):
        frac = frame / SCAN_STEPS
        pct = int(start + (100 - start) * frac)
        soft_masks[idx].points = soft_mask_shape(pct)
        bar_masks[idx].points = mask_shape(pct)
        time.sleep(SCAN_DELAY)

    soft_masks[idx].points = soft_mask_shape(100)
    bar_masks[idx].points = mask_shape(100)
    time.sleep(0.15)

    # Phase 2: drain 100% to 0%
    for frame in range(SCAN_STEPS):
        frac = frame / SCAN_STEPS
        pct = int(100 - 100 * frac)
        soft_masks[idx].points = soft_mask_shape(pct)
        bar_masks[idx].points = mask_shape(pct)
        time.sleep(SCAN_DELAY)

    time.sleep(0.15)

    # Phase 3: fill 0% to target
    for frame in range(SCAN_STEPS):
        frac = frame / SCAN_STEPS
        pct = int(target_pct * frac)
        soft_masks[idx].points = soft_mask_shape(pct)
        bar_masks[idx].points = mask_shape(pct)
        time.sleep(SCAN_DELAY)

    update_bar(idx, target_pct, target_txt)


def show_message(txt, duration=2.0):
    """Overlay a message with dark background bar."""
    msg_bg_pal = displayio.Palette(1)
    msg_bg_pal[0] = 0x000000
    bg_bar = vectorio.Rectangle(
        pixel_shader=msg_bg_pal,
        width=DISPLAY_W,
        height=24,
        x=0,
        y=DISPLAY_H // 2 - 12,
    )
    msg = label.Label(
        terminalio.FONT,
        text=txt,
        color=0xFFFFFF,
        anchor_point=(0.5, 0.5),
        anchored_position=(
            DISPLAY_W // 2, DISPLAY_H // 2
        ),
    )
    root.append(bg_bar)
    root.append(msg)
    time.sleep(duration)
    root.remove(msg)
    root.remove(bg_bar)


def do_co2_calibrate():
    """Software CO2 offset calibration."""
    global co2_offset
    if sensor is None:
        show_message("NO SENSOR")
        return
    show_message("CALIBRATING...")
    try:
        raw = sensor.CO2
    except (RuntimeError, OSError):
        show_message("READ ERROR")
        return
    co2_offset = 400 - int(raw)
    save_co2_offset()
    show_message(
        "OFFSET: {}".format(co2_offset), 2.0
    )
    print("CO2 offset set to {}".format(co2_offset))


def build_graph():
    """Build the LCARS-style CO2 graph display group."""
    global graph_group, graph_bmp, graph_pal
    global graph_co2_lbl, graph_minmax_lbl

    graph_group = displayio.Group()

    # Black background
    gbg_pal = displayio.Palette(1)
    gbg_pal[0] = BG_COLOR
    graph_group.append(
        vectorio.Rectangle(
            pixel_shader=gbg_pal,
            width=DISPLAY_W, height=DISPLAY_H,
            x=0, y=0,
        )
    )

    # LCARS left sweep panel - top rounded block
    lc_pal = displayio.Palette(1)
    lc_pal[0] = LCARS_GOLD
    # Top bar
    graph_group.append(
        vectorio.Rectangle(
            pixel_shader=lc_pal,
            width=50, height=8,
            x=0, y=0,
        )
    )
    # Left vertical bar
    graph_group.append(
        vectorio.Rectangle(
            pixel_shader=lc_pal,
            width=8, height=DISPLAY_H,
            x=0, y=0,
        )
    )
    # Bottom bar
    graph_group.append(
        vectorio.Rectangle(
            pixel_shader=lc_pal,
            width=50, height=8,
            x=0, y=DISPLAY_H - 8,
        )
    )
    # Accent blocks
    acc_pal = displayio.Palette(1)
    acc_pal[0] = LCARS_BLUE
    graph_group.append(
        vectorio.Rectangle(
            pixel_shader=acc_pal,
            width=42, height=6,
            x=8, y=10,
        )
    )
    occ_pal = displayio.Palette(1)
    occ_pal[0] = LCARS_ORANGE
    graph_group.append(
        vectorio.Rectangle(
            pixel_shader=occ_pal,
            width=42, height=6,
            x=8, y=DISPLAY_H - 16,
        )
    )

    # CO2 current reading label
    graph_co2_lbl = label.Label(
        terminalio.FONT,
        text="---",
        color=LCARS_GOLD,
        anchor_point=(0.5, 0.0),
        anchored_position=(30, 22),
    )
    graph_group.append(graph_co2_lbl)

    # "PPM" label
    graph_group.append(
        label.Label(
            terminalio.FONT,
            text="PPM",
            color=LCARS_BLUE,
            anchor_point=(0.5, 0.0),
            anchored_position=(30, 34),
        )
    )

    # Min/max labels
    graph_minmax_lbl = label.Label(
        terminalio.FONT,
        text="",
        color=LCARS_ORANGE,
        anchor_point=(0.5, 0.0),
        anchored_position=(30, 50),
    )
    graph_group.append(graph_minmax_lbl)

    # Time label
    graph_group.append(
        label.Label(
            terminalio.FONT,
            text="2HR",
            color=LCARS_GOLD,
            anchor_point=(0.5, 0.0),
            anchored_position=(30, 66),
        )
    )

    # Graph bitmap: 4 palette entries
    # 0=black, 1=green, 2=yellow, 3=red
    graph_pal = displayio.Palette(4)
    graph_pal[0] = BG_COLOR
    graph_pal[1] = LCARS_GREEN
    graph_pal[2] = LCARS_YELLOW
    graph_pal[3] = LCARS_RED

    graph_bmp = displayio.Bitmap(
        GRAPH_W, GRAPH_H, 4
    )

    grid = displayio.TileGrid(
        graph_bmp,
        pixel_shader=graph_pal,
        x=GRAPH_X, y=GRAPH_Y,
    )
    graph_group.append(grid)

    # Zone threshold lines (dashed effect)
    # 600 ppm line
    y600 = GRAPH_Y + GRAPH_H - int(
        (600 - GRAPH_CO2_LO)
        / (GRAPH_CO2_HI - GRAPH_CO2_LO) * GRAPH_H
    )
    for dx in range(0, GRAPH_W, 6):
        if dx + 2 <= GRAPH_W:
            g_pal = displayio.Palette(1)
            g_pal[0] = LCARS_GREEN
            graph_group.append(
                vectorio.Rectangle(
                    pixel_shader=g_pal,
                    width=2, height=1,
                    x=GRAPH_X + dx, y=y600,
                )
            )
    # 800 ppm line
    y800 = GRAPH_Y + GRAPH_H - int(
        (800 - GRAPH_CO2_LO)
        / (GRAPH_CO2_HI - GRAPH_CO2_LO) * GRAPH_H
    )
    for dx in range(0, GRAPH_W, 6):
        if dx + 2 <= GRAPH_W:
            r_pal = displayio.Palette(1)
            r_pal[0] = LCARS_RED
            graph_group.append(
                vectorio.Rectangle(
                    pixel_shader=r_pal,
                    width=2, height=1,
                    x=GRAPH_X + dx, y=y800,
                )
            )

    # Axis labels on graph
    graph_group.append(
        label.Label(
            terminalio.FONT,
            text="{}".format(GRAPH_CO2_LO),
            color=0x666666,
            anchor_point=(0.0, 1.0),
            anchored_position=(
                GRAPH_X, GRAPH_Y + GRAPH_H + 10
            ),
        )
    )
    graph_group.append(
        label.Label(
            terminalio.FONT,
            text="{}".format(GRAPH_CO2_HI),
            color=0x666666,
            anchor_point=(1.0, 0.0),
            anchored_position=(
                GRAPH_X + GRAPH_W,
                GRAPH_Y - 2
            ),
        )
    )


def update_graph():  # pylint: disable=too-many-locals,too-many-branches
    """Redraw the graph bitmap from co2_history."""
    if graph_bmp is None:
        return

    # Clear bitmap
    for x_pos in range(GRAPH_W):
        for y_pos in range(GRAPH_H):
            graph_bmp[x_pos, y_pos] = 0

    n = len(co2_history)
    bar_px, slot, x_start, count = graph_layout(
        n, graph_zoomed
    )
    data = co2_history[-count:] if count > 0 else []
    rng = GRAPH_CO2_HI - GRAPH_CO2_LO
    for i, val in enumerate(data):
        clamped = max(GRAPH_CO2_LO, min(
            GRAPH_CO2_HI, val
        ))
        bar_h = max(int(
            (clamped - GRAPH_CO2_LO) / rng * GRAPH_H
        ), 1)

        if clamped > 800:
            cidx = 3
        elif clamped > 600:
            cidx = 2
        else:
            cidx = 1

        bx = x_start + i * slot
        for px in range(bar_px):
            x_pos = bx + px
            if x_pos >= GRAPH_W:
                break
            for y_off in range(bar_h):
                y_pos = GRAPH_H - 1 - y_off
                graph_bmp[x_pos, y_pos] = cidx

    # Update labels
    if graph_co2_lbl is not None:
        if co2_history:
            graph_co2_lbl.text = "{}".format(
                int(co2_history[-1])
            )
        else:
            graph_co2_lbl.text = "---"
    if graph_minmax_lbl is not None:
        lo = co2_min if co2_min < 9999 else 0
        hi = co2_max if co2_max > 0 else 0
        graph_minmax_lbl.text = "{}-{}".format(
            int(lo), int(hi)
        )


def _build_lcars_graph(title, unit, lo, hi,  # pylint: disable=too-many-locals
                       frame_color, zones):
    """Generic LCARS graph builder.

    zones is a list of (threshold, palette_index)
    tuples sorted ascending. Returns
    (group, bmp, pal, val_lbl, minmax_lbl)."""
    grp = displayio.Group()

    # Black background
    p0 = displayio.Palette(1)
    p0[0] = BG_COLOR
    grp.append(vectorio.Rectangle(
        pixel_shader=p0,
        width=DISPLAY_W, height=DISPLAY_H,
        x=0, y=0,
    ))

    # LCARS left frame
    fp = displayio.Palette(1)
    fp[0] = frame_color
    grp.append(vectorio.Rectangle(
        pixel_shader=fp, width=50, height=8,
        x=0, y=0,
    ))
    grp.append(vectorio.Rectangle(
        pixel_shader=fp, width=8, height=DISPLAY_H,
        x=0, y=0,
    ))
    grp.append(vectorio.Rectangle(
        pixel_shader=fp, width=50, height=8,
        x=0, y=DISPLAY_H - 8,
    ))

    # Accent blocks
    ap1 = displayio.Palette(1)
    ap1[0] = LCARS_BLUE
    grp.append(vectorio.Rectangle(
        pixel_shader=ap1, width=42, height=6,
        x=8, y=10,
    ))
    ap2 = displayio.Palette(1)
    ap2[0] = LCARS_ORANGE
    grp.append(vectorio.Rectangle(
        pixel_shader=ap2, width=42, height=6,
        x=8, y=DISPLAY_H - 16,
    ))

    # Title + unit
    grp.append(label.Label(
        terminalio.FONT, text=title,
        color=frame_color,
        anchor_point=(0.5, 0.0),
        anchored_position=(30, 22),
    ))

    val_lbl = label.Label(
        terminalio.FONT, text="---",
        color=frame_color,
        anchor_point=(0.5, 0.0),
        anchored_position=(30, 34),
    )
    grp.append(val_lbl)

    grp.append(label.Label(
        terminalio.FONT, text=unit,
        color=LCARS_BLUE,
        anchor_point=(0.5, 0.0),
        anchored_position=(30, 46),
    ))

    mm_lbl = label.Label(
        terminalio.FONT, text="",
        color=LCARS_ORANGE,
        anchor_point=(0.5, 0.0),
        anchored_position=(30, 60),
    )
    grp.append(mm_lbl)

    grp.append(label.Label(
        terminalio.FONT, text="2HR",
        color=frame_color,
        anchor_point=(0.5, 0.0),
        anchored_position=(30, 74),
    ))

    # Bitmap with palette entries per zone + black
    n_colors = len(zones) + 1
    pal = displayio.Palette(n_colors)
    pal[0] = BG_COLOR
    zone_colors = [
        LCARS_GREEN, LCARS_YELLOW, LCARS_RED
    ]
    for i in range(len(zones)):
        pal[i + 1] = zone_colors[
            min(i, len(zone_colors) - 1)
        ]

    bmp = displayio.Bitmap(
        GRAPH_W, GRAPH_H, n_colors
    )
    grp.append(displayio.TileGrid(
        bmp, pixel_shader=pal,
        x=GRAPH_X, y=GRAPH_Y,
    ))

    # Zone threshold lines
    rng = hi - lo
    for thresh, _ in zones[:-1]:
        yt = GRAPH_Y + GRAPH_H - int(
            (thresh - lo) / rng * GRAPH_H
        )
        zp = displayio.Palette(1)
        zp[0] = 0x444444
        for dx in range(0, GRAPH_W, 6):
            if dx + 2 <= GRAPH_W:
                grp.append(vectorio.Rectangle(
                    pixel_shader=zp,
                    width=2, height=1,
                    x=GRAPH_X + dx, y=yt,
                ))

    # Axis labels
    grp.append(label.Label(
        terminalio.FONT,
        text="{}".format(int(lo)),
        color=0x666666,
        anchor_point=(0.0, 1.0),
        anchored_position=(
            GRAPH_X, GRAPH_Y + GRAPH_H + 10
        ),
    ))
    grp.append(label.Label(
        terminalio.FONT,
        text="{}".format(int(hi)),
        color=0x666666,
        anchor_point=(1.0, 0.0),
        anchored_position=(
            GRAPH_X + GRAPH_W, GRAPH_Y - 2
        ),
    ))

    return grp, bmp, pal, val_lbl, mm_lbl


def _update_lcars_graph(bmp, history, lo, hi,  # pylint: disable=too-many-locals,too-many-branches
                        zones, val_lbl, mm_lbl,
                        mn, mx, fmt_fn):
    """Generic graph bitmap updater with dynamic bars."""
    if bmp is None:
        return
    for x in range(GRAPH_W):
        for y in range(GRAPH_H):
            bmp[x, y] = 0

    n = len(history)
    bar_px, slot, x_start, count = graph_layout(
        n, graph_zoomed
    )
    data = history[-count:] if count > 0 else []
    rng = hi - lo
    for i, val in enumerate(data):
        clamped = max(lo, min(hi, val))
        bar_h = max(
            int((clamped - lo) / rng * GRAPH_H), 1
        )
        cidx = 1
        for thresh, zi in zones:
            if clamped > thresh:
                cidx = zi
        bx = x_start + i * slot
        for px in range(bar_px):
            x = bx + px
            if x >= GRAPH_W:
                break
            for y_off in range(bar_h):
                y = GRAPH_H - 1 - y_off
                bmp[x, y] = cidx

    if val_lbl is not None:
        if history:
            val_lbl.text = fmt_fn(history[-1])
        else:
            val_lbl.text = "---"
    if mm_lbl is not None:
        mm_lbl.text = "{}-{}".format(
            fmt_fn(mn), fmt_fn(mx)
        )


# --- Humidity graph ---
# Zones: good 30-60%, dry <30, humid >60
HUM_ZONES = [
    (30, 1),   # green above 0
    (60, 2),   # yellow above 60
    (80, 3),   # red above 80
]


def build_hum_graph():
    """Build the LCARS humidity graph."""
    global hum_graph_group, hum_graph_bmp
    global hum_graph_pal
    global hum_graph_lbl, hum_minmax_lbl
    result = _build_lcars_graph(
        "HUM", "%RH",
        GRAPH_HUM_LO, GRAPH_HUM_HI,
        LCARS_GREEN, HUM_ZONES,
    )
    hum_graph_group = result[0]
    hum_graph_bmp = result[1]
    hum_graph_pal = result[2]
    hum_graph_lbl = result[3]
    hum_minmax_lbl = result[4]


def update_hum_graph():
    """Update humidity graph bitmap."""
    mn = hum_min if hum_min < 999 else 0
    mx = hum_max if hum_max > 0 else 0
    _update_lcars_graph(
        hum_graph_bmp, hum_history,
        GRAPH_HUM_LO, GRAPH_HUM_HI,
        HUM_ZONES,
        hum_graph_lbl, hum_minmax_lbl,
        mn, mx,
        lambda v: "{}".format(int(v)),
    )


# --- Temperature graph ---
# Zones: cool <65F/18C, good, warm >80F/27C
TEMP_ZONES_F = [
    (65, 1),   # green above 50F
    (80, 2),   # yellow above 80F
    (90, 3),   # red above 90F
]
TEMP_ZONES_C = [
    (18, 1),   # green above 10C
    (27, 2),   # yellow above 27C
    (32, 3),   # red above 32C
]


def build_temp_graph():
    """Build the LCARS temperature graph."""
    global temp_graph_group, temp_graph_bmp
    global temp_graph_pal
    global temp_graph_lbl, temp_minmax_lbl
    if use_fahrenheit:
        lo, hi = GRAPH_TEMP_LO, GRAPH_TEMP_HI
        zones = TEMP_ZONES_F
        unit = "DEG.F"
    else:
        lo, hi = GRAPH_TEMP_LO_C, GRAPH_TEMP_HI_C
        zones = TEMP_ZONES_C
        unit = "DEG.C"
    result = _build_lcars_graph(
        "TEMP", unit, lo, hi,
        LCARS_YELLOW, zones,
    )
    temp_graph_group = result[0]
    temp_graph_bmp = result[1]
    temp_graph_pal = result[2]
    temp_graph_lbl = result[3]
    temp_minmax_lbl = result[4]


def update_temp_graph():
    """Update temperature graph bitmap."""
    if use_fahrenheit:
        lo, hi = GRAPH_TEMP_LO, GRAPH_TEMP_HI
        zones = TEMP_ZONES_F
        hist = [t * 9.0 / 5.0 + 32
                for t in temp_history]
        mn = temp_min_val * 9.0 / 5.0 + 32
        mx = temp_max_val * 9.0 / 5.0 + 32
    else:
        lo, hi = GRAPH_TEMP_LO_C, GRAPH_TEMP_HI_C
        zones = TEMP_ZONES_C
        hist = list(temp_history)
        mn = temp_min_val
        mx = temp_max_val
    if temp_min_val > 900:
        mn = 0
    if temp_max_val < -900:
        mx = 0
    _update_lcars_graph(
        temp_graph_bmp, hist, lo, hi,
        zones,
        temp_graph_lbl, temp_minmax_lbl,
        mn, mx,
        lambda v: "{}".format(int(v)),
    )


def build_stats():
    """Build the LCARS stats display group."""
    global stats_group
    global stats_uptime_lbl, stats_samples_lbl
    global stats_co2_lbl, stats_hum_lbl
    global stats_temp_lbl, stats_batt_lbl

    stats_group = displayio.Group()

    # Black background
    sbg = displayio.Palette(1)
    sbg[0] = BG_COLOR
    stats_group.append(
        vectorio.Rectangle(
            pixel_shader=sbg,
            width=DISPLAY_W, height=DISPLAY_H,
            x=0, y=0,
        )
    )

    # LCARS left frame
    sg = displayio.Palette(1)
    sg[0] = LCARS_BLUE
    stats_group.append(
        vectorio.Rectangle(
            pixel_shader=sg,
            width=8, height=DISPLAY_H,
            x=0, y=0,
        )
    )
    stats_group.append(
        vectorio.Rectangle(
            pixel_shader=sg,
            width=50, height=8,
            x=0, y=0,
        )
    )
    sb = displayio.Palette(1)
    sb[0] = LCARS_ORANGE
    stats_group.append(
        vectorio.Rectangle(
            pixel_shader=sb,
            width=50, height=8,
            x=0, y=DISPLAY_H - 8,
        )
    )

    # Title
    stats_group.append(
        label.Label(
            terminalio.FONT,
            text="DIAGNOSTICS",
            color=LCARS_GOLD,
            anchor_point=(0.0, 0.0),
            anchored_position=(14, 14),
        )
    )

    # Stat labels (left column)
    y_start = 32
    y_step = 16
    stat_names = [
        "UPTIME", "SAMPLES",
        "CO2", "HUM", "TEMP", "BATT"
    ]
    for i, nm in enumerate(stat_names):
        stats_group.append(
            label.Label(
                terminalio.FONT,
                text=nm,
                color=LCARS_BLUE,
                anchor_point=(0.0, 0.0),
                anchored_position=(
                    14, y_start + i * y_step
                ),
            )
        )

    # Value labels (right column)
    stats_uptime_lbl = label.Label(
        terminalio.FONT, text="0:00",
        color=LCARS_GOLD,
        anchor_point=(1.0, 0.0),
        anchored_position=(
            DISPLAY_W - 10, y_start
        ),
    )
    stats_group.append(stats_uptime_lbl)

    stats_samples_lbl = label.Label(
        terminalio.FONT, text="0/120",
        color=LCARS_GOLD,
        anchor_point=(1.0, 0.0),
        anchored_position=(
            DISPLAY_W - 10, y_start + y_step
        ),
    )
    stats_group.append(stats_samples_lbl)

    stats_co2_lbl = label.Label(
        terminalio.FONT, text="---",
        color=LCARS_GREEN,
        anchor_point=(1.0, 0.0),
        anchored_position=(
            DISPLAY_W - 10, y_start + 2 * y_step
        ),
    )
    stats_group.append(stats_co2_lbl)

    stats_hum_lbl = label.Label(
        terminalio.FONT, text="---",
        color=LCARS_GREEN,
        anchor_point=(1.0, 0.0),
        anchored_position=(
            DISPLAY_W - 10, y_start + 3 * y_step
        ),
    )
    stats_group.append(stats_hum_lbl)

    stats_temp_lbl = label.Label(
        terminalio.FONT, text="---",
        color=LCARS_YELLOW,
        anchor_point=(1.0, 0.0),
        anchored_position=(
            DISPLAY_W - 10, y_start + 4 * y_step
        ),
    )
    stats_group.append(stats_temp_lbl)

    stats_batt_lbl = label.Label(
        terminalio.FONT, text="---",
        color=LCARS_RED,
        anchor_point=(1.0, 0.0),
        anchored_position=(
            DISPLAY_W - 10, y_start + 5 * y_step
        ),
    )
    stats_group.append(stats_batt_lbl)


def update_stats(disp):
    """Update stats screen labels."""
    if stats_uptime_lbl is None:
        return
    elapsed = time.monotonic() - boot_time
    hrs = int(elapsed // 3600)
    mins = int((elapsed % 3600) // 60)
    stats_uptime_lbl.text = "{}:{:02d}".format(
        hrs, mins
    )
    stats_samples_lbl.text = "{}/{}".format(
        len(co2_history), HISTORY_SIZE
    )

    co2_r = disp[8]
    stats_co2_lbl.text = "{} {}-{}".format(
        int(co2_r),
        int(co2_min) if co2_min < 9999 else "---",
        int(co2_max) if co2_max > 0 else "---",
    )
    hlo = int(hum_min) if hum_min < 999 else "---"
    hhi = int(hum_max) if hum_max > 0 else "---"
    stats_hum_lbl.text = "{} {}-{}".format(
        disp[5], hlo, hhi
    )
    if use_fahrenheit:
        tlo = int(
            temp_min_val * 9.0 / 5.0 + 32
        ) if temp_min_val < 900 else "---"
        thi = int(
            temp_max_val * 9.0 / 5.0 + 32
        ) if temp_max_val > -900 else "---"
    else:
        tlo = int(
            temp_min_val
        ) if temp_min_val < 900 else "---"
        thi = int(
            temp_max_val
        ) if temp_max_val > -900 else "---"
    stats_temp_lbl.text = "{} {}-{}".format(
        disp[6], tlo, thi
    )
    stats_batt_lbl.text = disp[7]


def build_about():  # pylint: disable=too-many-locals,too-many-statements
    """Build the LCARS name badge display group."""
    global about_group

    about_group = displayio.Group()

    # Black background
    abg = displayio.Palette(1)
    abg[0] = BG_COLOR
    about_group.append(
        vectorio.Rectangle(
            pixel_shader=abg,
            width=DISPLAY_W, height=DISPLAY_H,
            x=0, y=0,
        )
    )

    # LCARS frame - left + top
    ag = displayio.Palette(1)
    ag[0] = LCARS_GOLD
    about_group.append(
        vectorio.Rectangle(
            pixel_shader=ag,
            width=8, height=DISPLAY_H,
            x=0, y=0,
        )
    )
    about_group.append(
        vectorio.Rectangle(
            pixel_shader=ag,
            width=DISPLAY_W, height=8,
            x=0, y=0,
        )
    )
    about_group.append(
        vectorio.Rectangle(
            pixel_shader=ag,
            width=DISPLAY_W, height=8,
            x=0, y=DISPLAY_H - 8,
        )
    )

    # Accent blocks
    ab1 = displayio.Palette(1)
    ab1[0] = LCARS_BLUE
    about_group.append(
        vectorio.Rectangle(
            pixel_shader=ab1,
            width=60, height=8,
            x=10, y=12,
        )
    )
    ab2 = displayio.Palette(1)
    ab2[0] = LCARS_ORANGE
    about_group.append(
        vectorio.Rectangle(
            pixel_shader=ab2,
            width=40, height=8,
            x=72, y=12,
        )
    )
    ab3 = displayio.Palette(1)
    ab3[0] = LCARS_RED
    about_group.append(
        vectorio.Rectangle(
            pixel_shader=ab3,
            width=30, height=8,
            x=114, y=12,
        )
    )

    # Name - large
    about_group.append(
        label.Label(
            terminalio.FONT,
            text=BADGE_NAME,
            color=LCARS_GOLD,
            scale=2,
            anchor_point=(0.0, 0.0),
            anchored_position=(14, 28),
        )
    )

    # Title
    about_group.append(
        label.Label(
            terminalio.FONT,
            text=BADGE_TITLE,
            color=LCARS_BLUE,
            anchor_point=(0.0, 0.0),
            anchored_position=(14, 52),
        )
    )

    # ID / registry
    about_group.append(
        label.Label(
            terminalio.FONT,
            text=BADGE_ID,
            color=LCARS_ORANGE,
            anchor_point=(0.0, 0.0),
            anchored_position=(14, 68),
        )
    )

    # Sensor status
    s_status = "STCC4: {}  DRV: {}".format(
        "OK" if sensor else "N/A",
        "OK" if haptic else "N/A",
    )
    about_group.append(
        label.Label(
            terminalio.FONT,
            text=s_status,
            color=0x666666,
            anchor_point=(0.0, 0.0),
            anchored_position=(14, 88),
        )
    )

    # Project info
    about_group.append(
        label.Label(
            terminalio.FONT,
            text=BADGE_PROJECT,
            color=0x666666,
            anchor_point=(0.0, 0.0),
            anchored_position=(14, 104),
        )
    )

    # QR code on right side
    if BADGE_QR_URL:
        try:
            import adafruit_miniqr  # pylint: disable=import-outside-toplevel,wrong-import-position
            qr = adafruit_miniqr.QRCode(
                qr_type=3,
                error_correct=adafruit_miniqr.L,
            )
            qr.add_data(
                BADGE_QR_URL.encode("utf-8")
            )
            qr.make()
            mtx = qr.matrix
            border = 1
            sz = mtx.width + border * 2
            # Scale to fit ~100px tall
            scale = max(100 // sz, 1)
            qr_bmp = displayio.Bitmap(sz, sz, 2)
            qr_pal = displayio.Palette(2)
            qr_pal[0] = 0xFFFFFF
            qr_pal[1] = 0x000000
            for y in range(mtx.height):
                for x in range(mtx.width):
                    if mtx[x, y]:
                        qr_bmp[
                            x + border,
                            y + border
                        ] = 1
                    else:
                        qr_bmp[
                            x + border,
                            y + border
                        ] = 0
            qr_grid = displayio.TileGrid(
                qr_bmp,
                pixel_shader=qr_pal,
                x=0, y=0,
            )
            qr_total = sz * scale
            qr_group = displayio.Group(
                scale=scale,
                x=DISPLAY_W - qr_total - 8,
                y=(DISPLAY_H - qr_total) // 2,
            )
            qr_group.append(qr_grid)
            about_group.append(qr_group)
            print("QR code generated: {}".format(
                BADGE_QR_URL
            ))
        except (ImportError, MemoryError) as err:
            print("QR skipped: {}".format(err))


def set_view(mode):
    """Switch to the specified view mode."""
    global current_view, graph_zoomed
    current_view = mode
    # Reset zoom when leaving graph views
    if mode not in (VIEW_CO2, VIEW_HUM, VIEW_TEMP):
        graph_zoomed = False
    if mode == VIEW_BARS:
        display.root_group = root
    elif mode == VIEW_STATS:
        if stats_group is None:
            build_stats()
        display.root_group = stats_group
    elif mode == VIEW_CO2:
        if graph_group is None:
            build_graph()
        update_graph()
        display.root_group = graph_group
    elif mode == VIEW_HUM:
        if hum_graph_group is None:
            build_hum_graph()
        update_hum_graph()
        display.root_group = hum_graph_group
    elif mode == VIEW_TEMP:
        if temp_graph_group is None:
            build_temp_graph()
        update_temp_graph()
        display.root_group = temp_graph_group
    elif mode == VIEW_ABOUT:
        if about_group is None:
            build_about()
        display.root_group = about_group


def cycle_view():
    """Cycle: bars->stats->co2->hum->temp->bars."""
    nxt = (current_view + 1) % NUM_CYCLE_VIEWS
    set_view(nxt)


def toggle_brightness():
    """Toggle between dim and full brightness."""
    global is_dimmed
    is_dimmed = not is_dimmed
    if is_dimmed:
        display.brightness = DIM_BRIGHTNESS
    else:
        display.brightness = FULL_BRIGHTNESS
    print("Brightness: {}".format(
        "dim" if is_dimmed else "full"
    ))


DEMO_HOLD = 3  # seconds per screen in demo mode


def demo_mode():  # pylint: disable=too-many-statements
    """Auto-cycle all screens for video recording."""
    global graph_zoomed
    print("Demo mode started")
    scan_buzz()

    # 1) Bar view with rescan animation
    set_view(VIEW_BARS)
    vals = read_sensors()
    disp = compute_display(*vals)
    co2p = disp[0]
    hump = disp[1]
    tmpp = disp[2]
    batp = disp[3]
    co2t = disp[4]
    humt = disp[5]
    tmpt = disp[6]
    bt = disp[7]
    current = [co2p, hump, tmpp, batp]
    targets = [
        (co2p, co2t), (hump, humt),
        (tmpp, tmpt), (batp, bt),
    ]
    rescan_animation(current, targets)
    update_bar(0, co2p, co2t)
    update_bar(1, hump, humt)
    update_bar(2, tmpp, tmpt)
    update_bar(3, batp, bt)
    time.sleep(DEMO_HOLD)

    # 2) Stats screen
    set_view(VIEW_STATS)
    update_stats(disp)
    time.sleep(DEMO_HOLD)

    # 3) CO2 graph zoomed
    graph_zoomed = True
    set_view(VIEW_CO2)
    time.sleep(DEMO_HOLD)

    # 4) CO2 graph full
    graph_zoomed = False
    update_graph()
    time.sleep(DEMO_HOLD)

    # 5) Humidity graph zoomed
    graph_zoomed = True
    set_view(VIEW_HUM)
    time.sleep(DEMO_HOLD)

    # 6) Humidity graph full
    graph_zoomed = False
    update_hum_graph()
    time.sleep(DEMO_HOLD)

    # 7) Temp graph zoomed
    graph_zoomed = True
    set_view(VIEW_TEMP)
    time.sleep(DEMO_HOLD)

    # 8) Temp graph full
    graph_zoomed = False
    update_temp_graph()
    time.sleep(DEMO_HOLD)

    # 9) Badge / about
    set_view(VIEW_ABOUT)
    time.sleep(DEMO_HOLD)

    # 10) Back to bars with scan
    graph_zoomed = False
    set_view(VIEW_BARS)
    scan_animation(targets)
    update_bar(0, co2p, co2t)
    update_bar(1, hump, humt)
    update_bar(2, tmpp, tmpt)
    update_bar(3, batp, bt)
    print("Demo mode complete")


def enter_sleep():
    """Enter low-power sleep. Any button press wakes."""
    global bolt_visible, volt_visible, last_activity
    print("Entering sleep...")
    show_message("SLEEP", 1.5)

    # Remove charging indicators if visible
    if bolt_visible:
        root.remove(bolt_shape_obj)
        bolt_visible = False
    if volt_visible:
        root.remove(volt_lbl)
        volt_visible = False

    # Save CO2 offset
    save_co2_offset()

    # Clear bars and labels
    for i in range(NUM_BARS):
        update_bar(i, 0, "")

    # Wait for ALL buttons to be released
    while (not btn_d0.value) or btn_d1.value or btn_d2.value:
        time.sleep(0.05)
    time.sleep(0.5)

    # Blank display
    display.brightness = 0

    # Light sleep loop - wake every 2s to check buttons
    while True:
        t_alarm = alarm.time.TimeAlarm(
            monotonic_time=time.monotonic() + 2
        )
        alarm.light_sleep_until_alarms(t_alarm)

        # Check if any button is pressed
        d0_wake = not btn_d0.value
        d1_wake = btn_d1.value
        d2_wake = btn_d2.value
        if d0_wake or d1_wake or d2_wake:
            break

    # Wake up
    display.brightness = (
        DIM_BRIGHTNESS if is_dimmed else
        FULL_BRIGHTNESS
    )
    last_activity = time.monotonic()

    # Wait for button release then boot scan
    while (not btn_d0.value) or btn_d1.value or btn_d2.value:
        time.sleep(0.05)
    time.sleep(0.2)
    print("Awake!")


# ============================================================
#  SENSOR READ HELPER
# ============================================================
def read_sensors():
    """Read all sensors and return raw values."""
    global co2_min, co2_max
    global hum_min, hum_max
    global temp_min_val, temp_max_val
    try:
        co2_r = sensor.CO2 if sensor else 0
        co2_r = co2_r + co2_offset
        hum_r = (
            sensor.relative_humidity if sensor else 0
        )
        tmp_r = sensor.temperature if sensor else 0
    except (RuntimeError, OSError) as err:
        print("Sensor error: {}".format(err))
        co2_r, hum_r, tmp_r = 0, 0, 0

    try:
        bat_r = batt.cell_percent if batt else 0
        bat_v = batt.cell_voltage if batt else 0
        bat_rate = batt.charge_rate if batt else 0
    except (RuntimeError, OSError) as err:
        print("Battery error: {}".format(err))
        bat_r, bat_v, bat_rate = 0, 0, 0

    # Track min/max for all sensors
    if sensor is not None:
        if co2_r > 0:
            if co2_r < co2_min:
                co2_min = co2_r
            if co2_r > co2_max:
                co2_max = co2_r
        if hum_r > 0:
            if hum_r < hum_min:
                hum_min = hum_r
            if hum_r > hum_max:
                hum_max = hum_r
        if tmp_r != 0:
            if tmp_r < temp_min_val:
                temp_min_val = tmp_r
            if tmp_r > temp_max_val:
                temp_max_val = tmp_r

    return co2_r, hum_r, tmp_r, bat_r, bat_v, bat_rate


def compute_display(co2_r, hum_r, tmp_r,  # pylint: disable=too-many-locals,too-many-branches
                    bat_r, _bat_v, bat_rate):
    """Compute percentages and label text."""
    global is_charging, bolt_visible, volt_visible

    co2p = max(to_pct(co2_r, CO2_MIN, CO2_MAX),
               CO2_FLOOR_PCT)
    hump = int(clamp(hum_r, 0, 100))
    tmpp = to_pct(tmp_r, TEMP_MIN, TEMP_MAX)
    batp = int(clamp(bat_r, 0, 100))

    co2t = "{}".format(int(co2_r))
    humt = "{}%".format(hump)
    if use_fahrenheit:
        tv = tmp_r * 9.0 / 5.0 + 32
        tmpt = "{}F".format(int(tv))
    else:
        tmpt = "{}C".format(int(tmp_r))

    is_charging = bat_rate > 0.5
    is_discharging = bat_rate < -0.5
    batt_t = "{}%".format(batp)  # always show % below

    # Compute time estimate
    bar_txt = ""
    if is_charging and bat_rate > 0.5:
        hrs = (100.0 - bat_r) / bat_rate
        if hrs < 1.0:
            bar_txt = "{}m".format(int(hrs * 60))
        else:
            bar_txt = "{:.1f}h".format(hrs)
    elif is_discharging and abs(bat_rate) > 0.5:
        hrs = bat_r / abs(bat_rate)
        if hrs < 1.0:
            bar_txt = "{}m".format(int(hrs * 60))
        else:
            bar_txt = "{:.1f}h".format(hrs)

    # Bolt: charging only
    if is_charging:
        if not bolt_visible:
            root.append(bolt_shape_obj)
            bolt_visible = True
    else:
        if bolt_visible:
            root.remove(bolt_shape_obj)
            bolt_visible = False

    # In-bar label: show time for both states
    if bar_txt:
        if is_charging:
            volt_lbl.color = 0xFFFFFF
            volt_lbl.anchored_position = (
                BATT_BAR_X + 28, BATT_BASE_MID
            )
        else:
            volt_lbl.color = 0xFFFFFF
            volt_lbl.anchored_position = (
                BATT_BAR_X + BAR_W // 2,
                BATT_BASE_MID
            )
        volt_lbl.text = bar_txt
        if not volt_visible:
            root.append(volt_lbl)
            volt_visible = True
    else:
        if volt_visible:
            root.remove(volt_lbl)
            volt_visible = False

    return (
        co2p, hump, tmpp, batp,
        co2t, humt, tmpt, batt_t,
        co2_r, tmp_r
    )


# ============================================================
#  MAIN LOOP
# ============================================================
time.sleep(2)

# Wait for all buttons to be released before boot scan
# (prevents double-scan on wake from deep sleep)
while (not btn_d0.value) or btn_d1.value or btn_d2.value:
    time.sleep(0.05)
time.sleep(0.2)

# Boot scan
vals = read_sensors()
disp = compute_display(*vals)
co2p = disp[0]
hump = disp[1]
tmpp = disp[2]
batp = disp[3]
co2t = disp[4]
humt = disp[5]
tmpt = disp[6]
batt_t = disp[7]
scan_animation([
    (co2p, co2t), (hump, humt),
    (tmpp, tmpt), (batp, batt_t),
])

# First sensor sample
co2_history.append(disp[8])
hum_history.append(vals[1])
temp_history.append(vals[2])
last_sample = time.monotonic()

# Button state - read actual values to avoid ghost press
d0_prev = not btn_d0.value  # active low, inverted
d1_prev = btn_d1.value
d2_prev = btn_d2.value
d0_down_at = 0
d1_down_at = 0
d2_down_at = 0
d0_long_fired = False
d1_long_fired = False
d2_long_fired = False
d0_pending = False     # single tap waiting for double
d0_release_at = 0
DOUBLE_TAP_MS = 400    # max gap for double tap
need_scan = False

while True:
    vals = read_sensors()
    disp = compute_display(*vals)
    co2p = disp[0]
    hump = disp[1]
    tmpp = disp[2]
    batp = disp[3]
    co2t = disp[4]
    humt = disp[5]
    tmpt = disp[6]
    batt_t = disp[7]
    co2_raw_adj = disp[8]
    temp_raw = disp[9]

    # --- Sample all sensors to history ---
    now_t = time.monotonic()
    if now_t - last_sample >= SAMPLE_INTERVAL:
        last_sample = now_t
        co2_history.append(co2_raw_adj)
        if len(co2_history) > HISTORY_SIZE:
            co2_history.pop(0)
        hum_history.append(vals[1])
        if len(hum_history) > HISTORY_SIZE:
            hum_history.pop(0)
        temp_history.append(vals[2])
        if len(temp_history) > HISTORY_SIZE:
            temp_history.pop(0)

    # --- Update display based on current view ---
    if current_view == VIEW_CO2:
        update_graph()
    elif current_view == VIEW_HUM:
        update_hum_graph()
    elif current_view == VIEW_TEMP:
        update_temp_graph()
    elif current_view == VIEW_STATS:
        update_stats(disp)
    elif current_view == VIEW_BARS:
        # Wake-from-sleep scan
        if need_scan:
            need_scan = False
            targets = [
                (co2p, co2t), (hump, humt),
                (tmpp, tmpt), (batp, batt_t),
            ]
            scan_animation(targets)

        update_bar(0, co2p, co2t)
        update_bar(1, hump, humt)
        update_bar(2, tmpp, tmpt)
        update_bar(3, batp, batt_t)

    if co2_raw_adj >= CO2_WARN:
        buzz_alert()

    print(
        "CO2: {}ppm | Hum: {}% | "
        "Temp: {} | Batt: {}".format(
            int(co2_raw_adj), hump, tmpt, batt_t
        )
    )

    # --- Poll buttons at 50ms ---
    poll_end = time.monotonic() + UPDATE_INTERVAL
    blink_time = time.monotonic()
    while time.monotonic() < poll_end:
        now = time.monotonic()

        # Bolt blink
        if is_charging and bolt_visible:
            if now - blink_time >= 0.5:
                charge_blink = not charge_blink
                if charge_blink:
                    bolt_pal[0] = 0xFFFFFF
                else:
                    bolt_pal[0] = TRACK_COLORS[3]
                blink_time = now

        # Idle sleep check
        if now - last_activity >= IDLE_SLEEP_S:
            enter_sleep()
            need_scan = True
            break  # restart main loop with scan

        # Read buttons
        d0_now = not btn_d0.value  # active low
        d1_now = btn_d1.value
        d2_now = btn_d2.value

        # --- D0 pending single-tap timeout ---
        if d0_pending:
            elapsed_ms = (now - d0_release_at) * 1000
            if elapsed_ms >= DOUBLE_TAP_MS:
                d0_pending = False
                # Fire delayed single-tap action
                if current_view == VIEW_BARS:
                    current = [
                        co2p, hump, tmpp, batp,
                    ]
                    targets = [
                        (co2p, co2t),
                        (hump, humt),
                        (tmpp, tmpt),
                        (batp, batt_t),
                    ]
                    rescan_animation(
                        current, targets
                    )
                else:
                    set_view(VIEW_BARS)
                last_activity = now

        # --- D0 press tracking ---
        if d0_now and not d0_prev:
            # Check for double tap
            if d0_pending:
                d0_pending = False
                d0_long_fired = True
                demo_mode()
                last_activity = now
            else:
                d0_down_at = now
                d0_long_fired = False
                last_activity = now
        if d0_now and not d0_long_fired:
            held = (now - d0_down_at) * 1000
            if held >= LONG_PRESS_MS:
                # Check combo D0+D2
                if d2_now:
                    d0_long_fired = True
                    d2_long_fired = True
                    enter_sleep()
                    need_scan = True
                    break  # restart main loop
                d0_long_fired = True
                do_co2_calibrate()
                last_activity = now
        if not d0_now and d0_prev:
            if not d0_long_fired:
                # Queue as pending, wait for
                # possible double tap
                d0_pending = True
                d0_release_at = now
        d0_prev = d0_now

        # --- D1 press tracking ---
        if d1_now and not d1_prev:
            d1_down_at = now
            d1_long_fired = False
            last_activity = now
        if d1_now and not d1_long_fired:
            held = (now - d1_down_at) * 1000
            if held >= LONG_PRESS_MS:
                d1_long_fired = True
                if current_view == VIEW_ABOUT:
                    set_view(VIEW_BARS)
                else:
                    set_view(VIEW_ABOUT)
                last_activity = now
        if not d1_now and d1_prev:
            if not d1_long_fired:
                if current_view in (
                    VIEW_CO2, VIEW_HUM, VIEW_TEMP
                ):
                    # Zoom toggle on graph views
                    graph_zoomed = not graph_zoomed
                    print("Zoom: {}".format(
                        "15min" if graph_zoomed
                        else "full"
                    ))
                else:
                    # F/C toggle on other views
                    use_fahrenheit = not use_fahrenheit
                    if use_fahrenheit:
                        tv = (
                            temp_raw * 9.0 / 5.0 + 32
                        )
                        tmpt = "{}F".format(int(tv))
                    else:
                        tmpt = "{}C".format(
                            int(temp_raw)
                        )
                    if current_view == VIEW_BARS:
                        solo_scan(
                            2, tmpp, tmpp, tmpt
                        )
                last_activity = now
        d1_prev = d1_now

        # --- D2 press tracking ---
        if d2_now and not d2_prev:
            d2_down_at = now
            d2_long_fired = False
            last_activity = now
        if d2_now and not d2_long_fired:
            held = (now - d2_down_at) * 1000
            if held >= LONG_PRESS_MS:
                d2_long_fired = True
                toggle_brightness()
                last_activity = now
        if not d2_now and d2_prev:
            if not d2_long_fired:
                # Short press - cycle views
                cycle_view()
                last_activity = now
        d2_prev = d2_now

        time.sleep(0.05)
