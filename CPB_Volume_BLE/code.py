"""
A CircuitPython 'multimedia' dial demo
Uses a Circuit Playground Bluefruit + Rotary Encoder -> BLE out
Knob controls volume, push encoder for mute, CPB button A for Play/Pause
Once paired, bonding will auto re-connect devices
"""

import time
import digitalio
import board
import rotaryio
import neopixel
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

import adafruit_ble
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.hid import HIDService
from adafruit_ble.services.standard.device_info import DeviceInfoService


ble = adafruit_ble.BLERadio()
ble.name = "Bluefruit-Volume-Control"
# Using default HID Descriptor.
hid = HIDService()
device_info = DeviceInfoService(software_revision=adafruit_ble.__version__,
                                manufacturer="Adafruit Industries")
advertisement = ProvideServicesAdvertisement(hid)
cc = ConsumerControl(hid.devices)

FILL_COLOR = (0, 32, 32)
UNMUTED_COLOR = (0, 128, 128)
MUTED_COLOR = (128, 0, 0)
DISCONNECTED_COLOR = (40, 40, 0)

# NeoPixel LED ring
# Ring code will auto-adjust if not 16 so change to any value!
ring = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=0.05, auto_write = False)
ring.fill(DISCONNECTED_COLOR)
ring.show()
dot_location = 0  # what dot is currently lit

# CPB button for Play/Pause
button_A = digitalio.DigitalInOut(board.BUTTON_A)
button_A.switch_to_input(pull=digitalio.Pull.DOWN)

button_a_pressed = False  # for debounce state

# Encoder button is a digital input with pullup on A1
# so button.value == False means pressed.
button = digitalio.DigitalInOut(board.A1)
button.pull = digitalio.Pull.UP

encoder = rotaryio.IncrementalEncoder(board.A2, board.A3)

last_pos = encoder.position
muted = False
command = None
# Disconnect if already connected, so that we pair properly.
if ble.connected:
    for connection in ble.connections:
        connection.disconnect()


def draw():
    if not muted:
        ring.fill(FILL_COLOR)
        ring[dot_location] = UNMUTED_COLOR
    else:
        ring.fill(MUTED_COLOR)
    ring.show()


advertising = False
connection_made = False
print("let's go!")
while True:
    if not ble.connected:
        ring.fill(DISCONNECTED_COLOR)
        ring.show()
        connection_made = False
        if not advertising:
            ble.start_advertising(advertisement)
            advertising = True
        continue
    else:
        if connection_made:
            pass
        else:
            ring.fill(FILL_COLOR)
            ring.show()
            connection_made = True

    advertising = False

    pos = encoder.position
    delta = pos - last_pos
    last_pos = pos
    direction = 0

    if delta > 0:
        command = ConsumerControlCode.VOLUME_INCREMENT
        direction = -1
    elif delta < 0:
        command = ConsumerControlCode.VOLUME_DECREMENT
        direction = 1

    if direction:
        muted = False
        for _ in range(abs(delta)):
            cc.send(command)
            # spin neopixel LED around in the correct direction!
            dot_location = (dot_location + direction) % len(ring)
            draw()

    if not button.value:
        if not muted:
            print("Muting")
            cc.send(ConsumerControlCode.MUTE)
            muted = True
        else:
            print("Unmuting")
            cc.send(ConsumerControlCode.MUTE)
            muted = False
        draw()
        while not button.value:  # debounce
            time.sleep(0.1)

    if button_A.value and not button_a_pressed:  # button is pushed
        cc.send(ConsumerControlCode.PLAY_PAUSE)
        print("Play/Pause")
        button_a_pressed = True  # state for debouncing
        time.sleep(0.05)

    if not button_A.value and button_a_pressed:
        button_a_pressed = False
        time.sleep(0.05)
