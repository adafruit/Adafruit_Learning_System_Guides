# SPDX-FileCopyrightText: 2022 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Very minimal image viewer for 6X square RGB LED matrices.

usage: sudo python imageviewer.py [filename]
"""

import time
import sys
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image

if len(sys.argv) < 2:
    sys.exit("Requires an image argument")
else:
    image_file = sys.argv[1]

image = Image.open(image_file).convert("RGB")

# Hardcoded matrix config; commandline args ignored
options = RGBMatrixOptions()
options.rows = 64
options.cols = 64
options.chain_length = 6
options.parallel = 1
options.hardware_mapping = "adafruit-hat-pwm"
options.gpio_slowdown = 4

matrix = RGBMatrix(options=options)

# Scale image to fit 6X matrix chain
image.thumbnail((matrix.width, matrix.height), Image.ANTIALIAS)

matrix.SetImage(image)

try:
    print("Press CTRL-C to stop.")
    while True:
        time.sleep(100)
except KeyboardInterrupt:
    sys.exit(0)
