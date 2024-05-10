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

cc = ConsumerControl(usb_hid.devices)

pixel_pin = board.A1
num_pixels = 20
pixels = neopixel.NeoPixel(pixel_pin, num_pixels,
                           brightness=1, auto_write=True)
hue = 0
pixels.fill(colorwheel(hue))

i2c = board.STEMMA_I2C()
seesaw = seesaw.Seesaw(i2c, 0x36)
seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
ss_pin = digitalio.DigitalIO(seesaw, 24)
button = Button(ss_pin, long_duration_ms=1000)

encoder = rotaryio.IncrementalEncoder(seesaw)
last_position = 0

while True:
    position = -encoder.position
    button.update()
    if position != last_position:
        if position > last_position:
            cc.send(ConsumerControlCode.VOLUME_DECREMENT)
            hue = hue - 7
            if hue <= 0:
                hue = hue + 256
        else:
            cc.send(ConsumerControlCode.VOLUME_INCREMENT)
            hue = hue + 7
            if hue >= 256:
                hue = hue - 256
        pixels.fill(colorwheel(hue))
        last_position = position
    if button.short_count:
        # print("Button pressed")
        cc.send(ConsumerControlCode.PLAY_PAUSE)
