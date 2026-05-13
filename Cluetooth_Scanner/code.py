# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
BLE Scanner for Adafruit CLUE nRF52840
Passively scans for BLE advertisement packets and displays device info.

CONTROLS
--------
Cap Touch Pad #0 : cycle filter (ALL → NAMED → KNOWN → APPLE → NO-APPLE)
Cap Touch Pad #1 : scroll up / previous detail page / back to list
Cap Touch Pad #2 : scroll down

Button A         : back to list (from detail view)
Button B         : open detail for selected device (list view)
                   next detail page (detail view)

DETAIL VIEW navigation:
  Pad #1 / A     : previous page, or back to list from page 1
  B              : next page (wraps)
"""

# pylint: disable=too-many-lines,too-many-statements,too-many-branches
# pylint: disable=too-many-locals,too-many-return-statements
# pylint: disable=global-statement,redefined-outer-name
# pylint: disable=too-many-boolean-expressions


import time
import gc
import displayio
import terminalio
from adafruit_display_text import label
from adafruit_ble import BLERadio
from adafruit_ble.advertising import Advertisement
import board
import digitalio
import touchio

# ── Display ────────────────────────────────────────────────────────────────────
display = board.DISPLAY
display.rotation = 0
W = display.width   # 240
H = display.height  # 240

C_HEADER  = 0x005080
C_TEXT    = 0xDDDDDD
C_DIM     = 0x778899
C_ACCENT  = 0x00FFAA
C_SEL_BG  = 0x1A2A3A
C_RSSI_HI = 0x00EE44
C_RSSI_MD = 0xFFCC00
C_RSSI_LO = 0xFF3333

SCALE    = 2
CHAR_H   = 12 * SCALE   # 24 px
CHAR_W   = 6  * SCALE   # 12 px
HEADER_H = CHAR_H
FOOTER_H = CHAR_H
MAX_ROWS = (H - HEADER_H - FOOTER_H) // CHAR_H  # 8

LONG_PRESS  = 0.5
SCAN_EVERY  = 12.0
SCAN_WINDOW = 1.0
MAX_DEVICES = 30    # cap device list to avoid memory exhaustion

NAME_CHARS = 19  # full width, no dBm label column
DBM_X      = W - 7 * CHAR_W - 2  # kept for layout but label hidden

# ── BLE ────────────────────────────────────────────────────────────────────────
ble        = BLERadio()
devices    = {}
addr_order = []

def rssi_color(r):
    if r >= -60:
        return C_RSSI_HI
    if r >= -75:
        return C_RSSI_MD
    return C_RSSI_LO

def trunc(s, n):
    """Truncate string to n chars, adding ~ if cut."""
    return s if len(s) <= n else s[:n-1] + "~"

def short_addr(a):
    p = a.split(":")
    return ":".join(p[-3:]) if len(p) >= 3 else a

def fmt_hex(data):
    """Format bytes as hex string."""
    if not data:
        return "(none)"
    return " ".join("{:02X}".format(b) for b in bytes(data))

def clean_addr(addr):
    a = str(addr)
    if a.startswith("<Address ") and a.endswith(">"):
        a = a[9:-1]
    return a

MFR_IDS = {
    (0x4C, 0x00): "Apple",
    (0x06, 0x00): "Microsoft",
    (0x75, 0x00): "Samsung",
    (0x83, 0x01): "Walt Disney",
    (0xD8, 0x0B): "Pura",
    (0xE0, 0x00): "Google",
    (0x0F, 0x00): "Broadcom",
    (0xD2, 0x02): "Tile",
    (0x59, 0x00): "Nordic Semi",
    (0x04, 0x09): "Sony",
    (0x87, 0x02): "Garmin",
    (0x1D, 0x00): "Qualcomm",
}

# BLE Appearance values (0x19 AD type, 16-bit little-endian)
APPEARANCE = {
    0x0000: "Unknown",
    0x0040: "Phone",
    0x0041: "Computer",
    0x0042: "Watch",
    0x0043: "Watch (Sports)",
    0x0044: "Clock",
    0x0045: "Display",
    0x0046: "Remote",
    0x0047: "Eye Glasses",
    0x0048: "Tag",
    0x0049: "Keyring",
    0x004A: "Media Player",
    0x004B: "Barcode Scanner",
    0x0080: "Thermometer",
    0x00C0: "Heart Rate Sensor",
    0x00C1: "Heart Rate Belt",
    0x0100: "Blood Pressure",
    0x0140: "HID",
    0x0141: "Keyboard",
    0x0142: "Mouse",
    0x0143: "Joystick",
    0x0144: "Gamepad",
    0x0145: "Digitizer",
    0x0146: "Card Reader",
    0x0147: "Digital Pen",
    0x0148: "Barcode Scanner",
    0x03C0: "HID Generic",
    0x03C1: "Keyboard",
    0x03C2: "Mouse",
    0x03C3: "Joystick",
    0x03C4: "Gamepad",
    0x03C5: "Digitizer Tablet",
    0x03C6: "Card Reader",
    0x03C7: "Digital Pen",
    0x03C8: "Barcode Scanner",
    0x03C9: "Touchpad",
    0x0C80: "Continuous Glucose",
    0x0180: "Glucose Meter",
    0x01C0: "Running Sensor",
    0x0200: "Cycling",
    0x0201: "Cycling Computer",
    0x0202: "Speed Sensor",
    0x0203: "Cadence Sensor",
    0x0204: "Power Sensor",
    0x0205: "Speed+Cadence",
    0x0300: "Pulse Oximeter",
    0x0301: "Fingertip Oximeter",
    0x0302: "Wrist Oximeter",
    0x0340: "Weight Scale",
    0x0341: "Running Speed Sensor",
    0x0380: "Personal Mobility",
    0x0400: "Insulin Pump",
    0x0440: "Medication Delivery",
    0x0480: "Spirometer",
    0x0500: "Outdoor Sports",
    0x0501: "Location Display",
    0x0502: "Location+Nav",
    0x0503: "Location Pod",
    0x0504: "Location+Nav Pod",
    0x0540: "Environmental Sensor",
    0x01C1: "Running Sensor (in-shoe)",
    0x01C2: "Running Sensor (on-shoe)",
    0x01C3: "Running Sensor (hip)",
    0x0841: "Headphones",
    0x0842: "Earbuds",
    0x0843: "Hearing Aid",
    0x0844: "Cochlear Implant",
}

def parse_appearance(data_dict):
    payload = data_dict.get(0x19)
    if payload and len(payload) >= 2:
        val = payload[0] | (payload[1] << 8)
        return APPEARANCE.get(val, "0x{:04X}".format(val))
    return None

def parse_mfr_data(data_dict):
    """Get manufacturer data from raw 0xFF AD type in data_dict."""
    payload = data_dict.get(0xFF)
    if payload and len(payload) >= 2:
        return bytes(payload)
    return None

def parse_svc_data(data_dict):
    """Get service data (0x16) as hex string."""
    payload = data_dict.get(0x16)
    if payload and len(payload) >= 2:
        return bytes(payload)
    return None

# Apple manufacturer data type byte (byte index 2 after 4C 00)
APPLE_MFR_TYPES = {
    0x01: "iBeacon (off)",
    0x02: "iBeacon",
    0x05: "AirDrop",
    0x07: "AirPods",
    0x08: "Hey Siri",
    0x09: "AirPlay Target",
    0x0A: "AirPlay Source",
    0x0B: "MagSafe",
    0x0C: "Handoff",
    0x0D: "Wi-Fi Settings",
    0x0E: "HomeKit",
    0x0F: "Proximity Pairing",
    0x10: "Nearby Action",
    0x12: "FindMy/Nearby",
    0x13: "Instant Hotspot",
    0x15: "AirPrint",
    0x16: "HomeKit Encryption",
    0x19: "AirTag/FindMy",
}

def decode_apple_mfr(mfr):
    """Decode Apple manufacturer data type from byte 2."""
    if not mfr or len(mfr) < 3:
        return None
    if mfr[0] == 0x4C and mfr[1] == 0x00:
        return APPLE_MFR_TYPES.get(mfr[2])
    return None

# Apple Nearby Action types (0x10 subtype, byte 4)
APPLE_NEARBY_ACTIONS = {
    0x01: "Apple TV Setup",
    0x04: "WiFi Password Share",
    0x06: "Instant Hotspot",
    0x07: "Join Network",
    0x08: "Watch Setup",
    0x09: "Apple TV Pair",
    0x0B: "Transfer Number",
    0x0C: "TV Color Balance",
    0x0D: "HomePod Setup",
    0x0E: "Setup After Restore",
    0x20: "Watch Auto Unlock",
    0x27: "AppleTV Color Balance",
    0x2B: "ApplePay",
    0x38: "Watch Auto Unlock Mac",
    0x43: "Continuity Camera",
    0x4C: "Universal Control",
}

def decode_apple_mfr_detail(mfr):
    """Decode Apple mfr payload into a human-readable summary."""
    if not mfr or len(mfr) < 3 or mfr[0] != 0x4C or mfr[1] != 0x00:
        return None
    t = mfr[2]
    if t == 0x09 and len(mfr) >= 11:
        ip = "{}.{}.{}.{}".format(mfr[6], mfr[7], mfr[8], mfr[9])
        return "AirPlay ip={}".format(ip)
    if t == 0x10 and len(mfr) >= 5:
        action = APPLE_NEARBY_ACTIONS.get(mfr[4], "0x{:02X}".format(mfr[4]))
        return "NearbyAction={}".format(action)
    if t == 0x12 and len(mfr) >= 6:
        status = mfr[4]
        flags  = mfr[5]
        return "FindMy status=0x{:02X} flags=0x{:02X}".format(status, flags)
    if t == 0x0C:
        return "Handoff (encrypted)"
    if t == 0x01:
        return "iBeacon (off)"
    if t == 0x19 and len(mfr) >= 4:
        return "AirTag/FindMy beacon"
    if t == 0x07 and len(mfr) >= 4:
        return "AirPods"
    return None

def guess_apple_device(mfr):
    """Best-guess Apple device type from advertisement data."""
    if not mfr or len(mfr) < 3 or mfr[0] != 0x4C or mfr[1] != 0x00:
        return None
    t = mfr[2]

    # AirPods — proximity pairing subtype
    if t == 0x07:
        return "AirPods"

    # AirTag / FindMy accessory — long FindMy payload with non-zero status
    if t == 0x19:
        return "AirTag/FindMy"
    if t == 0x12 and len(mfr) >= 6:
        status = mfr[4]
        if status != 0x00:
            return "AirTag? (separated)"

    # AirPlay Target — Apple TV or HomePod
    if t == 0x09:
        # HomePod tends to also advertise nearby action 0x0D (Whole Home Audio)
        # Apple TV tends to be stable, high seen count, fixed location
        return "AppleTV/HomePod"

    # Handoff — iPhone or iPad (Macs do Handoff too but less commonly)
    if t == 0x0C:
        # Nearby actions: Sidecar (0x3F) or Continuity Camera (0x43) → iPad
        # Universal Control (0x4C) → iPad or Mac
        return "iPhone/iPad"

    # Nearby Action
    if t == 0x10 and len(mfr) >= 5:
        action = mfr[4]
        if action == 0x3F:
            return "iPad (Sidecar)"
        if action == 0x43:
            return "iPhone/iPad (Cont.Cam)"
        if action == 0x4C:
            return "iPad/Mac (UnivCtrl)"
        if action == 0x38:
            return "Apple Watch"
        if action in (0x05, 0x01):
            return "Apple Watch (setup)"
        if action in (0x08, 0x07, 0x09):
            return "iPhone (setup)"
        if action in (0x0B, 0x0D):
            return "HomePod (setup)"
        if action == 0x06:
            return "Apple TV (setup)"
        return "iPhone/iPad"

    # FindMy/Nearby Info with zero status — iPhone in background
    if t == 0x12:
        return "iPhone"

    # iBeacon off — iPhone idle BLE
    if t == 0x01:
        return "iPhone (idle)"

    # HomeKit encryption — a HomeKit accessory
    if t == 0x16:
        return "HomeKit device"

    # Hey Siri
    if t == 0x08:
        return "Siri device"

    return "Apple device"

# OUI table: verified against IEEE registry
# Only public addresses carry meaningful OUIs
# Random addresses (type=1) use locally-administered bits and are not looked up
OUI = {
    # Apple
    "ACDE48": "Apple",
    "F0B479": "Apple",
    "28CFE9": "Apple",
    "9C2032": "Apple",
    "A45E60": "Apple",
    "689A87": "Apple",
    "3C2EFF": "Apple",
    "70ECE4": "Apple",
    "DC2B2A": "Apple",
    "F4F15A": "Apple",
    "1499E2": "Apple",
    "F0DCE2": "Apple",
    # Samsung
    "B8B409": "Samsung",
    "8825A8": "Samsung",
    "CC14F0": "Samsung",
    "F8042E": "Samsung",
    "784F43": "Samsung",
    "B47443": "Samsung",
    # Espressif (ESP32/ESP8266 — many IoT devices)
    "D0EF76": "Espressif",
    "34987A": "Espressif",
    "A4CF12": "Espressif",
    "24DCC3": "Espressif",
    "246F28": "Espressif",
    "80646F": "Espressif",
    "7C9EBD": "Espressif",
    "18FE34": "Espressif",
    "5CCF7F": "Espressif",
    "240AC4": "Espressif",
    "30AEA4": "Espressif",
    "ACDCA4": "Espressif",
    # Bose
    "786C1C": "Bose",
    "04526F": "Bose",
    "88C9E8": "Bose",
    # Nordic Semiconductor
    "F4CE36": "Nordic",
    "EF4A6C": "Nordic",
    # Texas Instruments
    "000A16": "TI",
    "000B57": "TI",
    "BCFC01": "TI",
    # Tile
    "0CF3EE": "Tile",
    # Fitbit
    "008098": "Fitbit",
}

# Standard GATT service UUIDs → profile name
GATT_SERVICES = {
    0x1800: "Generic Access",
    0x1801: "Generic Attribute",
    0x1802: "Immediate Alert",
    0x1803: "Link Loss",
    0x1804: "Tx Power",
    0x1805: "Current Time",
    0x180A: "Device Info",
    0x180D: "Heart Rate",
    0x180F: "Battery",
    0x1810: "Blood Pressure",
    0x1812: "HID",
    0x1816: "Cycling Speed",
    0x1818: "Cycling Power",
    0x1819: "Location & Nav",
    0x181A: "Environmental",
    0x181C: "User Data",
    0x181D: "Body Composition",
    0x181E: "Weight Scale",
    0x1820: "Internet Protocol",
    0x1826: "Fitness Machine",
    0x183B: "Audio Input",
    0x183E: "Microphone Control",
    0x1840: "Telephony Bearer",
    0x1843: "Media Control",
    0x1848: "Coordinated Set",
    # Common proprietary short UUIDs
    0xFD6F: "Apple Nearby",   # AirTag / FindMy
    0xFD5A: "Apple HomeKit",
    0xFE9F: "Google Fast Pair",
    0xFEAA: "Google Eddystone",
    0xFE2C: "Microsoft Swift Pair",
    0xFE03: "Amazon Alexa",
    # Proprietary / vendor-specific known UUIDs
    0x1725: "Scosche",
    0xFEBE: "Bose",
}

def parse_service_uuids(data_dict):
    """Extract service UUID names from a decoded data_dict.
    Keys are AD types: 0x02/0x03 = 16-bit UUIDs, 0x06/0x07 = 128-bit UUIDs."""
    results = []
    try:
        # 16-bit service UUIDs (incomplete=0x02, complete=0x03)
        for ad_type in (0x02, 0x03):
            payload = data_dict.get(ad_type)
            if payload:
                for j in range(0, len(payload) - 1, 2):
                    val = payload[j] | (payload[j+1] << 8)
                    svc_name = GATT_SERVICES.get(val)
                    svc_label = svc_name if svc_name else "0x{:04X}".format(val)
                    if svc_label not in results:
                        results.append(svc_label)
        # 128-bit vendor UUIDs (incomplete=0x06, complete=0x07)
        for ad_type in (0x06, 0x07):
            payload = data_dict.get(ad_type)
            if payload and len(payload) >= 16:
                # First 2 bytes are the varying part in little-endian
                val = payload[0] | (payload[1] << 8)
                svc_name = GATT_SERVICES.get(val)
                svc_label = svc_name if svc_name else "(proprietary)"
                if svc_label not in results:
                    results.append(svc_label)
    except Exception:  # pylint: disable=broad-except
        pass
    return results

def services_str(svcs):
    if not svcs:
        return "(none)"
    return ", ".join(svcs)

def company_from_mfr(mfr):
    if not mfr or len(mfr) < 2:
        return None
    return MFR_IDS.get((mfr[0], mfr[1]))

def company_from_addr(addr_str):
    oui = addr_str.replace(":", "").upper()[:6]
    return OUI.get(oui)

def company_tag(addr_str, mfr, addr_type):
    """Return best company name from mfr data or OUI."""
    c = company_from_mfr(mfr)
    if c:
        return c
    if addr_type == 0:
        c = company_from_addr(addr_str)
        if c:
            return c
    return ""

# ── Display build ──────────────────────────────────────────────────────────────
root = displayio.Group()
display.root_group = root

def make_rect(w, h, color):
    bmp = displayio.Bitmap(w, h, 1)
    pal = displayio.Palette(1)
    pal[0] = color
    return displayio.TileGrid(bmp, pixel_shader=pal)

# Header
hdr_bg = make_rect(W, HEADER_H, C_HEADER)
root.append(hdr_bg)
hdr_lbl = label.Label(terminalio.FONT, text="BLE SCANNER", color=0xFFFFFF,
                       scale=SCALE, x=4, y=HEADER_H // 2)
root.append(hdr_lbl)
pos_lbl = label.Label(terminalio.FONT, text="0/0", color=C_ACCENT,
                       scale=SCALE, x=W - 7 * CHAR_W, y=HEADER_H // 2)
root.append(pos_lbl)

# Footer
ftr_bg = make_rect(W, FOOTER_H, 0x111111)
ftr_bg.y = H - FOOTER_H
root.append(ftr_bg)
ftr_lbl = label.Label(terminalio.FONT, text="1^ 2v  B:info", color=C_DIM,
                       scale=SCALE, x=4, y=H - FOOTER_H // 2)
root.append(ftr_lbl)

# Selection highlight
sel_bg = make_rect(W, CHAR_H, C_SEL_BG)
sel_bg.y = HEADER_H
root.append(sel_bg)

# List rows
row_name = []
row_dbm  = []
for i in range(MAX_ROWS):
    y = HEADER_H + i * CHAR_H + CHAR_H // 2
    ln = label.Label(terminalio.FONT, text="", color=C_TEXT,    scale=SCALE, x=4,     y=y)
    ld = label.Label(terminalio.FONT, text="", color=C_RSSI_HI, scale=SCALE, x=DBM_X, y=y)
    root.append(ln)
    root.append(ld)
    row_name.append(ln)
    row_dbm.append(ld)

# Detail overlay
det_group = displayio.Group()
det_bg = make_rect(W, H, 0x050510)
det_group.append(det_bg)
det_lines = []
for i in range(H // CHAR_H):
    dl = label.Label(terminalio.FONT, text="", color=C_TEXT,
                     scale=SCALE, x=4, y=i * CHAR_H + CHAR_H // 2)
    det_group.append(dl)
    det_lines.append(dl)

# ── Buttons ────────────────────────────────────────────────────────────────────
_pin_a = digitalio.DigitalInOut(board.BUTTON_A)
_pin_a.switch_to_input(pull=digitalio.Pull.UP)
_pin_b = digitalio.DigitalInOut(board.BUTTON_B)
_pin_b.switch_to_input(pull=digitalio.Pull.UP)

_touch0      = touchio.TouchIn(board.P0)
_touch0_last = False
_touch1      = touchio.TouchIn(board.P1)
_touch1_last = False
_touch2      = touchio.TouchIn(board.P2)
_touch2_last = False

# Filter modes
FILTERS      = ["ALL", "NAMED", "KNOWN", "APPLE", "NO-APPLE"]
filter_mode  = 0

class Button:
    def __init__(self, pin):
        self._pin     = pin
        self._down_at = None
        self._last    = False
        self.tapped   = False
        self.held     = False

    def update(self, now):
        self.tapped = False
        self.held   = False
        pressed = not self._pin.value
        if pressed and not self._last:
            self._down_at = now
        elif not pressed and self._last:
            if self._down_at is not None and (now - self._down_at) < LONG_PRESS:
                self.tapped = True
            self._down_at = None
        elif pressed and self._down_at is not None:
            if (now - self._down_at) >= LONG_PRESS:
                self.held     = True
                self._down_at = None
        self._last = pressed

btn_A = Button(_pin_a)
btn_B = Button(_pin_b)

# ── State ──────────────────────────────────────────────────────────────────────
selected    = 0
scroll_off  = 0
show_detail = False
last_scan        = -SCAN_EVERY
last_button_time = -999.0   # time of last button activity
BUTTON_IDLE      = 3.0      # seconds of inactivity before scan is allowed

# ── Scan ───────────────────────────────────────────────────────────────────────
def do_scan():
    ftr_lbl.text = "...scanning..."
    gc.collect()  # reclaim memory before allocating scan buffer
    for buf in (4096, 2048, 1024):
        try:
            scan = ble.start_scan(
                Advertisement,
                minimum_rssi=-100,
                timeout=SCAN_WINDOW,
                active=True,
                buffer_size=buf,
            )
            break
        except MemoryError:
            try:
                ble.stop_scan()
            except Exception:  # pylint: disable=broad-except
                pass
            gc.collect()  # try to recover before next attempt
    else:
        print("scan failed: out of memory, waiting...")
        ftr_lbl.text = "mem err, waiting..."
        gc.collect()
        time.sleep(5.0)  # longer wait to let things settle
        ftr_lbl.text = "1^ 2v  B:info"
        return
    try:
        for entry in scan:
            addr_str = clean_addr(entry.address)
            try:
                name = entry.complete_name or entry.short_name or ""
            except Exception:  # pylint: disable=broad-except
                name = ""
            # Pull all fields from data_dict directly
            dd = entry.data_dict
            try:
                msd = parse_mfr_data(dd)
            except Exception:  # pylint: disable=broad-except
                msd = None
            try:
                svcs = parse_service_uuids(dd)
            except Exception:  # pylint: disable=broad-except
                svcs = []
            try:
                appearance = parse_appearance(dd)
            except Exception:  # pylint: disable=broad-except
                appearance = None
            try:
                svc_data = parse_svc_data(dd)
            except Exception:  # pylint: disable=broad-except
                svc_data = None
            if addr_str not in devices:
                if len(devices) >= MAX_DEVICES:
                    continue   # list full, skip new entries until pruning
                devices[addr_str] = {
                    "name": name, "rssi": entry.rssi,
                    "addr_type": entry.address.type, "msd": msd,
                    "svcs": svcs, "appearance": appearance,
                    "svc_data": svc_data, "count": 1,
                    "last_seen": time.monotonic(),
                }
                addr_order.append(addr_str)
            else:
                dev = devices[addr_str]
                dev["rssi"]      = entry.rssi
                dev["count"]    += 1
                dev["last_seen"] = time.monotonic()
                if name:
                    dev["name"] = name
                if msd:
                    dev["msd"] = msd
                if svcs:
                    dev["svcs"] = svcs
                if appearance:
                    dev["appearance"] = appearance
                if svc_data:
                    dev["svc_data"] = svc_data
        ble.stop_scan()
    except Exception as e:  # pylint: disable=broad-except
        print("scan error:", e)
        try:
            ble.stop_scan()
        except Exception:  # pylint: disable=broad-except
            pass

    # Prune devices not seen in the last 3 scan cycles
    cutoff = time.monotonic() - (SCAN_EVERY * 3)
    stale  = [a for a in addr_order if devices[a].get("last_seen", 0) < cutoff]
    for a in stale:
        addr_order.remove(a)
        del devices[a]
    # Clamp selected index if list shrank
    global selected, scroll_off
    if addr_order and selected >= len(addr_order):
        selected   = len(addr_order) - 1
        scroll_off = max(0, selected - MAX_ROWS + 1)

    # Sort: strongest signal first
    addr_order.sort(key=lambda a: -devices[a]["rssi"])
    gc.collect()
    print("free memory: {} bytes".format(gc.mem_free()))

    # Serial dump — full list then filtered view if active
    print("=" * 60)
    print("BLE SCANNER — {} devices".format(len(addr_order)))
    print("=" * 60)
    for i, addr in enumerate(addr_order):
        dev = devices[addr]
        co           = company_from_mfr(dev["msd"])
        oui_co       = company_from_addr(addr) if dev["addr_type"] == 0 else None
        apple_type   = decode_apple_mfr(dev["msd"])
        apple_detail = decode_apple_mfr_detail(dev["msd"])
        guess        = guess_apple_device(dev["msd"])
        display_co   = co or (oui_co if not co else co) or "(unknown)"
        mfr_str      = apple_detail if apple_detail else fmt_hex(dev["msd"])
        line1 = "[{:02d}] addr={} type={} name={!r}".format(
            i + 1, addr,
            "public" if dev["addr_type"] == 0 else "random",
            dev["name"] or "")
        line2 = "     company={} chip={} guess={} apple={}".format(
            display_co, oui_co or "(n/a)",
            guess or "(n/a)", apple_type or "(n/a)")
        line3 = "     appearance={} rssi={}dBm seen={} svcs=[{}]".format(
            dev.get("appearance") or "(none)",
            dev["rssi"], dev["count"],
            services_str(dev.get("svcs", [])))
        line4 = "     msd={} svc_data={}".format(
            mfr_str, fmt_hex(dev.get("svc_data")))
        print(line1)
        print(line2)
        print(line3)
        print(line4)

    # Print filtered view if a filter is active
    if filter_mode != 0:
        flist = filtered_order()
        print("-- FILTER: {} ({}/{}) --".format(
            FILTERS[filter_mode], len(flist), len(addr_order)))
        for i, addr in enumerate(flist):
            dev = devices[addr]
            guess = guess_apple_device(dev["msd"])
            co    = company_from_mfr(dev["msd"]) or \
                    (company_from_addr(addr) if dev["addr_type"] == 0 else None) or "(unknown)"
            name  = dev["name"] or guess or co or addr
            print("  [{:02d}] {} rssi={}dBm".format(i + 1, name, dev["rssi"]))
    print()

    ftr_lbl.text = "1^ 2v  B:info" if not show_detail else "A: back to list"

# ── Render ─────────────────────────────────────────────────────────────────────
def filtered_order():
    """Return addr_order filtered by current filter_mode."""
    if filter_mode == 0:  # ALL
        return addr_order
    result = []
    for addr in addr_order:
        dev = devices[addr]
        msd = dev["msd"]
        is_apple = (msd and len(msd) >= 2 and msd[0] == 0x4C and msd[1] == 0x00)
        has_name = bool(dev["name"])
        co   = company_tag(addr, msd, dev["addr_type"])
        guess = guess_apple_device(msd)
        is_known = bool(has_name or co or guess)
        if filter_mode == 1 and not has_name:  # NAMED
            continue
        if filter_mode == 2 and not is_known:  # KNOWN
            continue
        if filter_mode == 3 and not is_apple:  # APPLE
            continue
        if filter_mode == 4 and is_apple:  # NO-APPLE
            continue
        result.append(addr)
    return result

def render_list():
    flist = filtered_order()
    total = len(flist)
    visible = flist[scroll_off : scroll_off + MAX_ROWS]
    for i in range(MAX_ROWS):
        if i < len(visible):
            addr = visible[i]
            dev  = devices[addr]
            r    = dev["rssi"]
            # Build the best display name available
            guess = guess_apple_device(dev["msd"])
            co    = company_tag(addr, dev["msd"], dev["addr_type"])
            if dev["name"]:
                name = dev["name"]
            elif guess:
                name = guess
            elif co:
                name = co
            else:
                name = short_addr(addr)
            is_sel = (scroll_off + i) == selected
            row_name[i].text  = trunc(name, NAME_CHARS)
            row_name[i].color = C_ACCENT if is_sel else rssi_color(r)
            row_dbm[i].text   = ""
        else:
            row_name[i].text = ""
            row_dbm[i].text  = ""
    si = selected - scroll_off
    sel_bg.y      = HEADER_H + si * CHAR_H
    sel_bg.hidden = not 0 <= si < MAX_ROWS
    # Header shows filter mode and filtered/total count
    fmode = FILTERS[filter_mode]
    if filter_mode == 0:
        pos_lbl.text = str(len(addr_order))
        hdr_lbl.text = "BLE SCANNER"
    else:
        pos_lbl.text = "{}/{}".format(total, len(addr_order))
        hdr_lbl.text = "BLE " + fmode

detail_page = 0   # current page in detail view

def build_detail_lines():
    """Build the full list of (text, color) lines for the selected device."""
    flist = filtered_order()
    if not flist or selected >= len(flist):
        return []
    addr = flist[selected]
    dev  = devices[addr]
    r    = dev["rssi"]
    msd  = fmt_hex(dev["msd"])
    appearance   = dev.get("appearance")
    svc_data     = fmt_hex(dev.get("svc_data"))
    apple_type   = decode_apple_mfr(dev["msd"])
    apple_detail = decode_apple_mfr_detail(dev["msd"])
    mfr_co       = company_from_mfr(dev["msd"])
    oui_co       = company_from_addr(addr) if dev["addr_type"] == 0 else None
    display_co   = mfr_co or oui_co or "unknown"
    lines = [
        ("== DETAIL ==",                        C_ACCENT),
        (trunc(dev["name"] or "(unnamed)", 18), C_TEXT),
        (trunc(display_co, 18),                 C_DIM),
    ]
    if oui_co and oui_co != display_co:
        lines.append((trunc("chip: " + oui_co, 18), C_DIM))
    lines += [
        (trunc(addr, 18),                       C_DIM),
        ("{} dBm".format(r),                    rssi_color(r)),
        ("seen {} times".format(dev["count"]),  C_DIM),
    ]
    guess = guess_apple_device(dev["msd"])
    if guess:
        lines.append(("guess: " + trunc(guess, 11), C_ACCENT))
    if apple_type:
        lines.append(("apple: " + trunc(apple_type, 11), C_DIM))
    if appearance:
        lines.append(("appear: " + trunc(appearance, 10), C_DIM))
    lines.append(("-- services --",             C_ACCENT))
    svcs = dev.get("svcs", [])
    if svcs:
        for s in svcs:
            lines.append((trunc(s, 18),         C_DIM))
    else:
        lines.append(("(none advertised)",      C_DIM))
    lines.append(("-- msd data --",             C_ACCENT))
    if apple_detail:
        lines.append((trunc(apple_detail, 18),  C_DIM))
    else:
        lines.append((trunc(msd, 18),           C_DIM))
        if len(msd) > 18:
            lines.append((trunc(msd[18:], 18),  C_DIM))
    if svc_data != "(none)":
        lines.append(("-- svc data --",         C_ACCENT))
        lines.append((trunc(svc_data, 18),      C_DIM))
    return lines

def render_detail():
    global detail_page
    lines = build_detail_lines()
    if not lines:
        return
    page_size  = len(det_lines) - 1          # reserve last row for nav hint
    total_pages = max(1, (len(lines) + page_size - 1) // page_size)
    detail_page = min(detail_page, total_pages - 1)
    start = detail_page * page_size
    page_lines = lines[start : start + page_size]
    for i, dl in enumerate(det_lines):
        if i < len(page_lines):
            dl.text, dl.color = page_lines[i][0], page_lines[i][1]
        else:
            dl.text = ""
    # Nav hint on last row
    if total_pages > 1:
        if detail_page == 0:
            hint = "A:list B:next pg 1/{}".format(total_pages)
        else:
            hint = "A:prev B:next pg {}/{}".format(detail_page + 1, total_pages)
    else:
        hint = "A: back to list"
    det_lines[-1].text  = trunc(hint, 18)
    det_lines[-1].color = C_DIM

def open_detail():
    global show_detail, detail_page
    show_detail = True
    detail_page = 0
    render_detail()
    root.append(det_group)
    ftr_lbl.text = "A:back  B:next pg"

def close_detail():
    global show_detail
    show_detail = False
    if det_group in root:
        root.remove(det_group)
    ftr_lbl.text = "1^ 2v  B:info"

# ── Main loop ──────────────────────────────────────────────────────────────────
print("Bluetooth Scanner ready")

while True:
    now = time.monotonic()

    # Only scan if no button activity for BUTTON_IDLE seconds
    if (now - last_scan >= SCAN_EVERY and
            now - last_button_time >= BUTTON_IDLE):
        do_scan()
        last_scan = time.monotonic()
        render_list()

    btn_A.update(now)
    btn_B.update(now)

    # Pad #0 — filter, Pad #1 — scroll up, Pad #2 — scroll down
    touch0_val = _touch0.value
    touch0_tap = touch0_val and not _touch0_last
    _touch0_last = touch0_val

    touch1_val = _touch1.value
    touch1_tap = touch1_val and not _touch1_last
    _touch1_last = touch1_val

    touch2_val = _touch2.value
    touch2_tap = touch2_val and not _touch2_last
    _touch2_last = touch2_val

    # Track any button or touch activity
    if (btn_A.tapped or btn_A.held or btn_B.tapped or btn_B.held
            or touch0_tap or touch1_tap or touch2_tap):
        last_button_time = now

    if show_detail:
        if btn_A.tapped or touch1_tap:
            if detail_page > 0:
                detail_page -= 1
                render_detail()
            else:
                close_detail()
                render_list()
        if btn_B.tapped:
            lines = build_detail_lines()
            page_size   = len(det_lines) - 1
            total_pages = max(1, (len(lines) + page_size - 1) // page_size)
            detail_page = (detail_page + 1) % total_pages
            render_detail()
        if touch0_tap:
            # Filter cycles even from detail view
            filter_mode = (filter_mode + 1) % len(FILTERS)
            close_detail()
            render_list()
    else:
        if touch0_tap:
            filter_mode = (filter_mode + 1) % len(FILTERS)
            selected = scroll_off = 0
            render_list()

        if btn_A.tapped:
            close_detail()

        flist = filtered_order()
        if touch1_tap and flist:
            selected = (selected - 1) % len(flist)
            if selected < scroll_off:
                scroll_off = selected
            elif selected >= scroll_off + MAX_ROWS:
                scroll_off = selected - MAX_ROWS + 1
            render_list()

        if touch2_tap and flist:
            selected = (selected + 1) % len(flist)
            if selected < scroll_off:
                scroll_off = 0
            elif selected >= scroll_off + MAX_ROWS:
                scroll_off = selected - MAX_ROWS + 1
            render_list()

        if btn_B.tapped and flist:
            open_detail()
