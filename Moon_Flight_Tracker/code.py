# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''
LUNA TRANSIT flight tracker.
Alerts when a plane is about to cross (or pass near) the moon,
for photographing transits.
Adafruit Qualia ESP32-S3 + 2.1" round 480x480 touch TFT (product 5792).
'''
# pylint: disable=broad-except, redefined-outer-name, global-statement
# pylint: disable=too-many-locals, too-many-branches, too-many-statements
# pylint: disable=too-many-return-statements
# Screens: RAD (radar) / LIST / MOON / LOC (zip keypad)
# Data: adsb.fi open API + on-device moon ephemeris
import time
import math
import os
import ssl
import rtc
import wifi
import socketpool
import microcontroller
import board
import busio
import displayio
import terminalio
import vectorio
import dotclockframebuffer
from framebufferio import FramebufferDisplay
import adafruit_requests
import adafruit_ntp
from adafruit_display_text import label
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_bus_device.i2c_device import I2CDevice
import tl021wvc02
from moon_ephem import moon_altaz_phase, phase_name

# ---------------- palette ----------------
BG = 0x0A0F16
PANEL = 0x101A26
GRID = 0x1C2836
GRID2 = 0x24344A
CYAN = 0x00E5FF
PINK = 0xFF2E88
MOONC = 0xE9E4D4
DIM = 0x5A6472
GREEN = 0x3DDC84
DARK = 0x0D1219

CX, CY = 240, 240
PX_PER_MI = 42          # 5 mi -> 210 px ring
FETCH_S = 15            # aircraft refresh
MOON_S = 60             # ephemeris refresh
LOOKAHEAD_S = 300       # transit prediction window
SEP_HIT = 0.5           # pink: plane crosses right over the moon disc
SEP_NEAR = 2.0          # cyan: close pass — moon still in a 300mm frame
NM_RADIUS = 15          # adsb.fi query radius (nm)
DEBUG_TOUCH = False     # print every tap/release to serial — enable when tuning
DISPLAY_FREQ = 8_000_000   # pclk; guide default is 16 MHz — lowered to fight
                           # ESP32-S3 RGB "screen drift" during WiFi bursts

# ---------------- state ----------------
screen = "radar"
filter_mode = "mi"      # "mi" (5 mi ring) or "mm" (300mm lens ~3.1 mi)
zip_draft = None
aircraft = []           # dicts: cs, x, y (mi E/N), alt_ft, gs_kt, track, type
best = None             # (cs, eta_s, sep_deg)
sel = None              # aircraft dict selected from LIST
list_rows = []          # (eta, sep, ac) as drawn on LIST — for tap lookup
route_cache = {}        # callsign -> (codes, names) or None
route_pending = None    # callsign awaiting route lookup (detail screen)
demo_t0 = None          # "67"+OK on keypad: demo start time (60s total)
demo_phase = -1         # 0 = pink pass, 1 = cyan pass (rebuild once per pass)
demo_pass_t0 = None     # pass clock — starts AFTER the pass's slow rebuild
demo_grp = None         # the demo plane's displayio sub-group (moved per frame)
demo_lbl = None         # banner label (ETA text updated per frame)
moon = (0.0, 0.0, 0.5, True)  # alt, az, illum, waxing
moon_rs = None          # ("HH:MM", "HH:MM") local rise/set
TZ_OFF = -5             # replaced after geocode (UTC_OFFSET env or lon/15)
loc_msg = None          # (text, color) confirmation on LOC screen
loc_msg_t = 0
last_touch = 0          # touch dispatch state (poll_touch)
last_tx = last_ty = -999
was_down = False


def nvm_get_zip():
    try:
        z = bytes(microcontroller.nvm[0:5]).decode()
        if z.isdigit():
            return z
    except Exception:
        pass
    return "10013"


def nvm_set_zip(z):
    microcontroller.nvm[0:5] = z.encode()


def nvm_get_rot():
    try:
        r = microcontroller.nvm[5]
        if r < 4:
            return r * 90
    except Exception:
        pass
    return 0


def nvm_set_rot(deg):
    microcontroller.nvm[5] = deg // 90


ZIP = nvm_get_zip()
ROT = nvm_get_rot()      # 0 / 90 / 180 / 270 — set via LOC keypad
LAT, LON = 40.72, -74.00  # replaced by geocode at boot

# ---------------- display ----------------
# Direct init (TL021WVC02 codes + timings from the Adafruit learn guide).
# The panel is scanned continuously out of PSRAM; WiFi/SSL bursts contend for
# that bandwidth and cause horizontal jitter ("screen drift") — DISPLAY_FREQ
# runs below the guide's 16 MHz to leave headroom. Raise it back toward
# 16_000_000 if your unit is stable.
displayio.release_displays()

# Init sequence lives in tl021wvc02.py (keeps this module under
# pylint's 1000-line cap and reusable by other Qualia projects).

try:
    board.I2C().deinit()
except Exception:
    pass
_i2c_init = busio.I2C(board.SCL, board.SDA)
_io_exp = dict(board.TFT_IO_EXPANDER)
# _io_exp['i2c_address'] = 0x38  # uncomment for rev B boards
dotclockframebuffer.ioexpander_send_init_sequence(
    _i2c_init, tl021wvc02.INIT_SEQUENCE, **_io_exp)
_i2c_init.deinit()

_timings = {
    "frequency": DISPLAY_FREQ,
    "width": 480, "height": 480,
    "hsync_pulse_width": 20, "hsync_front_porch": 40, "hsync_back_porch": 40,
    "vsync_pulse_width": 10, "vsync_front_porch": 40, "vsync_back_porch": 40,
    "hsync_idle_low": False, "vsync_idle_low": False, "de_idle_high": False,
    "pclk_active_high": True, "pclk_idle_high": False,
}
_fb = dotclockframebuffer.DotClockFramebuffer(**dict(board.TFT_PINS), **_timings)
display = FramebufferDisplay(_fb, auto_refresh=False)
display.rotation = ROT
root = displayio.Group()
display.root_group = root

pal = {}
def P(color):
    if color not in pal:
        p = displayio.Palette(1)
        p[0] = color
        pal[color] = p
    return pal[color]


def circle(x, y, r, color):
    return vectorio.Circle(pixel_shader=P(color), radius=r, x=x, y=y)


def ring(group, r, color):
    group.append(circle(CX, CY, r, color))
    group.append(circle(CX, CY, r - 1, BG))


def rect(x, y, w, h, color):
    return vectorio.Rectangle(pixel_shader=P(color), width=w, height=h, x=x, y=y)


def text(s, x, y, color, scale=2, anchor=(0, 0)):
    t = label.Label(terminalio.FONT, text=s, color=color, scale=scale)
    t.anchor_point = anchor
    t.anchored_position = (x, y)
    return t


# ---------------- network ----------------
print("connecting wifi…")
wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
# WiFi TX bursts contend with the display's PSRAM scanout and cause the
# residual jitter — capping TX power shrinks those bursts considerably.
# Raise back toward 15–20 dBm if your AP is far and fetches start failing.
try:
    wifi.radio.tx_power = 8
    print("wifi tx_power capped at 8 dBm")
except Exception as e:
    print("tx_power cap failed:", e)
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())
ntp = adafruit_ntp.NTP(pool, tz_offset=0)


def sync_time():
    """One-shot NTP -> RTC so we never block on UDP again."""
    for attempt in range(4):
        try:
            rtc.RTC().datetime = ntp.datetime
            print("time synced")
            return True
        except Exception as e:
            print("ntp retry {}: {}".format(attempt + 1, e))
            time.sleep(2)
    return False

sync_time()


def utc_now():
    return time.localtime()  # RTC holds UTC (tz_offset=0)


def geocode(z):
    global LAT, LON, TZ_OFF
    try:
        r = requests.get("https://api.zippopotam.us/us/" + z, timeout=10)
        p = r.json()["places"][0]
        r.close()
        LAT, LON = float(p["latitude"]), float(p["longitude"])
        v = os.getenv("UTC_OFFSET")
        if v is not None:
            TZ_OFF = float(v)
        else:
            TZ_OFF = fetch_utc_offset() or round(LON / 15.0)
        return True
    except Exception as e:
        print("geocode failed:", e)
        return False


def fetch_aircraft():
    """adsb.fi open data — planes within NM_RADIUS of observer."""
    out = []
    url = "https://opendata.adsb.fi/api/v2/lat/{:.4f}/lon/{:.4f}/dist/{}".format(
        LAT, LON, NM_RADIUS)
    try:
        # short timeout: this call blocks the whole loop (touch included) —
        # better to skip one 15s cycle than freeze for 10s on a slow response
        r = requests.get(url, timeout=4)
        data = r.json()
        r.close()
    except Exception as e:
        print("adsb fetch failed:", e)
        return None
    for ac in data.get("aircraft", []):
        try:
            la, lo = ac["lat"], ac["lon"]
            alt = ac.get("alt_baro", 0)
            if alt == "ground" or not isinstance(alt, (int, float)) or alt < 500:
                continue
            dx = (lo - LON) * 69.17 * math.cos(math.radians(LAT))  # mi east
            dy = (la - LAT) * 69.17                                # mi north
            out.append({
                "cs": (ac.get("flight") or ac.get("hex", "?")).strip(),
                "x": dx, "y": dy, "alt": alt,
                "gs": ac.get("gs", 0) or 0,
                "track": ac.get("track", 0) or 0,
                "type": ac.get("t", "?") or "?",
            })
        except (KeyError, TypeError):
            continue
    return out


def fetch_route(cs):
    """Route lookup via adsbdb.com (free, no key) — better coverage than
    adsb.lol's routeset. Cached per callsign. Returns ("MCO-SRQ", [names]) or None."""
    if cs in route_cache:
        return route_cache[cs]
    info = None
    try:
        r = requests.get("https://api.adsbdb.com/v0/callsign/" + cs, timeout=10)
        status = r.status_code
        d = r.json()
        r.close()
        if status == 200:
            fr = d.get("response", {}).get("flightroute")
            if fr:
                o, dst = fr.get("origin", {}), fr.get("destination", {})
                codes = "{}-{}".format(o.get("iata_code", "?"), dst.get("iata_code", "?"))
                info = (codes, [o.get("name", "?"), dst.get("name", "?")])
        elif status == 404:
            print("route: not in adsbdb for", cs)  # genuine no-data → cache None
        else:
            print("route lookup HTTP", status)
            return None
    except Exception as e:
        print("route lookup failed:", e)
        return None  # don't cache failures — retry on next tap
    route_cache[cs] = info
    return info


def fetch_utc_offset():
    """DST-aware UTC offset for LAT/LON via timeapi.io (free, no key).
    Returns hours (e.g. -4.0 for EDT) or None on failure."""
    try:
        r = requests.get(
            "https://timeapi.io/api/TimeZone/coordinate"
            "?latitude={:.4f}&longitude={:.4f}".format(LAT, LON),
            timeout=10)
        d = r.json()
        r.close()
        off = d["currentUtcOffset"]["seconds"] / 3600.0
        print("tz: {} (UTC{:+.1f})".format(d.get("timeZone", "?"), off))
        return off
    except Exception as e:
        print("tz lookup failed:", e)
        return None


def fmt_local(ts):
    lt = time.localtime(int(ts + TZ_OFF * 3600))
    h, ap = lt.tm_hour % 12, ("AM" if lt.tm_hour < 12 else "PM")
    return "{}:{:02d}{}".format(h if h else 12, lt.tm_min, ap)


def compute_rise_set():
    """Scan the next 24h in 10-min steps for horizon crossings (interpolated)."""
    t = time.time()
    prev = moon_altaz_phase(time.localtime(t), LAT, LON)[0]
    rise = sett = None
    step = 600
    for _ in range(145):
        t += step
        alt = moon_altaz_phase(time.localtime(t), LAT, LON)[0]
        if rise is None and prev <= 0 < alt:
            rise = t - step + step * (-prev) / (alt - prev)
        if sett is None and prev > 0 >= alt:
            sett = t - step + step * prev / (prev - alt)
        if rise is not None and sett is not None:
            break
        prev = alt
    return (fmt_local(rise) if rise else "--:--",
            fmt_local(sett) if sett else "--:--")


# ---------------- geometry ----------------
def az_el(x_mi, y_mi, alt_ft):
    gd = math.sqrt(x_mi * x_mi + y_mi * y_mi) + 1e-6
    el = math.degrees(math.atan2(alt_ft / 5280.0, gd))
    az = math.degrees(math.atan2(x_mi, y_mi)) % 360
    return az, el


def ang_sep(az1, el1, az2, el2):
    a1, e1, a2, e2 = map(math.radians, (az1, el1, az2, el2))
    c = (math.sin(e1) * math.sin(e2)
         + math.cos(e1) * math.cos(e2) * math.cos(a1 - a2))
    return math.degrees(math.acos(max(-1, min(1, c))))


def predict(ac, m_az, m_el):
    """Return (eta_s, min_sep_deg). Always evaluates the CURRENT position
    (t=0), so aircraft with missing/low ground speed — common for GA
    transponders on adsb.fi — still register their live separation instead
    of being silently excluded from the alert logic."""
    az, el = az_el(ac["x"], ac["y"], ac["alt"])
    best_t, best_sep = 0, ang_sep(az, el, m_az, m_el)
    if ac["gs"] >= 40:
        v = ac["gs"] * 1.15078 / 3600.0  # mi/s
        tr = math.radians(ac["track"])
        vx, vy = v * math.sin(tr), v * math.cos(tr)
        for t in range(5, LOOKAHEAD_S + 1, 5):
            az, el = az_el(ac["x"] + vx * t, ac["y"] + vy * t, ac["alt"])
            s = ang_sep(az, el, m_az, m_el)
            if s < best_sep:
                best_sep, best_t = s, t
    return best_t, best_sep


# ---------------- screens ----------------
NAVS = ("RAD", "LIST", "MOON", "LOC")
KEYS = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "<", "0", "OK")


def outlined(g, x, y, w, h, fill, border, r=6):
    """Rounded, 1px-outlined panel — matches the mockup's bordered boxes.
    Needs adafruit_display_shapes in /lib."""
    g.append(RoundRect(x, y, w, h, r, fill=fill, outline=border))


def nav_group(active):
    g = displayio.Group()
    total = 4 * 56 + 3 * 6
    x0 = CX - total // 2
    for i, n in enumerate(NAVS):
        x = x0 + i * 62
        on = n == active
        outlined(g, x, 398, 56, 44, PANEL if on else DARK, CYAN if on else GRID, 10)
        g.append(text(n, x + 28, 420, CYAN if on else DIM, 1, (0.5, 0.5)))
    # edge-cycle hints (match the tap zones)
    g.append(text("<", 16, 240, DIM, 2, (0, 0.5)))
    g.append(text(">", 464, 240, DIM, 2, (1, 0.5)))
    return g


def moon_icon(g, x, y, r, illum, waxing):
    if illum < 0.06:
        # new moon: dotted outline so the position still reads on screen
        for i in range(24):
            a = math.radians(i * 15)
            g.append(circle(int(x + math.sin(a) * r), int(y - math.cos(a) * r), 2, MOONC))
        return
    g.append(circle(x, y, r, MOONC))
    # shadow disc slides across (fully off-disc at full moon); flips for waning
    off = int((illum * 2.1 - 0.1) * r)
    g.append(circle(x - off if waxing else x + off, y, r + 2, BG))


def build_radar():
    g = displayio.Group()
    g.append(rect(0, 0, 480, 480, BG))
    # alert bezel ring FIRST — ring() fills its inside with BG, so drawing
    # it last wiped the whole radar (moon + planes vanished under it)
    if best and best[2] < SEP_NEAR and best[1] <= 90:
        acol = PINK if best[2] < SEP_HIT else CYAN
        ring(g, 238, acol)
        ring(g, 236, acol)
    # largest ring FIRST — ring() fills its inside with BG, so smaller-first
    # gets painted over (the bug that hid the inner circles)
    ring(g, 210, GRID2)          # 5 mi
    ring(g, 130, GRID)           # 3.1 mi — 300mm capture zone
    ring(g, 70, GRID)
    g.append(circle(CX, CY, 3, CYAN))
    g.append(text("N", CX, 14, DIM, 2, (0.5, 0)))
    g.append(text("5MI", 40, 232, 0x2C3A4C, 1, (0, 0.5)))
    g.append(text("3.1", 118, 232, 0x2C3A4C, 1, (0, 0.5)))

    m_alt, m_az, illum, waxing = moon
    # moon centered — leaves the whole ring free for traffic;
    # the label carries the REAL alt/az for pointing the camera
    mx, my = CX, CY
    if m_alt > 0:
        # accent halo ring around the moon (mockup: 2px accent, inset -8)
        g.append(circle(mx, my, 49, 0xB3215F))
        g.append(circle(mx, my, 47, BG))
        moon_icon(g, mx, my, 40, illum, waxing)
        g.append(text("MOON {:.0f}/{:.0f}".format(m_alt, m_az), mx, my + 48, 0xB7AE93, 1, (0.5, 0)))
        # dotted bearing line at the moon's REAL azimuth — planes crossing
        # THIS line are transit candidates; screen-center proximity means nothing
        ar = math.radians(m_az)
        for rr in range(60, 206, 16):
            g.append(circle(int(CX + math.sin(ar) * rr), int(CY - math.cos(ar) * rr), 2, 0x63203F))
    else:
        g.append(text("MOON BELOW HORIZON", CX, 60, DIM, 1, (0.5, 0)))

    limit = 5.0 if filter_mode == "mi" else 3.1
    global demo_grp, demo_lbl
    for ac in aircraft:
        d = math.sqrt(ac["x"] ** 2 + ac["y"] ** 2)
        if d > limit:
            continue
        px = int(CX + ac["x"] * PX_PER_MI)
        py = int(CY - ac["y"] * PX_PER_MI)
        is_t = best and best[0] == ac["cs"] and best[2] < SEP_NEAR
        col = PINK if (is_t and best[2] < SEP_HIT) else CYAN
        tr = math.radians(ac["track"])
        pts = []
        for a, r in ((0, 10), (140, 9), (180, 4), (220, 9)):
            aa = tr + math.radians(a)
            pts.append((int(math.sin(aa) * r), int(-math.cos(aa) * r)))
        # blip + labels live in a sub-group at (px,py) so the demo driver can
        # slide the whole thing per-frame without a full screen rebuild
        sub = displayio.Group(x=px, y=py)
        sub.append(vectorio.Polygon(pixel_shader=P(col), points=pts, x=0, y=0))
        sub.append(text(ac["cs"], 12, -10, col, 1))
        sub.append(text("{:d}".format(int(ac["alt"])), 12, 2, DIM, 1))
        if "sep" in ac:
            sub.append(text("{:.1f}d".format(ac["sep"]), 12, 14, DIM, 1))
        if is_t:
            sub.append(text("T-{}:{:02d}".format(best[1] // 60, best[1] % 60), 12, 26, col, 1))
        g.append(sub)
        if ac["cs"] == "DEMO67":
            demo_grp = sub

    # filter chip — cyan pill, matches mockup (radius 22, cyan border/text)
    outlined(g, CX - 85, 40, 170, 36, PANEL, CYAN, 18)
    lbl = "RANGE 5 MI" if filter_mode == "mi" else "300MM 3.1 MI"
    g.append(text(lbl, CX, 58, CYAN, 2, (0.5, 0.5)))

    # closest-candidate readout — always visible so a near-miss is
    # distinguishable from a dead alert pipeline
    if best:
        g.append(text("CLOSEST {} {:.1f}D T-{}:{:02d}".format(
            best[0], best[2], best[1] // 60, best[1] % 60),
            CX, 378, DIM, 1, (0.5, 0)))
    elif moon[0] <= 5:
        g.append(text("MOON TOO LOW - ALERTS OFF", CX, 378, DIM, 1, (0.5, 0)))

    # alert banner — pink = over the disc, cyan = close pass (bezel ring
    # itself is drawn first, at the bottom of the stack)
    if best and best[2] < SEP_NEAR and best[1] <= 90:
        acol = PINK if best[2] < SEP_HIT else CYAN
        word = "TRANSIT" if best[2] < SEP_HIT else "NEAR"
        g.append(rect(CX - 140, 90, 280, 34, acol))
        lbl = text("{} {}:{:02d} {}".format(word, best[1] // 60, best[1] % 60, best[0]),
                   CX, 107, BG, 2, (0.5, 0.5))
        g.append(lbl)
        if best[0] == "DEMO67":
            demo_lbl = lbl
    g.append(nav_group("RAD"))
    return g


def build_list():
    global list_rows
    g = displayio.Group()
    g.append(rect(0, 0, 480, 480, BG))
    g.append(text("UPCOMING PASSES", CX, 66, CYAN, 2, (0.5, 0)))
    g.append(text("SEP IN DEG FROM MOON CENTER - TAP FOR INFO", CX, 92, DIM, 1, (0.5, 0)))
    m_alt, m_az = moon[0], moon[1]
    rows = []
    for ac in aircraft:
        p = predict(ac, m_az, m_alt)
        if p:
            rows.append((p[0], p[1], ac))
    rows.sort(key=lambda r: r[1])
    list_rows = rows[:6]
    y = 124
    for eta, sep, ac in list_rows:
        col = PINK if sep < SEP_HIT else (CYAN if sep < SEP_NEAR else MOONC)
        outlined(g, 100, y, 280, 40, PANEL, col if sep < SEP_NEAR else GRID, 6)
        g.append(text(ac["cs"], 112, y + 20, col, 2, (0, 0.5)))
        g.append(text(ac["type"], 218, y + 20, DIM, 1, (0, 0.5)))
        g.append(text("{:.1f}d".format(sep), 306, y + 20, DIM, 2, (1, 0.5)))
        g.append(text("{}:{:02d}".format(eta // 60, eta % 60), 368, y + 20, col, 2, (1, 0.5)))
        y += 46
    if not rows:
        g.append(text("NO CANDIDATES IN RANGE", CX, 220, DIM, 2, (0.5, 0)))
    g.append(nav_group("LIST"))
    return g


def build_detail():
    global route_pending
    g = displayio.Group()
    g.append(rect(0, 0, 480, 480, BG))
    if not sel:
        g.append(text("NO FLIGHT SELECTED", CX, 200, DIM, 2, (0.5, 0)))
        g.append(nav_group("LIST"))
        return g
    eta, sep, ac = sel
    hot = sep < SEP_HIT
    col = PINK if hot else (CYAN if sep < SEP_NEAR else MOONC)
    g.append(text(ac["cs"], CX, 70, col, 3, (0.5, 0)))
    # position in list, e.g. 2/6 — the edge arrows page through these
    for k, row in enumerate(list_rows):
        if row[2]["cs"] == ac["cs"]:
            g.append(text("{}/{}".format(k + 1, len(list_rows)), CX, 30, DIM, 1, (0.5, 0)))
            break
    g.append(text(ac["type"], CX, 112, DIM, 2, (0.5, 0)))
    if ac["cs"] in route_cache:
        route = route_cache[ac["cs"]]
        if route:
            g.append(text(route[0].replace("-", " > "), CX, 150, MOONC, 3, (0.5, 0)))
            y = 192
            for name in route[1]:
                g.append(text(name[:36], CX, y, DIM, 1, (0.5, 0)))
                y += 16
        else:
            g.append(text("NO ROUTE FILED", CX, 156, DIM, 2, (0.5, 0)))
    else:
        # paint INSTANTLY with a loading dial; the (blocking) route lookup
        # happens in the main loop right after this frame is on screen
        for i in range(10):
            a = math.radians(i * 36)
            dc = CYAN if i < 3 else GRID2
            g.append(circle(int(CX + math.sin(a) * 22), int(160 - math.cos(a) * 22), 3, dc))
        g.append(text("ROUTE LOOKUP...", CX, 192, DIM, 1, (0.5, 0)))
        route_pending = ac["cs"]
    d = math.sqrt(ac["x"] ** 2 + ac["y"] ** 2)
    g.append(text("ALT {}   GS {:.0f} KT".format(ac["alt"], ac["gs"]), CX, 240, CYAN, 2, (0.5, 0)))
    g.append(text("DIST {:.1f} MI   TRK {:.0f}".format(d, ac["track"]), CX, 270, CYAN, 2, (0.5, 0)))
    g.append(text("SEP {:.1f} DEG   ETA {}:{:02d}".format(
        sep, eta // 60, eta % 60), CX, 300, col, 2, (0.5, 0)))
    g.append(nav_group("LIST"))
    return g


def build_moon():
    g = displayio.Group()
    g.append(rect(0, 0, 480, 480, BG))
    m_alt, m_az, illum, waxing = moon
    moon_icon(g, CX, 150, 85, illum, waxing)
    g.append(text(phase_name(illum, waxing), CX, 254, MOONC, 2, (0.5, 0)))
    g.append(text("{:.0f}% ILLUMINATED".format(illum * 100), CX, 282, PINK, 2, (0.5, 0)))
    g.append(text("ALT {:.0f}   AZ {:.0f}".format(m_alt, m_az), CX, 316, CYAN, 2, (0.5, 0)))
    if moon_rs:
        g.append(text("RISE {}   SET {}".format(moon_rs[0], moon_rs[1]),
                      CX, 346, MOONC, 2, (0.5, 0)))
    g.append(text("ZIP {}  LAT {:.2f} LON {:.2f}".format(ZIP, LAT, LON), CX, 378, DIM, 1, (0.5, 0)))
    g.append(nav_group("MOON"))
    return g


def build_loc():
    g = displayio.Group()
    g.append(rect(0, 0, 480, 480, BG))
    g.append(text("ZIP LOCATION", CX, 30, CYAN, 2, (0.5, 0)))
    g.append(text("5 DIGITS = ZIP / 90 180 270 = ROTATE", CX, 58, DIM, 1, (0.5, 0)))
    shown = ZIP if zip_draft is None else (zip_draft + "_" * 5)[:5]
    outlined(g, CX - 80, 78, 160, 40, PANEL, GRID2, 6)
    g.append(text(shown, CX, 98, MOONC, 3, (0.5, 0.5)))
    for i, k in enumerate(KEYS):
        col_i, row_i = i % 3, i // 3
        x, y = CX - 105 + col_i * 74, 134 + row_i * 62
        bg = 0x12261E if k == "OK" else PANEL
        fg = GREEN if k == "OK" else (PINK if k == "<" else MOONC)
        outlined(g, x, y, 66, 52, bg, GRID2, 8)
        g.append(text(k, x + 33, y + 26, fg, 2, (0.5, 0.5)))
    if loc_msg and time.monotonic() - loc_msg_t < 4:
        g.append(text(loc_msg[0], CX, 382, loc_msg[1], 1, (0.5, 0)))
    g.append(nav_group("LOC"))
    return g


BUILDERS = {"radar": build_radar, "list": build_list, "moon": build_moon,
            "loc": build_loc, "detail": build_detail}

# ---------------- touch init ----------------
class RawCST8XX:
    """Minimal CST8xx poller — skips the driver's chip-ID whitelist,
    which rejects some panel revisions ("Did not find supported CST8XX chip")."""
    def __init__(self, i2c, addr=0x15):
        self._dev = I2CDevice(i2c, addr)
        self._buf = bytearray(7)

    def _read(self):
        with self._dev as d:
            d.write_then_readinto(bytes([0x00]), self._buf)

    def disable_auto_sleep(self):
        """CST8xx auto-sleeps after ~5s idle and ignores I2C while asleep —
        the first tap only WAKES the chip and is swallowed. Reg 0xFE = 0x01,
        same as the Adafruit lib driver does at init."""
        with self._dev as d:
            d.write(bytes([0xFE, 0x01]))

    def dump_id_regs(self):
        """Read 0xA0-0xAA (chip id / fw version live here on CST816S) —
        diagnostic for the Adafruit_CircuitPython_CST8XX chip-ID issue."""
        out = []
        b = bytearray(1)
        for reg in range(0xA0, 0xAB):
            try:
                with self._dev as d:
                    d.write_then_readinto(bytes([reg]), b)
                out.append("{:02X}={:02X}".format(reg, b[0]))
            except OSError:
                out.append("{:02X}=NAK".format(reg))
        return " ".join(out)

    @property
    def touched(self):
        self._read()
        return self._buf[2] & 0x0F

    @property
    def touches(self):
        # wake-tolerant read: a sleeping/busy CST8xx NAKs or returns zeros on
        # the first poke — retry a few times over ~45ms before giving up
        for _ in range(3):
            try:
                self._read()
                if self._buf[2] & 0x0F:
                    x = ((self._buf[3] & 0x0F) << 8) | self._buf[4]
                    y = ((self._buf[5] & 0x0F) << 8) | self._buf[6]
                    return [{"x": x, "y": y}]
                return []
            except OSError:
                time.sleep(0.015)
        return []


# Touch init: raw poller ONLY. Do not attempt the stock adafruit_cst8xx
# driver first — its init reconfigures the chip's reporting mode before
# rejecting the unrecognized chip ID (0xA7 reads 0x00 on this panel batch),
# which silently breaks polled reads afterward. Tracking issue filed against
# Adafruit_CircuitPython_CST8XX; revisit once it accepts this variant.
try:
    touch = RawCST8XX(board.I2C())
    _ = touch.touched  # probe one read
    try:
        touch.disable_auto_sleep()
        print("touch: auto-sleep disabled")
    except Exception as e:
        print("touch: could not disable auto-sleep:", e)
    print("touch: raw CST8XX @0x15 ok")
    if DEBUG_TOUCH:
        print("touch id regs (boot):", touch.dump_id_regs())
except Exception as e:
    print("touch init failed:", e)
    touch = None


def show():
    global demo_grp, demo_lbl
    demo_grp = demo_lbl = None  # build_radar reassigns them when relevant
    while len(root):
        root.pop()
    root.append(BUILDERS[screen]())
    display.refresh()


# ---------------- touch ----------------
def rotate_touch(x, y):
    """Map physical touch coords to logical (rotated) display coords.
    If left/right feel swapped at 90/270 on your unit, swap those two cases."""
    if ROT == 90:
        return y, 479 - x
    if ROT == 180:
        return 479 - x, 479 - y
    if ROT == 270:
        return 479 - y, x
    return x, y


def handle_touch(x, y, repeat=False):
    global screen, filter_mode, zip_draft, ZIP, loc_msg, loc_msg_t, ROT, sel, route_pending, demo_t0
    # nav bar — nearest-chip mapping, no dead gaps between chips
    if 388 <= y <= 452:
        total = 4 * 56 + 3 * 6
        x0 = CX - total // 2
        if x0 <= x <= x0 + total:
            i = max(0, min(3, (x - x0) // 62))
            screen = ("radar", "list", "moon", "loc")[i]
            zip_draft = None
            return True
    # far left / right edge zones. On DETAIL they page through the flight
    # list (past either end exits back to LIST); elsewhere they cycle screens.
    # Generous: the CST8xx reports near-bezel taps compressed inward — a
    # finger on the chevron at x=464 can report as low as ~382.
    if x <= 118 or x >= 385:
        d = 1 if x >= 385 else -1
        if screen == "detail" and sel:
            idx = -1
            for k, row in enumerate(list_rows):
                if row[2]["cs"] == sel[2]["cs"]:
                    idx = k
                    break
            j = idx + d
            if idx >= 0 and 0 <= j < len(list_rows):
                sel = list_rows[j]
            else:
                screen = "list"  # walked off either end (or flight left range)
            return True
        order = ("radar", "list", "moon", "loc")
        i = order.index(screen) if screen in order else 1
        screen = order[(i + d) % 4]
        zip_draft = None
        return True
    if screen == "list" and 124 <= y < 124 + 6 * 46:
        i = (y - 124) // 46  # no dead gaps — nearest row wins
        if i < len(list_rows):
            sel = list_rows[i]
            screen = "detail"
            return True
    if screen == "radar" and 26 <= y <= 90 and CX - 105 <= x <= CX + 105:
        filter_mode = "mm" if filter_mode == "mi" else "mi"
        return True
    if screen == "loc" and 122 <= y <= 392 and 120 <= x <= 364:
        if repeat:
            return False  # held finger must not enter the same digit twice
        # nearest-key mapping, no dead gaps — taps report ~25px low near the
        # bottom of the round panel, so a strict per-key box misses row 4
        col = max(0, min(2, (x - 135) // 74))
        row = max(0, min(3, (y - 134) // 62))
        k = KEYS[row * 3 + col]
        if k == "OK":
            if zip_draft == "67":
                # demo mode: 30s TRANSIT (pink) + 30s NEAR (cyan)
                # passes with a fake plane — for filming/testing
                demo_t0 = time.monotonic()
                screen = "radar"
                zip_draft = None
                return True
            if zip_draft in ("0", "90", "180", "270"):
                ROT = int(zip_draft)
                display.rotation = ROT
                nvm_set_rot(ROT)
                loc_msg = ("ROTATION {} SAVED".format(ROT), GREEN)
                loc_msg_t = time.monotonic()
                zip_draft = None
                return True
            if zip_draft and len(zip_draft) == 5:
                if geocode(zip_draft):
                    ZIP = zip_draft
                    nvm_set_zip(ZIP)
                    loc_msg = ("SAVED {}  {:.2f} {:.2f}".format(ZIP, LAT, LON), GREEN)
                else:
                    loc_msg = ("ZIP LOOKUP FAILED - RETRY", PINK)
                zip_draft = None
            else:
                loc_msg = ("ENTER 5 DIGITS", PINK)
            loc_msg_t = time.monotonic()
        elif k == "<":
            zip_draft = (zip_draft or "")[:-1]
        elif zip_draft and len(zip_draft) >= 5:
            # full draft: say so instead of silently ignoring digits
            loc_msg = ("5 DIGITS MAX - OK OR <", PINK)
            loc_msg_t = time.monotonic()
        else:
            zip_draft = (zip_draft or "") + k
        return True
    return False


# ---------------- main ----------------
def poll_touch():
    """One touch poll + tap dispatch. Called every loop iteration AND
    immediately after every blocking operation (network fetch, ephemeris
    scan, screen rebuild) — the CST8xx has no event buffer, so the sooner
    we read after a freeze, the more of a quick tap we can still catch."""
    global was_down, last_touch, last_tx, last_ty
    if not touch:
        return
    now = time.monotonic()
    try:
        pts = touch.touches
    except Exception:
        pts = []
    if pts:
        tx, ty = rotate_touch(pts[0]["x"], pts[0]["y"])
        moved = abs(tx - last_tx) + abs(ty - last_ty) > 40
        if not was_down or moved or now - last_touch > 0.6:
            is_repeat = was_down and not moved
            was_down = True
            last_touch = now
            last_tx, last_ty = tx, ty
            hit = handle_touch(tx, ty, is_repeat)
            if DEBUG_TOUCH:
                print("tap raw=({},{}) rot=({},{}) screen={} rep={} hit={}".format(
                    pts[0]["x"], pts[0]["y"], tx, ty, screen, is_repeat, hit))
                if isinstance(touch, RawCST8XX):
                    print("touch id regs (finger down):", touch.dump_id_regs())
            if hit:
                show()
                poll_touch()  # catch a finger held through the rebuild
    elif was_down:
        was_down = False
        if DEBUG_TOUCH:
            print("release")


geocode(ZIP)
last_fetch = last_moon = last_rs = -9999
last_demo_frame = 0
show()

while True:
    now = time.monotonic()
    # pending route lookup: the detail screen painted its loading dial first,
    # then we fetch here (blocking) and repaint with the result
    if route_pending:
        cs = route_pending
        route_pending = None
        if fetch_route(cs) is None and cs not in route_cache:
            route_cache[cs] = None  # lookup failed: show NO ROUTE, allow retry via re-tap
            fail = True
        else:
            fail = False
        if screen == "detail":
            show()
        if fail:
            del route_cache[cs]
        poll_touch()

    # defer blocking work (network, ephemeris scans) while the user is
    # interacting — the CST8xx has no buffer, so a tap during a blocked
    # loop is lost forever. Touch gets a 2s priority window.
    interacting = now - last_touch < 2.0

    # demo mode: fake plane crosses the display W>E — first pass dead over
    # the moon (pink TRANSIT), second pass offset (cyan NEAR). Each pass's
    # 30s clock starts only after its slow full rebuild, so the plane's
    # motion is visible from the left edge onward.
    if demo_t0 is not None and now - last_demo_frame > 0.25:
        last_demo_frame = now
        if demo_phase < 0:
            demo_phase = 0
            demo_pass_t0 = None
        p = 0.0 if demo_pass_t0 is None else (now - demo_pass_t0) / 30.0
        if p >= 1.0:
            if demo_phase == 0:
                demo_phase = 1
                demo_pass_t0 = None
                p = 0.0
            else:
                demo_t0 = None
                demo_phase = -1
                aircraft = []
                best = None
                last_fetch = -9999  # resume real data immediately
                show()
        if demo_t0 is not None:
            hit = demo_phase == 0
            fake = {"cs": "DEMO67", "x": -3.0 + 6.0 * p,
                    "y": 0.0 if hit else 0.9,
                    "alt": 3500, "gs": 140, "track": 90, "type": "B738",
                    "sep": 0.2 if hit else 1.5, "eta": int(30 - p * 30)}
            aircraft = [fake]
            best = ("DEMO67", fake["eta"], fake["sep"])
            if screen == "radar" and demo_pass_t0 is not None and demo_grp:
                # incremental frame: slide the plane group + tick the banner
                # ETA — no full rebuild, so this runs at several fps
                demo_grp.x = int(CX + fake["x"] * PX_PER_MI)
                if demo_lbl:
                    word = "TRANSIT" if hit else "NEAR"
                    demo_lbl.text = "{} 0:{:02d} DEMO67".format(word, fake["eta"])
                display.refresh()
            else:
                if screen in ("radar", "list"):
                    show()  # full rebuild once per pass (ring color, banner)
                if demo_pass_t0 is None:
                    demo_pass_t0 = time.monotonic()  # clock starts NOW
        poll_touch()

    if not interacting and now - last_moon > MOON_S:
        try:
            moon = moon_altaz_phase(utc_now(), LAT, LON)
        except Exception as e:
            print("moon calc failed:", e)
        last_moon = now
        poll_touch()

    if not interacting and now - last_rs > 1800:
        try:
            moon_rs = compute_rise_set()
        except Exception as e:
            print("rise/set failed:", e)
        last_rs = now
        poll_touch()

    if not interacting and demo_t0 is None and now - last_fetch > FETCH_S:
        planes = fetch_aircraft()
        poll_touch()  # fetch is the longest freeze — read touch before drawing
        if planes is not None:
            aircraft = planes
            m_alt, m_az = moon[0], moon[1]
            best = None
            if m_alt > 5:
                for ac in aircraft:
                    ac["eta"], ac["sep"] = predict(ac, m_az, m_alt)
                    if best is None or ac["sep"] < best[2]:
                        best = (ac["cs"], ac["eta"], ac["sep"])
        last_fetch = now
        if screen in ("radar", "list"):
            show()
        poll_touch()

    if screen == "loc" and loc_msg and now - loc_msg_t >= 4:
        loc_msg = None
        show()

    # tap detection lives in poll_touch() — see notes there
    poll_touch()

    time.sleep(0.01)
