#!/usr/bin/env python3
from enum import Enum
import time
import tkinter

import adafruit_ble
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.device_info import DeviceInfoService
from adafruit_ble_cycling_speed_and_cadence import CyclingSpeedAndCadenceService

import Xlib.X as X
import Xlib.XK as XK
import Xlib.display as display
import Xlib.ext.xtest as xtest

# Customize me!  Set the minimum RPM to start the video, target RPM, and the
# grace time (number of seconds) you can be below the minimum RPM before it
# stops.
MINIMUM_RPM = 60
TARGET_RPM = 72
GRACE_TIME = 2

class Keystroke:
    """Use a connection to the X Server (linux display server) to send # fake
    keystrokes to the Chromium browser window."""
    def __init__(self):
        self.display = display.Display()
        self.root = self.display.screen().root
        self._keycodes = {}

    def _keycode(self, sym):
        if isinstance(sym, str):
            sym = XK.string_to_keysym(sym)
        result = self._keycodes.get(sym, None)
        if result is None:
            self._keycodes[sym] = result = self.display.keysym_to_keycode(sym)
        return result

    def send_keysym(self, keysym):
        keycode = self._keycode(keysym)
        print("sending", keycode, keysym)
        xtest.fake_input(self.root, X.KeyPress, keycode)
        self.display.sync()
        time.sleep(.01)
        xtest.fake_input(self.root, X.KeyRelease, keycode)
        self.display.sync()

    @property
    def current_window_class(self):
        window = self.display.get_input_focus().focus
        while window:
            class_ = window.get_wm_class()
            if class_:
                return class_[1]
            window = window.query_tree().parent
        return ''

class OSD:
    """Use Tkinter to display a simple OSD window on top of all regular windows"""
    def __init__(self, width=12, text='', geometry='-0+48', font=('Arial', 36)):
        self.app = tkinter.Tk()
        self.app.wm_geometry(geometry)
        self.app.wm_overrideredirect(1)
        self._label = tkinter.Label(self.app, width=width, text=text, font=font)
        self._label.pack()

    @property
    def label(self):
        return self._label['text']

    @label.setter
    def label(self, text):
        self._label['text'] = text
        self.update()

    def mainloop(self):
        self.app.mainloop()

    def destroy(self):
        self.app.destroy()

    def update(self):
        self.app.update()

    @property
    def background(self):
        return self.label['background']

    @background.setter
    def background(self, color):
        self._label['background'] = color

def send_pause():
    """Send the key 'p', to send a video to the paused state"""
    if keystroke.current_window_class != 'Chromium-browser':
        return
    print('actually send play')
    keystroke.send_keysym('p')

def send_play():
    """Send the keys 'pk', to send a video into the playing state"""
    if keystroke.current_window_class != 'Chromium-browser':
        return
    print('actually send play')
    keystroke.send_keysym('p')
    keystroke.send_keysym('k')

def delta16(v1, v2):
    """Return the delta (difference) between two increasing 16-bit counters,
    accounting for the wraparound from 65535 back to 0"""
    diff = v2 - v1
    if diff < 0:
        diff += (1<<16)
    return diff

# PyLint can't find BLERadio for some reason so special case it here.
ble = adafruit_ble.BLERadio()  # pylint: disable=no-member
keystroke = Keystroke()
osd = OSD()
class VideoState(Enum):
    PAUSED = 0
    PLAYING = 1

while True:
    state = VideoState.PAUSED

    osd.label = "Scanning"
    osd.background = '#ffffff'
    print("Scanning...")
    # Save advertisements, indexed by address
    advs = {}
    for adv in ble.start_scan(ProvideServicesAdvertisement, timeout=5):
        if CyclingSpeedAndCadenceService in adv.services:
            print("found a CyclingSpeedAndCadenceService advertisement")
            # Save advertisement. Overwrite duplicates from same address (device).
            advs[adv.address] = adv

    ble.stop_scan()
    print("Stopped scanning")
    if not advs:
        # Nothing found. Go back and keep looking.
        continue

    osd.label = "Connecting"
    # Connect to all available CSC sensors.
    cyc_connections = []
    for adv in advs.values():
        cyc_connections.append(ble.connect(adv))
        print("Connected", len(cyc_connections))

    # Print out info about each sensors.
    for conn in cyc_connections:
        if conn.connected:
            if DeviceInfoService in conn:
                dis = conn[DeviceInfoService]
                try:
                    manufacturer = dis.manufacturer
                except AttributeError:
                    manufacturer = "(Manufacturer Not specified)"
                print("Device:", manufacturer)
            else:
                print("No device information")

    osd.label = "Polling"
    print("Waiting for data... (could be 10-20 seconds or more)")
    # Get CSC Service from each sensor.
    cyc_services = []
    for conn in cyc_connections:
        cyc_services.append(conn[CyclingSpeedAndCadenceService])
    # Read data from each sensor once a second.
    # Stop if we lose connection to all sensors.

    last_crank_time_ms = 0
    last_crank_revs = 0
    grace_period_end = 0
    est_rpm = 0

    while True:
        still_connected = False
        crank_revs = None
        crank_time_ms = None
        for conn, svc in zip(cyc_connections, cyc_services):
            if conn.connected:
                still_connected = True
                values = svc.measurement_values
                if values is not None:
                    if values.cumulative_crank_revolutions:
                        crank_revs = values.cumulative_crank_revolutions
                        crank_time_ms = values.last_crank_event_time
        if not still_connected:
            break

        if crank_revs is None:
            continue

        if crank_time_ms == last_crank_time_ms:
            est_rpm = 0
        else:
            # If we were stopped prior to this, jump to MINIMUM_RPM
            # it gives a faster restart after paused
            if est_rpm == 0 and state == VideoState.PAUSED:
                est_rpm = MINIMUM_RPM
            else:
                delta_revs = delta16(last_crank_revs, crank_revs)
                delta_t = delta16(last_crank_time_ms, crank_time_ms) / 1000
                est_rpm = 60 * delta_revs / delta_t
        if est_rpm >= MINIMUM_RPM:
            grace_period_end = time.monotonic() + GRACE_TIME
            if state == VideoState.PAUSED:
                send_play()
                state = VideoState.PLAYING
        elif time.monotonic() > grace_period_end:
            if state == VideoState.PLAYING:
                send_pause()
            state = VideoState.PAUSED

        last_crank_revs = crank_revs
        last_crank_time_ms = crank_time_ms
        print(f"Crank: {crank_revs}")
        print(f"Crank RPM: {est_rpm:.1f}")

        if est_rpm < MINIMUM_RPM:
            osd.background = '#ff0000'
        elif est_rpm < TARGET_RPM:
            osd.background = '#ffff00'
        else:
            osd.background = '#00ff00'
        osd.label = f"RPM: {est_rpm:.1f}"
        time.sleep(0.1)
