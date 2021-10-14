# SPDX-FileCopyrightText: 2021 Phil Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
MOVE-AND-BLINK EYES for Adafruit EyeLights (LED Glasses + Driver).

I'd written a very cool squash-and-stretch effect for the eye movement,
but unfortunately the resolution and frame rate are such that the pupils
just look like circles regardless. I'm keeping it in despite the added
complexity, because CircuitPython devices WILL get faster, LED matrix
densities WILL improve, and this way the code won't require a re-write
at such a later time. It's a really adorable effect with enough pixels.
"""

import math
import random
import time
from supervisor import reload
import board
from busio import I2C
import adafruit_is31fl3741
from adafruit_is31fl3741.adafruit_ledglasses import LED_Glasses


# CONFIGURABLES ------------------------

eye_color = (255, 128, 0)  #      Amber pupils
ring_open_color = (75, 75, 75)  # Color of LED rings when eyes open
ring_blink_color = (50, 25, 0)  # Color of LED ring "eyelid" when blinking

radius = 3.4  # Size of pupil (3X because of downsampling later)

# Reading through the code, you'll see a lot of references to this "3X"
# space. What it's referring to is a bitmap that's 3 times the resolution
# of the LED matrix (i.e. 15 pixels tall instead of 5), which gets scaled
# down to provide some degree of antialiasing. It's why the pupils have
# soft edges and can make fractional-pixel motions.
# Because of the way the downsampling is done, the eyelid edge when drawn
# across the eye will always be the same hue as the pupils, it can't be
# set independently like the ring blink color.

gamma = 2.6  # For color adjustment. Leave as-is.


# CLASSES & FUNCTIONS ------------------


class Eye:
    """Holds per-eye positional data; each covers a different area of the
    overall LED matrix."""

    def __init__(self, left, xoff):
        self.left = left  #     Leftmost column on LED matrix
        self.x_offset = xoff  # Horizontal offset (3X space) to fixate

    def smooth(self, data, rect):
        """Scale bitmap (in 'data') to LED array, with smooth 1:3
        downsampling. 'rect' is a 4-tuple rect of which pixels get
        filtered (anything outside is cleared to 0), saves a few cycles."""
        # Quantize bounds rect from 3X space to LED matrix space.
        rect = (
            rect[0] // 3,  #       Left
            rect[1] // 3,  #       Top
            (rect[2] + 2) // 3,  # Right
            (rect[3] + 2) // 3,  # Bottom
        )
        for y in range(rect[1]):  # Erase rows above top
            for x in range(6):
                glasses.pixel(self.left + x, y, 0)
        for y in range(rect[1], rect[3]):  #  Each row, top to bottom...
            pixel_sum = bytearray(6)  #  Initialize row of pixel sums to 0
            for y1 in range(3):  # 3 rows of bitmap...
                row = data[y * 3 + y1]  # Bitmap data for current row
                for x in range(rect[0], rect[2]):  # Column, left to right
                    x3 = x * 3
                    # Accumulate 3 pixels of bitmap into pixel_sum
                    pixel_sum[x] += row[x3] + row[x3 + 1] + row[x3 + 2]
            # 'pixel_sum' will now contain values from 0-9, indicating the
            # number of set pixels in the corresponding section of the 3X
            # bitmap. 'colormap' expands the sum to 24-bit RGB space.
            for x in range(rect[0]):  # Erase any columns to left
                glasses.pixel(self.left + x, y, 0)
            for x in range(rect[0], rect[2]):  # Column, left to right
                glasses.pixel(self.left + x, y, colormap[pixel_sum[x]])
            for x in range(rect[2], 6):  # Erase columns to right
                glasses.pixel(self.left + x, y, 0)
        for y in range(rect[3], 5):  # Erase rows below bottom
            for x in range(6):
                glasses.pixel(self.left + x, y, 0)


# pylint: disable=too-many-locals
def rasterize(data, point1, point2, rect):
    """Rasterize an arbitrary ellipse into the 'data' bitmap (3X pixel
    space), given foci point1 and point2 and with area determined by global
    'radius' (when foci are same point; a circle). Foci and radius are all
    floating point values, which adds to the buttery impression. 'rect' is
    a 4-tuple rect of which pixels are likely affected. Data is assumed 0
    before arriving here; no clearing is performed."""

    dx = point2[0] - point1[0]
    dy = point2[1] - point1[1]
    d2 = dx * dx + dy * dy  # Dist between foci, squared
    if d2 <= 0:
        # Foci are in same spot - it's a circle
        perimeter = 2 * radius
        d = 0
    else:
        # Foci are separated - it's an ellipse.
        d = d2 ** 0.5  # Distance between foci
        c = d * 0.5  # Center-to-foci distance
        # This is an utterly brute-force way of ellipse-filling based on
        # the "two nails and a string" metaphor...we have the foci points
        # and just need the string length (triangle perimeter) to yield
        # an ellipse with area equal to a circle of 'radius'.
        # c^2 = a^2 - b^2  <- ellipse formula
        #   a = r^2 / b    <- substitute
        # c^2 = (r^2 / b)^2 - b^2
        # b = sqrt(((c^2) + sqrt((c^4) + 4 * r^4)) / 2)  <- solve for b
        b2 = ((c ** 2) + (((c ** 4) + 4 * (radius ** 4)) ** 0.5)) * 0.5
        # By my math, perimeter SHOULD be...
        # perimeter = d + 2 * ((b2 + (c ** 2)) ** 0.5)
        # ...but for whatever reason, working approach here is really...
        perimeter = d + 2 * (b2 ** 0.5)

    # Like I'm sure there's a way to rasterize this by spans rather than
    # all these square roots on every pixel, but for now...
    for y in range(rect[1], rect[3]):  # For each row...
        y5 = y + 0.5  #         Pixel center
        dy1 = y5 - point1[1]  # Y distance from pixel to first point
        dy2 = y5 - point2[1]  # " to second
        dy1 *= dy1  # Y1^2
        dy2 *= dy2  # Y2^2
        for x in range(rect[0], rect[2]):  # For each column...
            x5 = x + 0.5  #         Pixel center
            dx1 = x5 - point1[0]  # X distance from pixel to first point
            dx2 = x5 - point2[0]  # " to second
            d1 = (dx1 * dx1 + dy1) ** 0.5  # 2D distance to first point
            d2 = (dx2 * dx2 + dy2) ** 0.5  # " to second
            if (d1 + d2 + d) <= perimeter:
                data[y][x] = 1  # Point is inside ellipse


def gammify(color):
    """Given an (R,G,B) color tuple, apply gamma correction and return
    a packed 24-bit RGB integer."""
    rgb = [int(((color[x] / 255) ** gamma) * 255 + 0.5) for x in range(3)]
    return (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]


def interp(color1, color2, blend):
    """Given two (R,G,B) color tuples and a blend ratio (0.0 to 1.0),
    interpolate between the two colors and return a gamma-corrected
    in-between color as a packed 24-bit RGB integer. No bounds clamping
    is performed on blend value, be nice."""
    inv = 1.0 - blend  # Weighting of second color
    return gammify([color1[x] * blend + color2[x] * inv for x in range(3)])


# HARDWARE SETUP -----------------------

# Manually declare I2C (not board.I2C() directly) to access 1 MHz speed...
i2c = I2C(board.SCL, board.SDA, frequency=1000000)

# Initialize the IS31 LED driver, buffered for smoother animation
glasses = LED_Glasses(i2c, allocate=adafruit_is31fl3741.MUST_BUFFER)
glasses.show()  # Clear any residue on startup
glasses.global_current = 20  # Just middlin' bright, please


# INITIALIZE TABLES & OTHER GLOBALS ----

# This table is for mapping 3x3 averaged bitmap values (0-9) to
# RGB colors. Avoids a lot of shift-and-or on every pixel.
colormap = []
for n in range(10):
    colormap.append(gammify([n / 9 * eye_color[x] for x in range(3)]))

# Pre-compute the Y position of 1/2 of the LEDs in a ring, relative
# to the 3X bitmap resolution, so ring & matrix animation can be aligned.
y_pos = []
for n in range(13):
    angle = n / 24 * math.pi * 2
    y_pos.append(10 - math.cos(angle) * 12)

# Pre-compute color of LED ring in fully open (unblinking) state
ring_open_color_packed = gammify(ring_open_color)

# A single pre-computed scanline of "eyelid edge during blink" can be
# stuffed into the 3X raster as needed, avoids setting pixels manually.
eyelid = (
    b"\x01\x01\x00\x01\x01\x00\x01\x01\x00" b"\x01\x01\x00\x01\x01\x00\x01\x01\x00"
)  # 2/3 of pixels set

# Initialize eye position and move/blink animation timekeeping
cur_pos = next_pos = (9, 7.5)  # Current, next eye position in 3X space
in_motion = False  #             True = eyes moving, False = eyes paused
blink_state = 0  #               0, 1, 2 = unblinking, closing, opening
move_start_time = move_duration = blink_start_time = blink_duration = 0

# Two eye objects. The first starts at column 1 of the matrix with its
# pupil offset by +2 (in 3X space), second at column 11 with -2 offset.
# The offsets make the pupils fixate slightly (converge on a point), so
# the two pupils aren't always aligned the same on the pixel grid, which
# would be conspicuously pixel-y.
eyes = [Eye(1, 2), Eye(11, -2)]

frames, start_time = 0, time.monotonic()  # For frames/second calculation


# MAIN LOOP ----------------------------

while True:
    # The try/except here is because VERY INFREQUENTLY the I2C bus will
    # encounter an error when accessing the LED driver, whether from bumping
    # around the wires or sometimes an I2C device just gets wedged. To more
    # robustly handle the latter, the code will restart if that happens.
    try:

        # The eye animation logic is a carry-over from like a billion
        # prior eye projects, so this might be comment-light.
        now = time.monotonic()  # 'Snapshot' the time once per frame

        # Blink logic
        elapsed = now - blink_start_time  # Time since start of blink event
        if elapsed > blink_duration:  #     All done with event?
            blink_start_time = now  #       A new one starts right now
            elapsed = 0
            blink_state += 1  #             Cycle closing/opening/paused
            if blink_state == 1:  #         Starting new blink...
                blink_duration = random.uniform(0.06, 0.12)
            elif blink_state == 2:  #       Switching closing to opening...
                blink_duration *= 2  #      Opens at half the speed
            else:  #                        Switching to pause in blink
                blink_state = 0
                blink_duration = random.uniform(0.5, 4)
        if blink_state:  #                  If currently in a blink...
            ratio = elapsed / blink_duration  # 0.0-1.0 as it closes
            if blink_state == 2:
                ratio = 1.0 - ratio  #          1.0-0.0 as it opens
            upper = ratio * 15 - 4  #       Upper eyelid pos. in 3X space
            lower = 23 - ratio * 8  #       Lower eyelid pos. in 3X space

        # Eye movement logic. Two points, 'p1' and 'p2', are the foci of an
        # ellipse. p1 moves from current to next position a little faster
        # than p2, creating a "squash and stretch" effect (frame rate and
        # resolution permitting). When motion is stopped, the two points
        # are at the same position.
        elapsed = now - move_start_time  # Time since start of move event
        if in_motion:  #                   Currently moving?
            if elapsed > move_duration:  # If end of motion reached,
                in_motion = False  #            Stop motion and
                p1 = p2 = cur_pos = next_pos  # Set to new position
                move_duration = random.uniform(0.5, 1.5)  # Wait this long
            else:  # Still moving
                # Determine p1, p2 position in time
                delta = (next_pos[0] - cur_pos[0], next_pos[1] - cur_pos[1])
                ratio = elapsed / move_duration
                if ratio < 0.6:  # First 60% of move time
                    # p1 is in motion
                    # Easing function: 3*e^2-2*e^3 0.0 to 1.0
                    e = ratio / 0.6  # 0.0 to 1.0
                    e = 3 * e * e - 2 * e * e * e
                    p1 = (cur_pos[0] + delta[0] * e, cur_pos[1] + delta[1] * e)
                else:  # Last 40% of move time
                    p1 = next_pos  # p1 has reached end position
                if ratio > 0.3:  # Last 60% of move time
                    # p2 is in motion
                    e = (ratio - 0.3) / 0.7  #       0.0 to 1.0
                    e = 3 * e * e - 2 * e * e * e  # Easing func.
                    p2 = (cur_pos[0] + delta[0] * e, cur_pos[1] + delta[1] * e)
                else:  # First 40% of move time
                    p2 = cur_pos  # p2 waits at start position
        else:  # Eye is stopped
            p1 = p2 = cur_pos  # Both foci at current eye position
            if elapsed > move_duration:  # Pause time expired?
                in_motion = True  #        Start up new motion!
                move_start_time = now
                move_duration = random.uniform(0.15, 0.25)
                angle = random.uniform(0, math.pi * 2)
                dist = random.uniform(0, 7.5)
                next_pos = (
                    9 + math.cos(angle) * dist,
                    7.5 + math.sin(angle) * dist * 0.8,
                )

        # Draw the raster part of each eye...
        for eye in eyes:
            # Allocate/clear the 3X bitmap buffer
            bitmap = [bytearray(6 * 3) for _ in range(5 * 3)]
            # Each eye's foci are offset slightly, to fixate toward center
            p1a = (p1[0] + eye.x_offset, p1[1])
            p2a = (p2[0] + eye.x_offset, p2[1])
            # Compute bounding rectangle (in 3X space) of ellipse
            # (min X, min Y, max X, max Y). Like the ellipse rasterizer,
            # this isn't optimal, but will suffice.
            bounds = (
                max(int(min(p1a[0], p2a[0]) - radius), 0),
                max(int(min(p1a[1], p2a[1]) - radius), 0, int(upper)),
                min(int(max(p1a[0], p2a[0]) + radius + 1), 18),
                min(int(max(p1a[1], p2a[1]) + radius + 1), 15, int(lower) + 1),
            )
            rasterize(bitmap, p1a, p2a, bounds)  # Render ellipse into buffer
            # If the eye is currently blinking, and if the top edge of the
            # eyelid overlaps the bitmap, draw a scanline across the bitmap
            # and update the bounds rect so the whole width of the bitmap
            # is scaled.
            if blink_state and upper >= 0:
                bitmap[int(upper)] = eyelid
                bounds = (0, int(upper), 18, bounds[3])
            eye.smooth(bitmap, bounds)  # 1:3 downsampling for eye

        # Matrix and rings share a few pixels. To make the rings take
        # precedence, they're drawn later. So blink state is revisited now...
        if blink_state:  # In mid-blink?
            for i in range(13):  # Half an LED ring, top-to-bottom...
                a = min(max(y_pos[i] - upper + 1, 0), 3)
                b = min(max(lower - y_pos[i] + 1, 0), 3)
                ratio = a * b / 9  # Proximity of LED to eyelid edges
                packed = interp(ring_open_color, ring_blink_color, ratio)
                glasses.left_ring[i] = glasses.right_ring[i] = packed
                if 0 < i < 12:
                    i = 24 - i  # Mirror half-ring to other side
                    glasses.left_ring[i] = glasses.right_ring[i] = packed
        else:
            glasses.left_ring.fill(ring_open_color_packed)
            glasses.right_ring.fill(ring_open_color_packed)

        glasses.show()  # Buffered mode MUST use show() to refresh matrix

    except OSError:  # See "try" notes above regarding rare I2C errors.
        print("Restarting")
        reload()

    frames += 1
    elapsed = time.monotonic() - start_time
    print(frames / elapsed)
