# SPDX-FileCopyrightText: 2021 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from picamera import PiCamera
import time
from fractions import Fraction
import datetime

cur_time = datetime.datetime.now()
stub = cur_time.strftime("%Y%m%d%H%M_low")

camera = PiCamera(framerate=Fraction(1,6))

# You can change these as needed. Six seconds (6000000)
# is the max for shutter speed and 800 is the max for ISO.
camera.shutter_speed = 1750000
camera.iso = 800

time.sleep(30)
camera.exposure_mode = 'off'

outfile = "%s.jpg" % (stub)
camera.capture(outfile)

camera.close()
