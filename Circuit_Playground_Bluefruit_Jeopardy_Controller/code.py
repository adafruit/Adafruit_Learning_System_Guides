# SPDX-FileCopyrightText: 2021 Dylan Herrada for Adafruit Industries
# SPDX-License-Identifier: MIT

# General imports
import time
import random
import board
import digitalio
import neopixel

# HID imports
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS

# BLE imports
import adafruit_ble
from adafruit_ble.advertising import Advertisement
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.hid import HIDService
from adafruit_ble.services.standard.device_info import DeviceInfoService

try:
    from audiocore import WaveFile
except ImportError:
    from audioio import WaveFile

try:
    from audioio import AudioOut
except ImportError:
    try:
        from audiopwmio import PWMAudioOut as AudioOut
    except ImportError:
        pass  # not always supported by every board!

# Enable the speaker
spkrenable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
spkrenable.direction = digitalio.Direction.OUTPUT
spkrenable.value = True


# Make the input buttons
btn1 = digitalio.DigitalInOut(board.D10)  # Marked A3
btn1.direction = digitalio.Direction.INPUT
btn1.pull = digitalio.Pull.UP

btn2 = digitalio.DigitalInOut(board.D9)  # Marked A2
btn2.direction = digitalio.Direction.INPUT
btn2.pull = digitalio.Pull.UP

btn3 = digitalio.DigitalInOut(board.D3)  # Marked SCL A4
btn3.direction = digitalio.Direction.INPUT
btn3.pull = digitalio.Pull.UP

central = digitalio.DigitalInOut(board.D0)  # Marked RX A6
central.direction = digitalio.Direction.INPUT
central.pull = digitalio.Pull.UP

led = digitalio.DigitalInOut(board.D2)  # Marked SDA A5
led.switch_to_output()
led.value = False

buttons = [btn1, btn2, btn3]
upper = len(buttons) - 1

ble_enabled = digitalio.DigitalInOut(board.SLIDE_SWITCH)
ble_enabled.direction = digitalio.Direction.INPUT
ble_enabled.pull = digitalio.Pull.UP

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=0.5)
# Use default HID descriptor
hid = HIDService()
device_info = DeviceInfoService(
    software_revision=adafruit_ble.__version__, manufacturer="Adafruit Industries"
)
advertisement = ProvideServicesAdvertisement(hid)
advertisement.appearance = 961
scan_response = Advertisement()

ble = adafruit_ble.BLERadio()
if ble.connected:
    for c in ble.connections:
        c.disconnect()

if ble_enabled.value:
    print("advertising")
    ble.start_advertising(advertisement, scan_response)

k = Keyboard(hid.devices)
kl = KeyboardLayoutUS(k)

wave_file = open("jeopardy.wav", "rb")
wave = WaveFile(wave_file)
audio = AudioOut(board.SPEAKER)

while True:
    if ble_enabled.value:
        while not ble.connected:
            pass
        if ble.connected:
            print("Connected")
            led.value = True
            time.sleep(0.1)
            led.value = False
            time.sleep(0.1)
            led.value = True
            time.sleep(0.1)
            led.value = False

    while ble.connected or not ble_enabled.value:
        if not central.value:
            led.value = True
            print("Running")
            while True:
                i = random.randint(0, upper)
                if not buttons[i].value:
                    break

            audio.play(wave)
            if i == 0:
                print("Button 1")
                pixels.fill((0, 0, 255))
                if ble_enabled.value:
                    kl.write("Button 1")
            elif i == 1:
                print("Button 2")
                pixels.fill((0, 255, 0))
                if ble_enabled.value:
                    kl.write("Button 2")
            elif i == 2:
                print("Button 3")
                pixels.fill((255, 255, 255))
                if ble_enabled.value:
                    kl.write("Button 3")

            if not ble_enabled.value:
                print(
                    "BLE HID has been disabled, slide the slide switch to the left to re-enable"
                )

            print("Finished")
            led.value = False

            while central.value:
                pass

            print("reset")
            pixels.fill((0, 0, 0))
            led.value = True
            time.sleep(0.5)
            led.value = False
            print("Ready")
        if ble_enabled.value:
            if not ble.connected:
                break
    else:
        continue
    break
