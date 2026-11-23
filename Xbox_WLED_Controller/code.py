# SPDX-FileCopyrightText: 2026 Erin St Blaine for Adafruit Industries
# SPDX-License-Identifier: MIT

# Pylint exceptions for embedded CircuitPython application:
# - The single-file guide runs directly as CIRCUITPY/code.py.
# - Wi-Fi/BLE failures must not terminate the remote control loop.
# - Two small state-management functions update shared device selection.
# pylint: disable=too-many-lines,broad-except,global-statement

# Xbox WLED Controller — Adafruit Learn example.
#
# Xbox Controller -> CircuitPython -> WLED
# Hardware: Adafruit Feather ESP32-S3 TFT (#5483), Xbox Wireless Controller
# Firmware: CircuitPython 10.3.x
#
# SETUP
# 1. Install adafruit_requests.mpy, adafruit_connection_manager.mpy,
#    and adafruit_display_text/ in CIRCUITPY/lib/.
# 2. Add CIRCUITPY_WIFI_SSID and CIRCUITPY_WIFI_PASSWORD to settings.toml.
# 3. No Xbox Bluetooth address needed: controller is discovered by BLE HID.
# 4. Save this file as CIRCUITPY/code.py. Turn on the Xbox controller;
#    hold its pairing button if automatic reconnection does not start.
# 5. WLED devices must advertise _wled._tcp on the same local network.
#
# CONTROLS
# D-pad left/right: previous/next WLED device
# D-pad up: refresh network discovery
# A button: power on/off for selected device
# Left joystick up/down: previous/next PALETTE (one per flick)
# Left joystick left/right: previous/next EFFECT (one per flick)
# X button: save current lighting settings to the first free preset slot
# Y button: reserved for a user-defined action (currently unassigned)
# B button: RECALL the already-configured boot preset (does not change startup settings)
# Right joystick up/down: brightness (repeats while held)
# Right joystick left/right: previous/next saved preset or playlist
# Right trigger: toggle WLED UDP sync SEND (leaves RECEIVE unchanged)
#
# Selecting a device schedules two warm-yellow flashes. The original
# segment settings and power state are restored afterward. The identification
# signals are not broadcast to other WLED nodes.
#
# The HID byte offsets below were determined for the tested Xbox controller;
# other controller models/firmware may have different reports.

import os
import time
import board
import displayio
import terminalio
import wifi
import mdns
import _bleio
import adafruit_requests
import adafruit_connection_manager
from adafruit_display_text import label

# Most readers can leave this at None. If there are multiple BLE HID devices
# nearby (for example a Bluetooth keyboard), set this to your Xbox address
# to avoid connecting to the wrong device.
XBOX_ADDRESS = None
SCAN_SECONDS = 5
XBOX_SCAN_SECONDS = 8
XBOX_CONNECT_TIMEOUT = 10
RECONNECT_DELAY = 2
HTTP_TIMEOUT = 4
HID_SERVICE_UUID = _bleio.UUID(0x1812)
HID_REPORT_UUID = _bleio.UUID(0x2A4D)

# Xbox BLE HID report offsets. 16-bit values are little-endian.
DPAD_BYTE = 12
BUTTONS_BYTE = 13
LEFT_X_BYTE = 0
LEFT_Y_BYTE = 2
RIGHT_X_BYTE = 4
RIGHT_Y_BYTE = 6
RIGHT_TRIGGER_BYTE = 10
DPAD_UP = 1
DPAD_RIGHT = 3
DPAD_LEFT = 7
A_BUTTON_MASK = 0x01
B_BUTTON_MASK = 0x02
X_BUTTON_MASK = 0x08  # Confirmed with the controller: X reports 0x08
Y_BUTTON_MASK = 0x10  # Available for a future custom action

# Display
screen = displayio.Group()
board.DISPLAY.root_group = screen
heading = label.Label(terminalio.FONT, text="WLED REMOTE", color=0x00FFFF)
heading.x, heading.y = 12, 14
screen.append(heading)
project_text = label.Label(terminalio.FONT, text="Starting", color=0xFFFFFF, scale=2)
project_text.x, project_text.y = 12, 43
screen.append(project_text)
fx_text = label.Label(terminalio.FONT, text="FX: --", color=0x77E8D7)
fx_text.x, fx_text.y = 12, 77
screen.append(fx_text)
palette_text = label.Label(terminalio.FONT, text="Palette: --", color=0xFFD58C)
palette_text.x, palette_text.y = 12, 95
screen.append(palette_text)
status_text = label.Label(terminalio.FONT, text="", color=0xFFFFFF)
status_text.x, status_text.y = 12, 119
screen.append(status_text)

# ---------------------------- Display helpers ----------------------------

def show(message):
    print(message)
    status_text.text = message[:35]

def set_detail_labels(effect="--", palette="--"):
    # The built-in terminal font is approximately 6 pixels per character.
    fx_text.text = "FX: " + str(effect)[:34]
    palette_text.text = "Palette: " + str(palette)[:30]

# ----------------------- Network and discovery -----------------------

# Wi-Fi credentials in CIRCUITPY/settings.toml
if not wifi.radio.connected:
    ssid = os.getenv("CIRCUITPY_WIFI_SSID")
    password = os.getenv("CIRCUITPY_WIFI_PASSWORD")
    if not ssid or not password:
        raise RuntimeError("Wi-Fi settings missing from settings.toml")
    show("Connecting Wi-Fi...")
    wifi.radio.connect(ssid, password)

pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
requests = adafruit_requests.Session(pool)
mdns_server = mdns.Server(wifi.radio)

# Tuples: (display name, current IP string, hostname)
devices = []
selected = 0

def display_selection():
    if not devices:
        project_text.text = "No WLED"
        set_detail_labels()
        show("D-pad UP: rescan")
        return
    name, ip, hostname = devices[selected]
    project_text.text = name[:17]
    print("Selected:", name, "at", ip, "(" + hostname + ")")
    show(f"{selected + 1}/{len(devices)}  A:power UP:scan")

def discover():
    global devices, selected
    previous_host = devices[selected][2] if devices else None
    show("Scanning for WLED...")
    try:
        found = mdns_server.find(service_type="_wled", protocol="_tcp", timeout=SCAN_SECONDS)
        unique = {}
        for svc in found:
            if svc.ipv4_address is None:
                continue
            hostname = svc.hostname
            key = hostname.lower()
            unique[key] = (svc.instance_name or hostname, str(svc.ipv4_address), hostname)
        devices = sorted(unique.values(), key=lambda entry: entry[0].lower())
        selected = 0
        if previous_host:
            for i, entry in enumerate(devices):
                if entry[2].lower() == previous_host.lower():
                    selected = i
                    break
        print("Found", len(devices), "WLED devices")
        for name, ip, host in devices:
            print("  ", name, host, ip)
        reset_control_cache()
        display_selection()
    except Exception as error:
        print("Discovery error:", repr(error))
        show("Scan failed; UP retries")
        # Preserve old list in case of transient discovery failures.

# ----------------------- Gamepad report parsing -----------------------

def axis_value(data, index):
    """16-bit little-endian analog joystick axis."""
    return data[index] | (data[index + 1] << 8)

# Axes center around 32768. Avoid drifting joysticks.
STICK_LOW = 12000
STICK_HIGH = 53500
BRIGHTNESS_STEP = 32  # About 13% per step instead of 5%
BRIGHTNESS_REPEAT = 0.10  # Actual speed also limited by Wi-Fi response time

# ----------------------- WLED state and controls -----------------------

# Cache state for currently selected device to avoid GET+POST for every flick.
# Refresh when changing projects; this does not track changes from other apps.
control_cache = {"host": None, "brightness": None, "effect": None,
                 "segment_id": None, "effects": None, "effect_count": None,
                 "palette": None, "palettes": None,
                 "preset_ids": None, "preset_names": None,
                 "preset_types": None, "preset": None}

def reset_control_cache():
    control_cache["host"] = None
    control_cache["brightness"] = None
    control_cache["effect"] = None
    control_cache["segment_id"] = None
    control_cache["effects"] = None
    control_cache["effect_count"] = None
    control_cache["palette"] = None
    control_cache["palettes"] = None
    control_cache["preset_ids"] = None
    control_cache["preset_names"] = None
    control_cache["preset_types"] = None
    control_cache["preset"] = None

def ensure_control_state(ip):
    if control_cache["host"] == ip and control_cache["brightness"] is not None:
        return
    state = get_state(ip)
    segments = [s for s in state.get("seg", []) if s.get("stop", 1) > 0]
    main_id = state.get("mainseg", 0)
    active = segments[0] if segments else None
    for seg in segments:
        if seg.get("id") == main_id:
            active = seg
            break
    control_cache["host"] = ip
    control_cache["brightness"] = int(state.get("bri", 128))
    control_cache["segment_id"] = active.get("id", 0) if active else None
    control_cache["effect"] = int(active.get("fx", 0)) if active else None
    control_cache["palette"] = int(active.get("pal", 0)) if active else None
    control_cache["effects"] = None
    control_cache["effect_count"] = None
    control_cache["palettes"] = None
    control_cache["preset"] = state.get("ps", -1)

def get_effect_names(ip):
    if control_cache["effects"] is not None:
        return control_cache["effects"]
    try:
        with requests.get(f"http://{ip}/json/eff", timeout=HTTP_TIMEOUT) as response:
            if response.status_code != 200:
                raise RuntimeError(f"Effect names HTTP {response.status_code}")
            names = response.json()
        if not isinstance(names, list):
            raise ValueError("Effects response was not a list")
        control_cache["effects"] = names
        control_cache["effect_count"] = len(names)
        return names
    finally:
        adafruit_connection_manager.connection_manager_close_all(pool)

def get_palette_names(ip):
    """Get the named palettes from this WLED instance, once per selection."""
    if control_cache["palettes"] is not None:
        return control_cache["palettes"]
    try:
        with requests.get(f"http://{ip}/json/pal", timeout=HTTP_TIMEOUT) as response:
            if response.status_code != 200:
                raise RuntimeError(f"Palette names HTTP {response.status_code}")
            names = response.json()
        if not isinstance(names, list):
            raise ValueError("Palettes response was not a list")
        control_cache["palettes"] = names
        return names
    finally:
        adafruit_connection_manager.connection_manager_close_all(pool)


def refresh_display_details():
    """Read the selected WLED project's effect and palette names.

    This runs on selection/reconnect, not every time a button is pressed.
    An offline device leaves useful placeholders instead of crashing.
    """
    if not devices:
        set_detail_labels()
        return
    name, ip, _ = devices[selected]
    set_detail_labels("Loading...", "Loading...")
    try:
        ensure_control_state(ip)
        effect_number = control_cache["effect"]
        palette_number = control_cache["palette"]
        effect_name = "--"
        palette_name = "--"
        if effect_number is not None:
            effect_names = get_effect_names(ip)
            if 0 <= effect_number < len(effect_names):
                effect_name = str(effect_names[effect_number]).split("@", 1)[0]
            else:
                effect_name = f"#{effect_number}"
        if palette_number is not None:
            palette_names = get_palette_names(ip)
            if 0 <= palette_number < len(palette_names):
                palette_name = str(palette_names[palette_number]).split("@", 1)[0]
            else:
                palette_name = f"#{palette_number}"
        set_detail_labels(effect_name, palette_name)
    except Exception as error:
        print("Display details error:", name, repr(error))
        set_detail_labels("Unavailable", "Unavailable")
        reset_control_cache()


def change_palette(direction):
    """One palette per horizontal flick; show its name on the TFT."""
    if not devices:
        show("No WLED: press UP")
        return
    if not cancel_identification():
        show("Restore pending; retry later")
        return
    name, ip, _ = devices[selected]
    try:
        ensure_control_state(ip)
        segment_id = control_cache["segment_id"]
        if segment_id is None:
            show("No active segment")
            return
        names = get_palette_names(ip)
        if not names:
            show("No palettes listed")
            return
        current = control_cache["palette"]
        new_palette = (current + direction) % len(names)
        set_state(ip, {"on": True,
                       "seg": [{"id": segment_id, "pal": new_palette}]})
        control_cache["palette"] = new_palette
        palette_name = str(names[new_palette]).split("@", 1)[0]
        palette_text.text = "Palette: " + palette_name[:30]
        show("Palette changed")
        print("Palette", name, current, "->", new_palette, palette_name)
    except Exception as error:
        print("Palette error:", name, repr(error))
        show(name[:12] + " Pal error")
        reset_control_cache()



def get_saved_presets(ip):
    """Get this project's actual saved preset IDs and their display names.

    WLED /presets.json keys are strings such as "1", "3", "12".
    Key 0 is metadata, not a recallable preset.
    Playlist entries are listed alongside regular presets.
    """
    if control_cache["preset_ids"] is not None:
        return control_cache["preset_ids"]
    try:
        with requests.get(f"http://{ip}/presets.json", timeout=5) as response:
            if response.status_code != 200:
                raise RuntimeError(f"Presets HTTP {response.status_code}")
            saved = response.json()
        if not isinstance(saved, dict):
            raise ValueError("Preset response is not an object")
        ids = []
        names = {}
        types = {}
        for key, entry in saved.items():
            try:
                preset_id = int(key)
            except (ValueError, TypeError):
                continue
            if preset_id <= 0 or not isinstance(entry, dict):
                continue
            ids.append(preset_id)
            is_playlist = "playlist" in entry
            types[preset_id] = "Playlist" if is_playlist else "Preset"
            names[preset_id] = str(entry.get("n") or f"{types[preset_id]} {preset_id}")
        ids.sort()
        control_cache["preset_ids"] = ids
        control_cache["preset_names"] = names
        control_cache["preset_types"] = types
        return ids
    finally:
        adafruit_connection_manager.connection_manager_close_all(pool)


# Saving presets involves validation, state capture, naming, and verification.
# Keep this sequence together to preserve tested error recovery behavior.
def save_current_as_preset():  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Save the current lighting state in the first UNUSED preset slot.

    Does not overwrite existing presets/playlists and does not change
    the WLED boot preset configuration.
    """
    if not devices:
        show("No WLED: press UP")
        return
    if not cancel_identification():
        show("Restore pending; retry later")
        return
    name, ip, _ = devices[selected]
    try:
        # Bypass potentially stale saved-preset caches before picking an ID.
        control_cache["preset_ids"] = None
        control_cache["preset_names"] = None
        control_cache["preset_types"] = None
        existing = get_saved_presets(ip)
        existing_set = set(existing)
        free_id = None
        for candidate in range(1, 251):
            if candidate not in existing_set:
                free_id = candidate
                break
        if free_id is None:
            show("No free preset slots")
            return

        # Read the ACTUAL WLED state at save time, in case the phone or a
        # playlist changed the look since our last controller interaction.
        state = get_state(ip)
        segments = [seg for seg in state.get("seg", [])
                    if isinstance(seg, dict) and seg.get("stop", 1) > 0]
        main_id = state.get("mainseg", 0)
        active = segments[0] if segments else None
        for seg in segments:
            if seg.get("id") == main_id:
                active = seg
                break

        effect_name = "Effect"
        palette_name = "Palette"
        if active is not None:
            fx_id = int(active.get("fx", 0))
            pal_id = int(active.get("pal", 0))
            effect_names = get_effect_names(ip)
            palette_names = get_palette_names(ip)
            if 0 <= fx_id < len(effect_names):
                effect_name = str(effect_names[fx_id]).split("@", 1)[0].strip()
            else:
                effect_name = f"Effect {fx_id}"
            if 0 <= pal_id < len(palette_names):
                palette_name = str(palette_names[pal_id]).split("@", 1)[0].strip()
            else:
                palette_name = f"Palette {pal_id}"

        new_name = f"{effect_name} {palette_name}".strip()
        # WLED supports psave, n, ib and sb on /json/state.
        # ib includes brightness and sb includes segment boundaries.
        set_state(ip, {"psave": free_id, "n": new_name,
                       "ib": True, "sb": True})

        # WLED may write presets.json asynchronously; give it a moment.
        time.sleep(0.3)
        control_cache["preset_ids"] = None
        control_cache["preset_names"] = None
        control_cache["preset_types"] = None
        saved_ids = get_saved_presets(ip)
        if free_id in saved_ids:
            show(f"Saved #{free_id}: {new_name}"[:35])
            print("Saved", name, new_name)
        else:
            show("Save sent; verify in WLED")
            print("Preset save not yet verified:", name, free_id)
    except Exception as error:
        print("Save preset error:", name, repr(error))
        show("Save preset failed")


def recall_boot_preset():
    """PLAY the preset WLED is already configured to use on power-up.

    Read boot preset from /json/cfg (read-only). Never change boot settings.
    """
    if not devices:
        show("No WLED: press UP")
        return
    if not cancel_identification():
        show("Restore pending; retry later")
        return
    name, ip, _ = devices[selected]
    try:
        try:
            with requests.get(f"http://{ip}/json/cfg",
                              timeout=HTTP_TIMEOUT) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"Config HTTP {response.status_code}")
                config = response.json()
        finally:
            adafruit_connection_manager.connection_manager_close_all(pool)
        boot_id = int(config.get("def", {}).get("ps", 0) or 0)
        if boot_id <= 0:
            show("No boot preset assigned")
            return
        ids = get_saved_presets(ip)
        if boot_id not in ids:
            show(f"Boot preset #{boot_id} missing")
            return
        preset_name = control_cache["preset_names"].get(boot_id, f"Preset {boot_id}")
        preset_type = control_cache["preset_types"].get(boot_id, "Preset")
        # Recall it NOW, but never change the boot preset assignment.
        set_state(ip, {"ps": boot_id})
        reset_control_cache()
        refresh_display_details()
        show(f"Boot {preset_type} {boot_id}: {preset_name}"[:35])
        print("Recalled configured boot preset:", name, boot_id, preset_name)
    except Exception as error:
        # Leave network ready even if /json/cfg failed.
        adafruit_connection_manager.connection_manager_close_all(pool)
        print("Boot preset error:", name, repr(error))
        show("Boot preset error")


def change_preset(direction):  # pylint: disable=too-many-branches
    """One saved preset per right-stick horizontal flick."""
    if not devices:
        show("No WLED: press UP")
        return
    if not cancel_identification():
        show("Restore pending; retry later")
        return
    name, ip, _ = devices[selected]
    try:
        ensure_control_state(ip)
        ids = get_saved_presets(ip)
        if not ids:
            show("No saved presets")
            return
        current = control_cache["preset"]
        if current in ids:
            new_index = (ids.index(current) + direction) % len(ids)
        elif direction > 0:
            # If effect/palette was changed manually, choose the next higher ID.
            new_index = 0
            if isinstance(current, int) and current > 0:
                for i, preset_id in enumerate(ids):
                    if preset_id > current:
                        new_index = i
                        break
        else:
            new_index = len(ids) - 1
            if isinstance(current, int) and current > 0:
                for i in range(len(ids) - 1, -1, -1):
                    if ids[i] < current:
                        new_index = i
                        break
        preset_id = ids[new_index]
        # Allow WLED to broadcast this user-requested change if send is enabled.
        set_state(ip, {"ps": preset_id})
        preset_name = control_cache["preset_names"].get(preset_id, f"Preset {preset_id}")
        preset_type = control_cache["preset_types"].get(preset_id, "Preset")
        # Presets may update FX, palette, brightness and segments all at once.
        # Keep saved presets list; refresh current WLED state and display.
        control_cache["host"] = None
        refresh_display_details()
        show(f"{preset_type} {preset_id}: {preset_name}"[:35])
        print(preset_type + ":", name, preset_id, preset_name)
    except Exception as error:
        print("Preset error:", name, repr(error))
        show(name[:12] + " Preset error")
        # Avoid repeating a failed request for an outdated device.
        reset_control_cache()


def axis_direction(value):
    if value <= STICK_LOW:
        return -1
    if value >= STICK_HIGH:
        return 1
    return 0

def change_effect(direction):
    """Increment the main segment effect; display the name returned by WLED."""
    if not devices:
        show("No WLED: press UP")
        return
    if not cancel_identification():
        show("Restore pending; retry later")
        return
    name, ip, _ = devices[selected]
    try:
        ensure_control_state(ip)
        segment_id = control_cache["segment_id"]
        if segment_id is None:
            show("No active segment")
            return
        names = get_effect_names(ip)
        if not names:
            show("No effects listed")
            return
        current = control_cache["effect"]
        new_effect = (current + direction) % len(names)
        set_state(ip, {"on": True,
                       "seg": [{"id": segment_id, "fx": new_effect}]})
        control_cache["effect"] = new_effect
        effect_name = str(names[new_effect]).split("@", 1)[0]
        fx_text.text = "FX: " + effect_name[:34]
        show("Effect changed")
        print("Effect", name, current, "->", new_effect, effect_name)
    except Exception as error:
        print("Effect error:", name, repr(error))
        show(name[:12] + " FX error")
        reset_control_cache()

def change_brightness(direction):
    """Adjust brightness quickly, without a GET for every step."""
    if not devices:
        show("No WLED: press UP")
        return
    if not cancel_identification():
        show("Restore pending; retry later")
        return
    name, ip, _ = devices[selected]
    try:
        ensure_control_state(ip)
        current = control_cache["brightness"]
        updated = max(1, min(255, current + direction * BRIGHTNESS_STEP))
        if updated != current:
            set_state(ip, {"on": True, "bri": updated, "tt": 0})
            control_cache["brightness"] = updated
        show(f"Bright: {round(updated * 100 / 255)}%")
    except Exception as error:
        print("Brightness error:", name, repr(error))
        show(name[:12] + " Bright err")
        reset_control_cache()

def state_url(ip):
    return f"http://{ip}/json/state"

def get_state(ip):
    try:
        with requests.get(state_url(ip), timeout=HTTP_TIMEOUT) as response:
            if response.status_code != 200:
                raise RuntimeError(f"GET HTTP {response.status_code}")
            return response.json()
    finally:
        adafruit_connection_manager.connection_manager_close_all(pool)

def set_state(ip, changes):
    try:
        with requests.post(state_url(ip), json=changes, timeout=HTTP_TIMEOUT) as response:
            if response.status_code != 200:
                raise RuntimeError(f"POST HTTP {response.status_code}")
            _ = response.text  # Consume WLED response before socket cleanup.
    finally:
        adafruit_connection_manager.connection_manager_close_all(pool)

def toggle():
    if not devices:
        show("No WLED: press UP")
        return
    if not cancel_identification():
        show("Restore pending; retry later")
        return
    name, ip, _ = devices[selected]
    try:
        old = get_state(ip)
        new_on = not bool(old["on"])
        # Allow broadcasts when this WLED project has sync sending enabled.
        set_state(ip, {"on": new_on})
        reset_control_cache()
        show(name[:13] + (" ON" if new_on else " OFF"))
    except Exception as error:
        print("Power toggle error:", name, repr(error))
        show(name[:13] + " Power error")


# RT sends a 10-bit analog value in report bytes 10-11 (0..1023).
# A high threshold plus a lower release threshold avoids accidental double toggles.
RT_PRESS_THRESHOLD = 800
RT_RELEASE_THRESHOLD = 250

def toggle_sync_send():
    """Toggle WLED's UDP sync SEND only for the selected project."""
    if not devices:
        show("No WLED: press UP")
        return
    if not cancel_identification():
        show("Restore pending; retry later")
        return
    name, ip, _ = devices[selected]
    try:
        state = get_state(ip)
        old_send = bool(state.get("udpn", {}).get("send", False))
        new_send = not old_send
        # Suppress a broadcast JUST for this configuration change.
        # Do not change udpn.recv or the configured sync groups.
        set_state(ip, {"udpn": {"send": new_send, "nn": True}})
        # Confirm the WLED device applied the change before showing success.
        current_send = bool(get_state(ip).get("udpn", {}).get("send", False))
        if current_send != new_send:
            raise RuntimeError("WLED did not apply sync-send change")
        show("SYNC SEND: " + ("ON" if current_send else "OFF"))
        print("Sync send", name, "->", current_send)
    except Exception as error:
        print("Sync-send error:", name, repr(error))
        show(name[:13] + " Sync error")


# ----------------------- Device identification -----------------------

# Project selection is immediate. The identification blinks are stepped through
# from the main loop instead of blocking BLE input with time.sleep() calls.
# A short settle delay lets the user flick through several devices rapidly;
# only the final device blinks after they stop moving the D-pad.
SELECTION_SETTLE = 0.35
BLINK_HOLD = 0.14
ident = {"phase": "idle", "deadline": 0, "ip": None,
         "name": None, "original": None, "restore_segments": None,
         "yellow": None, "playlist_id": -1, "retry_count": 0}
RESTORE_RETRY_SECONDS = 1.0
RESTORE_MAX_RETRIES = 5


def restore_identification():
    """Restore a flashed fixture; retain the snapshot if any request fails.

    Restoring the segment effects alone cannot resume a running WLED
    playlist. Applying its saved playlist preset restarts that playlist.
    """
    if ident["original"] is None:
        ident["phase"] = "idle"
        return True
    original = ident["original"]
    try:
        restore = {"on": original.get("on", False),
                   "bri": original.get("bri", 128),
                   "tt": 0, "udpn": {"nn": True},
                   "seg": ident["restore_segments"]}
        set_state(ident["ip"], restore)
        playlist_id = ident["playlist_id"]
        if playlist_id > 0:
            # WLED's 'pl' is read-only. Recalling its stored preset ID
            # restarts the playlist from the beginning, not mid-track.
            set_state(ident["ip"], {"ps": playlist_id,
                                    "udpn": {"nn": True}})
    except Exception as restore_error:
        ident["retry_count"] += 1
        print("Restore failed:", ident["name"], repr(restore_error))
        ident["phase"] = "restoring"
        ident["deadline"] = time.monotonic() + RESTORE_RETRY_SECONDS
        if ident["retry_count"] == RESTORE_MAX_RETRIES:
            show("Restore stuck; check WLED")
        else:
            show("Restore retry: " + str(ident["name"])[:14])
        return False
    # Only discard the original when WLED accepted restoration.
    ident["original"] = None
    ident["restore_segments"] = None
    ident["yellow"] = None
    ident["playlist_id"] = -1
    ident["retry_count"] = 0
    ident["phase"] = "idle"
    reset_control_cache()
    return True


def cancel_identification():
    """Stop any pending flash, restoring it before other WLED commands."""
    if ident["original"] is not None:
        if not restore_identification():
            return False
    ident["phase"] = "idle"
    return True


def queue_identification():
    """Show selection now, and flash only after D-pad activity settles."""
    if not cancel_identification():
        return False
    ident["phase"] = "waiting" if devices else "idle"
    ident["deadline"] = time.monotonic() + SELECTION_SETTLE
    ident["ip"] = None
    ident["original"] = None
    ident["restore_segments"] = None
    ident["yellow"] = None
    return True


def begin_identification():
    if not devices:
        ident["phase"] = "idle"
        return
    name, ip, _ = devices[selected]
    ident["name"] = name
    ident["ip"] = ip
    try:
        original = get_state(ip)
        segments = original.get("seg", [])
        if not segments:
            ident["phase"] = "idle"
            return
        settings = (
            "on", "bri", "fx", "sx", "ix", "pal", "col", "cct",
            "c1", "c2", "c3", "sel", "rev", "mi", "frz",
            "o1", "o2", "o3", "si", "m12", "bm",
        )
        restore_segments = []
        yellow_segments = []
        for seg in segments:
            if "id" not in seg:
                continue
            saved = {"id": seg["id"]}
            for key in settings:
                if key in seg:
                    saved[key] = seg[key]
            restore_segments.append(saved)
            yellow_segments.append({
                "id": seg["id"], "on": True, "frz": False,
                "fx": 0, "bri": 255, "col": [[255, 185, 35]],
            })
        if not restore_segments:
            ident["phase"] = "idle"
            return
        ident["original"] = original
        ident["playlist_id"] = int(original.get("pl", -1) or -1)
        ident["retry_count"] = 0
        ident["restore_segments"] = restore_segments
        ident["yellow"] = {"on": True, "bri": 180, "tt": 0,
                           "udpn": {"nn": True}, "seg": yellow_segments}
        set_state(ip, ident["yellow"])
        ident["phase"] = "yellow1"
        ident["deadline"] = time.monotonic() + BLINK_HOLD
    except Exception as identify_error:
        print("Identify error:", name, repr(identify_error))
        show(name[:18] + " offline/error")
        if ident["original"] is not None:
            restore_identification()
        else:
            ident["phase"] = "idle"


def identification_tick():
    """Advance the nonblocking blink or retry a failed restoration."""
    phase = ident["phase"]
    if phase == "idle" or time.monotonic() < ident["deadline"]:
        return
    if phase == "waiting":
        begin_identification()
        return
    if phase == "restoring":
        restore_identification()
        return
    try:
        if phase == "yellow1":
            set_state(ident["ip"], {"on": False, "tt": 0,
                                    "udpn": {"nn": True}})
            ident["phase"] = "dark1"
        elif phase == "dark1":
            set_state(ident["ip"], ident["yellow"])
            ident["phase"] = "yellow2"
        elif phase == "yellow2":
            set_state(ident["ip"], {"on": False, "tt": 0,
                                    "udpn": {"nn": True}})
            ident["phase"] = "dark2"
        elif phase == "dark2":
            if restore_identification():
                refresh_display_details()
            return
        ident["deadline"] = time.monotonic() + BLINK_HOLD
    except Exception as blink_error:
        print("Blink step error:", repr(blink_error))
        restore_identification()


def change_selection(delta):
    global selected  # pylint: disable=global-statement
    if not devices:
        show("No WLED: press UP")
        return
    if not cancel_identification():
        show("Restore pending; retry later")
        return
    selected = (selected + delta) % len(devices)
    reset_control_cache()
    display_selection()
    set_detail_labels("--", "--")
    queue_identification()

# -------------------- Find a gamepad without hardcoding MAC --------------------

def ble_ad_fields(raw):
    """Yield (type, value) pairs from Bluetooth advertising bytes."""
    i = 0
    while i < len(raw):
        size = raw[i]
        if size == 0 or i + size >= len(raw):
            break
        yield raw[i + 1], raw[i + 2:i + size + 1]
        i += size + 1


def advertised_hid(raw):
    """Check for the standard BLE Human Interface Device service (0x1812)."""
    for field_type, field in ble_ad_fields(raw):
        if field_type in (0x02, 0x03):  # 16-bit service UUID lists
            for i in range(0, len(field) - 1, 2):
                if field[i] == 0x12 and field[i + 1] == 0x18:
                    return True
    return False


def xbox_name(raw):
    """Some controllers advertise a name; others advertise only HID UUID."""
    for field_type, field in ble_ad_fields(raw):
        if field_type in (0x08, 0x09):
            try:
                name = field.decode("utf-8")
                if "xbox" in name.lower():
                    return True
            except UnicodeError:
                pass
    return False


def find_xbox_address():
    """Prefer a named Xbox; otherwise select the sole BLE HID candidate.

    A BLE keyboard or mouse can advertise the same HID service. When several
    ambiguous candidates appear, ask the reader for an explicit address.
    """
    candidates = {}  # key: formatted BLE address, value: (Address, named Xbox)
    try:
        for adv in _bleio.adapter.start_scan(timeout=XBOX_SCAN_SECONDS):
            addr = str(adv.address)
            if XBOX_ADDRESS is not None:
                if XBOX_ADDRESS.lower() == addr.lower():
                    return adv.address
                continue
            raw = adv.advertisement_bytes
            old = candidates.get(addr)
            is_xbox = xbox_name(raw) or (old[1] if old else False)
            if is_xbox or advertised_hid(raw) or old is not None:
                # Some packets are scan responses, so keep a previously seen
                # connectable entry's Address when present.
                if adv.connectable or old is None:
                    candidates[addr] = (adv.address, is_xbox)
                else:
                    candidates[addr] = (old[0], is_xbox)
    finally:
        _bleio.adapter.stop_scan()

    named = [value[0] for value in candidates.values() if value[1]]
    if len(named) == 1:
        return named[0]
    if len(named) > 1:
        show("Multiple Xbox devices")
        print("Multiple named Xbox controllers found; set XBOX_ADDRESS.")
    elif len(candidates) == 1:
        return next(iter(candidates.values()))[0]
    elif len(candidates) > 1:
        show("Multiple BLE gamepads")
        print("Multiple BLE HID devices found. Specify XBOX_ADDRESS:")
        for addr in candidates:
            print(" ", addr)
    return None


# ----------------------- Main controller loop -----------------------

# Discover first; then establish the BLE connection.
discover()
_bleio.adapter.enabled = True

while True:
    controller = None
    packet_buffer = None
    try:
        show("Turn on Xbox / scanning")
        address = find_xbox_address()
        if address is None:
            show("Xbox not found; retry")
        else:
            show("Connecting Xbox...")
            controller = _bleio.adapter.connect(address, timeout=XBOX_CONNECT_TIMEOUT)
            if not controller.paired:
                show("Pairing Xbox...")
                controller.pair()
            if not (controller.connected and controller.paired):
                raise RuntimeError("Xbox pairing incomplete")
            services = controller.discover_remote_services([HID_SERVICE_UUID])
            input_report = None
            for service in services:
                for char in service.characteristics:
                    if (char.uuid == HID_REPORT_UUID and
                            char.properties & _bleio.Characteristic.NOTIFY):
                        input_report = char
                        break
                if input_report is not None:
                    break
            if input_report is None:
                raise RuntimeError("No HID input characteristic")
            packet_buffer = _bleio.PacketBuffer(
                input_report, buffer_size=10, max_packet_size=64
            )
            input_report.set_cccd(notify=True)
            report = bytearray(64)
            previous_a = False
            previous_b = False
            previous_x = False
            previous_y = False
            rt_armed = True
            previous_dpad = 0
            previous_effect_dir = 0
            previous_palette_dir = 0
            previous_brightness_dir = 0
            previous_preset_dir = 0
            next_brightness_at = 0
            display_selection()
            refresh_display_details()
            while controller.connected:
                identification_tick()
                count = packet_buffer.readinto(report)
                if count >= 14:
                    a = bool(report[BUTTONS_BYTE] & A_BUTTON_MASK)
                    b = bool(report[BUTTONS_BYTE] & B_BUTTON_MASK)
                    x = bool(report[BUTTONS_BYTE] & X_BUTTON_MASK)
                    y = bool(report[BUTTONS_BYTE] & Y_BUTTON_MASK)
                    dpad = report[DPAD_BYTE]
                    if a and not previous_a:
                        toggle()
                    if (b and not previous_b) or (x and not previous_x):
                        # Avoid saving the yellow identification flash or
                        # having it override a freshly recalled preset.
                        if b and not previous_b:
                            recall_boot_preset()
                        if x and not previous_x:
                            save_current_as_preset()
                    if y and not previous_y:
                        # Customize Y here. This fires once per press.
                        # Example: call a WLED action you define above.
                        pass
                    # RT: one toggle per squeeze; release to re-arm.
                    if count >= 12:
                        rt_value = axis_value(report, RIGHT_TRIGGER_BYTE)
                        if rt_value <= RT_RELEASE_THRESHOLD:
                            rt_armed = True
                        elif rt_value >= RT_PRESS_THRESHOLD and rt_armed:
                            rt_armed = False
                            # Never send the identification yellow blink to
                            # the rest of the WLED sync group.
                            toggle_sync_send()
                    if dpad != previous_dpad:
                        if dpad == DPAD_RIGHT:
                            change_selection(1)
                        elif dpad == DPAD_LEFT:
                            change_selection(-1)
                        elif dpad == DPAD_UP:
                            if cancel_identification():
                                discover()  # UP refreshes available projects
                                refresh_display_details()
                    # Any new controller action cancels a pending identification
                    # to avoid applying adjustments during the blink.
                    # Left stick UP/DOWN: palettes, LEFT/RIGHT: effects.
                    # Vertical UP=0 and DOWN=65535 on this Xbox controller.
                    palette_dir = axis_direction(axis_value(report, LEFT_Y_BYTE))
                    effect_dir = axis_direction(axis_value(report, LEFT_X_BYTE))
                    # Ignore diagonal movements to avoid double actions.
                    if palette_dir != previous_palette_dir and palette_dir != 0 and effect_dir == 0:
                        change_palette(-palette_dir)
                    if effect_dir != previous_effect_dir and effect_dir != 0 and palette_dir == 0:
                        change_effect(effect_dir)
                    previous_effect_dir = effect_dir
                    previous_palette_dir = palette_dir

                    # Right stick up/down: repeat brightness while held.
                    # Axis 3 (bytes 6-7): UP=0, DOWN=65535.
                    brightness_dir = axis_direction(axis_value(report, RIGHT_Y_BYTE))
                    preset_dir = axis_direction(axis_value(report, RIGHT_X_BYTE))
                    # Ignore diagonal right-stick movement: a preset flick
                    # should not also adjust brightness.
                    if (preset_dir != previous_preset_dir and
                            preset_dir != 0 and brightness_dir == 0):
                        change_preset(preset_dir)
                    previous_preset_dir = preset_dir
                    now = time.monotonic()
                    if brightness_dir == 0:
                        next_brightness_at = 0
                    elif preset_dir == 0 and (brightness_dir != previous_brightness_dir or
                          now >= next_brightness_at):
                        change_brightness(-brightness_dir)
                        next_brightness_at = time.monotonic() + BRIGHTNESS_REPEAT
                    previous_brightness_dir = brightness_dir

                    previous_a = a
                    previous_b = b
                    previous_x = x
                    previous_y = y
                    previous_dpad = dpad
                time.sleep(0.01)
            show("Xbox disconnected")
    except Exception as bluetooth_error:
        print("Bluetooth error:", repr(bluetooth_error))
        show("Xbox reconnecting...")
    finally:
        if ident["original"] is not None:
            restore_identification()
        if packet_buffer is not None:
            try:
                packet_buffer.deinit()
            except Exception:
                pass
        if controller is not None and controller.connected:
            try:
                controller.disconnect()
            except Exception:
                pass
        _bleio.adapter.stop_scan()
    time.sleep(RECONNECT_DELAY)
