# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import microcontroller
import board
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
import adafruit_ble
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.hid import HIDService
from adafruit_seesaw import seesaw, rotaryio, digitalio

# ios modifier
mod = Keycode.CAPS_LOCK
#  keycodes
KBD_CODES = [
    [Keycode.SPACE], # center
    [mod], # up
    [Keycode.LEFT_ARROW], # left
    [Keycode.DOWN_ARROW], # down
    [Keycode.RIGHT_ARROW], # right
]

i2c = board.STEMMA_I2C()
seesaw = seesaw.Seesaw(i2c, addr=0x49)

seesaw_product = (seesaw.get_version() >> 16) & 0xFFFF
print(f"Found product {seesaw_product}")
if seesaw_product != 5740:
    print("Wrong firmware loaded?  Expected 5740")

buttons = []
button_names = ["Select", "Up", "Left", "Down", "Right"]
button_states = []

for s in range(1, 6):
    seesaw.pin_mode(s, seesaw.INPUT_PULLUP)
    pin = digitalio.DigitalIO(seesaw, s)
    pin_state = False
    buttons.append(pin)
    button_states.append(pin_state)

encoder = rotaryio.IncrementalEncoder(seesaw)
last_position = 0

if not buttons[0].value and button_states[0] is False:
    button_states[0] = True
    try:
        import _bleio
        time.sleep(2)
        _bleio.adapter.erase_bonding()
        time.sleep(2)
        print("Last BLE bonding deleted, restarting..")
        time.sleep(2)
        microcontroller.reset()
    except Exception: # pylint: disable=broad-except
        pass

#  BLE HID setup
hid = HIDService()
#  keyboard & mouse HID setup
kbd = Keyboard(hid.devices)

advertisement = ProvideServicesAdvertisement(hid)
advertisement.appearance = 961
scan_response = Advertisement()
scan_response.complete_name = "CircuitPython HID"
ble = adafruit_ble.BLERadio()

if not ble.connected:
    print("advertising")
    ble.start_advertising(advertisement, scan_response)
else:
    print("already connected")
    print(ble.connections)
time.sleep(2)

while True:
	#  check for BLE connection
    while not ble.connected:
        pass
	#  while BLE connected
    while ble.connected:
        position = encoder.position
        #  if the encoder is turned to the right
        if position > last_position:
            kbd.send(Keycode.RIGHT_ARROW)
		#  if the encoder is turned to the left
        if position < last_position:
            kbd.send(Keycode.LEFT_ARROW)
		#  reset encoder position
        if position != last_position:
            last_position = position
            print(f"Position: {position}")
        for b in range(5):
            if not buttons[b].value and button_states[b] is False:
                button_states[b] = True
                if b != 0:
                    kbd.press(*KBD_CODES[b])
                    print(*KBD_CODES[b])
                else:
                    kbd.press(mod)
                    kbd.press(*KBD_CODES[b])
                print(f"{button_names[b]} button pressed")
            if buttons[b].value and button_states[b] is True:
                button_states[b] = False
                kbd.release_all()
                print(f"{button_names[b]} button released")
	#  if BLE disconnects, begin advertising again
    ble.start_advertising(advertisement)
