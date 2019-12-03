"""
Circuit Playground Bluefruit Ornament Proximity
This demo uses advertising to set the color of scanning devices depending on the strongest broadcast
signal received. Circuit Playgrounds can be switched between advertising and scanning using the
slide switch. The buttons change the color when advertising.
"""

import time
import board
import digitalio

import neopixel

from adafruit_ble import BLERadio
from adafruit_ble.advertising.adafruit import AdafruitColor

# The color pickers will cycle through this list with buttons A and B.
color_options = [0x110000,
                 0x111100,
                 0x001100,
                 0x001111,
                 0x000011,
                 0x110011,
                 0x111111,
                 0x221111,
                 0x112211,
                 0x111122]

ble = BLERadio()

slide_switch = digitalio.DigitalInOut(board.SLIDE_SWITCH)
slide_switch.pull = digitalio.Pull.UP
button_a = digitalio.DigitalInOut(board.BUTTON_A)
button_a.pull = digitalio.Pull.DOWN
button_b = digitalio.DigitalInOut(board.BUTTON_B)
button_b.pull = digitalio.Pull.DOWN

led = digitalio.DigitalInOut(board.D13)
led.switch_to_output()

neopixels = neopixel.NeoPixel(board.NEOPIXEL, 10, auto_write=False)

i = 0
advertisement = AdafruitColor()
advertisement.color = color_options[i]
neopixels.fill(color_options[i])
while True:
    # The first mode is the color selector which broadcasts it's current color to other devices.
    if slide_switch.value:
        print("Broadcasting color")
        ble.start_advertising(advertisement)
        while slide_switch.value:
            last_i = i
            if button_a.value:
                i += 1
            if button_b.value:
                i -= 1
            i %= len(color_options)
            if last_i != i:
                color = color_options[i]
                neopixels.fill(color)
                neopixels.show()
                print("New color {:06x}".format(color))
                advertisement.color = color
                ble.stop_advertising()
                ble.start_advertising(advertisement)
                time.sleep(0.5)
        ble.stop_advertising()
    # The second mode listens for color broadcasts and shows the color of the strongest signal.
    else:
        closest = None
        closest_rssi = -80
        closest_last_time = 0
        print("Scanning for colors")
        while not slide_switch.value:
            for entry in ble.start_scan(AdafruitColor, minimum_rssi=-100, timeout=1):
                if slide_switch.value:
                    break
                now = time.monotonic()
                new = False
                if entry.address == closest:
                    pass
                elif entry.rssi > closest_rssi or now - closest_last_time > 0.4:
                    closest = entry.address
                else:
                    continue
                closest_rssi = entry.rssi
                closest_last_time = now
                discrete_strength = min((100 + entry.rssi) // 5, 10)
                #print(entry.rssi, discrete_strength)
                neopixels.fill(0x000000)
                for i in range(0, discrete_strength):
                    neopixels[i] = entry.color
                neopixels.show()

            # Clear the pixels if we haven't heard from anything recently.
            now = time.monotonic()
            if now - closest_last_time > 1:
                neopixels.fill(0x000000)
                neopixels.show()
        ble.stop_scan()
