# SPDX-FileCopyrightText: 2022 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Conway's Game of Life for 6X square RGB LED matrices.
Uses same physical matrix arrangement as "globe" program; see notes there.

usage: sudo python life.py [options]

(You may or may not need the 'sudo' depending how the rpi-rgb-matrix
library is configured)

Options include all of the rpi-rgb-matrix flags, such as --led-pwm-bits=N
or --led-gpio-slowdown=N, and then the following:

  -k <int>   : Index of color palette to use. 0 = default black & white
               (sorry, -c and -p already taken by matrix configurables).
  -t <float> : Run time in seconds. Program will exit after this.
               Default is to run indefinitely, until crtl+C received.
  -f <float> : Fade in/out time in seconds. Used in combination with the
               -t option, this provides a nice fade-in, run for a
               while, fade-out and exit.

rpi-rgb-matrix has the following single-character abbreviations for
some configurables: -b (--led-brightness), -c (--led-chain),
-m (--led-gpio-mapping), -p (--led-pwm-bits), -P (--led-parallel),
-r (--led-rows). AVOID THESE in any future configurables added to this
program, as some users may have "muscle memory" for those options.

This code depends on the rpi-rgb-matrix library. While this .py file has
a permissive MIT licence, libraries may (or not) have restrictions on
commercial use, distributing precompiled binaries, etc. Check their
license terms if this is relevant to your situation.
"""

import argparse
import os
import sys
import time
import random
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image

# import cProfile  # Used only when profiling

EDGE_TOP = 0
EDGE_LEFT = 1
EDGE_RIGHT = 2
EDGE_BOTTOM = 3
FACE = (  # Topology for 6 faces of cube; constant, not runtime-configurable.
    # Sequence within each face is top, left, right, bottom.
    # Top, left, etc. are with respect to exterior view of LED face sides.
    (  # For face[0]...
        (1, EDGE_LEFT),  # Top edge connects to left of face[1]
        (2, EDGE_TOP),   # Left edge connects to top of face[2]
        (4, EDGE_TOP),   # Right edge connects to top of face[4]
        (3, EDGE_RIGHT), # etc...
    ),
    (  # face[1]...
        (2, EDGE_LEFT),  # Top edge connects to left of face[2]
        (0, EDGE_TOP),   # etc...
        (5, EDGE_TOP),
        (4, EDGE_RIGHT),
    ),
    (
        (0, EDGE_LEFT),
        (1, EDGE_TOP),
        (3, EDGE_TOP),
        (5, EDGE_RIGHT),
    ),
    (
        (2, EDGE_RIGHT),
        (5, EDGE_BOTTOM),
        (0, EDGE_BOTTOM),
        (4, EDGE_LEFT),
    ),
    (
        (0, EDGE_RIGHT),
        (3, EDGE_BOTTOM),
        (1, EDGE_BOTTOM),
        (5, EDGE_LEFT),
    ),
    (
        (1, EDGE_RIGHT),
        (4, EDGE_BOTTOM),
        (2, EDGE_BOTTOM),
        (3, EDGE_LEFT),
    ),
)

# Colormaps appear reversed from what one might expect. The first element
# of each is the 'on' pixel color, and each subsequent element is the color
# as a pixel 'ages,' up to the final 'background' color. Hence simple B&W
# on/off palette is white in index 0, black in index 1.
COLORMAP = (
    ((255, 255, 255), (0, 0, 0)),  # Simple B&W
    (  # Log2 Grayscale
        (255, 255, 255),
        (127, 127, 127),
        (63, 63, 63),
        (31, 31, 31),
        (15, 15, 15),
        (7, 7, 7),
        (3, 3, 3),
        (1, 1, 1),
        (0, 0, 0),
    ),
    (  # Heatmap (white-yellow-red-black)
        (255, 255, 255),  # White
        (255, 255, 127),  # Two steps to...
        (255, 255, 0),  # Yellow
        (255, 170, 0),  # Three steps...
        (255, 85, 0),
        (255, 0, 0),  # Red
        (204, 0, 0),  # Four steps...
        (153, 0, 0),
        (102, 0, 0),
        (51, 0, 0),
        (0, 0, 0),  # Black
    ),
    (  # Spectrum
        (255, 255, 255),  # White (100%)
        (127, 0, 0),  # Red (50%)
        (127, 31, 0),
        (127, 63, 0),  # Orange (50%)
        (127, 95, 0),
        (127, 127, 0),  # Yellow (etc)
        (63, 127, 0),
        (0, 127, 0),  # Green
        (0, 127, 127),  # Cyan
        (0, 0, 127),  # Blue
        (63, 0, 127),
        (127, 0, 127),  # Magenta
        (82, 0, 82),
        (41, 0, 41),
        (0, 0, 0),  # Black
    ),
)

# pylint: disable=too-many-instance-attributes
class Life:
    """
    Conway's Game of Life, mapped on a cube. See, the trick is that you
    can't just treat it as a big 2D rectangle...faces may be arranged in
    different orientations, and the space is discontiguous...the edges
    and corners create shenanigans.
    """

    def __init__(self):
        self.matrix = None  # RGB matrix object (initialized after inputs)
        self.canvas = None  # Offscreen canvas (after inputs)
        self.matrix_size = 0  # Matrix width/height in pixels (after inputs)
        self.matrix_max = 0  # Maximum column/row (after inputs)
        self.data = None  # Pixel 'age' data (after inputs)
        self.direct = None  # Table of 'OK to read pixel data directly' flags
        self.idx = 0  # Currently active data index (0/1, double-buffered)
        self.run_time = -1.0  # If >0 (input can override), limit run time
        self.fade_time = 0.0  # Fade in/out time (input can override)
        self.max_brightness = 255  # Matrix brightness (input can override)
        self.chain_length = 6  # Matrix chain length
        self.colormap = COLORMAP[0]  # Input can override
        self.colormap_max = None  # Initialized after inputs
        self.imgbuf = None  # PIL image buffer (initialized after inputs)

    # pylint: disable=too-many-statements
    def setup(self):
        """ Returns False on success, True on error """
        parser = argparse.ArgumentParser()

        # RGB matrix standards
        parser.add_argument(
            "-r",
            "--led-rows",
            action="store",
            help="Display rows. 32 for 32x32, 64 for 64x64. Default: 64",
            default=64,
            type=int,
        )
        parser.add_argument(
            "--led-cols",
            action="store",
            help="Panel columns. Typically 32 or 64. (Default: 64)",
            default=64,
            type=int,
        )
        parser.add_argument(
            "-c",
            "--led-chain",
            action="store",
            help="Daisy-chained boards. Default: 6.",
            default=6,
            type=int,
        )
        parser.add_argument(
            "-P",
            "--led-parallel",
            action="store",
            help="For Plus-models or RPi2: parallel chains. 1..3. Default: 1",
            default=1,
            type=int,
        )
        parser.add_argument(
            "-p",
            "--led-pwm-bits",
            action="store",
            help="Bits used for PWM. Something between 1..11. Default: 11",
            default=11,
            type=int,
        )
        parser.add_argument(
            "-b",
            "--led-brightness",
            action="store",
            help="Sets brightness level. Default: 100. Range: 1..100",
            default=100,
            type=int,
        )
        parser.add_argument(
            "-m",
            "--led-gpio-mapping",
            help="Hardware Mapping: regular, adafruit-hat, adafruit-hat-pwm",
            choices=["regular", "regular-pi1", "adafruit-hat", "adafruit-hat-pwm"],
            type=str,
        )
        parser.add_argument(
            "--led-scan-mode",
            action="store",
            help="Progressive or interlaced scan. 0 Progressive, 1 Interlaced (default)",
            default=1,
            choices=range(2),
            type=int,
        )
        parser.add_argument(
            "--led-pwm-lsb-nanoseconds",
            action="store",
            help="Base time-unit for the on-time in the lowest "
            "significant bit in nanoseconds. Default: 130",
            default=130,
            type=int,
        )
        parser.add_argument(
            "--led-show-refresh",
            action="store_true",
            help="Shows the current refresh rate of the LED panel",
        )
        parser.add_argument(
            "--led-slowdown-gpio",
            action="store",
            help="Slow down writing to GPIO. Range: 0..4. Default: 3",
            default=4, # For Pi 4 w/6 matrices
            type=int,
        )
        parser.add_argument(
            "--led-no-hardware-pulse",
            action="store",
            help="Don't use hardware pin-pulse generation",
        )
        parser.add_argument(
            "--led-rgb-sequence",
            action="store",
            help="Switch if your matrix has led colors swapped. Default: RGB",
            default="RGB",
            type=str,
        )
        parser.add_argument(
            "--led-pixel-mapper",
            action="store",
            help='Apply pixel mappers. e.g "Rotate:90"',
            default="",
            type=str,
        )
        parser.add_argument(
            "--led-row-addr-type",
            action="store",
            help="0 = default; 1=AB-addressed panels; 2=row direct; "
            "3=ABC-addressed panels; 4 = ABC Shift + DE direct",
            default=0,
            type=int,
            choices=[0, 1, 2, 3, 4],
        )
        parser.add_argument(
            "--led-multiplexing",
            action="store",
            help="Multiplexing type: 0=direct; 1=strip; 2=checker; 3=spiral; "
            "4=ZStripe; 5=ZnMirrorZStripe; 6=coreman; 7=Kaler2Scan; "
            "8=ZStripeUneven... (Default: 0)",
            default=0,
            type=int,
        )
        parser.add_argument(
            "--led-panel-type",
            action="store",
            help="Needed to initialize special panels. Supported: 'FM6126A'",
            default="",
            type=str,
        )
        parser.add_argument(
            "--led-no-drop-privs",
            dest="drop_privileges",
            help="Don't drop privileges from 'root' after initializing the hardware.",
            action="store_false",
        )

        # Extra args unique to this program
        parser.add_argument(
            "-k",
            action="store",
            help="Index of color palette to use. Default: 0",
            default=0,
            type=int,
        )
        parser.add_argument(
            "-t",
            action="store",
            help="Run time in seconds. Default: run indefinitely",
            default=-1.0,
            type=float,
        )
        parser.add_argument(
            "-f",
            action="store",
            help="Fade in/out time in seconds. Default: 0.0",
            default=0.0,
            type=float,
        )

        parser.set_defaults(drop_privileges=True)

        args = parser.parse_args()

        if args.led_rows != args.led_cols:
            print(
                os.path.basename(__file__) + ": error: led rows and columns must match"
            )
            return True

        if args.led_chain * args.led_parallel != 6:
            print(
                os.path.basename(__file__)
                + ": error: total chained * parallel matrices must equal 6"
            )
            return True

        options = RGBMatrixOptions()

        if args.led_gpio_mapping is not None:
            options.hardware_mapping = args.led_gpio_mapping
        options.rows = args.led_rows
        options.cols = args.led_cols
        options.chain_length = args.led_chain
        options.parallel = args.led_parallel
        options.row_address_type = args.led_row_addr_type
        options.multiplexing = args.led_multiplexing
        options.pwm_bits = args.led_pwm_bits
        options.brightness = args.led_brightness
        options.pwm_lsb_nanoseconds = args.led_pwm_lsb_nanoseconds
        options.led_rgb_sequence = args.led_rgb_sequence
        options.pixel_mapper_config = args.led_pixel_mapper
        options.panel_type = args.led_panel_type

        if args.led_show_refresh:
            options.show_refresh_rate = 1

        if args.led_slowdown_gpio is not None:
            options.gpio_slowdown = args.led_slowdown_gpio
        if args.led_no_hardware_pulse:
            options.disable_hardware_pulsing = True
        if not args.drop_privileges:
            options.drop_privileges = False

        self.matrix = RGBMatrix(options=options)
        self.canvas = self.matrix.CreateFrameCanvas()
        self.matrix_size = args.led_rows
        self.matrix_max = self.matrix_size - 1
        self.chain_length = args.led_chain
        self.max_brightness = args.led_brightness * 2.55 # 0-100 -> 0-255
        self.run_time = args.t
        self.fade_time = args.f

        self.colormap = COLORMAP[min(max(args.k, 0), len(COLORMAP) - 1)]
        self.colormap_max = len(self.colormap) - 1

        # Alloc & randomize initial state; 50% chance of any pixel being set
        self.data = [
            [
                [
                    [
                        random.randrange(2) * self.colormap_max
                        for x in range(self.matrix_size)
                    ]
                    for y in range(self.matrix_size)
                ]
                for face in range(6)
            ]
            for i in range(2)
        ]

        # Rather than testing X & Y to see if we should use get_edge_pixel
        # or access the data array directly, this table pre-stores which
        # pixel-getting approach to use for each row/column of one face.
        self.direct = (
            [[False] * self.matrix_size]
            + [[False] + [True] * (self.matrix_size - 2) + [False]]
            * (self.matrix_size - 2)
            + [[False] * self.matrix_size]
        )

        self.imgbuf = bytearray(self.matrix_size * self.matrix_size * 3)

        return False

    # NOTE: if the code starts looking super atrocious from here down,
    # that's no coincidence. To keep the animation smooth and appealing,
    # this was written to be fast, not Pythonic. Tons of A/B testing was
    # performed against different approaches to each piece, using cProfile
    # and/or the displayed FPS values. Some of this looks REALLY bad. If
    # you're wondering "why didn't they just [X]?", that's why.
    # NOT GOOD CODE TO LEARN FROM, except maybe for setting a bad example.

    # pylint: disable=too-many-branches
    def cross(self, face, col, row, edge):
        """Given a face index and a column & row known to be ONE pixel
        off ONE edge, return a new face index and a corresponding
        column & row within that face's native coordinate system.
        """
        to_edge = FACE[face][edge][1]
        if edge == EDGE_TOP:
            if to_edge == EDGE_TOP:
                col, row = self.matrix_max - col, 0
            elif to_edge == EDGE_LEFT:
                col, row = 0, col
            elif to_edge == EDGE_RIGHT:
                col, row = self.matrix_max, self.matrix_max - col
            else:
                row = self.matrix_max
        elif edge == EDGE_LEFT:
            if to_edge == EDGE_TOP:
                col, row = row, 0
            elif to_edge == EDGE_LEFT:
                col, row = 0, self.matrix_max - row
            elif to_edge == EDGE_RIGHT:
                col = self.matrix_max
            else:
                col, row = self.matrix_max - row, self.matrix_max
        elif edge == EDGE_RIGHT:
            if to_edge == EDGE_TOP:
                col, row = self.matrix_max - row, 0
            elif to_edge == EDGE_LEFT:
                col = 0
            elif to_edge == EDGE_RIGHT:
                col, row = self.matrix_max, self.matrix_max - row
            else:
                col, row = row, self.matrix_max
        else:
            if to_edge == EDGE_TOP:
                row = 0
            elif to_edge == EDGE_LEFT:
                col, row = 0, self.matrix_max - col
            elif to_edge == EDGE_RIGHT:
                col, row = self.matrix_max, col
            else:
                col, row = self.matrix_max - col, self.matrix_max

        return FACE[face][edge][0], col, row

    def get_edge_pixel(self, face, col, row):
        """Given a face index and a column & row that might be in-bounds
        OR one pixel off one or two edges, return 'age' of pixel, wrapping
        around edges as appropriate.
        """
        if 0 <= col <= self.matrix_max:  # Pixel in X bounds
            if 0 <= row <= self.matrix_max:  # Pixel in Y bounds
                return self.data[self.idx][face][row][col]
            # Else pixel in X bounds, but out of Y bounds
            edge = EDGE_TOP if row < 0 else EDGE_BOTTOM
        elif 0 <= row <= self.matrix_max:  # Pixel in Y bounds, off left/right
            edge = EDGE_LEFT if col < 0 else EDGE_RIGHT
        else:  # Pixel off two edges; treat corners as "dead"
            return 1

        face, col, row = self.cross(face, col, row, edge)
        return self.data[self.idx][face][row][col]

    def run(self):
        """Main loop of Life simulation."""
        start_time, frames = time.monotonic(), 0

        while True:
            if self.run_time > 0:  # Handle fade in / fade out
                elapsed = time.monotonic() - start_time
                if elapsed >= self.run_time:
                    break
                if elapsed < self.fade_time:
                    self.matrix.brightness = int(
                        self.max_brightness * elapsed / self.fade_time
                    )
                elif elapsed > (self.run_time - self.fade_time):
                    self.matrix.brightness = int(
                        self.max_brightness * (self.run_time - elapsed) / self.fade_time
                    )
                else:
                    self.matrix.brightness = self.max_brightness

            self.iterate()  # Process and render one frame

            # Swap double-buffered canvas, show frames per second
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            frames += 1
            print(frames / (time.monotonic() - start_time))

    # pylint: disable=too-many-locals
    def iterate(self):
        """Run one cycle of the Life simulation, drawing to offscreen canvas."""
        next_idx = 1 - self.idx  # Destination
        # Certain instance variables (ones referenced in inner loop) are
        # copied to locals to speed up access. This is kind of a jerk thing
        # to do and not "Pythonic," but anything for a boost in this code.
        imgbuf = self.imgbuf
        colormap = self.colormap
        colormap_max = self.colormap_max
        get_edge_pixel = self.get_edge_pixel
        for face in range(6):
            offset = 0
            for row in range(0, self.matrix_size):
                row_data = self.data[self.idx][face][row]
                row_data_next = self.data[next_idx][face][row]
                rm1 = row - 1
                rp1 = row + 1
                if row > 0:
                    above_data = self.data[self.idx][face][rm1]
                if row < self.matrix_max:
                    below_data = self.data[self.idx][face][rp1]
                cm1 = -1
                col = 0
                direct = self.direct[row]
                for cp1 in range(1, self.matrix_size + 1):
                    neighbors = (
                        (
                            above_data[cm1],
                            above_data[col],
                            above_data[cp1],
                            row_data[cm1],
                            row_data[cp1],
                            below_data[cm1],
                            below_data[col],
                            below_data[cp1],
                        )
                        if direct[col]
                        else (
                            get_edge_pixel(face, cm1, rm1),
                            get_edge_pixel(face, col, rm1),
                            get_edge_pixel(face, cp1, rm1),
                            get_edge_pixel(face, cm1, row),
                            get_edge_pixel(face, cp1, row),
                            get_edge_pixel(face, cm1, rp1),
                            get_edge_pixel(face, col, rp1),
                            get_edge_pixel(face, cp1, rp1),
                        )
                    ).count(0)
                    # Live cell w/2 or 3 neighbors continues, else dies.
                    # Empty cell w/3 neighbors goes live.
                    age = row_data[col]
                    if age == 0:  # Pixel (col,row) is active
                        if not neighbors in (2, 3):
                            age = 1  # Pixel aging starts
                    else:  # Pixel (col,row) is aged
                        if neighbors == 3:
                            age = 0  # Arise!
                        elif age < colormap_max:
                            age += 1  # Decay
                    row_data_next[col] = age
                    rgb = colormap[age]
                    imgbuf[offset] = rgb[0]
                    imgbuf[offset + 1] = rgb[1]
                    imgbuf[offset + 2] = rgb[2]
                    offset += 3
                    cm1 = col
                    col = cp1
            image = Image.frombuffer(
                "RGB",
                (self.matrix_size, self.matrix_size),
                bytes(imgbuf),
                "raw",
                "RGB",
                0,
                1,
            )
            # Upper-left corner of face in canvas space:
            xoffset = (face % self.chain_length) * self.matrix_size
            yoffset = (face // self.chain_length) * self.matrix_size
            self.canvas.SetImage(image, offset_x=xoffset, offset_y=yoffset)
        self.idx = next_idx


# pylint: disable=superfluous-parens
if __name__ == "__main__":
    life = Life()
    if not (status := life.setup()):
        try:
            print("Press CTRL-C to stop")
            life.run()
            # cProfile.run('life.run()') # Used only when profiling
        except KeyboardInterrupt:
            print("Exiting\n")
    sys.exit(status)
