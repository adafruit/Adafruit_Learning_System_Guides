# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Analog Clock for MatrixPortal S3 with 32x32 RGB LED Matrix.

Displays an analog clock with hour and minute hands over a
gradient background that shifts through four palettes across
the day. Color inspiration drawn from the Florida Arts License
Plate. Designed for a diffused display aesthetic inspired by
LED artwork behind thick resin.

Hardware:
  - Adafruit MatrixPortal S3 (ESP32-S3, 8 MB flash, 2 MB SRAM)
  - 32x32 RGB LED Matrix — 4mm pitch (Adafruit PID 607)
  - No Address E jumper needed (4 address lines only)

Boot flow:
  - If WiFi creds found in settings.toml -> NTP sync ->
    compute DST from date -> clock
  - If no WiFi creds or connection fails -> display message ->
    manual time set with UP/DOWN buttons -> clock

Libraries required in /lib:
  adafruit_ntp.mpy
"""

import math
import os
import time

import board
import digitalio
import displayio
import framebufferio
import rgbmatrix
import rtc

# ------------------------------------------------------------------ #
#  Display dimensions and clock geometry                              #
# ------------------------------------------------------------------ #
WIDTH = 32
HEIGHT = 32
CENTER_X = 16
CENTER_Y = 16
CLOCK_RADIUS = 14
MINUTE_HAND_LEN = 11
HOUR_HAND_LEN = 7

# ------------------------------------------------------------------ #
#  Time-sync interval (seconds) and day-period boundaries (24h)       #
# ------------------------------------------------------------------ #
SYNC_INTERVAL = 3600
MORNING_HOUR = 6
DAY_HOUR = 12
EVENING_HOUR = 17
NIGHT_HOUR = 20

# Wave speed settings (toggled via UP button)
WAVE_SPEED = 0.9      # calm (default)
WAVE_SPEED_FAST = 1.8  # energetic

# Display rotation (0, 90, 180, 270) — set for USB cable direction.
# 0=USB left, 90=USB down, 180=USB right, 270=USB up.
# Long-press UP button to cycle through rotations at runtime.
ROTATIONS = (0, 90, 180, 270)
DEFAULT_ROTATION = int(os.getenv("DISPLAY_ROTATION") or "90")

# Timezone — US DST computed automatically from NTP date.
# Standard offset from UTC (no DST). Code adds +1 during DST.
# Examples: -5 for Eastern, -6 for Central, -7 for Mountain,
# -8 for Pacific.  Set DST_AUTO = "false" to disable.
TZ_STD_OFFSET = int(os.getenv("TZ_STD_OFFSET") or "-5")
DST_AUTO = (os.getenv("DST_AUTO") or "true").lower() == "true"

# ------------------------------------------------------------------ #
#  Color palettes — (top, middle, bottom) RGB tuples per period       #
# ------------------------------------------------------------------ #
GRAD_MORNING = (
    (0x73, 0x61, 0xB5), (0xF2, 0xBC, 0x42), (0x5D, 0x6A, 0x2F)
)
GRAD_DAY = (
    (0x31, 0x6B, 0xB4), (0xC4, 0xDC, 0xF4), (0xD7, 0xB9, 0x96)
)
GRAD_EVENING = (
    (0x63, 0x9B, 0xAC), (0xB9, 0x65, 0x65), (0x7C, 0xA0, 0xD2)
)
GRAD_NIGHT = (
    (0xCD, 0x41, 0x7E), (0x64, 0x29, 0x69), (0x2F, 0x6E, 0x99)
)

# Hand colours — near-black to contrast against all gradients
# Pure 0x000000 causes flicker at low bit_depth; a slight
# dark value keeps LEDs minimally energized and smooth.
HAND_MORNING = 0x00C6FF
HAND_DAY = 0xDD5500
HAND_EVENING = 0xEAFF00
HAND_NIGHT = 0xFFDD00

# 5-minute markers — match hand colours per period
MARKER_MORNING = 0x00C6FF
MARKER_DAY = 0xDD5500
MARKER_EVENING = 0xEAFF00
MARKER_NIGHT = 0xFFDD00

# Star positions (x, y, phase_offset) — scaled for 32x32
STARS = [
    (3, 3, 0.0), (27, 5, 0.8), (2, 24, 1.5),
    (28, 27, 2.3), (11, 2, 3.0), (22, 29, 3.8),
    (8, 10, 4.2), (24, 12, 5.0), (9, 22, 5.7),
    (23, 21, 0.4),
]

# ------------------------------------------------------------------ #
#  Palette index assignments for the foreground overlay               #
# ------------------------------------------------------------------ #
IDX_CLEAR = 0
IDX_HAND = 1
IDX_MARKER = 2
IDX_CARDINAL = 3
IDX_CENTER = 4
IDX_GLOW = 15  # hand glow — blended colour, last index
IDX_STAR_BASE = 5  # indices 5..14 for ten stars


# ================================================================== #
#  Mini 3x5 pixel font for setup screens                              #
# ================================================================== #
# Each char is a tuple of 5 rows, each row is 3 bits wide.
FONT_3X5 = {
    '0': (0b111, 0b101, 0b101, 0b101, 0b111),
    '1': (0b010, 0b110, 0b010, 0b010, 0b111),
    '2': (0b111, 0b001, 0b111, 0b100, 0b111),
    '3': (0b111, 0b001, 0b111, 0b001, 0b111),
    '4': (0b101, 0b101, 0b111, 0b001, 0b001),
    '5': (0b111, 0b100, 0b111, 0b001, 0b111),
    '6': (0b111, 0b100, 0b111, 0b101, 0b111),
    '7': (0b111, 0b001, 0b010, 0b010, 0b010),
    '8': (0b111, 0b101, 0b111, 0b101, 0b111),
    '9': (0b111, 0b101, 0b111, 0b001, 0b111),
    ':': (0b000, 0b010, 0b000, 0b010, 0b000),
    'N': (0b101, 0b111, 0b111, 0b101, 0b101),
    'O': (0b111, 0b101, 0b101, 0b101, 0b111),
    'W': (0b101, 0b101, 0b111, 0b111, 0b101),
    'I': (0b111, 0b010, 0b010, 0b010, 0b111),
    'F': (0b111, 0b100, 0b110, 0b100, 0b100),
    'S': (0b111, 0b100, 0b111, 0b001, 0b111),
    'E': (0b111, 0b100, 0b111, 0b100, 0b111),
    'T': (0b111, 0b010, 0b010, 0b010, 0b010),
    'H': (0b101, 0b101, 0b111, 0b101, 0b101),
    'R': (0b111, 0b101, 0b111, 0b110, 0b101),
    'M': (0b101, 0b111, 0b111, 0b101, 0b101),
    ' ': (0b000, 0b000, 0b000, 0b000, 0b000),
    'U': (0b101, 0b101, 0b101, 0b101, 0b111),
    'P': (0b111, 0b101, 0b111, 0b100, 0b100),
    'D': (0b110, 0b101, 0b101, 0b101, 0b110),
}


def draw_char_3x5(bmp, char, pos_x, pos_y, pal_idx):
    """Draw a 3x5 character into a bitmap."""
    glyph = FONT_3X5.get(char.upper())
    if glyph is None:
        return
    for row in range(5):
        for col in range(3):
            if glyph[row] & (1 << (2 - col)):
                p_x = pos_x + col
                p_y = pos_y + row
                if 0 <= p_x < WIDTH and 0 <= p_y < HEIGHT:
                    bmp[p_x, p_y] = pal_idx


def draw_text_3x5(bmp, text, pos_x, pos_y, pal_idx):
    """Draw a string using the 3x5 font, 4px per char."""
    for i, char in enumerate(text):
        draw_char_3x5(bmp, char, pos_x + i * 4, pos_y, pal_idx)


def center_text_x(text):
    """Return X position to center text on display."""
    text_width = len(text) * 4 - 1
    return (WIDTH - text_width) // 2


# ================================================================== #
#  Helper functions                                                    #
# ================================================================== #
def _nth_weekday(year, month, weekday, nth):
    """Return day-of-month for the nth weekday in a month.

    weekday: 0=Mon ... 6=Sun.  nth: 1=first, 2=second, etc.
    """
    # Day-of-week for the 1st of the month (time.mktime unavail,
    # so use Zeller-like formula via time.struct_time)
    first = time.mktime(time.struct_time((
        year, month, 1, 0, 0, 0, 0, -1, -1
    )))
    first_wday = time.localtime(first).tm_wday
    # Days until the target weekday
    diff = (weekday - first_wday) % 7
    return 1 + diff + (nth - 1) * 7


def compute_dst_offset(std_offset):
    """Return UTC offset including US DST if active.

    US DST: 2nd Sunday in March 2:00 AM -> 1st Sunday in
    November 2:00 AM.  Adds +1 hour during DST.
    """
    if not DST_AUTO:
        return std_offset
    cur = time.localtime()
    year = cur.tm_year
    dst_start_day = _nth_weekday(year, 3, 6, 2)
    dst_end_day = _nth_weekday(year, 11, 6, 1)
    month = cur.tm_mon
    day = cur.tm_mday
    hour = cur.tm_hour
    # Determine if current date/time falls in DST window
    in_dst = False
    if 3 < month < 11:
        in_dst = True
    elif month == 3:
        in_dst = (day > dst_start_day
                  or (day == dst_start_day and hour >= 2))
    elif month == 11:
        in_dst = (day < dst_end_day
                  or (day == dst_end_day and hour < 2))
    return std_offset + 1 if in_dst else std_offset
def lerp_color(color_a, color_b, frac):
    """Blend two (r, g, b) tuples by fraction 0.0-1.0."""
    return (
        int(color_a[0] + (color_b[0] - color_a[0]) * frac),
        int(color_a[1] + (color_b[1] - color_a[1]) * frac),
        int(color_a[2] + (color_b[2] - color_a[2]) * frac),
    )


def pack_rgb(red, green, blue):
    """Pack r, g, b bytes into a 24-bit integer."""
    return (red << 16) | (green << 8) | blue


def get_period(hour_24):
    """Return period key for a 24-hour value."""
    if MORNING_HOUR <= hour_24 < DAY_HOUR:
        return "morning"
    if DAY_HOUR <= hour_24 < EVENING_HOUR:
        return "day"
    if EVENING_HOUR <= hour_24 < NIGHT_HOUR:
        return "evening"
    return "night"


def build_gradient(top, mid, bot):
    """Return list of 32 packed RGB values for a 3-stop gradient."""
    colors = []
    half = HEIGHT // 2
    for row in range(HEIGHT):
        if row < half:
            frac = row / max(half - 1, 1)
            rgb = lerp_color(top, mid, frac)
        else:
            frac = (row - half) / max(half - 1, 1)
            rgb = lerp_color(mid, bot, frac)
        colors.append(pack_rgb(*rgb))
    return colors


def draw_line(bmp, x_0, y_0, x_1, y_1, idx):
    """Draw a 1-pixel wide line using Bresenham's algorithm."""
    d_x = abs(x_1 - x_0)
    d_y = -abs(y_1 - y_0)
    step_x = 1 if x_0 < x_1 else -1
    step_y = 1 if y_0 < y_1 else -1
    err = d_x + d_y
    while True:
        if 0 <= x_0 < WIDTH and 0 <= y_0 < HEIGHT:
            bmp[x_0, y_0] = idx
        if x_0 == x_1 and y_0 == y_1:
            break
        err2 = 2 * err
        if err2 >= d_y:
            err += d_y
            x_0 += step_x
        if err2 <= d_x:
            err += d_x
            y_0 += step_y


def draw_thick_line(bmp, x_0, y_0, x_1, y_1, idx):
    """Draw a ~2 px wide line (three parallel lines)."""
    draw_line(bmp, x_0, y_0, x_1, y_1, idx)
    draw_line(bmp, x_0 + 1, y_0, x_1 + 1, y_1, idx)
    draw_line(bmp, x_0, y_0 + 1, x_1, y_1 + 1, idx)


def fill_dot(bmp, c_x, c_y, radius, idx):
    """Fill a small circular area."""
    for d_y in range(-radius, radius + 1):
        for d_x in range(-radius, radius + 1):
            if d_x * d_x + d_y * d_y <= radius * radius:
                p_x = c_x + d_x
                p_y = c_y + d_y
                if 0 <= p_x < WIDTH and 0 <= p_y < HEIGHT:
                    bmp[p_x, p_y] = idx


# ================================================================== #
#  DISPLAY SETUP                                                      #
# ================================================================== #
displayio.release_displays()

# -- Background palette + bitmap ------------------------------------
BG_COLORS = 128
BG_TIERS = 4
BG_MULTS = (0.75, 0.90, 1.10, 1.35)
bg_palette = displayio.Palette(BG_COLORS)
bg_bitmap = displayio.Bitmap(WIDTH, HEIGHT, BG_COLORS)

# Pre-compute radial glow map
GLOW_RADIUS = 16.0
glow_map = []  # pylint: disable=invalid-name
for _gy in range(HEIGHT):
    glow_row = []
    for _gx in range(WIDTH):
        dist = math.sqrt(
            (_gx - CENTER_X) ** 2 + (_gy - CENTER_Y) ** 2
        )
        g_frac = max(0.0, 1.0 - dist / GLOW_RADIUS)
        if g_frac > 0.70:
            t_ofs = 96  # pylint: disable=invalid-name
        elif g_frac > 0.45:
            t_ofs = 64  # pylint: disable=invalid-name
        elif g_frac > 0.20:
            t_ofs = 32
        else:
            t_ofs = 0
        glow_row.append(t_ofs)
    glow_map.append(glow_row)

# -- Foreground palette + bitmap ------------------------------------
FG_COLORS = 16
fg_palette = displayio.Palette(FG_COLORS)
fg_palette.make_transparent(IDX_CLEAR)
fg_bitmap = displayio.Bitmap(WIDTH, HEIGHT, FG_COLORS)

# -- Matrix init ----------------------------------------------------
rgb_matrix = rgbmatrix.RGBMatrix(
    width=WIDTH,
    height=HEIGHT,
    bit_depth=2,
    rgb_pins=[
        board.MTX_R1, board.MTX_G1, board.MTX_B1,
        board.MTX_R2, board.MTX_G2, board.MTX_B2,
    ],
    addr_pins=[
        board.MTX_ADDRA, board.MTX_ADDRB,
        board.MTX_ADDRC, board.MTX_ADDRD,
    ],
    clock_pin=board.MTX_CLK,
    latch_pin=board.MTX_LAT,
    output_enable_pin=board.MTX_OE,
    doublebuffer=True,
)

display = framebufferio.FramebufferDisplay(
    rgb_matrix, auto_refresh=False
)
display.rotation = DEFAULT_ROTATION

group = displayio.Group()
group.append(displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette))
group.append(displayio.TileGrid(fg_bitmap, pixel_shader=fg_palette))
display.root_group = group


# ================================================================== #
#  SETUP SCREEN HELPERS                                               #
# ================================================================== #
# Use bg_palette index 0 for black, index 1 for text colour
def setup_screen(lines, color=0x00C6FF):
    """Display centered text lines on a black background."""
    bg_palette[0] = 0x000000
    bg_palette[1] = color
    bg_bitmap.fill(0)
    fg_bitmap.fill(IDX_CLEAR)
    total_h = len(lines) * 7
    start_y = (HEIGHT - total_h) // 2
    for i, txt in enumerate(lines):
        draw_text_3x5(
            bg_bitmap, txt, center_text_x(txt),
            start_y + i * 7, 1
        )
    display.refresh()


def setup_time_display(hour, minute, is_editing_hr, blink_on):
    """Show time being set. Blink the field being edited."""
    bg_palette[0] = 0x000000
    bg_palette[1] = 0x00C6FF
    bg_palette[2] = 0x666666
    bg_bitmap.fill(0)
    fg_bitmap.fill(IDX_CLEAR)

    h_str = "{:02d}".format(hour)
    m_str = "{:02d}".format(minute)

    # "SET TIME" label at top
    draw_text_3x5(
        bg_bitmap, "SET", center_text_x("SET"), 2, 2
    )

    # Time display: HH:MM centered
    time_str = "{}:{}".format(h_str, m_str)
    t_x = center_text_x(time_str)
    t_y = 14

    if is_editing_hr:
        h_pal = 1 if blink_on else 0
        m_pal = 2
    else:
        h_pal = 2
        m_pal = 1 if blink_on else 0

    # Draw each part with its palette index
    draw_text_3x5(bg_bitmap, h_str, t_x, t_y, h_pal)
    draw_text_3x5(bg_bitmap, ":", t_x + 8, t_y, 2)
    draw_text_3x5(bg_bitmap, m_str, t_x + 12, t_y, m_pal)

    # "UP" / "DOWN" hints at bottom
    draw_text_3x5(bg_bitmap, "UP", 1, 25, 2)
    draw_text_3x5(bg_bitmap, "DOWN", 15, 25, 2)

    display.refresh()


# ================================================================== #
#  BUTTON SETUP                                                       #
# ================================================================== #
btn_up = digitalio.DigitalInOut(board.BUTTON_UP)
btn_up.direction = digitalio.Direction.INPUT
btn_up.pull = digitalio.Pull.UP

btn_down = digitalio.DigitalInOut(board.BUTTON_DOWN)
btn_down.direction = digitalio.Direction.INPUT
btn_down.pull = digitalio.Pull.UP

PERIODS = ("morning", "day", "evening", "night")
demo_index = -1  # pylint: disable=invalid-name
btn_was_pressed = False  # pylint: disable=invalid-name
btn_dn_was_pressed = False  # pylint: disable=invalid-name
wave_speed = WAVE_SPEED  # pylint: disable=invalid-name
rot_index = ROTATIONS.index(DEFAULT_ROTATION)  # pylint: disable=invalid-name
up_hold_start = 0.0  # pylint: disable=invalid-name
up_handled = False  # pylint: disable=invalid-name


# ================================================================== #
#  WIFI + NTP — OR MANUAL TIME SET                                    #
# ================================================================== #
has_wifi = False  # pylint: disable=invalid-name
last_sync = 0  # pylint: disable=invalid-name
active_period = None  # pylint: disable=invalid-name
ntp = None  # pylint: disable=invalid-name
pool = None  # pylint: disable=invalid-name

ssid = os.getenv("CIRCUITPY_WIFI_SSID")
password = os.getenv("CIRCUITPY_WIFI_PASSWORD")

if ssid and password:
    setup_screen(["WIFI", "..."])
    try:
        import socketpool  # pylint: disable=import-outside-toplevel
        import wifi  # pylint: disable=import-outside-toplevel
        import adafruit_ntp  # pylint: disable=import-outside-toplevel
        print("Connecting to WiFi...")
        wifi.radio.connect(ssid, password)
        print("WiFi OK - IP: {}".format(wifi.radio.ipv4_address))
        pool = socketpool.SocketPool(wifi.radio)

        # First sync with standard offset to get correct date
        print("NTP sync (standard offset)...")
        ntp = adafruit_ntp.NTP(
            pool, tz_offset=TZ_STD_OFFSET, cache_seconds=3600
        )
        rtc.RTC().datetime = ntp.datetime

        # Compute DST from the date we just got
        tz_offset = compute_dst_offset(TZ_STD_OFFSET)
        if tz_offset != TZ_STD_OFFSET:
            print("DST active: offset {}".format(tz_offset))
            ntp = adafruit_ntp.NTP(
                pool, tz_offset=tz_offset, cache_seconds=3600
            )
            rtc.RTC().datetime = ntp.datetime
        else:
            print("Standard time: offset {}".format(tz_offset))

        last_sync = time.monotonic()
        has_wifi = True  # pylint: disable=invalid-name
        print("NTP sync OK: {}".format(time.localtime()))
    except Exception as exc:  # pylint: disable=broad-except
        print("WiFi failed: {}".format(exc))
        setup_screen(["WIFI", "ERROR"])
        time.sleep(2)

if not has_wifi:
    # ---- No WiFi: manual time set mode ----
    if not ssid:
        setup_screen(["NO WIFI", "IN TOML"])
        print("No WiFi creds in settings.toml")
    else:
        print("Falling back to manual time set")
    time.sleep(2)

    set_hour = 12  # pylint: disable=invalid-name
    set_min = 0  # pylint: disable=invalid-name
    editing_hr = True  # pylint: disable=invalid-name
    blink_timer = time.monotonic()  # pylint: disable=invalid-name
    blink_state = True  # pylint: disable=invalid-name
    up_prev = True  # pylint: disable=invalid-name
    dn_prev = True  # pylint: disable=invalid-name
    hold_start = 0.0  # pylint: disable=invalid-name
    HOLD_TIME = 1.5  # seconds to hold for confirm

    print("Manual time set: UP=increment, DOWN=toggle field")
    print("  Long press either button to confirm")

    while True:
        # Blink toggle every 0.4s
        if time.monotonic() - blink_timer > 0.4:
            blink_state = not blink_state  # pylint: disable=invalid-name
            blink_timer = time.monotonic()  # pylint: disable=invalid-name

        setup_time_display(
            set_hour, set_min, editing_hr, blink_state
        )

        up_now = not btn_up.value
        dn_now = not btn_down.value

        # -- Long press detection (either button) --
        if up_now or dn_now:
            if hold_start == 0.0:
                hold_start = time.monotonic()  # pylint: disable=invalid-name
            elif time.monotonic() - hold_start >= HOLD_TIME:
                # Long press: accept time
                print("Time confirmed")
                cur_t = time.localtime()
                rtc.RTC().datetime = time.struct_time((
                    cur_t.tm_year, cur_t.tm_mon,
                    cur_t.tm_mday, set_hour, set_min,
                    0, cur_t.tm_wday, cur_t.tm_yday, -1
                ))
                print("RTC set to {:02d}:{:02d}".format(
                    set_hour, set_min
                ))
                break
        else:
            hold_start = 0.0  # pylint: disable=invalid-name

        # -- Short press: UP increments, DOWN toggles field --
        if up_now and not up_prev:
            if editing_hr:
                set_hour = (set_hour + 1) % 24  # pylint: disable=invalid-name
            else:
                set_min = (set_min + 1) % 60  # pylint: disable=invalid-name

        if dn_now and not dn_prev:
            editing_hr = not editing_hr  # pylint: disable=invalid-name
            if editing_hr:
                print("Editing: hours")
            else:
                print("Editing: minutes")

        up_prev = up_now  # pylint: disable=invalid-name
        dn_prev = dn_now  # pylint: disable=invalid-name
        time.sleep(0.05)


def sync_time():
    """Set the onboard RTC from the NTP server (WiFi only)."""
    global last_sync, ntp  # pylint: disable=global-statement,invalid-name
    if not has_wifi:
        return
    try:
        # Recompute DST in case it changed since boot
        tz_ofs = compute_dst_offset(TZ_STD_OFFSET)
        ntp = adafruit_ntp.NTP(
            pool, tz_offset=tz_ofs, cache_seconds=3600
        )
        rtc.RTC().datetime = ntp.datetime
        last_sync = time.monotonic()
        print("NTP sync OK (offset {}): {}".format(
            tz_ofs, time.localtime()
        ))
    except Exception as exc:  # pylint: disable=broad-except
        print("NTP sync failed: {}".format(exc))


# ================================================================== #
#  PALETTE / GRADIENT BUILDERS                                        #
# ================================================================== #
def palette_for_period(period):
    """Return (gradient_tuple, hand_hex, marker_hex)."""
    table = {
        "morning": (GRAD_MORNING, HAND_MORNING, MARKER_MORNING),
        "day":     (GRAD_DAY, HAND_DAY, MARKER_DAY),
        "evening": (GRAD_EVENING, HAND_EVENING, MARKER_EVENING),
        "night":   (GRAD_NIGHT, HAND_NIGHT, MARKER_NIGHT),
    }
    return table[period]


def _fill_tiered_palette(gradient):
    """Fill background palette with dim-to-bright tiers."""
    for row in range(HEIGHT):
        base = gradient[row]
        r_b = (base >> 16) & 0xFF
        g_b = (base >> 8) & 0xFF
        b_b = base & 0xFF
        for t_idx in range(BG_TIERS):
            mult = BG_MULTS[t_idx]
            t_r = min(255, int(r_b * mult))
            t_g = min(255, int(g_b * mult))
            t_b = min(255, int(b_b * mult))
            bg_palette[t_idx * 32 + row] = pack_rgb(
                t_r, t_g, t_b
            )


def _glow_color(color_hex):
    """Return colour at ~30% brightness for hand glow halo."""
    return pack_rgb(
        ((color_hex >> 16) & 0xFF) // 3,
        ((color_hex >> 8) & 0xFF) // 3,
        (color_hex & 0xFF) // 3,
    )


def apply_background(period):
    """Rebuild palette colours for a new period (called once)."""
    grad_stops, hand_hex, marker_hex = palette_for_period(period)
    _fill_tiered_palette(build_gradient(*grad_stops))

    fg_palette[IDX_HAND] = hand_hex
    fg_palette[IDX_MARKER] = marker_hex
    fg_palette[IDX_CARDINAL] = marker_hex
    fg_palette[IDX_CENTER] = hand_hex
    fg_palette[IDX_GLOW] = _glow_color(hand_hex)

    for s_i, _ in enumerate(STARS):
        fg_palette[IDX_STAR_BASE + s_i] = 0xFFDD00


# Wave animation parameters
WAVE_AMP = 2.5       # max row displacement in pixels
WAVE_LEN_X = 0.22    # horizontal frequency (across columns)
WAVE_LEN_Y = 0.15    # vertical frequency (subtle secondary)


def animate_background(mono_now):
    """Update background bitmap with wave + radial glow."""
    spd = wave_speed
    for row_y in range(HEIGHT):
        g_row = glow_map[row_y]
        for col_x in range(WIDTH):
            wave1 = math.sin(
                col_x * WAVE_LEN_X + mono_now * spd
            )
            wave2 = math.sin(
                row_y * WAVE_LEN_Y - mono_now * spd * 0.7
            )
            offset = (wave1 + wave2 * 0.5) * WAVE_AMP
            idx = int(row_y + offset)
            if idx < 0:
                idx = 0
            elif idx >= HEIGHT:
                idx = HEIGHT - 1
            bg_bitmap[col_x, row_y] = idx + g_row[col_x]


# ================================================================== #
#  FRAME RENDERER                                                     #
# ================================================================== #
def _draw_markers():
    """Draw 12 hour markers as plus shapes."""
    for h_mark in range(12):
        angle = h_mark * math.pi / 6.0
        m_x = int(CENTER_X + CLOCK_RADIUS * math.sin(angle))
        m_y = int(CENTER_Y - CLOCK_RADIUS * math.cos(angle))
        p_idx = IDX_CARDINAL if h_mark % 3 == 0 else IDX_MARKER
        if 0 <= m_x < WIDTH and 0 <= m_y < HEIGHT:
            fg_bitmap[m_x, m_y] = p_idx
        for d_xy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            p_x = m_x + d_xy[0]
            p_y = m_y + d_xy[1]
            if 0 <= p_x < WIDTH and 0 <= p_y < HEIGHT:
                fg_bitmap[p_x, p_y] = p_idx


def _draw_stars(mono_now):
    """Draw twinkling yellow stars (nighttime only)."""
    for s_idx, star in enumerate(STARS):
        s_x, s_y, phase = star
        brightness = 0.25 + 0.75 * max(
            0.0, math.sin(mono_now * 0.4 + phase)
        )
        fg_palette[IDX_STAR_BASE + s_idx] = pack_rgb(
            int(0xFF * brightness), int(0xDD * brightness), 0
        )
        if 0 <= s_x < WIDTH and 0 <= s_y < HEIGHT:
            fg_bitmap[s_x, s_y] = IDX_STAR_BASE + s_idx


def _draw_hands(hours, minutes, seconds):
    """Draw glow halos then hands on top, plus center dot."""
    m_angle = (minutes * math.pi / 30.0
               + seconds * math.pi / 1800.0)
    m_end_x = int(CENTER_X + MINUTE_HAND_LEN * math.sin(m_angle))
    m_end_y = int(CENTER_Y - MINUTE_HAND_LEN * math.cos(m_angle))

    h_angle = ((hours % 12) * math.pi / 6.0
               + minutes * math.pi / 360.0)
    h_end_x = int(CENTER_X + HOUR_HAND_LEN * math.sin(h_angle))
    h_end_y = int(CENTER_Y - HOUR_HAND_LEN * math.cos(h_angle))

    # Glow halos (drawn first, hands paint over)
    draw_thick_line(
        fg_bitmap, CENTER_X, CENTER_Y, m_end_x, m_end_y, IDX_GLOW
    )
    draw_thick_line(
        fg_bitmap, CENTER_X, CENTER_Y, h_end_x, h_end_y, IDX_GLOW
    )
    draw_line(
        fg_bitmap, CENTER_X - 1, CENTER_Y - 1,
        h_end_x - 1, h_end_y - 1, IDX_GLOW
    )
    draw_line(
        fg_bitmap, CENTER_X + 1, CENTER_Y + 1,
        h_end_x + 1, h_end_y + 1, IDX_GLOW
    )

    # Minute hand (single pixel, over glow)
    draw_line(
        fg_bitmap, CENTER_X, CENTER_Y, m_end_x, m_end_y, IDX_HAND
    )

    # Hour hand (thicker, over glow)
    draw_thick_line(
        fg_bitmap, CENTER_X, CENTER_Y, h_end_x, h_end_y, IDX_HAND
    )

    # Center pivot dot
    fill_dot(fg_bitmap, CENTER_X, CENTER_Y, 1, IDX_CENTER)


def draw_clock(hours, minutes, seconds, mono_now,
               period_override=None):
    """Render one frame of the analog clock onto the foreground."""
    global active_period  # pylint: disable=global-statement,invalid-name

    if period_override is not None:
        period = period_override
    else:
        period = get_period(hours)

    if period != active_period:
        apply_background(period)
        active_period = period

    animate_background(mono_now)
    fg_bitmap.fill(IDX_CLEAR)
    _draw_markers()
    if period == "night":
        _draw_stars(mono_now)
    _draw_hands(hours, minutes, seconds)
    display.refresh()


# ================================================================== #
#  MAIN LOOP                                                          #
# ================================================================== #
if has_wifi:
    print("UP = wave speed (hold=rotate) | DOWN = backgrounds")
else:
    print("Offline: UP = speed (hold=rotate) | DOWN = bg")

now = time.localtime()
draw_clock(now.tm_hour, now.tm_min, now.tm_sec, time.monotonic())

while True:
    # ---- UP button: short=wave speed, long=rotate display ----
    btn_pressed = not btn_up.value
    if btn_pressed:
        if not btn_was_pressed:
            # Button just pressed — start hold timer
            up_hold_start = time.monotonic()  # pylint: disable=invalid-name
            up_handled = False  # pylint: disable=invalid-name
        elif (not up_handled
              and time.monotonic() - up_hold_start >= 1.5):
            # Long press: cycle rotation
            rot_index = (rot_index + 1) % 4  # pylint: disable=invalid-name
            display.rotation = ROTATIONS[rot_index]
            up_handled = True  # pylint: disable=invalid-name
            print("Rotation: {}".format(ROTATIONS[rot_index]))
    elif btn_was_pressed and not up_handled:
        # Button released before long press — short press
        if wave_speed == WAVE_SPEED:
            wave_speed = WAVE_SPEED_FAST  # pylint: disable=invalid-name
            print("Wave speed: fast")
        else:
            wave_speed = WAVE_SPEED  # pylint: disable=invalid-name
            print("Wave speed: calm")
    btn_was_pressed = btn_pressed  # pylint: disable=invalid-name

    # ---- DOWN button: cycle backgrounds ----
    btn_dn_pressed = not btn_down.value
    if btn_dn_pressed and not btn_dn_was_pressed:
        demo_index = demo_index + 1  # pylint: disable=invalid-name
        if demo_index >= len(PERIODS):
            demo_index = -1  # pylint: disable=invalid-name
            print("Auto mode (time-based)")
        else:
            print("Demo: {}".format(PERIODS[demo_index]))
        active_period = None  # force background redraw
    btn_dn_was_pressed = btn_dn_pressed  # pylint: disable=invalid-name

    # Build override (None = use real time)
    override = PERIODS[demo_index] if demo_index >= 0 else None

    now = time.localtime()
    draw_clock(
        now.tm_hour, now.tm_min, now.tm_sec,
        time.monotonic(), period_override=override
    )

    if has_wifi and time.monotonic() - last_sync > SYNC_INTERVAL:
        sync_time()

    time.sleep(0.05)
