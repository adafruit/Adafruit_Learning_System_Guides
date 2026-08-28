# SPDX-FileCopyrightText: 2026 Erin St Blaine for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""Three-spoke CircuitPython bike wheel persistence-of-vision display."""

import gc
import os
import time
from array import array

import adafruit_imageload
import adafruit_pioasm
import adafruit_tmag5273
import board
import rp2pio


# ---------------------------------------------------------------------------
# DISPLAY SETTINGS
# ---------------------------------------------------------------------------

NUM_LEDS = 36
IMAGE_FOLDER = "/img"
IMAGE_SECONDS = 8.0

# Approximate angular resolution of the wheel display.
#
# Examples:
#   36 px wide  -> 4 repeats per revolution
#   72 px wide  -> 2 repeats per revolution
#   144 px wide -> 1 repeat per revolution
SCANLINES_PER_REVOLUTION = 144

# Keep playback fast enough for clean POV at lower wheel speeds.
MIN_SCANLINES_PER_SECOND = 400.0

# 1.0 corrects the measured phase error over roughly one revolution.
STABILIZATION_STRENGTH = 1.0

# Rotate the entire pattern relative to the Hall sensor magnet.
PATTERN_ROTATION_DEGREES = 30.0

# DotStar global brightness: 0-31.
DOTSTAR_BRIGHTNESS = 10

PIO_FREQUENCY = 8_000_000


# ---------------------------------------------------------------------------
# HALL SENSOR SETTINGS
# ---------------------------------------------------------------------------

MAG_TRIGGER = 800.0
MAG_RELEASE = 450.0

MAG_TRIGGER_SQ = MAG_TRIGGER * MAG_TRIGGER
MAG_RELEASE_SQ = MAG_RELEASE * MAG_RELEASE

MIN_REVOLUTION_MS = 120

HALL_CLEAR_MS = 50
HALL_CLEAR_NS = HALL_CLEAR_MS * 1_000_000

START_CONFIRM_SECONDS = 1.5
START_CONFIRM_NS = int(START_CONFIRM_SECONDS * 1_000_000_000)

SENSOR_POLL_MS = 4
SENSOR_POLL_NS = SENSOR_POLL_MS * 1_000_000

STOP_TIMEOUT_SECONDS = 2.0
STOP_REVOLUTION_MULTIPLIER = 2.5

STARTING_RPM = 110.0
STARTING_REV_NS = int(60_000_000_000 / STARTING_RPM)

REV_SMOOTHING = 1.0

PRINT_RPM = False


# ---------------------------------------------------------------------------
# PIO
#
# A1, A2 and A3 drive the three physical spokes.
# Each data line feeds the matching strip on both sides of the wheel.
# All six DotStar strips share SCK.
# ---------------------------------------------------------------------------

PIO_PROGRAM = """
.program dotstar_three_spokes
.side_set 1
.wrap_target
    out pins, 3 side 0
    nop         side 1
.wrap
"""

assembled = adafruit_pioasm.assemble(PIO_PROGRAM)

state_machine = rp2pio.StateMachine(
    assembled,
    frequency=PIO_FREQUENCY,
    first_out_pin=board.A1,
    out_pin_count=3,
    first_sideset_pin=board.SCK,
    sideset_pin_count=1,
    auto_pull=True,
    pull_threshold=24,
    out_shift_right=True,
    initial_out_pin_state=0,
    initial_out_pin_direction=0b111,
    initial_sideset_pin_state=0,
    initial_sideset_pin_direction=1,
)


# ---------------------------------------------------------------------------
# TMAG5273 HALL SENSOR
# ---------------------------------------------------------------------------

i2c = board.STEMMA_I2C()
tmag = adafruit_tmag5273.TMAG5273(i2c)

tmag.magnetic_channels = adafruit_tmag5273.MAG_CH_XYZ
tmag.conversion_average = adafruit_tmag5273.CONV_AVG_1X
tmag.operating_mode = adafruit_tmag5273.MODE_CONTINUOUS


# ---------------------------------------------------------------------------
# DOTSTAR DATA PACKING
# ---------------------------------------------------------------------------


def make_pin_table(pin_number):
    """Build packed PIO values for one DotStar data pin."""
    table = array("I", [0] * 256)

    for value in range(256):
        packed = 0

        for position in range(8):
            source_bit = 7 - position

            if value & (1 << source_bit):
                packed |= 1 << ((position * 3) + pin_number)

        table[value] = packed

    return table


PIN_A_BYTES = make_pin_table(0)
PIN_B_BYTES = make_pin_table(1)
PIN_C_BYTES = make_pin_table(2)


def pack_three_bytes(value_a, value_b, value_c):
    """Pack one byte for each of the three DotStar outputs."""
    return (
        PIN_A_BYTES[value_a]
        | PIN_B_BYTES[value_b]
        | PIN_C_BYTES[value_c]
    )


BRIGHTNESS_BYTE = 0xE0 | DOTSTAR_BRIGHTNESS

PACKED_BRIGHTNESS = pack_three_bytes(
    BRIGHTNESS_BYTE,
    BRIGHTNESS_BYTE,
    BRIGHTNESS_BYTE,
)

PACKED_END = pack_three_bytes(0xFF, 0xFF, 0xFF)

FRAME_WORDS = 4 + (NUM_LEDS * 4) + 4


# ---------------------------------------------------------------------------
# IMAGE HELPERS
# ---------------------------------------------------------------------------


def find_images():
    """Return all GIF and BMP files found in the image folder."""
    try:
        filenames = os.listdir(IMAGE_FOLDER)
    except OSError:
        return []

    images = []

    for filename in filenames:
        if filename.startswith("."):
            continue

        lower_name = filename.lower()

        if lower_name.endswith((".gif", ".bmp")):
            images.append(filename)

    images.sort()

    return images


def pixel_color(bitmap, shader, x_position, y_position):
    """Return one source pixel as 0xRRGGBB."""
    pixel_value = bitmap[x_position, y_position]

    try:
        return int(shader[pixel_value]) & 0xFFFFFF
    except TypeError:
        pass

    try:
        return int(shader.convert(pixel_value)) & 0xFFFFFF
    except (AttributeError, TypeError):
        pass

    return int(pixel_value) & 0xFFFFFF


def split_color(color):
    """Return red, green and blue values from a packed RGB color."""
    return (
        (color >> 16) & 0xFF,
        (color >> 8) & 0xFF,
        color & 0xFF,
    )


def pack_pixel_colors(color_a, color_b, color_c):
    """Pack three RGB colors into DotStar blue, green and red words."""
    rgb_a = split_color(color_a)
    rgb_b = split_color(color_b)
    rgb_c = split_color(color_c)

    return (
        pack_three_bytes(
            rgb_a[2],
            rgb_b[2],
            rgb_c[2],
        ),
        pack_three_bytes(
            rgb_a[1],
            rgb_b[1],
            rgb_c[1],
        ),
        pack_three_bytes(
            rgb_a[0],
            rgb_b[0],
            rgb_c[0],
        ),
    )


def calculate_repeats(width):
    """Return the number of image repeats for one wheel revolution."""
    repeats = int((SCANLINES_PER_REVOLUTION / width) + 0.5)

    return max(1, repeats)


def calculate_spoke_offsets(width, repeats):
    """Return source-image offsets for the three 120-degree spokes."""
    spoke_offset = int(round((repeats * width) / 3))

    return (
        0,
        spoke_offset % width,
        (spoke_offset * 2) % width,
    )


# ---------------------------------------------------------------------------
# IMAGE PREPACKING
# ---------------------------------------------------------------------------


def make_scanline_frame(bitmap, shader, x_position, spoke_offsets):
    """Build one complete DotStar frame for all three spokes."""
    frame = array("I", [0] * FRAME_WORDS)

    x_positions = (
        x_position,
        (x_position + spoke_offsets[1]) % bitmap.width,
        (x_position + spoke_offsets[2]) % bitmap.width,
    )

    index = 4

    for led_number in range(NUM_LEDS):
        source_y = (NUM_LEDS - 1) - led_number

        color_a = pixel_color(
            bitmap,
            shader,
            x_positions[0],
            source_y,
        )

        color_b = pixel_color(
            bitmap,
            shader,
            x_positions[1],
            source_y,
        )

        color_c = pixel_color(
            bitmap,
            shader,
            x_positions[2],
            source_y,
        )

        blue_word, green_word, red_word = pack_pixel_colors(
            color_a,
            color_b,
            color_c,
        )

        frame[index] = PACKED_BRIGHTNESS
        frame[index + 1] = blue_word
        frame[index + 2] = green_word
        frame[index + 3] = red_word

        index += 4

    frame[index] = PACKED_END
    frame[index + 1] = PACKED_END
    frame[index + 2] = PACKED_END
    frame[index + 3] = PACKED_END

    return frame


def load_image(filename):
    """Load one image and prepack it for fast POV playback."""
    path = IMAGE_FOLDER + "/" + filename

    gc.collect()

    bitmap, shader = adafruit_imageload.load(path)

    width = bitmap.width
    height = bitmap.height

    if height != NUM_LEDS:
        del bitmap
        del shader

        gc.collect()

        raise ValueError(
            f"Image must be exactly {NUM_LEDS} pixels high."
        )

    repeats = calculate_repeats(width)
    spoke_offsets = calculate_spoke_offsets(width, repeats)

    frames = []

    try:
        for x_position in range(width):
            frames.append(
                make_scanline_frame(
                    bitmap,
                    shader,
                    x_position,
                    spoke_offsets,
                )
            )

    except MemoryError as error:
        del frames
        del bitmap
        del shader

        gc.collect()

        raise MemoryError(
            f"Not enough RAM to prepack {filename}."
        ) from error

    del bitmap
    del shader

    gc.collect()

    return frames, width, repeats


# ---------------------------------------------------------------------------
# BLANK FRAME
# ---------------------------------------------------------------------------


def make_blank_frame():
    """Create one all-black DotStar frame."""
    frame = array("I", [0] * FRAME_WORDS)

    index = 4

    for _ in range(NUM_LEDS):
        frame[index] = PACKED_BRIGHTNESS
        frame[index + 1] = 0
        frame[index + 2] = 0
        frame[index + 3] = 0

        index += 4

    frame[index] = PACKED_END
    frame[index + 1] = PACKED_END
    frame[index + 2] = PACKED_END
    frame[index + 3] = PACKED_END

    return frame


BLANK_FRAME = make_blank_frame()


def blank_all():
    """Turn off all LED strips."""
    state_machine.write(BLANK_FRAME)


# ---------------------------------------------------------------------------
# IMAGE PLAYLIST
# ---------------------------------------------------------------------------

image_files = find_images()

if not image_files:
    raise RuntimeError("No GIF or BMP images found in /img.")

image_number = -1
scanline_frames = None
image_width = 0
image_repeats = 1


def load_next_usable_image():
    """Load the next image that can be successfully prepacked."""
    # pylint: disable=global-statement
    global image_number
    global scanline_frames
    global image_width
    global image_repeats

    if scanline_frames is not None:
        old_frames = scanline_frames
        scanline_frames = None

        del old_frames

        gc.collect()

    attempts = 0

    while attempts < len(image_files):
        image_number = (image_number + 1) % len(image_files)

        filename = image_files[image_number]

        try:
            (
                scanline_frames,
                image_width,
                image_repeats,
            ) = load_image(filename)

            print(
                "Now playing:",
                filename,
                "| width:",
                image_width,
                "| repeats:",
                image_repeats,
            )

            return

        except (
            MemoryError,
            ValueError,
            OSError,
            RuntimeError,
        ) as error:
            print()
            print("IMAGE SKIPPED")
            print("File:", filename)
            print("Error:", type(error).__name__)
            print("Reason:", error)
            print()

            attempts += 1

    raise RuntimeError("None of the images could be loaded.")


load_next_usable_image()


def send_scanline(line_number):
    """Send one prepacked scanline to the three physical spokes."""
    state_machine.write(scanline_frames[line_number])


# ---------------------------------------------------------------------------
# WHEEL TIMING
# ---------------------------------------------------------------------------

moving = False
magnet_active = False

last_sensor_ns = 0
last_magnet_ns = 0
last_revolution_ns = 0
magnet_clear_since_ns = 0
previous_valid_pass_ns = 0

valid_passes = 0

revolution_ns = STARTING_REV_NS

image_line = 0

scanline_period_ns = int(
    revolution_ns / (image_width * image_repeats)
)

now = time.monotonic_ns()

next_scanline_ns = now
image_change_ns = now


def update_scanline_timing():
    """Update POV scanline speed using the measured wheel revolution."""
    # pylint: disable=global-statement
    global scanline_period_ns

    total_lines = image_width * image_repeats

    target_line = int(
        round(
            (PATTERN_ROTATION_DEGREES / 360.0)
            * total_lines
        )
    ) % image_width

    phase_error = image_line - target_line

    if phase_error > image_width / 2:
        phase_error -= image_width

    elif phase_error < -(image_width / 2):
        phase_error += image_width

    correction = phase_error * STABILIZATION_STRENGTH

    corrected_lines = max(
        total_lines - correction,
        1,
    )

    hall_period_ns = int(
        revolution_ns / corrected_lines
    )

    minimum_rate_period_ns = int(
        1_000_000_000 / MIN_SCANLINES_PER_SECOND
    )

    scanline_period_ns = min(
        hall_period_ns,
        minimum_rate_period_ns,
    )


def update_magnet_state(now_ns, magnitude_sq):
    """Update magnet re-arm state."""
    # pylint: disable=global-statement
    global magnet_active
    global magnet_clear_since_ns

    if magnitude_sq <= MAG_RELEASE_SQ:
        if magnet_clear_since_ns == 0:
            magnet_clear_since_ns = now_ns

        if (
            magnet_active
            and now_ns - magnet_clear_since_ns
            >= HALL_CLEAR_NS
        ):
            magnet_active = False

    else:
        magnet_clear_since_ns = 0


def handle_magnet_pass(now_ns):
    """Process one valid Hall sensor magnet pass."""
    # pylint: disable=global-statement
    global last_magnet_ns
    global last_revolution_ns
    global previous_valid_pass_ns
    global valid_passes
    global revolution_ns
    global moving
    global next_scanline_ns
    global image_change_ns

    if (
        last_magnet_ns
        and now_ns - last_magnet_ns
        < MIN_REVOLUTION_MS * 1_000_000
    ):
        return

    last_magnet_ns = now_ns

    if last_revolution_ns:
        measured_ns = now_ns - last_revolution_ns

        revolution_ns = int(
            revolution_ns * (1.0 - REV_SMOOTHING)
            + measured_ns * REV_SMOOTHING
        )

        update_scanline_timing()

        if PRINT_RPM:
            rpm = 60_000_000_000.0 / revolution_ns
            print(f"RPM {rpm:.1f}")

    last_revolution_ns = now_ns

    if moving:
        return

    if (
        valid_passes == 0
        or now_ns - previous_valid_pass_ns
        > START_CONFIRM_NS
    ):
        valid_passes = 1

    else:
        valid_passes += 1

    previous_valid_pass_ns = now_ns

    if valid_passes >= 2:
        moving = True
        image_change_ns = now_ns
        next_scanline_ns = now_ns

        print("Wheel moving")


def check_hall(now_ns):
    """Poll the Hall sensor and update wheel speed."""
    # pylint: disable=global-statement
    global last_sensor_ns
    global magnet_active

    if now_ns - last_sensor_ns < SENSOR_POLL_NS:
        return

    last_sensor_ns = now_ns

    x_axis, y_axis, z_axis = tmag.magnetic

    magnitude_sq = (
        (x_axis * x_axis)
        + (y_axis * y_axis)
        + (z_axis * z_axis)
    )

    update_magnet_state(
        now_ns,
        magnitude_sq,
    )

    if (
        not magnet_active
        and magnitude_sq >= MAG_TRIGGER_SQ
    ):
        magnet_active = True

        handle_magnet_pass(now_ns)


# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------

blank_all()

print()
print("POV bike wheel ready.")
print("Images:", len(image_files))
print("Scanlines/revolution:", SCANLINES_PER_REVOLUTION)

while True:
    now = time.monotonic_ns()

    check_hall(now)

    # Stop after several missed Hall passes.
    if moving and last_magnet_ns:
        stop_timeout_ns = max(
            int(STOP_TIMEOUT_SECONDS * 1_000_000_000),
            int(
                revolution_ns
                * STOP_REVOLUTION_MULTIPLIER
            ),
        )

        if now - last_magnet_ns >= stop_timeout_ns:
            moving = False
            valid_passes = 0
            previous_valid_pass_ns = 0
            image_line = 0

            blank_all()

            print("Wheel stopped")

    if not moving:
        continue

    # Advance to the next image.
    if (
        len(image_files) > 1
        and now - image_change_ns
        >= int(IMAGE_SECONDS * 1_000_000_000)
    ):
        load_next_usable_image()

        image_line = 0

        update_scanline_timing()

        now = time.monotonic_ns()
        image_change_ns = now
        next_scanline_ns = now

        continue

    # Draw the next angular slice.
    if now >= next_scanline_ns:
        send_scanline(image_line)

        image_line += 1

        if image_line >= image_width:
            image_line = 0

        next_scanline_ns += scanline_period_ns

        # Skip stale frames instead of blasting through them after a delay.
        if now - next_scanline_ns > scanline_period_ns * 4:
            next_scanline_ns = now + scanline_period_ns
