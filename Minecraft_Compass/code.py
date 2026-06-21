# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Minecraft Compass - a GPS waypoint navigator with a pixel-art needle.

A Minecraft-styled prop compass for kids navigating a campsite. The needle
points at the cardinal you face (or toward a saved waypoint), driven by a
tilt-compensated heading from the LSM6DSOX+LIS3MDL 9-DoF and a PA1010D GPS.

This file is the orchestrator: it creates the hardware, hands it to the
sensor and UI modules, runs the calibration hand-off if needed, and then
runs the main loop. The detail lives in three modules:
  - mc_config: constants and the editable settings (waypoint names, etc.)
  - mc_compass: sensor reads, heading math, and storage
  - mc_ui: the display - dial, needle, menus, and touch handling

Hardware (all Adafruit): Feather RP2350 8MB, 3.5" TFT FeatherWing (HX8357
+ TSC2007 touch), LSM6DSOX+LIS3MDL 9-DoF, PA1010D GPS, optional MAX17048
battery gauge, and a momentary button on D5. CircuitPython 10.x.
"""

import gc
import time

import board
import digitalio
import displayio
import fourwire
import supervisor

import adafruit_gps
import adafruit_lis3mdl
import adafruit_tsc2007
from adafruit_debouncer import Debouncer
from adafruit_lsm6ds.lsm6dsox import LSM6DSOX
from adafruit_max1704x import MAX17048
from adafruit_hx8357 import HX8357

import mc_compass
import mc_settings
import mc_ui
import mc_waypoints
from mc_compass import (
    declination_index, marine_mode, mode, rotation_flipped, theme_index,
    waypoints,
)
from mc_config import (
    BUTTON_PIN, DECLINATION_OPTIONS, HEADING_SMOOTHING, MAX_WAYPOINTS,
    MODE_COMPASS, MODE_WAYPOINT, NEEDLE_DEADBAND_DEG,
)

# --- Display: 3.5" TFT FeatherWing (HX8357) over SPI ---
displayio.release_displays()
spi = board.SPI()
# board.SPI() defaults to a conservative baud rate, which made each
# display.refresh() take ~150 ms. Raising it to 24 MHz roughly halved that
# to ~76 ms. The RP2350 SPI clock is an integer divisor of the system clock,
# so it rounds the request DOWN to the nearest achievable rate: 24 MHz lands
# on a good divisor, while 32 MHz rounds to a SLOWER real rate here, so
# 24 MHz is the sweet spot. (Measured.)
display_bus = fourwire.FourWire(
    spi, command=board.D10, chip_select=board.D9, baudrate=24_000_000
)
display = HX8357(display_bus, width=480, height=320)
# Manual refresh: the needle is redrawn by clearing its bitmap then drawing
# the rotated image. With auto-refresh on, the display could refresh in the
# gap between clear and draw, showing a blank "blink". Refreshing manually
# once per loop (after all drawing) makes each frame appear all at once.
display.auto_refresh = False
root = displayio.Group()
display.root_group = root

# --- Sensors on the STEMMA QT I2C chain ---
i2c = board.STEMMA_I2C()
mag = adafruit_lis3mdl.LIS3MDL(i2c)
imu = LSM6DSOX(i2c)

# PA1010D GPS on the same chain (I2C 0x10).
gps = adafruit_gps.GPS_GtopI2C(i2c, debug=False)
# Stream just the sentences we need: GGA (fix + sats) and RMC (position).
gps.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
# Update position once per second (plenty for walking navigation).
gps.send_command(b"PMTK220,1000")


def detect_battery_gauge():
    """Return a MAX17048 if one answers at 0x36, else None.

    The Feather RP2350 has no onboard gauge, so this is an optional external
    breakout that may not be mounted yet. If absent, the battery indicator
    is hidden and everything else runs normally.
    """
    while not i2c.try_lock():
        pass
    try:
        present = 0x36 in i2c.scan()
    finally:
        i2c.unlock()
    return MAX17048(i2c) if present else None


battery = detect_battery_gauge()

# TSC2007 resistive touch (I2C 0x48). invert_x + swap_xy map raw touch to
# the 480x320 landscape orientation (per Adafruit's reference for this wing).
touch = adafruit_tsc2007.TSC2007(i2c, invert_x=True, swap_xy=True)

# Momentary button on D5, active-low with an internal pull-up.
button_io = digitalio.DigitalInOut(BUTTON_PIN)
button_io.direction = digitalio.Direction.INPUT
button_io.pull = digitalio.Pull.UP
button = Debouncer(button_io)

# --- Wire the modules together ---
# mc_compass takes the sensors and loads saved settings + waypoints; mc_ui
# takes the display objects and builds the scene.
mc_compass.setup(imu, mag, gps, battery, button)
mc_ui.setup(display, root, touch)
# Assemble the finished scene: add the background and every UI group to the
# root in draw order, hide the battery gauge if no fuel gauge is present, then
# apply the saved theme and rotation. The overlay groups live in their own
# modules; everything is appended here so the draw order is explicit.
root.append(mc_ui.bg_rect)
root.append(mc_ui.static_group)
root.append(mc_ui.needle_group)
root.append(mc_ui.header_shadow)
root.append(mc_ui.header_fg)
root.append(mc_ui.heading_num_shadow)
root.append(mc_ui.heading_num_fg)
root.append(mc_ui.battery_group)
root.append(mc_ui.inventory_group)
root.append(mc_ui.gear_group)
root.append(mc_waypoints.list_group)
root.append(mc_waypoints.picker_group)
root.append(mc_settings.settings_group)
root.append(mc_settings.info_group)
mc_ui.battery_group.hidden = not mc_compass.hw["battery_present"]
mc_ui.apply_theme()
mc_ui.apply_rotation()

# --- Phase routing ---
# If there is no calibration yet, hand off to the calibration program rather
# than dead-ending. supervisor runs calibration.py on the reload; when it
# finishes it hands control back here. This is what makes field
# recalibration work with no computer or file renaming.
cal = mc_compass.load_calibration()
if cal is None:
    print("No calibration found - launching calibration.py")
    supervisor.set_next_code_file("calibration.py")
    supervisor.reload()
    # reload() is not instant; stop here so nothing runs with cal=None.
    while True:
        time.sleep(0.1)

heading_offset = cal[6]
print("Minecraft Compass running.")
print(f"Heading offset: {heading_offset:0.2f} deg")
print("Tap: switch mode.  Hold 1.5s: save waypoint.  Hold 3.5s: theme.")

def handle_save_waypoint():
    """Open the name picker to capture the current fix, or preview it.

    With a fix, the picker assigns a name and the waypoint is saved. Without
    a fix the picker still opens so the names can be browsed (a preview of
    what locations can be called), but tapping one saves nothing and just
    reports there is no fix yet. A full list is the one hard block.
    """
    if len(waypoints) >= MAX_WAYPOINTS:
        mc_ui.header_fg.text = "List full"
        mc_ui.header_shadow.text = "List full"
        mc_ui.ui["display"].refresh(minimum_frames_per_second=0)
        time.sleep(1.0)
        return
    if not mc_compass.hw["gps"].has_fix:
        # Preview mode: open the picker with no coordinates. Selecting a name
        # won't save (handled in handle_picker_touch); it alerts instead.
        mc_waypoints.open_name_picker(None, None, keep_active=mode[0] == MODE_WAYPOINT)
        return
    # Capture the fix now and let the picker assign the name. In Waypoint
    # Mode keep the current target active (breadcrumb save); in Compass Mode
    # make the new point active.
    gps_obj = mc_compass.hw["gps"]
    mc_waypoints.open_name_picker(
        gps_obj.latitude, gps_obj.longitude,
        keep_active=mode[0] == MODE_WAYPOINT,
    )


# --- Loop state ---
last_needle_update = 0.0
last_text_update = 0.0
last_gps_update = 0.0
last_battery_update = 0.0
last_footer_text = [""]     # last footer string, to skip no-op text updates
smoothed_heading = [None]   # low-pass filtered heading (None until first read)
drawn_needle_angle = [None]  # last angle actually drawn, for the deadband
touch_was_down = [False]    # tracks touch state across polls for tap edges
mc_ui.update_battery()      # initial read so the icon is correct on frame 1
mc_ui.apply_mode_header(mode[0])

while True:
    now = time.monotonic()
    # Set True by anything that changes the screen this iteration; the single
    # display.refresh() at the bottom fires only when it's True.
    needs_refresh = False

    # GPS reads are expensive: the adafruit_gps GtopI2C driver reads one byte
    # per I2C transaction, so one NMEA sentence is ~70 locked transactions
    # (~300-500 ms). Position only changes at 1 Hz for walking, so read once
    # per second - the unavoidable stall then happens 4x less often. (A
    # faster fix would need a custom bulk-I2C reader the stock lib lacks.)
    if now - last_gps_update >= 1.0:
        gps.update()
        mc_ui.update_nav_target()
        last_gps_update = now

    event = mc_compass.poll_button()

    # Touch: route to whichever overlay is open (picker, list, settings),
    # else to the mode's button (inventory in Waypoint, gear in Compass).
    # Acts once per tap on the press edge.
    touch_point = mc_ui.read_touch()
    if touch_point is not None and not touch_was_down[0]:
        touch_was_down[0] = True
        if not mc_settings.info_group.hidden:
            mc_settings.handle_info_touch(touch_point)
        elif not mc_waypoints.picker_group.hidden:
            mc_waypoints.handle_picker_touch(touch_point)
        elif not mc_waypoints.list_group.hidden:
            mc_waypoints.handle_list_touch(touch_point)
        elif not mc_settings.settings_group.hidden:
            mc_settings.handle_settings_touch(touch_point)
        elif mode[0] == MODE_WAYPOINT and mc_ui.touched_inventory_button(touch_point):
            mc_waypoints.open_list()
        elif mode[0] == MODE_COMPASS and mc_ui.touched_gear(touch_point):
            mc_settings.open_settings()
        needs_refresh = True   # a tap may have changed an overlay/menu
    elif touch_point is None:
        touch_was_down[0] = False

    # While an overlay is open, the physical button closes it (matching the
    # tap-outside behavior) rather than switching modes or saving behind it.
    # A short press closes the topmost overlay; holds are ignored so a
    # hold-to-save/theme can't fire behind a menu.
    any_overlay = not (mc_waypoints.list_group.hidden and mc_waypoints.picker_group.hidden
                       and mc_settings.settings_group.hidden
                       and mc_settings.info_group.hidden)
    if any_overlay:
        if event == "short":
            if not mc_settings.info_group.hidden:
                mc_settings.info_group.hidden = True     # info closes to settings
            elif not mc_waypoints.picker_group.hidden:
                mc_waypoints.pending_save.clear()          # cancel pending save
                mc_waypoints.picker_group.hidden = True
                mc_ui.apply_mode_header(mode[0])
            elif not mc_settings.settings_group.hidden:
                mc_settings.close_settings()
            elif not mc_waypoints.list_group.hidden:
                mc_waypoints.close_list()
            needs_refresh = True
        event = "none"   # never fall through to mode-switch/save while open

    if event == "short":
        mode[0] = MODE_WAYPOINT if mode[0] == MODE_COMPASS else MODE_COMPASS
        mc_ui.apply_mode_header(mode[0])
        needs_refresh = True
    elif event == "enter_save":
        # Crossed the save threshold while holding; show what release does.
        mc_ui.header_fg.text = "Save?"
        mc_ui.header_shadow.text = "Save?"
        needs_refresh = True
    elif event == "enter_theme":
        # Kept holding into the theme tier; show what release does now.
        mc_ui.header_fg.text = "Theme?"
        mc_ui.header_shadow.text = "Theme?"
        needs_refresh = True
    elif event == "save":
        # Hold-to-save works in both modes. In Compass Mode the new point
        # becomes the active target (you saved it to go to it). In Waypoint
        # Mode it's saved as a breadcrumb without redirecting the navigation
        # you're already following - select it from the list to switch.
        handle_save_waypoint()
        mc_ui.apply_mode_header(mode[0])
        needs_refresh = True
    elif event == "theme":
        mc_ui.toggle_theme()
        theme_name = "Light" if theme_index[0] == 1 else "Dark"
        mc_ui.header_fg.text = theme_name
        mc_ui.header_shadow.text = theme_name
        display.refresh(minimum_frames_per_second=0)
        time.sleep(0.6)
        mc_ui.apply_mode_header(mode[0])
        needs_refresh = True

    # Sensor reads (I2C) and heading math are the loop's most expensive work,
    # so do them only when we actually update the needle (30 Hz) rather than
    # every ~5 ms loop.
    if now - last_needle_update >= 0.033:  # 30 Hz
        mag_cal = mc_compass.read_mag_calibrated(cal)
        accel = mc_compass.read_accel()
        # corrected_heading is magnetic; add declination (E positive) to get
        # true heading so compass and waypoint bearings read true north.
        declination = DECLINATION_OPTIONS[declination_index[0]]
        raw_heading = (
            mc_compass.corrected_heading(mag_cal, accel, heading_offset)
            + declination
        ) % 360
        # Low-pass the heading so magnetometer noise doesn't make the needle
        # twitch. Jitter both looks bad and forces a large dirty region (slow
        # refresh), so smoothing helps the look and the frame rate.
        smoothed_heading[0] = mc_compass.smooth_heading(
            raw_heading, smoothed_heading[0], HEADING_SMOOTHING
        )
        heading_deg = smoothed_heading[0]

        # When the case is built button-at-bottom, the display is flipped 180
        # and the IMU is physically turned 180 with it, so the same facing
        # reads a heading 180 off. Correct it so N still reads N.
        if rotation_flipped[0]:
            heading_deg = (heading_deg + 180) % 360

        if mode[0] == MODE_WAYPOINT:
            needle_angle, footer_text = mc_ui.waypoint_needle_and_footer(
                heading_deg
            )
        else:
            # Marine mode: needle always points to true north. Intuitive mode
            # (default): needle points at the cardinal you face.
            if marine_mode[0]:
                needle_angle = (0.0 - heading_deg) % 360
            else:
                needle_angle = heading_deg
            cardinal = mc_compass.cardinal_from_heading(heading_deg)
            footer_text = f"{heading_deg:3.0f} deg  {cardinal}"

        # Only redraw the needle when it actually moved beyond a small
        # deadband. Holding still then does almost no refreshing (the needle
        # bitmap clear+rotozoom and the SPI push are the costly steps), and
        # tiny sub-degree wobble is ignored.
        if (drawn_needle_angle[0] is None
                or abs(mc_compass.angle_diff(needle_angle, drawn_needle_angle[0]))
                >= NEEDLE_DEADBAND_DEG):
            mc_ui.set_needle_heading(needle_angle)
            drawn_needle_angle[0] = needle_angle
            needs_refresh = True
        last_needle_update = now

        if now - last_text_update >= 0.2:  # 5 Hz text update
            # Only touch the labels when the string actually changed. The
            # footer is far from the needle, so a footer change forces a
            # refresh spanning both (the ~158 ms spikes); skipping no-op
            # updates keeps most frames to the needle-only ~76 ms path.
            if footer_text != last_footer_text[0]:
                mc_ui.heading_num_fg.text = footer_text
                mc_ui.heading_num_shadow.text = footer_text
                last_footer_text[0] = footer_text
                needs_refresh = True
            last_text_update = now

    if now - last_battery_update >= 10.0:  # battery changes slowly
        mc_ui.update_battery()
        last_battery_update = now
        needs_refresh = True

    # Refresh only when something actually changed (at most the 30 Hz needle
    # rate), not every ~5 ms loop. Refreshing every loop was pushing the SPI
    # display ~200x/sec for no reason, throttling the whole loop.
    if needs_refresh:
        display.refresh(minimum_frames_per_second=0)

    # Collect garbage at a controlled point each loop so GC pauses stay small
    # and regular instead of building up and firing mid-render (which showed
    # as the needle going smooth-then-choppy and laggy taps).
    gc.collect()

    time.sleep(0.005)
