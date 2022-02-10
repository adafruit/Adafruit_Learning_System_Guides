# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

from adafruit_crickit import crickit

#  crickit setup
ss = crickit.seesaw
#  pin for photo interrupter
photo = crickit.SIGNAL1
ss.pin_mode(photo, ss.INPUT_PULLUP)

#  dc motor setup
motor = crickit.dc_motor_1

#  party parrot colors for the NeoPixel
parrot_0 = (255, 75, 0)
parrot_1 = (255, 200, 0)
parrot_2 = (90, 255, 90)
parrot_3 = (0, 255, 255)
parrot_4 = (0, 160, 255)
parrot_5 = (90, 0, 255)
parrot_6 = (175, 0, 255)
parrot_7 = (255, 0, 200)
parrot_8 = (255, 0, 125)
parrot_9 = (255, 0, 0)

colors = (parrot_0, parrot_1, parrot_2, parrot_3, parrot_4, parrot_5,
            parrot_6, parrot_7, parrot_8, parrot_9)

#  setup using crickit neopixel library
crickit.init_neopixel(1)
crickit.neopixel.fill((parrot_0))

#  counter for party parrot colors
z = 0
#  speed for the dc motor
speed = 0.3

while True:
    #  begin the dc motor
    #  will run throughout the loop
    motor.throttle = speed
    #  read the input from the photo interrupter
    data = ss.digital_read(photo)

    #  if the photo interrupter detects a break:
    if data is True:
        #  debug print
        print(z)
        #  change the neopixel's color to the z index of the colors array
        crickit.neopixel.fill((colors[z]))
        #  increase z by 1
        z += 1
        #  if z reaches the end of the colors array...
        if z > 9:
            #  index is reset
            z = 0
