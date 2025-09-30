# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# FFT calculations based on Phil B.'s Audio Spectrum Light Show Code
# https://github.com/adafruit/Adafruit_Learning_System_Guides/blob/main/
# Feather_Sense_Audio_Visualizer_13x9_RGB_LED_Matrix/audio_spectrum_lightshow/code.py

from array import array
from math import cos, log, sin, pi
from random import randint, choice
import board
import keypad
from audiobusio import PDMIn
import displayio
import picodvi
import framebufferio
import vectorio
import adafruit_imageload
from analogio import AnalogIn
from adafruit_display_shapes.polygon import Polygon
from digitalio import DigitalInOut, Direction
import simpleio
from ulab import numpy as np
try:
    from ulab.utils import spectrogram
except ImportError:
    from ulab.scipy.signal import spectrogram

# ------ PICODVI SETUP ------
displayio.release_displays()
fb = picodvi.Framebuffer(320, 240, clk_dp=board.CKP, clk_dn=board.CKN,
                         red_dp=board.D0P, red_dn=board.D0N,
                         green_dp=board.D1P, green_dn=board.D1N,
                         blue_dp=board.D2P, blue_dn=board.D2N,
                         color_depth=8)
display = framebufferio.FramebufferDisplay(fb, auto_refresh=False)

# ------ SHARED VARIABLES ------
fft_size = 512
low_bin = 15
high_bin = 75
low_band = (15, 75)
mid_band = (100, 120)
spectrum_size = fft_size // 2
spectrum_bits = log(spectrum_size, 2)
mode = 0
new_mode = True
states = {}

# ------ PDM MIC ------
mic = PDMIn(board.D6, board.D7, sample_rate=44100, bit_depth=16)
rec_buf = array("H", [0] * fft_size)

# ------ POTENTIOMETER SETUP ------
pot1 = AnalogIn(board.A0)
read_pots = True
# ------ POTENTIOMETER MODE VALUES ------
mode0_values = [0, 0, 0]
mode1_values = [0, 0, 0]
mode2_values = [0, 0, 0]
mode_vals = [0, 0, 0]
# ------ POTENTIOMETER READ FUNCTION ------
def val(pin):
    return pin.value

# ------ SWITCH SETUP ------
keys = keypad.Keys((board.A1, board.A3), value_when_pressed=False, pull=True)

# ------ LED SETUP ------
led_0 = DigitalInOut(board.A2)
led_0.direction = Direction.OUTPUT
led_1 = DigitalInOut(board.A4)
led_1.direction = Direction.OUTPUT

leds = [led_0, led_1]

# pylint: disable=too-many-locals, global-statement, too-many-statements, global-variable-not-assigned
# pylint: disable=too-many-nested-blocks, too-many-branches, too-many-lines

def initialize_party(freq):
    global states
    spectrum_group = displayio.Group()
    display.root_group = spectrum_group

    low_frac = log(low_bin, 2) / spectrum_bits
    frac_range = log(high_bin, 2) / spectrum_bits - low_frac
    num_columns = freq
    column_table = []
    moving_avg_buffer = [0] * num_columns
    smoothing_factor = 0.3
    dynamic_level = 10
    noise_floor = 3.1

    # Threshold for triggering frame advance (0-1 range, adjust as needed)
    trigger_threshold = 0.1
    # Frames to advance when triggered
    frames_per_trigger = 1
    # Cooldown frames between advances
    frame_cooldown = 1

    # Load the bitmap
    bitmap, palette = adafruit_imageload.load(
        "/partyParrotsXtraSmol.bmp",
        bitmap=displayio.Bitmap,
        palette=displayio.Palette
    )

    # Create 16 parrot grids arranged in a 4x4 layout
    parrot_grids = []
    grid_size = 32  # Tile size
    grid_cols = int(freq ** 0.5)
    grid_rows = int(freq ** 0.5)

    # Calculate spacing to center the grid
    total_width = grid_cols * grid_size
    total_height = grid_rows * grid_size
    start_x = (display.width - total_width) // 2
    start_y = (display.height - total_height) // 2

    for i in range(num_columns):
        row = i // grid_cols
        col = i % grid_cols

        parrot_grid = displayio.TileGrid(
            bitmap,
            width=1,
            height=1,
            pixel_shader=palette,
            tile_height=grid_size,
            tile_width=grid_size,
            x=start_x + col * grid_size,
            y=start_y + row * grid_size
        )
        parrot_grids.append(parrot_grid)
        spectrum_group.append(parrot_grid)

    # Initialize frame tracking for each bitmap
    frame_indices = [0] * num_columns
    frame_cooldowns = [0] * num_columns

    # Build frequency mapping table (same as original)
    for column in range(num_columns):
        lower = low_frac + frac_range * (column / num_columns * 0.95)
        upper = low_frac + frac_range * ((column + 1) / num_columns)
        mid = (lower + upper) * 0.5
        half_width = (upper - lower) * 0.5
        first_bin = int(2 ** (spectrum_bits * lower) + 1e-4)
        last_bin = int(2 ** (spectrum_bits * upper) + 1e-4)
        bin_weights = []
        for bin_index in range(first_bin, last_bin + 1):
            bin_center = log(bin_index + 0.5, 2) / spectrum_bits
            dist = abs(bin_center - mid) / half_width
            if dist < 1.0:
                dist = 1.0 - dist
                bin_weights.append(((3.0 - (dist * 2.0)) * dist) * dist)
        total = sum(bin_weights)
        bin_weights = [
            (weight / total) * (0.8 + idx / num_columns * 1.4)
            for idx, weight in enumerate(bin_weights)
        ]
        column_table.append([first_bin - low_bin, bin_weights])

    states = {
        "spectrum_group": spectrum_group,
        "parrot_grids": parrot_grids,
        "frame_indices": frame_indices,
        "frame_cooldowns": frame_cooldowns,
        "column_table": column_table,
        "moving_avg_buffer": moving_avg_buffer,
        "smoothing_factor": smoothing_factor,
        "dynamic_level": dynamic_level,
        "noise_floor": noise_floor,
        "num_columns": num_columns,
        "trigger_threshold": trigger_threshold,
        "frames_per_trigger": frames_per_trigger,
        "frame_cooldown": frame_cooldown,
        "total_frames": 10,
        "bounce_counter": 0,
        "bounce_phase": 0,
        "bounce_amplitude": 8,
        "bounce_speed": 0.1,
        "start_x": start_x,
        "start_y": start_y,
        "grid_size": 32,
        "grid_cols": grid_cols,
        "grid_rows": grid_rows,
    }

# ------ BITMAP ANIMATION ------
def party(pos, read):
    global states
    if read:
        # Optionally adjust parameters based on knob positions
        states["noise_floor"] = pos

    parrot_grids = states["parrot_grids"]
    frame_indices = states["frame_indices"]
    frame_cooldowns = states["frame_cooldowns"]
    column_table = states["column_table"]
    moving_avg_buffer = states["moving_avg_buffer"]
    smoothing_factor = states["smoothing_factor"]
    dynamic_level = states["dynamic_level"]
    noise_floor = states["noise_floor"]
    num_columns = states["num_columns"]
    trigger_threshold = states["trigger_threshold"]
    frames_per_trigger = states["frames_per_trigger"]
    frame_cooldown = states["frame_cooldown"]
    total_frames = states["total_frames"]
    # Update bounce animation
    bounce_counter = states["bounce_counter"]
    bounce_phase = states["bounce_phase"]
    bounce_amplitude = states["bounce_amplitude"]
    bounce_speed = states["bounce_speed"]
    start_x = states["start_x"]
    start_y = states["start_y"]
    grid_size = states["grid_size"]
    grid_cols = states["grid_cols"]

    # Record and analyze audio
    mic.record(rec_buf, fft_size)
    samples = np.array(rec_buf)

    spectrum = spectrogram(samples)[low_bin : high_bin + 1]
    spectrum = np.log(spectrum + 1e-7)
    spectrum = np.maximum(spectrum - noise_floor, 0)
    lower = max(np.min(spectrum), 4)
    upper = min(max(np.max(spectrum), lower + 12), 20)

    # Dynamic level adjustment
    if upper > dynamic_level:
        dynamic_level = upper * 0.7 + dynamic_level * 0.3
    else:
        dynamic_level = dynamic_level * 0.5 + lower * 0.5
    states["dynamic_level"] = dynamic_level

    # Normalize spectrum data
    data = (spectrum - lower) / (dynamic_level - lower)

    # Process each frequency band
    for column in range(num_columns):
        element = column_table[column]
        first_bin = element[0]
        bin_weights = element[1]

        # Calculate weighted intensity for this frequency band
        intensity = 0
        for bin_offset, weight in enumerate(bin_weights):
            if first_bin + bin_offset < len(data):
                intensity += data[first_bin + bin_offset] * weight

        # Apply smoothing
        moving_avg_buffer[column] = (
            moving_avg_buffer[column] * (1 - smoothing_factor) +
            intensity * smoothing_factor
        )
        smoothed_intensity = moving_avg_buffer[column]

        # Update cooldown
        if frame_cooldowns[column] > 0:
            frame_cooldowns[column] -= 1

        # Check if we should advance the frame
        if smoothed_intensity > trigger_threshold and frame_cooldowns[column] == 0:
            # Advance frame
            frame_indices[column] = (frame_indices[column] + frames_per_trigger) % total_frames
            parrot_grids[column][0] = frame_indices[column]
            # Set cooldown
            frame_cooldowns[column] = frame_cooldown

    # Calculate bounce offset using sine wave
    bounce_offset = int(sin(bounce_counter) * bounce_amplitude)

    # Update positions based on phase
    for i, parrot in enumerate(parrot_grids):
        row = i // grid_cols
        col = i % grid_cols
        base_x = start_x + col * grid_size
        base_y = start_y + row * grid_size

        if bounce_phase == 0:  # Rows bounce horizontally
            # Even rows go right, odd rows go left
            if row % 2 == 0:
                parrot.x = base_x + bounce_offset
            else:
                parrot.x = base_x - bounce_offset
            parrot.y = base_y
        else:  # Columns bounce vertically
            # Even columns go up, odd columns go down
            if col % 2 == 0:
                parrot.y = base_y - bounce_offset
            else:
                parrot.y = base_y + bounce_offset
            parrot.x = base_x

    # Update counter
    bounce_counter += bounce_speed
    states["bounce_counter"] = bounce_counter

    # Check if we've completed a full bounce cycle
    if bounce_counter >= pi * 2:
        bounce_counter = 0
        states["bounce_counter"] = 0
        # Switch phase
        states["bounce_phase"] = 1 - bounce_phase

    display.refresh()

# ------ DIAMOND PATTERN INIT ------
def initialize_diamond(dia_count):
    global states

    spectrum_group = displayio.Group()
    display.root_group = spectrum_group

    # Create palette with colors
    palette = displayio.Palette(8)
    palette[0] = 0x000000  # Black background
    palette[1] = 0xFF0000  # Red
    palette[2] = 0xFF7F00  # Orange
    palette[3] = 0xFFFF00  # Yellow
    palette[4] = 0x00FF00  # Green
    palette[5] = 0x0000FF  # Blue
    palette[6] = 0xFF00FF  # Magenta
    palette[7] = 0xFFFFFF  # White

    # Create background
    background = displayio.Bitmap(display.width, display.height, 8)
    background.fill(0)
    bg_sprite = displayio.TileGrid(background, pixel_shader=palette)
    spectrum_group.append(bg_sprite)

    # Diamond parameters
    center_x = display.width // 2
    center_y = display.height // 2
    base_width = 30
    base_height = 50

    # Side diamonds are half the size
    side_base_width = base_width // 2
    side_base_height = base_height // 2
    orbit_radius = 85  # Distance from center

    # Create center diamond
    center_initial_points = [
        (center_x, center_y - base_height),  # Top
        (center_x + base_width, center_y),    # Right
        (center_x, center_y + base_height),  # Bottom
        (center_x - base_width, center_y),    # Left
    ]

    center_diamond = Polygon(
        points=center_initial_points,
        outline=palette[3],  # Yellow outline
        stroke=2
    )
    spectrum_group.append(center_diamond)

    # Initialize with 2 side diamonds
    num_side_diamonds = dia_count

    # Create new side diamonds
    new_diamonds = []
    # Initialize color indices for new diamonds
    new_color_indices = []
    for i in range(num_side_diamonds):
        angle = (2 * pi * i) / num_side_diamonds  # Start from right (0 radians)
        x = center_x + int(cos(angle) * orbit_radius)
        y = center_y + int(sin(angle) * orbit_radius)

        points = [
            (x, y - side_base_height),  # Top
            (x + side_base_width, y),    # Right
            (x, y + side_base_height),  # Bottom
            (x - side_base_width, y),    # Left
        ]

        # Determine color based on position/angle
        # Normalize angle to 0-360 degrees for easier logic
        angle_deg = (angle * 180 / pi) % 360

        # Right (0°) and Left (180°) - original pair
        if abs(angle_deg - 0) < 10 or abs(angle_deg - 180) < 10:
            initial_color = 5  # Blue for left/right
        # Bottom (90°) and Top (270°) - second pair
        elif abs(angle_deg - 90) < 10 or abs(angle_deg - 270) < 10:
            initial_color = 2  # Orange for top/bottom
        # Diagonals (45°, 135°, 225°, 315°) - third group
        else:
            initial_color = 6  # Magenta for diagonals

        new_color_indices.append(initial_color)

        diamond = Polygon(
            points=points,
            outline=palette[initial_color],
            stroke=2
        )
        new_diamonds.append(diamond)
        spectrum_group.append(diamond)

    states["side_diamonds"] = new_diamonds
    states["side_color_indices"] = new_color_indices
    print(f"Side diamonds: {num_side_diamonds}")

    states = {
        "spectrum_group": spectrum_group,
        "center_diamond": center_diamond,
        "side_diamonds": new_diamonds,
        "palette": palette,
        "center_x": center_x,
        "center_y": center_y,
        "orbit_radius": orbit_radius,
        "base_width": base_width,
        "base_height": base_height,
        "side_base_width": side_base_width,
        "side_base_height": side_base_height,
        "current_width": base_width,
        "current_height": base_height,
        "side_current_width": side_base_width,
        "side_current_height": side_base_height,
        "center_color_index": 3,    # Start with yellow
        "side_color_indices": new_color_indices,  # Individual color for each side diamond
        "color_change_counter": 0,  # Track which group should change next
        "orbit_angle_offset": 0,     # For rotating diamonds around center
        "orbit_speed": 0.02,         # Speed of rotation (radians per frame)
        "smoothing_factor": 0.15,   # Lower = faster response
        "dynamic_level": 10,
        "noise_floor": 2.5,         # Lower = more sensitive
        "frame_count": 0,
        "color_timer": 0,
        "num_side_diamonds": num_side_diamonds
    }

# ------ DIAMOND PATTERN ANIMATION ------
def diamonds(pos, read):
    global states

    if read:
        # Handle both list and single value inputs
        if isinstance(pos, (list, tuple)):
            states["noise_floor"] = pos[0]
        else:
            # Single value - use for noise floor only
            states["noise_floor"] = pos

    center_diamond = states["center_diamond"]
    side_diamonds = states["side_diamonds"]
    palette = states["palette"]
    center_x = states["center_x"]
    center_y = states["center_y"]
    orbit_radius = states["orbit_radius"]
    base_width = states["base_width"]
    base_height = states["base_height"]
    side_base_width = states["side_base_width"]
    side_base_height = states["side_base_height"]
    current_width = states["current_width"]
    current_height = states["current_height"]
    side_current_width = states["side_current_width"]
    side_current_height = states["side_current_height"]
    center_color_index = states["center_color_index"]
    side_color_indices = states.get("side_color_indices",
                                    [5] * len(side_diamonds))
    smoothing_factor = states["smoothing_factor"]
    dynamic_level = states["dynamic_level"]
    noise_floor = states["noise_floor"]
    color_timer = states["color_timer"]
    num_side_diamonds = states["num_side_diamonds"]
    orbit_angle_offset = states.get("orbit_angle_offset", 0)

    # Record audio
    mic.record(rec_buf, fft_size)
    samples = np.array(rec_buf)

    # Get spectrum - same as bars() function
    spectrum = spectrogram(samples)[low_bin : high_bin + 1]
    spectrum = np.log(spectrum + 1e-7)
    spectrum = np.maximum(spectrum - noise_floor, 0)

    # Get min/max for normalization
    lower = max(np.min(spectrum), 4)
    upper = min(max(np.max(spectrum), lower + 12), 20)

    # Update dynamic level - more aggressive adaptation
    if upper > dynamic_level:
        dynamic_level = upper * 0.8 + dynamic_level * 0.2  # Faster rise
    else:
        dynamic_level = dynamic_level * 0.7 + lower * 0.3  # Faster fall
    states["dynamic_level"] = dynamic_level

    # Normalize data
    if dynamic_level > lower:
        data = (spectrum - lower) / (dynamic_level - lower)
    else:
        data = spectrum * 0

    # Split spectrum for width and height control
    spectrum_len = len(data)
    mid_point = spectrum_len // 2

    # Low frequencies affect height (vertical stretch)
    low_level = np.mean(data[0:mid_point]) if mid_point > 0 else 0
    # High frequencies affect width (horizontal stretch)
    high_level = np.mean(data[mid_point:]) if mid_point < spectrum_len else 0

    # Overall level for color changes
    overall_level = np.mean(data)

    # Calculate target dimensions for center diamond
    target_height = base_height + int(low_level * 120)
    target_width = base_width + int(high_level * 60)

    # Smooth the changes - faster response
    current_height = int(current_height * (1 - smoothing_factor * 2)
                        + target_height * smoothing_factor * 2)
    current_width = int(current_width * (1 - smoothing_factor * 2)
                        + target_width * smoothing_factor * 2)

    # Clamp dimensions
    current_height = max(20, min(current_height, display.height // 2 - 10))
    current_width = max(10, min(current_width, display.width // 2 - 10))

    states["current_width"] = current_width
    states["current_height"] = current_height

    # Calculate target dimensions for side diamonds (half the scaling)
    side_target_height = side_base_height + int(low_level * 60)  # Half the scaling
    side_target_width = side_base_width + int(high_level * 30)   # Half the scaling

    # Smooth the side diamond changes
    side_current_height = int(side_current_height * (1 - smoothing_factor * 2)
                                + side_target_height * smoothing_factor * 2)
    side_current_width = int(side_current_width * (1 - smoothing_factor * 2)
                                + side_target_width * smoothing_factor * 2)

    # Clamp side dimensions
    side_current_height = max(10, min(side_current_height, display.height // 4 - 5))
    side_current_width = max(5, min(side_current_width, display.width // 4 - 5))

    states["side_current_width"] = side_current_width
    states["side_current_height"] = side_current_height

    # Update center diamond points
    center_new_points = [
        (center_x, center_y - current_height),  # Top
        (center_x + current_width, center_y),    # Right
        (center_x, center_y + current_height),  # Bottom
        (center_x - current_width, center_y),    # Left
    ]
    center_diamond.points = center_new_points

    # Update orbit angle for rotation - speed up with audio
    # Base speed plus audio-reactive component
    base_speed = 0.02
    audio_speed_boost = overall_level * 0.08  # Speed boost based on audio level
    current_orbit_speed = base_speed + audio_speed_boost

    orbit_angle_offset += current_orbit_speed
    if orbit_angle_offset >= 2 * pi:
        orbit_angle_offset -= 2 * pi
    states["orbit_angle_offset"] = orbit_angle_offset

    # Update side diamonds points with rotation
    for i, diamond in enumerate(side_diamonds):
        # Calculate angle with rotation offset
        base_angle = (2 * pi * i) / num_side_diamonds  # Original position
        angle = base_angle + orbit_angle_offset  # Add rotation
        x = center_x + int(cos(angle) * orbit_radius)
        y = center_y + int(sin(angle) * orbit_radius)

        new_points = [
            (x, y - side_current_height),  # Top
            (x + side_current_width, y),    # Right
            (x, y + side_current_height),  # Bottom
            (x - side_current_width, y),    # Left
        ]
        diamond.points = new_points

    # Color cycling based on threshold
    # Calculate threshold based on noise floor
    color_threshold = 0.05 + (noise_floor - 2.0) * 0.02
    color_threshold = max(0.0, min(color_threshold, 0.15))  # Clamp between 0.0 and 0.15

    color_timer += 1
    # Change colors when we hit the threshold OR after timeout
    if overall_level > color_threshold or color_timer > 60:
        # Center diamond ALWAYS goes forward through colors
        center_color_index = (center_color_index % 7) + 1
        states["center_color_index"] = center_color_index
        center_diamond.outline = palette[center_color_index]

        # Get or initialize color change counter
        color_change_counter = states.get("color_change_counter", 0)

        # Side diamonds alternate which group changes
        new_side_indices = []

        # Track unique colors for each group
        blue_idx = None
        orange_idx = None
        magenta_idx = None

        for i, diamond in enumerate(side_diamonds):
            current_color = side_color_indices[i]

            # Determine which color group this diamond belongs to (based on ORIGINAL position)
            base_angle = (2 * pi * i) / num_side_diamonds
            angle_deg = (base_angle * 180 / pi) % 360

            # Determine if this diamond should change based on the pattern
            should_change = False

            if num_side_diamonds == 2:
                # With 2 diamonds: always change (all are left/right)
                should_change = True
            elif num_side_diamonds == 4:
                # With 4 diamonds: alternate between left/right and top/bottom
                if color_change_counter % 2 == 0:
                    # Change left/right
                    if abs(angle_deg - 0) < 10 or abs(angle_deg - 180) < 10:
                        should_change = True
                else:
                    # Change top/bottom
                    if abs(angle_deg - 90) < 10 or abs(angle_deg - 270) < 10:
                        should_change = True
            else:  # 8 diamonds
                # Pattern: left/right -> diagonals -> top/bottom -> diagonals -> repeat
                pattern_position = color_change_counter % 4
                if pattern_position == 0:
                    # Change left/right
                    if abs(angle_deg - 0) < 10 or abs(angle_deg - 180) < 10:
                        should_change = True
                elif pattern_position in (1, 3):
                    # Change diagonals
                    if not (abs(angle_deg - 0) < 10 or abs(angle_deg - 180) < 10 or
                           abs(angle_deg - 90) < 10 or abs(angle_deg - 270) < 10):
                        should_change = True
                else:  # pattern_position == 2
                    # Change top/bottom
                    if abs(angle_deg - 90) < 10 or abs(angle_deg - 270) < 10:
                        should_change = True

            # Apply color change or keep current color
            if should_change:
                # Right (0°) and Left (180°) - blue group
                if abs(angle_deg - 0) < 10 or abs(angle_deg - 180) < 10:
                    if blue_idx is None:
                        blue_idx = current_color - 1
                        if blue_idx < 1:
                            blue_idx = 7
                    color_idx = blue_idx
                # Bottom (90°) and Top (270°) - orange group
                elif abs(angle_deg - 90) < 10 or abs(angle_deg - 270) < 10:
                    if orange_idx is None:
                        orange_idx = current_color - 1
                        if orange_idx < 1:
                            orange_idx = 7
                    color_idx = orange_idx
                # Diagonals - magenta group
                else:
                    if magenta_idx is None:
                        magenta_idx = current_color - 1
                        if magenta_idx < 1:
                            magenta_idx = 7
                    color_idx = magenta_idx
            else:
                # Keep current color
                color_idx = current_color

            new_side_indices.append(color_idx)
            diamond.outline = palette[color_idx]

        states["side_color_indices"] = new_side_indices
        states["color_change_counter"] = color_change_counter + 1

        color_timer = 0

    states["color_timer"] = color_timer
    states["frame_count"] += 1

    display.refresh()

# ------ LINES PATTERN INIT ------
def initialize_lines(num_lines=8):
    global states

    spectrum_group = displayio.Group()
    display.root_group = spectrum_group

    # Create palette with colors
    palette = displayio.Palette(8)
    palette[0] = 0x000000  # Black background
    palette[1] = 0xFF0000  # Red
    palette[2] = 0xFF7F00  # Orange
    palette[3] = 0xFFFF00  # Yellow
    palette[4] = 0x00FF00  # Green
    palette[5] = 0x0000FF  # Blue
    palette[6] = 0xFF00FF  # Magenta
    palette[7] = 0xFFFFFF  # White

    # Create background
    background = displayio.Bitmap(display.width, display.height, 8)
    background.fill(0)
    bg_sprite = displayio.TileGrid(background, pixel_shader=palette)
    spectrum_group.append(bg_sprite)

    # Create lines - split evenly between vertical and horizontal
    lines = []
    line_data = []  # Store line properties for animation
    num_vertical = num_lines // 2
    num_horizontal = num_lines - num_vertical

    # Create vertical lines (full height)
    for i in range(num_vertical):
        x = randint(20, display.width - 20)
        thickness = randint(2, 5)  # Random thickness between 2 and 5
        color_idx = (i % 7) + 1  # Cycle through colors 1-7

        # Create a thin vertical rectangle
        line = vectorio.Rectangle(
            pixel_shader=palette,
            width=thickness,
            height=display.height,
            x=x,
            y=0,
            color_index=color_idx
        )
        lines.append(line)
        spectrum_group.append(line)

        # Store line data for animation
        line_data.append({
            'type': 'vertical',
            'base_x': x,
            'current_x': x,
            'jitter_amount': 0,
            'color_index': color_idx,
            'thickness': thickness
        })

    # Create horizontal lines (full width)
    for i in range(num_horizontal):
        y = randint(20, display.height - 20)
        thickness = randint(2, 5)  # Random thickness between 2 and 5
        color_idx = ((i + num_vertical) % 7) + 1  # Continue color cycle

        # Create a thin horizontal rectangle
        line = vectorio.Rectangle(
            pixel_shader=palette,
            width=display.width,
            height=thickness,
            x=0,
            y=y,
            color_index=color_idx
        )
        lines.append(line)
        spectrum_group.append(line)

        # Store line data for animation
        line_data.append({
            'type': 'horizontal',
            'base_y': y,
            'current_y': y,
            'jitter_amount': 0,
            'color_index': color_idx,
            'thickness': thickness
        })

    states = {
        "spectrum_group": spectrum_group,
        "lines": lines,
        "line_data": line_data,
        "palette": palette,
        "smoothing_factor": 0.15,
        "dynamic_level": 10,
        "noise_floor": 2.5,
        "color_timer": 0,
        "jitter_decay": 0.9,  # How quickly jitter settles (higher = smoother)
        "max_jitter": 20,  # Maximum jitter distance
        "num_lines": num_lines,
        "color_change_threshold": 0.3,
        "trigger_threshold": 0.15,  # Lower threshold for more sensitivity
    }

# ------ LINES PATTERN ANIMATION ------
def lines_pattern(pos, read):
    global states

    if read:
        if isinstance(pos, (list, tuple)):
            states["noise_floor"] = pos[0]
        else:
            states["noise_floor"] = pos

    lines = states["lines"]
    line_data = states["line_data"]
    dynamic_level = states["dynamic_level"]
    noise_floor = states["noise_floor"]
    color_timer = states["color_timer"]
    jitter_decay = states["jitter_decay"]
    max_jitter = states["max_jitter"]
    num_lines = states["num_lines"]
    color_change_threshold = states["color_change_threshold"]
    trigger_threshold = states["trigger_threshold"]

    # Record audio
    mic.record(rec_buf, fft_size)
    samples = np.array(rec_buf)

    # Get spectrum
    spectrum = spectrogram(samples)[low_bin : high_bin + 1]
    spectrum = np.log(spectrum + 1e-7)
    spectrum = np.maximum(spectrum - noise_floor, 0)

    # Get min/max for normalization
    lower = max(np.min(spectrum), 4)
    upper = min(max(np.max(spectrum), lower + 12), 20)

    # Update dynamic level
    if upper > dynamic_level:
        dynamic_level = upper * 0.8 + dynamic_level * 0.2
    else:
        dynamic_level = dynamic_level * 0.7 + lower * 0.3
    states["dynamic_level"] = dynamic_level

    # Normalize data
    if dynamic_level > lower:
        data = (spectrum - lower) / (dynamic_level - lower)
    else:
        data = spectrum * 0

    # Split spectrum into bands for each line
    spectrum_len = len(data)
    num_lines = states["num_lines"]
    band_size = max(1, spectrum_len // num_lines)  # Ensure at least 1

    # Update each line based on its frequency band
    for i, (line, line_info) in enumerate(zip(lines, line_data)):
        # Get the frequency band for this line
        band_start = i * band_size
        band_end = min(band_start + band_size, spectrum_len)

        if band_end > band_start:
            band_level = np.mean(data[band_start:band_end])
        else:
            band_level = 0

        # Apply jitter based on band level
        if band_level > trigger_threshold:  # Threshold for triggering jitter
            # Add new jitter based on intensity
            new_jitter = band_level * max_jitter * choice([-1, 1])
            line_info['jitter_amount'] = line_info['jitter_amount'] * 0.7 + new_jitter * 0.3
        else:
            # Decay existing jitter
            line_info['jitter_amount'] *= jitter_decay

        # Clamp jitter
        line_info['jitter_amount'] = max(-max_jitter, min(max_jitter, line_info['jitter_amount']))

        # Apply jitter to line position
        if line_info['type'] == 'vertical':
            # Vertical lines jitter left/right
            new_x = int(line_info['base_x'] + line_info['jitter_amount'])
            # Clamp to screen bounds (accounting for thickness)
            new_x = max(0, min(display.width - line_info['thickness'], new_x))
            line_info['current_x'] = new_x

            # Update rectangle position
            line.x = new_x
        else:
            # Horizontal lines jitter up/down
            new_y = int(line_info['base_y'] + line_info['jitter_amount'])
            # Clamp to screen bounds (accounting for thickness)
            new_y = max(0, min(display.height - line_info['thickness'], new_y))
            line_info['current_y'] = new_y

            # Update rectangle position
            line.y = new_y

        # Color changes based on intensity
        if band_level > color_change_threshold:
            # Cycle to next color (skip black at index 0)
            line_info['color_index'] = (line_info['color_index'] % 7) + 1
            line.color_index = line_info['color_index']

    color_timer += 1
    states["color_timer"] = color_timer

    display.refresh()

# Add these variables at the top of your main loop
mode = 0
new_mode = True
diamond_count_index = 0
diamond_count_options = [2, 4, 8]
update_diamonds = False
party_count_index = 0
party_count_options = [1, 4, 9, 16]
update_party = False
lines_count_index = 0
lines_count_options = [8, 12, 16, 20]
update_lines = False

# Auto-cycle mode variables
auto_cycle_active = False
cycle_frame_counter = 0
cycle_current_mode = 0
FRAMES_PER_MODE = 60

# Main loop
while True:
    event = keys.events.get()
    if event:
        if event.pressed:
            leds[event.key_number].value = True
            if event.key_number == 0:
                # Cycle through modes: 0=diamond, 1=bars, 2=lines, 3=auto-cycle
                mode = (mode + 1) % 4
                new_mode = True

                # Handle auto-cycle mode LED
                if mode == 3:
                    auto_cycle_active = True
                    # Keep LED on for auto-cycle mode
                    leds[0].value = True
                else:
                    auto_cycle_active = False
                    # LED will turn off on button release for normal modes

            elif event.key_number == 1 and not auto_cycle_active:
                # Button 2 only works when not in auto-cycle mode
                if mode == 0:
                    diamond_count_index = (diamond_count_index + 1) % 3
                    update_diamonds = True
                elif mode == 1:
                    party_count_index = (party_count_index + 1) % 4
                    update_party = True
                elif mode == 2:
                    lines_count_index = (lines_count_index + 1) % 4
                    update_lines = True
        else:
            # Only turn off LED if not in auto-cycle mode
            if event.key_number == 0 and not auto_cycle_active:
                leds[0].value = False
            elif event.key_number == 1:
                leds[1].value = False
        print(event)

    # Initialize new mode
    if new_mode:
        if mode == 0:
            initialize_diamond(diamond_count_options[diamond_count_index])
        elif mode == 1:
            initialize_party(party_count_options[party_count_index])
        elif mode == 2:
            initialize_lines(lines_count_options[lines_count_index])
        elif mode == 3:

            # Randomize starting counts
            diamond_count_index = randint(0, (len(diamond_count_options) - 1))
            party_count_index = randint(0, (len(party_count_options) - 1))
            lines_count_index = randint(0, (len(lines_count_options) - 1))

            # Start with a random animation
            cycle_current_mode = randint(0, 2)
            cycle_frame_counter = 0

            # Initialize the first random animation
            if cycle_current_mode == 0:
                initialize_diamond(diamond_count_options[diamond_count_index])
            elif cycle_current_mode == 1:
                initialize_party(party_count_options[party_count_index])
            elif cycle_current_mode == 2:
                initialize_lines(lines_count_options[lines_count_index])
        new_mode = False

    # Handle manual count updates
    if update_diamonds and mode == 0:
        initialize_diamond(diamond_count_options[diamond_count_index])
        update_diamonds = False
    if update_party and mode == 1:
        initialize_party(party_count_options[party_count_index])
        update_party = False
    if update_lines and mode == 2:
        initialize_lines(lines_count_options[lines_count_index])
        update_lines = False

    # Run animations
    noise = simpleio.map_range(val(pot1), 0, 65535, 3.5, 1.5)

    if mode == 0:
        diamonds(noise, read_pots)
    elif mode == 1:
        party(noise, read_pots)
    elif mode == 2:
        lines_pattern(noise, read_pots)
    elif mode == 3:
        # Auto-cycle mode
        cycle_frame_counter += 1

        # Check if it's time to switch animations
        if cycle_frame_counter >= FRAMES_PER_MODE:
            cycle_frame_counter = 0
            cycle_current_mode = randint(0, 2)

            # Initialize the next animation with random count
            if cycle_current_mode == 0:
                diamond_count_index = randint(0, (len(diamond_count_options) - 1))
                initialize_diamond(diamond_count_options[diamond_count_index])
            elif cycle_current_mode == 1:
                party_count_index = randint(0, (len(party_count_options) - 1))
                initialize_party(party_count_options[party_count_index])
            elif cycle_current_mode == 2:
                lines_count_index = randint(0, (len(lines_count_options) - 1))
                initialize_lines(lines_count_options[lines_count_index])

        # Run the current animation
        if cycle_current_mode == 0:
            diamonds(noise, read_pots)
        elif cycle_current_mode == 1:
            party(noise, read_pots)
        elif cycle_current_mode == 2:
            lines_pattern(noise, read_pots)
