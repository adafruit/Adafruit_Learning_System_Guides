# Magic 9 Ball
# Turn HalloWing face down and then face up to change images at random
# place 128 x 128 pixel 24-bit .bmp images at root level of HalloWing

import time
import os
import random
import board
import displayio
import adafruit_lis3dh

splash = displayio.Group()
board.DISPLAY.show(splash)

SENSITIVITY = 5   # reading in Z direction to trigger, adjustable

images = list(filter(lambda x: x.endswith("bmp"), os.listdir("/")))

i = random.randint(0, (len(images)-1))  # initial image is randomly selected

# Set up accelerometer on I2C bus, 4G range:
ACCEL = adafruit_lis3dh.LIS3DH_I2C(board.I2C(), address=0x18)

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
        face = displayio.TileGrid(odb, pixel_shader=displayio.ColorConverter())

        splash.append(face)
        # Wait for the image to load.
        board.DISPLAY.wait_for_frame()

        # Fade up the backlight
        for b in range(101):
            board.DISPLAY.brightness = b / 100
            time.sleep(0.01)  # default (0.01)

        # Wait until the board gets shaken
        while not shaken:
            try:
                ACCEL_Z = ACCEL.acceleration[2]  # Read Z axis acceleration
            except OSError:
                pass
            # print(ACCEL_Z)  # uncomment to see the accelerometer z reading
            if ACCEL_Z > SENSITIVITY:
                shaken = True

        # Fade down the backlight
        for b in range(100, 0, -1):
            board.DISPLAY.brightness = b
            time.sleep(0.005)  # default (0.005)

        splash.pop()

        i = random.randint(0, (len(images)-1))  # pick a new random image
        # print("shaken")
        faceup = False
        i %= len(images) - 1
