# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import usb_hid
import neopixel
from rainbowio import colorwheel
from adafruit_debouncer import Button
from adafruit_seesaw import seesaw, rotaryio, digitalio
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

enc_inc = ConsumerControlCode.VOLUME_INCREMENT
enc_dec = ConsumerControlCode.VOLUME_DECREMENT
one_press = ConsumerControlCode.PLAY_PAUSE
two_press = ConsumerControlCode.SCAN_NEXT_TRACK
three_press = [Keycode.LEFT_CONTROL, Keycode.UP_ARROW]
long_press = ConsumerControlCode.MUTE

cc = ConsumerControl(usb_hid.devices)
kbd = Keyboard(usb_hid.devices)

pixel_pin = board.A1
num_pixels = 18
pixels = neopixel.NeoPixel(pixel_pin, num_pixels,
                           brightness=.5, auto_write=True)
hue = 0
pixels.fill(colorwheel(hue))

i2c = board.STEMMA_I2C()
seesaw = seesaw.Seesaw(i2c, 0x36)
seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
ss_pin = digitalio.DigitalIO(seesaw, 24)
button = Button(ss_pin, long_duration_ms=600)

encoder = rotaryio.IncrementalEncoder(seesaw)
last_position = 0

while True:
    position = -encoder.position
    button.update()
    if position != last_position:
        if position > last_position:
            cc.send(enc_dec)
            hue = hue - 7
            if hue <= 0:
                hue = hue + 256
        else:
            cc.send(enc_inc)
            hue = hue + 7
            if hue >= 256:
                hue = hue - 256
        pixels.fill(colorwheel(hue))
        last_position = position
    if button.short_count == 1:
        cc.send(one_press)
    if button.short_count == 2:
        cc.send(two_press)
    if button.short_count == 3:
        kbd.press(*three_press)
        kbd.release_all()
    if button.long_press:
        cc.send(long_press)
