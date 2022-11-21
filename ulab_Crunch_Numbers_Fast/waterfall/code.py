# SPDX-FileCopyrightText: 2020 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Waterfall FFT demo adapted from
https://teaandtechtime.com/fft-circuitpython-library/
to work with ulab on Adafruit CLUE"""

import array

import board
import audiobusio
import displayio
from ulab import numpy as np

try:
    from ulab.utils import spectrogram
except ImportError:
    from ulab.scipy.signal import spectrogram

display = board.DISPLAY

# Create a heatmap color palette
palette = displayio.Palette(52)
for i, pi in enumerate(
    (
        0xFF0000,
        0xFF0A00,
        0xFF1400,
        0xFF1E00,
        0xFF2800,
        0xFF3200,
        0xFF3C00,
        0xFF4600,
        0xFF5000,
        0xFF5A00,
        0xFF6400,
        0xFF6E00,
        0xFF7800,
        0xFF8200,
        0xFF8C00,
        0xFF9600,
        0xFFA000,
        0xFFAA00,
        0xFFB400,
        0xFFBE00,
        0xFFC800,
        0xFFD200,
        0xFFDC00,
        0xFFE600,
        0xFFF000,
        0xFFFA00,
        0xFDFF00,
        0xD7FF00,
        0xB0FF00,
        0x8AFF00,
        0x65FF00,
        0x3EFF00,
        0x17FF00,
        0x00FF10,
        0x00FF36,
        0x00FF5C,
        0x00FF83,
        0x00FFA8,
        0x00FFD0,
        0x00FFF4,
        0x00A4FF,
        0x0094FF,
        0x0084FF,
        0x0074FF,
        0x0064FF,
        0x0054FF,
        0x0044FF,
        0x0032FF,
        0x0022FF,
        0x0012FF,
        0x0002FF,
        0x0000FF,
    )
):
    palette[51 - i] = pi


class RollingGraph(displayio.TileGrid):
    def __init__(self, scale=2):
        # Create a bitmap with heatmap colors
        self._bitmap = displayio.Bitmap(
            display.width // scale, display.height // scale, len(palette)
        )
        super().__init__(self._bitmap, pixel_shader=palette)

        self.scroll_offset = 0

    def show(self, data):
        y = self.scroll_offset
        bitmap = self._bitmap

        board.DISPLAY.auto_refresh = False
        offset = max(0, (bitmap.width - len(data)) // 2)
        for x in range(min(bitmap.width, len(data))):
            bitmap[x + offset, y] = int(data[x])

        board.DISPLAY.auto_refresh = True

        self.scroll_offset = (y + 1) % self.bitmap.height


group = displayio.Group(scale=3)
graph = RollingGraph(3)
fft_size = 256

# Add the TileGrid to the Group
group.append(graph)

# Add the Group to the Display
display.show(group)

# instantiate board mic
mic = audiobusio.PDMIn(
    board.MICROPHONE_CLOCK, board.MICROPHONE_DATA, sample_rate=16000, bit_depth=16
)

# use some extra sample to account for the mic startup
samples_bit = array.array("H", [0] * (fft_size + 3))

# Main Loop
def main():
    max_all = 10

    while True:
        mic.record(samples_bit, len(samples_bit))
        samples = np.array(samples_bit[3:])
        spectrogram1 = spectrogram(samples)
        # spectrum() is always nonnegative, but add a tiny value
        # to change any zeros to nonzero numbers
        spectrogram1 = np.log(spectrogram1 + 1e-7)
        spectrogram1 = spectrogram1[1 : (fft_size // 2) - 1]
        min_curr = np.min(spectrogram1)
        max_curr = np.max(spectrogram1)

        if max_curr > max_all:
            max_all = max_curr
        else:
            max_curr = max_curr - 1

        print(min_curr, max_all)
        min_curr = max(min_curr, 3)
        # Plot FFT
        data = (spectrogram1 - min_curr) * (51.0 / (max_all - min_curr))
        # This clamps any negative numbers to zero
        data = data * np.array((data > 0))
        graph.show(data)


main()
