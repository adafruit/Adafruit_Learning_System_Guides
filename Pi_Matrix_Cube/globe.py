# SPDX-FileCopyrightText: 2022 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
IF GLOBES WERE SQUARE: a revolving "globe" for 6X square RGB LED matrices on
Raspberry Pi w/Adafruit Matrix Bonnet or HAT.

usage: sudo ./globe [options]

usage: sudo python globe.py [options]

(You may or may not need the 'sudo' depending how the rpi-rgb-matrix
library is configured)

Options include all of the rpi-rgb-matrix flags, such as --led-pwm-bits=N
or --led-gpio-slowdown=N, and then the following:

  -i <filename> : Image filename for texture map. MUST be JPEG image format.
                  Default is maps/earth.jpg
  -v            : Orient cube with vertices at top & bottom, rather than
                  flat faces on top & bottom. No accompanying value.
  -s <float>    : Spin time in seconds (per revolution). Positive values
                  will revolve in the correct direction for the Earth map.
                  Negative values spin the opposite direction (magnitude
                  specifies seconds), maybe useful for text, logos or Uranus.
  -a <int>      : Antialiasing samples, per-axis. Range 1-8. Default is 1,
                  no supersampling. Fast hardware can sometimes go higher,
                  most should stick with 1.
  -t <float>    : Run time in seconds. Program will exit after this.
                  Default is to run indefinitely, until crtl+C received.
  -f <float>    : Fade in/out time in seconds. Used in combination with the
                  -t option, this provides a nice fade-in, revolve for a
                  while, fade-out and exit. Combined with a simple shell
                  script, it provides a classy way to cycle among different
                  planetoids/scenes/etc. without having to explicitly
                  implement such a feature here.
  -e <float>    : Edge-to-edge physical measure of LED matrix. Combined
                  with -E below, provides spatial compensation for edge
                  bezels when matrices are arranged in a cube (i.e. pixels
                  don't "jump" across the seam -- has a bit of dead space).
  -E <float>    : Edge-to-edge measure of opposite faces of assembled cube,
                  used in combination with -e above. This will be a little
                  larger than the -e value (lower/upper case is to emphasize
                  this relationship). Units for both are arbitrary; use
                  millimeters, inches, whatever, it's the ratio that's
                  important.

-rgb-matrix has the following single-character abbreviations for
some configurables: -b (--led-brightness), -c (--led-chain),
-m (--led-gpio-mapping), -p (--led-pwm-bits), -P (--led-parallel),
-r (--led-rows). AVOID THESE in any future configurables added to this
program, as some users may have "muscle memory" for those options.

This is not great learning-from code, being a fairly direct mash-up of
code taken from life.py and adapted from globe.cc. It's mostly here to
fulfill a need to offer these demos in both C++ and Python versions.
The C++ code is a little better commented.

This code depends on the rpi-rgb-matrix library. While this .py file has
a permissive MIT licence, libraries may (or not) have restrictions on
commercial use, distributing precompiled binaries, etc. Check their
license terms if this is relevant to your situation.
"""

import argparse
import math
import os
import sys
import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image

VERTS = (
    (0, 1, 3),  # Vertex indices for UL, UR, LL of top face matrix
    (0, 4, 1),  # " left
    (0, 3, 4),  # " front face
    (7, 3, 6),  # " right
    (2, 1, 6),  # " back
    (5, 4, 6),  # " bottom matrix
)

SQUARE_COORDS = (
    (-1, 1, 1),
    (-1, 1, -1),
    (1, 1, -1),
    (1, 1, 1),
    (-1, -1, 1),
    (-1, -1, -1),
    (1, -1, -1),
    (1, -1, 1),
)

# Alternate coordinates for a rotated cube with points at poles.
# Vertex indices are the same (does not need a new VERTS array),
# relationships are the same, the whole thing is just pivoted to
# "hang" from vertex 3 at top. I will NOT attempt ASCII art of this.
XX = (26.0 / 9.0) ** 0.5
YY = (3.0 ** 0.5) / 3.0
CC = -0.5  # cos(120.0 * M_PI / 180.0);
SS = 0.75 ** 0.5  # sin(120.0 * M_PI / 180.0);
POINTY_COORDS = (
    (-XX, YY, 0.0),  # Vertex 0 = leftmost point
    (XX * CC, -YY, -XX * SS),  # 1
    (-XX * CC, YY, -XX * SS),  # 2
    (0.0, 3.0 ** 0.5, 0.0),  # 3 = top
    (XX * CC, -YY, XX * SS),  # 4
    (0.0, -(3.0 ** 0.5), 0.0),  # 5 = bottom
    (XX, -YY, 0.0),  # 6 = rightmost point
    (-XX * CC, YY, XX * SS),  # 7
)


class Globe:
    """
    Revolving globe on a cube.
    """

    # pylint: disable=too-many-instance-attributes, too-many-locals
    def __init__(self):
        self.matrix = None  # RGB matrix object (initialized after inputs)
        self.canvas = None  # Offscreen canvas (after inputs)
        self.matrix_size = 0  # Matrix width/height in pixels (after inputs)
        self.run_time = -1.0  # If >0 (input can override), limit run time
        self.fade_time = 0.0  # Fade in/out time (input can override)
        self.max_brightness = 255  # Matrix brightness (input can override)
        self.samples_per_pixel = 1  # Total antialiasing samples per pixel
        self.map_width = 0  # Map image width in pixels
        self.map_data = None  # Map image pixel data in RAM
        self.longitude = None  # Table of longitude values
        self.latitude = None  # Table of latitude values
        self.imgbuf = None  # Image is rendered to this RGB buffer
        self.spin_time = 10.0
        self.chain_length = 6

    # pylint: disable=too-many-branches, too-many-statements
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
            "-i",
            action="store",
            help="Image filename for texture map. Default: maps/earth.jpg",
            default="maps/earth.jpg",
            type=str,
        )
        parser.add_argument(
            "-v",
            dest="pointy",
            help="Orient cube with vertices at top & bottom.",
            action="store_true",
        )
        parser.add_argument(
            "-s",
            action="store",
            help="Spin time in seconds/revolution. Default: 10.0",
            default=10.0,
            type=float,
        )
        parser.add_argument(
            "-a",
            action="store",
            help="Antialiasing samples/axis. Default: 1",
            default=1,
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
        parser.add_argument(
            "-e",
            action="store",
            help="Edge-to-edge measure of matrix.",
            default=1.0,
            type=float,
        )
        parser.add_argument(
            "-E",
            action="store",
            help="Edge-to-edge measure of opposite cube faces.",
            default=1.0,
            type=float,
        )

        parser.set_defaults(drop_privileges=True)
        parser.set_defaults(pointy=False)

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
        self.chain_length = args.led_chain
        self.max_brightness = args.led_brightness
        self.run_time = args.t
        self.fade_time = args.f
        self.samples_per_pixel = args.a * args.a
        matrix_measure = args.e
        cube_measure = args.E
        self.spin_time = args.s

        try:
            image = Image.open(args.i)
        except FileNotFoundError:
            print(
                os.path.basename(__file__)
                + ": error: image file "
                + args.i
                + " not found"
            )
            return True

        self.map_width = image.size[0]
        map_height = image.size[1]
        self.map_data = image.tobytes()

        # Longitude and latitude tables are 1-dimensional,
        # can do that because we iterate every pixel every frame.
        pixels = self.matrix.width * self.matrix.height
        subpixels = pixels * self.samples_per_pixel
        self.longitude = [0.0 for _ in range(subpixels)]
        self.latitude = [0 for _ in range(subpixels)]
        # imgbuf holds result for one face of cube
        self.imgbuf = bytearray(self.matrix_size * self.matrix_size * 3)

        coords = POINTY_COORDS if args.pointy else SQUARE_COORDS

        # Fill the longitude & latitude tables, one per subpixel.
        ll_index = 0  # Index into longitude[] and latitude[] arrays
        ratio = matrix_measure / cube_measure  # Scale ratio
        offset = ((1.0 - ratio) + ratio / (self.matrix_size * args.a)) * 0.5
        # Axis offset
        for face in range(6):
            upper_left = coords[VERTS[face][0]]
            upper_right = coords[VERTS[face][1]]
            lower_left = coords[VERTS[face][2]]
            for ypix in range(self.matrix_size):  # For each pixel Y...
                for xpix in range(self.matrix_size):  # For each pixel X...
                    for yaa in range(args.a):  # " antialiased sample Y...
                        yfactor = offset + ratio * (ypix * args.a + yaa) / (
                            self.matrix_size * args.a
                        )
                        for xaa in range(args.a):  # " antialiased sample X...
                            xfactor = offset + ratio * (xpix * args.a + xaa) / (
                                self.matrix_size * args.a
                            )
                            # Figure out the pixel's 3D position in space...
                            x3d = (
                                upper_left[0]
                                + (lower_left[0] - upper_left[0]) * yfactor
                                + (upper_right[0] - upper_left[0]) * xfactor
                            )
                            y3d = (
                                upper_left[1]
                                + (lower_left[1] - upper_left[1]) * yfactor
                                + (upper_right[1] - upper_left[1]) * xfactor
                            )
                            z3d = (
                                upper_left[2]
                                + (lower_left[2] - upper_left[2]) * yfactor
                                + (upper_right[2] - upper_left[2]) * xfactor
                            )
                            # Then convert to polar coords on a sphere...
                            self.longitude[ll_index] = (
                                (math.pi + math.atan2(-z3d, x3d))
                                / (math.pi * 2.0)
                                * self.map_width
                            ) % self.map_width
                            self.latitude[ll_index] = int(
                                (
                                    math.pi * 0.5
                                    - math.atan2(y3d, math.sqrt(x3d * x3d + z3d * z3d))
                                )
                                / math.pi
                                * map_height
                            )
                            ll_index += 1

        return False

    def run(self):
        """Main loop."""
        start_time, frames = time.monotonic(), 0

        while True:
            elapsed = time.monotonic() - start_time
            if self.run_time > 0:  # Handle fade in / fade out
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

            loffset = (
                (elapsed % abs(self.spin_time)) / abs(self.spin_time) * self.map_width
            )
            if self.spin_time > 0:
                loffset = self.map_width - loffset
            self.render(loffset)

            # Swap double-buffered canvas, show frames per second
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            frames += 1
            print(frames / (time.monotonic() - start_time))

    # pylint: disable=too-many-locals
    def render(self, loffset):
        """Render one frame of the globe animation, taking latitude offset
        as input."""
        # Certain instance variables (ones referenced in inner loop) are
        # copied to locals to speed up access. This is kind of a jerk thing
        # to do and not "Pythonic," but anything for a boost in this code.
        imgbuf = self.imgbuf
        map_data = self.map_data
        lon = self.longitude
        lat = self.latitude
        samples = self.samples_per_pixel
        map_width = self.map_width
        ll_index = 0  # Index into longitude/latitude tables
        for face in range(6):
            img_index = 0  # Index into imgbuf[]
            for _ in range(self.matrix_size * self.matrix_size):
                red = green = blue = 0
                for _ in range(samples):
                    map_index = (
                        lat[ll_index] * map_width
                        + (int(lon[ll_index] + loffset) % map_width)
                    ) * 3
                    red += map_data[map_index]
                    green += map_data[map_index + 1]
                    blue += map_data[map_index + 2]
                    ll_index += 1
                imgbuf[img_index] = red // samples
                imgbuf[img_index + 1] = green // samples
                imgbuf[img_index + 2] = blue // samples
                img_index += 3
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


# pylint: disable=superfluous-parens
if __name__ == "__main__":
    globe = Globe()
    if not (status := globe.setup()):
        try:
            print("Press CTRL-C to stop")
            globe.run()
        except KeyboardInterrupt:
            print("Exiting\n")
    sys.exit(status)
