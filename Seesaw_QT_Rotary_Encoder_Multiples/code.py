# SPDX-FileCopyrightText: 2021 John Park
# SPDX-License-Identifier: MIT

# I2C rotary encoder multiple test example.
# solder the A0 jumper on the second QT Rotary Encoder board

import board
from adafruit_seesaw import seesaw, rotaryio, digitalio, neopixel

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller

qt_enc1 = seesaw.Seesaw(i2c, addr=0x36)
qt_enc2 = seesaw.Seesaw(i2c, addr=0x37)

qt_enc1.pin_mode(24, qt_enc1.INPUT_PULLUP)
button1 = digitalio.DigitalIO(qt_enc1, 24)
button_held1 = False

qt_enc2.pin_mode(24, qt_enc2.INPUT_PULLUP)
button2 = digitalio.DigitalIO(qt_enc2, 24)
button_held2 = False

encoder1 = rotaryio.IncrementalEncoder(qt_enc1)
last_position1 = None

encoder2 = rotaryio.IncrementalEncoder(qt_enc2)
last_position2 = None

pixel1 = neopixel.NeoPixel(qt_enc1, 6, 1)
pixel1.brightness = 0.2
pixel1.fill(0xff0000)

pixel2 = neopixel.NeoPixel(qt_enc2, 6, 1)
pixel2.brightness = 0.2
pixel2.fill(0x0000ff)


while True:

    # negate the position to make clockwise rotation positive
    position1 = -encoder1.position
    position2 = -encoder2.position

    if position1 != last_position1:
        last_position1 = position1
        print("Position 1: {}".format(position1))

    if not button1.value and not button_held1:
        button_held1 = True
        pixel1.brightness = 0.5
        print("Button 1 pressed")

    if button1.value and button_held1:
        button_held1 = False
        pixel1.brightness = 0.2
        print("Button 1 released")


    if position2 != last_position2:
        last_position2 = position2
        print("Position 2: {}".format(position2))

    if not button2.value and not button_held2:
        button_held2 = True
        pixel2.brightness = 0.5
        print("Button 2 pressed")

    if button2.value and button_held2:
        button_held2 = False
        pixel2.brightness = 0.2
        print("Button 2 released")
