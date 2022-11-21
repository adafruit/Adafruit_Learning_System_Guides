# SPDX-FileCopyrightText: 2021 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Adapted from the FFT Example: Waterfall Spectrum Analyzer
by Jeff Epler
https://learn.adafruit.com/ulab-crunch-numbers-fast-with-circuitpython/overview """

import array
import board
import audiobusio
import busio
from ulab import numpy as np

try:
    from ulab.utils import spectrogram
except ImportError:
    from ulab.scipy.signal import spectrogram
import adafruit_is31fl3741
from adafruit_is31fl3741.adafruit_rgbmatrixqt import Adafruit_RGBMatrixQT

#  Manually declare I2c (not board.I2C()) to access 1 MHz speed for
i2c = busio.I2C(board.SCL, board.SDA, frequency=1000000)
#  Declare is31 w/buffering preferred (low RAM will fall back on unbuffered)
is31 = Adafruit_RGBMatrixQT(i2c, allocate=adafruit_is31fl3741.PREFER_BUFFER)
#  In buffered mode, MUST use show() to refresh matrix (see line 94)

#  brightness for the RGBMatrixQT
#  set to about 20%
is31.set_led_scaling(0x19)
is31.global_current = 0x03
is31.enable = True

#  array of colors for the LEDs
#  goes from purple to red
#  gradient generated using https://colordesigner.io/gradient-generator
heatmap = [
    0xB000FF,
    0xA600FF,
    0x9B00FF,
    0x8F00FF,
    0x8200FF,
    0x7400FF,
    0x6500FF,
    0x5200FF,
    0x3900FF,
    0x0003FF,
    0x0003FF,
    0x0047FF,
    0x0066FF,
    0x007EFF,
    0x0093FF,
    0x00A6FF,
    0x00B7FF,
    0x00C8FF,
    0x00D7FF,
    0x00E5FF,
    0x00E0FF,
    0x00E6FD,
    0x00ECF6,
    0x00F2EA,
    0x00F6D7,
    0x00FAC0,
    0x00FCA3,
    0x00FE81,
    0x00FF59,
    0x00FF16,
    0x00FF16,
    0x45FF08,
    0x62FF00,
    0x78FF00,
    0x8BFF00,
    0x9BFF00,
    0xAAFF00,
    0xB8FF00,
    0xC5FF00,
    0xD1FF00,
    0xEDFF00,
    0xF5EB00,
    0xFCD600,
    0xFFC100,
    0xFFAB00,
    0xFF9500,
    0xFF7C00,
    0xFF6100,
    0xFF4100,
    0xFF0000,
    0xFF0000,
    0xFF0000,
]

#  size of the FFT data sample
fft_size = 64

#  setup for onboard mic
mic = audiobusio.PDMIn(
    board.MICROPHONE_CLOCK, board.MICROPHONE_DATA, sample_rate=16000, bit_depth=16
)

#  use some extra sample to account for the mic startup
samples_bit = array.array("H", [0] * (fft_size + 3))

#  sends visualized data to the RGB matrix with colors
def waves(data, y):
    offset = max(0, (13 - len(data)) // 2)

    for x in range(min(13, len(data))):
        is31.pixel(x + offset, y, heatmap[int(data[x])])


# main loop
def main():
    #  value for audio samples
    max_all = 10
    #  variable to move data along the matrix
    scroll_offset = 0
    #  setting the y axis value to equal the scroll_offset
    y = scroll_offset

    while True:
        #  record the audio sample
        mic.record(samples_bit, len(samples_bit))
        #  send the sample to the ulab array
        samples = np.array(samples_bit[3:])
        #  creates a spectogram of the data
        spectrogram1 = spectrogram(samples)
        # spectrum() is always nonnegative, but add a tiny value
        # to change any zeros to nonzero numbers
        spectrogram1 = np.log(spectrogram1 + 1e-7)
        spectrogram1 = spectrogram1[1 : (fft_size // 2) - 1]
        #  sets range of the spectrogram
        min_curr = np.min(spectrogram1)
        max_curr = np.max(spectrogram1)
        #  resets values
        if max_curr > max_all:
            max_all = max_curr
        else:
            max_curr = max_curr - 1
        min_curr = max(min_curr, 3)
        # stores spectrogram in data
        data = (spectrogram1 - min_curr) * (51.0 / (max_all - min_curr))
        # sets negative numbers to zero
        data = data * np.array((data > 0))
        #  resets y
        y = scroll_offset
        #  runs waves to write data to the LED's
        waves(data, y)
        #  updates scroll_offset to move data along matrix
        scroll_offset = (y + 1) % 9
        #  writes data to the RGB matrix
        is31.show()


main()
