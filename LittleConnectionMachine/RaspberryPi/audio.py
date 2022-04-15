# SPDX-FileCopyrightText: 2022 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Audio spectrum display for Little Connection Machine. This is designed to be
fun to look at, not a Serious Audio Tool(tm). Requires USB microphone & ALSA
config. Prerequisite libraries include PyAudio and NumPy:
sudo apt-get install libatlas-base-dev libportaudio2
pip3 install numpy pyaudio
See the following for ALSA config (use Stretch directions):
learn.adafruit.com/usb-audio-cards-with-a-raspberry-pi/updating-alsa-config
"""

import math
import time
import numpy as np
import pyaudio
from cm1 import CM1

# FFT configurables. These numbers are 'hard,' actual figures:
RATE = 11025  # For audio vis, don't want or need high sample rate!
FFT_SIZE = 128  # Audio samples to read per frame (for FFT input)
ROWS = 32  # FFT output filtered down to this many 'buckets'
# Then things start getting subjective. For example, the lower and upper
# ends of the FFT output don't make a good contribution to the resulting
# graph...either too noisy, or out of musical range. Clip a range between
# between 0 and FFT_SIZE-1. These aren't hard science, they were determined
# by playing various music and seeing what looked good:
LEAST = 1  # Lowest bin of FFT output to use
MOST = 111  # Highest bin of FFT output to use
# And moreso. Normally, FFT results are linearly spaced by frequency,
# and with music this results in a crowded low end and sparse high end.
# The visualizer reformats this logarithmically so octaves are linearly
# spaced...the low end is expanded, upper end compressed. But just picking
# individial FFT bins will cause visual dropouts. Instead, a number of
# inputs are merged into each output, and because of the logarithmic scale,
# that number needs to be focused near the low end and spread out among
# many samples toward the top. Again, not scientific, these were derived
# empirically by throwing music at it and adjusting:
FIRST_WIDTH = 2  # Width of sampling curve at low end
LAST_WIDTH = 40  # Width of sampling curve at high end
# Except for ROWS above, none of this is involved in the actual rendering
# of the graph, just how the data is massaged. If modifying this for your
# own FFT-based visualizer, you could keep this around and just change the
# drawing parts of the main loop.


class AudioSpectrum(CM1):
    """Audio spectrum display for Little Connection Machine."""

    # pylint: disable=too-many-locals
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # CM1 base initialization

        # Access USB mic via PyAudio
        audio = pyaudio.PyAudio()
        self.stream = audio.open(
            format=pyaudio.paInt16,  # 16-bit int
            channels=1,  # Mono
            rate=RATE,
            input=True,
            output=False,
            frames_per_buffer=FFT_SIZE,
        )

        # Precompute a few items for the math to follow
        first_center_log = math.log2(LEAST + 0.5)
        center_log_spread = math.log2(MOST + 0.5) - first_center_log
        width_low_log = math.log2(FIRST_WIDTH)
        width_log_spread = math.log2(LAST_WIDTH) - width_low_log

        # As mentioned earlier, each row of the graph is filtered down from
        # multiple FFT elements. These lists are involved in that filtering,
        # each has one item per row of output:
        self.low_bin = []  # First FFT bin that contributes to row
        self.bin_weight = []  # List of subsequent FFT element weightings
        self.bin_sum = []  # Precomputed sum of bin_weight for row
        self.noise = []  # Subtracted from FFT output (see note later)

        for row in range(ROWS):  # For each row...
            # Calc center & spread of cubic curve for bin weighting
            center_log = first_center_log + center_log_spread * row / (ROWS - 1)
            center_linear = 2**center_log
            width_log = width_low_log + width_log_spread * row / (ROWS - 1)
            width_linear = 2**width_log
            half_width = width_linear * 0.5
            lower = center_linear - half_width
            upper = center_linear + half_width
            low_bin = int(lower)  # First FFT element to use
            hi_bin = min(FFT_SIZE - 1, int(upper))  # Last "
            weights = []  # FFT weights for row
            for bin_num in range(low_bin, hi_bin + 1):
                bin_center = bin_num + 0.5
                dist = abs(bin_center - center_linear) / half_width
                if dist < 1.0:  # Filter out a math stragglers at either end
                    # Bin weights have a cubic falloff curve within range:
                    dist = 1.0 - dist  # Invert dist so 1.0 is at center
                    weight = ((3.0 - (dist * 2.0)) * dist) * dist
                    weights.append(weight)
            self.bin_weight.append(weights)  # Save list of weights for row
            self.bin_sum.append(sum(weights))  # And sum of weights
            self.low_bin.append(low_bin)  # And first FFT bin index
            # FFT output always has a little "sparkle" due to ambient hum.
            # Subtracting a bit helps. Noise varies per element, more at low
            # end...this table is just a non-scientific fudge factor...
            self.noise.append(int(2.4 ** (4 - 4 * row / ROWS)))

    def run(self):
        """Main loop for audio visualizer."""

        # Some tables associated with each row of the display. These are
        # visualizer specific, not part of the FFT processing, so they're
        # here instead of part of the class above.
        width = [0 for _ in range(ROWS)]  # Current row width
        peak = [0 for _ in range(ROWS)]  # Recent row peak
        dropv = [0.0 for _ in range(ROWS)]  # Current peak falling speed
        autolevel = [32.0 for _ in range(ROWS)]  # Per-row auto adjust

        start_time = time.monotonic()
        frames = 0

        while True:

            # Read bytes from PyAudio stream, convert to int16, process
            # via NumPy's FFT function...
            data_8 = self.stream.read(FFT_SIZE * 2, exception_on_overflow=False)
            data_16 = np.frombuffer(data_8, np.int16)
            fft_out = np.fft.fft(data_16, norm="ortho")
            # fft_out will have FFT_SIZE * 2 elements, mirrored at center

            # Get spectrum of first half. Instead of square root for
            # magnitude, use something between square and cube root.
            # No scientific reason, just looked good.
            spec_y = [
                (c.real * c.real + c.imag * c.imag) ** 0.4 for c in fft_out[0:FFT_SIZE]
            ]

            self.clear()  # Clear canvas before drawing
            for row in range(ROWS):  # Low to high freq...
                # Weigh & sum up all the FFT outputs affecting this row
                total = 0
                for idx, weight in enumerate(self.bin_weight[row]):
                    total += (spec_y[self.low_bin[row] + idx]) * weight
                total /= self.bin_sum[row]

                # Auto-leveling is intended to make each column 'pop'.
                # When a particular column isn't getting a lot of input
                # from the FFT, gradually boost that column's sensitivity.
                if total > autolevel[row]:  # New level is louder
                    # Make autolevel rise quickly if column total exceeds it
                    autolevel[row] = autolevel[row] * 0.25 + total * 0.75
                else:  # New level is softer
                    # And fall slowly otherwise
                    autolevel[row] = autolevel[row] * 0.98 + total * 0.02
                # Autolevel limit keeps things from getting TOO boosty.
                # Trial and error, no science to this number.
                autolevel[row] = max(autolevel[row], 20)

                # Apply autoleveling to weighted input.
                # This is the prelim. row width before further filtering...
                total *= 18 / autolevel[row]  # 18 is 1/2 display width

                # ...then filter the column width computed above
                if total > width[row]:
                    # If it's greater than this column's current width,
                    # move column's width quickly in that direction
                    width[row] = width[row] * 0.3 + total * 0.7
                else:
                    # If less, move slowly down
                    width[row] = width[row] * 0.5 + total * 0.5

                # Compute "peak dots," which sort of show the recent
                # peak level for each column (mostly just neat to watch).
                if width[row] > peak[row]:
                    # If column exceeds old peak, move peak immediately,
                    # give it a slight upward boost.
                    dropv[row] = (peak[row] - width[row]) * 0.07
                    peak[row] = min(width[row], 18)
                else:
                    # Otherwise, peak gradually accelerates down
                    dropv[row] += 0.2
                    peak[row] -= dropv[row]

                # Draw bar for this row. It's done as a gradient,
                # bright toward center, dim toward edge.
                iwidth = int(width[row] + 0.5)  # Integer width
                drow = ROWS - 1 - row  # Display row, reverse of freq row
                if iwidth > 0:
                    iwidth = min(iwidth, 18)  # Clip to 18 pixels
                    scale = self.brightness * iwidth / 18  # Center brightness
                    for col in range(iwidth):
                        level = int(scale * ((1.0 - col / iwidth) ** 2.6))
                        self.draw.point([17 - col, drow], fill=level)
                        self.draw.point([18 + col, drow], fill=level)

                # Draw peak dot
                if peak[row] > 0:
                    col = int(peak[row] + 0.5)
                    self.draw.point([17 - col, drow], fill=self.brightness)
                    self.draw.point([18 + col, drow], fill=self.brightness)

            # Update matrices and show est. frames/second
            self.redraw()
            frames += 1
            elapsed = time.monotonic() - start_time
            print(frames / elapsed)


if __name__ == "__main__":
    MY_APP = AudioSpectrum()  # Instantiate class, calls __init__() above
    MY_APP.process()
