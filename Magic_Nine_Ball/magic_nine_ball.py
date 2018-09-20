# Magic 9 Ball
# Turn HalloWing face down and then face up to change images at random
# place 128 x 128 pixel 24-bit .bmp images at root level of HalloWing

import time
import os
import random
import board
import displayio
import pulseio
import busio
import adafruit_lis3dh

backlight = pulseio.PWMOut(board.TFT_BACKLIGHT)
splash = displayio.Group()
board.DISPLAY.show(splash)

max_brightness = 2 ** 15

images = list(filter(lambda x: x.endswith("bmp"), os.listdir("/")))

i = random.randint(0, 19)  # initial image is randomly selected

# Set up accelerometer on I2C bus, 4G range:
I2C = busio.I2C(board.SCL, board.SDA)

ACCEL = adafruit_lis3dh.LIS3DH_I2C(I2C, address=0x18)

ACCEL.range = adafruit_lis3dh.RANGE_4_G

while True:
    shaken = False
    with open(images[i], "rb") as f:
        print("Image load {}".format(images[i]))
        try:
            odb = displayio.OnDiskBitmap(f)
        except ValueError:
            print("Image unsupported {}".format(images[i]))
            del images[i]
            continue
        face = displayio.Sprite(odb, pixel_shader=displayio.ColorConverter(),
                                position=(0, 0))
        splash.append(face)
        # Wait for the image to load.
        board.DISPLAY.wait_for_frame()

        # Fade up the backlight
        for b in range(100):
            backlight.duty_cycle = b * max_brightness // 100
            time.sleep(0.01)  # default (0.01)

        # Wait forever
        while not shaken:
            try:
                ACCEL_X, ACCEL_Y, ACCEL_Z = ACCEL.acceleration  # Read the accelerometer
            except IOError:
                pass
            # print(ACCEL_Z)  # uncomment to see the accelerometer z reading
            if ACCEL_Z > 5:
                shaken = True

        # Fade down the backlight
        for b in range(50, -1, -1):
            backlight.duty_cycle = b * max_brightness // 100
            time.sleep(0.005)  # default (0.005)

        splash.pop()

        if ACCEL_Z > 5:
            i = random.randint(0, 19)  # initial image is randomly selected
            print("shaken")
            faceup = False
        i %= len(images) - 1
