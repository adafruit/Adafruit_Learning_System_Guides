# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# FFT calculations based on Phil B.'s Audio Spectrum Light Show Code
# https://github.com/adafruit/Adafruit_Learning_System_Guides/blob/main/
# Feather_Sense_Audio_Visualizer_13x9_RGB_LED_Matrix/audio_spectrum_lightshow/code.py
import gc
from array import array
from math import log
from random import randint
import board
from audiobusio import PDMIn
import displayio
import picodvi
import framebufferio
import vectorio
from rainbowio import colorwheel
import adafruit_imageload
from adafruit_display_shapes.line import Line
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from adafruit_seesaw import seesaw, rotaryio, digitalio
from analogio import AnalogIn
import simpleio
from ulab import numpy as np
try:
    from ulab.utils import spectrogram
except ImportError:
    from ulab.scipy.signal import spectrogram

# ------ POTENTIOMETER SETUP ------
pot1 = AnalogIn(board.A1)
pot2 = AnalogIn(board.A2)
pot3 = AnalogIn(board.A3)
read_pots = True
# ------ POTENTIOMETER MODE VALUES ------
mode0_values = [0, 0, 0]
mode1_values = [0, 0, 0]
mode2_values = [0, 0, 0]
mode_vals = [mode0_values, mode1_values, mode2_values]
# ------ POTENTIOMETER READ FUNCTION ------
def val(pin):
    return pin.value

# ------ SEESAW ENCODER ------
i2c = board.STEMMA_I2C()
seesaw = seesaw.Seesaw(i2c, addr=0x36)
seesaw_product = (seesaw.get_version() >> 16) & 0xFFFF
print("Found product {}".format(seesaw_product))
if seesaw_product != 4991:
    print("Wrong firmware loaded?  Expected 4991")
seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
button = digitalio.DigitalIO(seesaw, 24)
button_held = False
encoder = rotaryio.IncrementalEncoder(seesaw)
last_position = 0

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

# ------ PICODVI SETUP ------
displayio.release_displays()
fb = picodvi.Framebuffer(320, 240, clk_dp=board.CKP, clk_dn=board.CKN,
                         red_dp=board.D0P, red_dn=board.D0N,
                         green_dp=board.D1P, green_dn=board.D1N,
                         blue_dp=board.D2P, blue_dn=board.D2N,
                         color_depth=8)
display = framebufferio.FramebufferDisplay(fb, auto_refresh=False)

# ------ PDM MIC ------
mic = PDMIn(board.D5, board.D6, sample_rate=44100, bit_depth=16)
rec_buf = array("H", [0] * fft_size)

# pylint: disable=too-many-locals, global-statement, too-many-statements, global-variable-not-assigned

# ------ INITIALIZE BAR GRAPH ANIMATION ------
def initialize_bars():
    # based on Phil B.'s Audio Spectrum Light Show Code
    # https://github.com/adafruit/Adafruit_Learning_System_Guides/blob/main/
    # Feather_Sense_Audio_Visualizer_13x9_RGB_LED_Matrix/audio_spectrum_lightshow/code.py
    global states
    spectrum_group = displayio.Group()
    display.root_group = spectrum_group

    low_frac = log(low_bin, 2) / spectrum_bits
    frac_range = log(high_bin, 2) / spectrum_bits - low_frac
    num_columns = 16
    column_width = display.width // num_columns
    column_table = []
    moving_avg_buffer = [display.height] * num_columns
    smoothing_factor = 0.5
    height_multiplier = 5
    dynamic_level = 10
    noise_floor = 3.1

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
        column_table.append(
            [
                first_bin - low_bin,
                bin_weights,
                colorwheel(225 * column / num_columns),
                display.height,
                0.0,
            ]
        )
        bar_pal = displayio.Palette(1)
        bar_pal[0] = colorwheel(225 * column / num_columns)
        rect = vectorio.Rectangle(
            pixel_shader=bar_pal,
            width=column_width,
            height=1,
            x=column * column_width,
            y=display.height,
        )
        spectrum_group.append(rect)

    peak_palette = displayio.Palette(1)
    peak_palette[0] = 0x808080
    for column in range(num_columns):
        column_table[column].append(display.height)
        column_table[column].append(0.0)
        peak_dot = vectorio.Rectangle(
            pixel_shader=peak_palette,
            width=column_width,
            height=5,
            x=column * column_width,
            y=display.height,
        )
        spectrum_group.append(peak_dot)

    states = {
        "spectrum_group": spectrum_group,
        "column_table": column_table,
        "moving_avg_buffer": moving_avg_buffer,
        "smoothing_factor": smoothing_factor,
        "height_multiplier": height_multiplier,
        "dynamic_level": dynamic_level,
        "noise_floor": noise_floor,
        "num_columns": num_columns,
        "column_width": column_width,
        "peak_pal": peak_palette,
    }

# ------ BAR GRAPH ANIMATION ------
def bars(pos, read):
    global states
    if read:
        states["peak_pal"][0] = colorwheel(pos[0])
        states["noise_floor"] = pos[1]
        states["smoothing_factor"] = pos[2]
    spectrum_group = states["spectrum_group"]
    column_table = states["column_table"]
    moving_avg_buffer = states["moving_avg_buffer"]
    smoothing_factor = states["smoothing_factor"]
    height_multiplier = states["height_multiplier"]
    dynamic_level = states["dynamic_level"]
    noise_floor = states["noise_floor"]
    num_columns = states["num_columns"]

    mic.record(rec_buf, fft_size)
    samples = np.array(rec_buf)

    spectrum = spectrogram(samples)[low_bin : high_bin + 1]
    spectrum = np.log(spectrum + 1e-7)
    spectrum = np.maximum(spectrum - noise_floor, 0)
    lower = max(np.min(spectrum), 4)
    upper = min(max(np.max(spectrum), lower + 12), 20)
    if upper > dynamic_level:
        dynamic_level = upper * 0.7 + dynamic_level * 0.3
    else:
        dynamic_level = dynamic_level * 0.5 + lower * 0.5
    states["dynamic_level"] = dynamic_level
    max_height = display.height
    data = (spectrum - lower) * (max_height / (dynamic_level - lower)) * height_multiplier

    for column, element in enumerate(column_table):
        first_bin = element[0]
        column_top = display.height + 1
        for bin_offset, weight in enumerate(element[1]):
            if first_bin + bin_offset < len(data):
                column_top -= data[first_bin + bin_offset] * weight
        column_top = max(0, int(column_top))
        moving_avg_buffer[column] = (
            moving_avg_buffer[column] * (1 - smoothing_factor) +
            column_top * smoothing_factor
        )
        smoothed_top = int(moving_avg_buffer[column])
        rect = spectrum_group[column]
        rect.height = display.height - smoothed_top
        rect.y = smoothed_top

        if smoothed_top < element[3]:
            element[3] = smoothed_top - 1
            element[4] = 0
        else:
            element[3] += element[4]
            element[4] += 0.2
        peak_position = max(0, int(element[3]))
        peak_dot = spectrum_group[num_columns + column]
        peak_dot.y = peak_position
    display.refresh()
# ------ INITIALIZE CIRCLE ANIMATION ------
def initialize_circles():
    global states
    spectrum_group = displayio.Group()
    display.root_group = spectrum_group
    palette = displayio.Palette(1)
    palette[0] = 0xFFFFFF
    center_palette = displayio.Palette(1)
    center_palette[0] = 0xFF0000
    center_circle = (
    vectorio.Circle(pixel_shader=center_palette, radius=5,
                    x=display.width // 2, y=display.height // 2)
    )
    spectrum_group.append(center_circle)
    num_circles = 16
    smoothing_factor = 0.5
    decay_factor = 0.2
    circles = []
    directions = []
    smoothed_radii = [5] * num_circles

    for i in range(num_circles):
        radius = 5
        x_pos = randint(radius, display.width - radius)
        y_pos = randint(radius, display.height - radius)
        dx = randint(-2, 2) or 1
        dy = randint(-2, 2) or 1
        color_index = (255 * i) // num_circles
        circle_palette = displayio.Palette(1)
        circle_palette[0] = colorwheel(color_index)
        circle = vectorio.Circle(pixel_shader=circle_palette, radius=radius, x=x_pos, y=y_pos)
        spectrum_group.append(circle)
        circles.append(circle)
        directions.append([dx, dy])
    states = {
        "spectrum_group": spectrum_group,
        "center_circle": center_circle,
        "center_radius_smoothed": 5,
        "circles": circles,
        "directions": directions,
        "smoothed_radii": smoothed_radii,
        "smoothing_factor": smoothing_factor,
        "decay_factor": decay_factor,
        "dynamic_level": 15,
        "noise_floor": 3.1,
        "max_radius": 100,
        "num_circles": num_circles,
        "center_palette": center_palette,
        "speed": 1,
    }
# ------ BOUNCING CIRCLES ANIMATION ------
def bouncing_circles(pos, read):
    global states
    if read:
        states["center_palette"][0] = colorwheel(pos[0])
        states["noise_floor"] = pos[1]
        states["smoothing_factor"] = pos[2]
        states["decay_factor"] = pos[2] - 0.3
    mic.record(rec_buf, fft_size)
    samples = np.array(rec_buf)
    spectrum = spectrogram(samples)[low_bin : high_bin + 1]
    spectrum = np.log(spectrum + 1e-7)
    spectrum = np.maximum(spectrum - states["noise_floor"], 0)
    lower = max(np.min(spectrum), 4)
    upper = min(max(np.max(spectrum), lower + 12), 20)
    if upper > states["dynamic_level"]:
        states["dynamic_level"] = upper * 0.7 + states["dynamic_level"] * 0.3
    else:
        states["dynamic_level"] = states["dynamic_level"] * 0.5 + lower * 0.5
    overall_amplitude = np.sum(spectrum)
    max_center_radius = 50
    target_center_radius = (
    int((overall_amplitude / (states["dynamic_level"] * states["num_circles"])) * max_center_radius)
    )
    if target_center_radius < states["center_radius_smoothed"]:
        states["center_radius_smoothed"] = (
            states["center_radius_smoothed"] * (1 - states["decay_factor"]) +
            target_center_radius * states["decay_factor"]
        )
    else:
        states["center_radius_smoothed"] = (
            states["center_radius_smoothed"] * (1 - states["smoothing_factor"]) +
            target_center_radius * states["smoothing_factor"]
        )
    states["center_circle"].radius = int(states["center_radius_smoothed"])
    data = (spectrum - lower) * (states["max_radius"] / (states["dynamic_level"] - lower))
    for i, circle in enumerate(states["circles"]):
        target_radius = max(2, int(data[i]))
        if target_radius < states["smoothed_radii"][i]:
            states["smoothed_radii"][i] = (
                states["smoothed_radii"][i] * (1 - states["decay_factor"]) +
                target_radius * states["decay_factor"]
            )
        else:
            states["smoothed_radii"][i] = (
                states["smoothed_radii"][i] * (1 - states["smoothing_factor"]) +
                target_radius * states["smoothing_factor"]
            )
        circle.radius = int(states["smoothed_radii"][i])
        dx, dy = states["directions"][i]
        circle.x += dx
        circle.y += dy
        if circle.x - circle.radius <= 0 or circle.x + circle.radius >= display.width:
            states["directions"][i][0] *= -1  # Reverse x direction
        if circle.y - circle.radius <= 0 or circle.y + circle.radius >= display.height:
            states["directions"][i][1] *= -1 # Reverse y direction
    display.refresh()
# ------ PARTY PARROT INIT ------
def initialize_party():
    global states
    spectrum_group = displayio.Group()
    display.root_group = spectrum_group
    bitmap, palette = adafruit_imageload.load(
        "/partyParrotsBig.bmp",
        bitmap=displayio.Bitmap,
        palette=displayio.Palette
    )
    parrot_grid = displayio.TileGrid(
        bitmap,
        pixel_shader=palette,
        tile_height=128,
        tile_width=132,
        x=(display.width - 128) // 2,
        y=0
    )
    spectrum_group.append(parrot_grid)
    line_group = displayio.Group()
    spectrum_group.append(line_group)
    pal_bg = displayio.Palette(1)
    pal_bg[0] = 0x0000FF
    palette_white = displayio.Palette(1)
    palette_white[0] = 0xFFFFFF
    pal = displayio.Palette(1)
    pal[0] = 0xFF00FF
    left_circle = vectorio.Circle(
        pixel_shader=pal, radius=5, x=5, y=5
    )
    right_circle = vectorio.Circle(
        pixel_shader=pal, radius=5, x=display.width - 5, y=5
    )
    spectrum_group.append(left_circle)
    spectrum_group.append(right_circle)
    ground = vectorio.Rectangle(
        pixel_shader=pal_bg,
        width=display.width,
        height=display.height - 128,
        x=0,
        y=128
    )
    line_group.append(ground)
    horizon_line = vectorio.Rectangle(
        pixel_shader=palette_white,
        width=display.width,
        height=1,
        x=0,
        y=128
    )
    line_group.append(horizon_line)
    slanted_lines_coords = [
        (0, 136, 34, 128),
        (0, 188, 76, 128),
        (34, 240, 113, 128),
        (117, 240, 148, 128),
        (198, 240, 182, 128),
        (294, 240, 216, 128),
        (320, 176, 255, 128),
        (320, 133, 297, 128)
    ]
    for coords in slanted_lines_coords:
        line = Line(coords[0], coords[1], coords[2], coords[3], 0xFFFFFF)
        line_group.append(line)
    horizontal_lines = []
    for _ in range(5):
        line_rect = vectorio.Rectangle(
            pixel_shader=palette_white,
            width=display.width,
            height=2,
            x=0,
            y=0
        )
        line_group.append(line_rect)
        horizontal_lines.append(line_rect)
    states = {
        "pal": pal,
        "pal_bg": pal_bg,
        "pal_line": palette_white,
        "spectrum_group": spectrum_group,
        "parrot_grid": parrot_grid,
        "line_group": line_group,
        "horizontal_lines": horizontal_lines,
        "frame_index": 0,
        "low_band_threshold": 3.4,
        "mid_band_threshold": 3.4,
        "smoothing_factor": 0.5,
        "last_i": 146,
        "dynamic_level": 15,
        "decay_factor": 2,
        "max_center_radius": 10,
        "center_radius_smoothed": 2,
        "left_circle": left_circle,
        "right_circle": right_circle,
        "clock_clock": ticks_ms(),
        "clock_time": int(0.01 * 1000),
        "i": 152
    }
# ------ PARTY PARROT ANIMATION ------
def party_parrot(pos, read):
    global states
    if read:
        states["pal"][0] = colorwheel(pos[0])
        states["max_center_radius"] = pos[1]
        states["low_band_threshold"] = pos[2]
        states["mid_band_threshold"] = pos[2]
    left_circle = states["left_circle"]
    right_circle = states["right_circle"]
    parrot_grid = states["parrot_grid"]
    horizontal_lines = states["horizontal_lines"]
    frame_index = states["frame_index"]
    last_i = states["last_i"]
    center_radius_smoothed = states["center_radius_smoothed"]
    dynamic_level = states["dynamic_level"]
    low_band_threshold = states["low_band_threshold"]
    mid_band_threshold = states["mid_band_threshold"]
    smoothing_factor = states["smoothing_factor"]
    decay_factor = states["decay_factor"]
    clock_clock = states["clock_clock"]
    palette_blue = states["pal_bg"]
    palette_white = states["pal_line"]
    i = states["i"]
    if i > 128:
        last_i = i
        i -= 1
    else:
        i = 152
    mic.record(rec_buf, fft_size)
    samples = np.array(rec_buf)
    spectrum = spectrogram(samples)
    spectrum = np.log(spectrum + 1e-7)
    spectrum = np.maximum(spectrum - 3.1, 0)
    low_band_avg = np.mean(spectrum[low_band[0]:low_band[1] + 1])
    mid_band_avg = np.mean(spectrum[mid_band[0]:mid_band[1] + 1])
    overall_amplitude = np.sum(spectrum)
    target_center_radius = (
    int((overall_amplitude / (dynamic_level * 16)) * states["max_center_radius"])
    )
    if target_center_radius < center_radius_smoothed:
        center_radius_smoothed = (
        center_radius_smoothed * (1 - decay_factor) + target_center_radius * decay_factor
        )
    else:
        center_radius_smoothed = (
        center_radius_smoothed * (1 - smoothing_factor) + target_center_radius * smoothing_factor
        )
    left_circle.radius = int(center_radius_smoothed)
    right_circle.radius = int(center_radius_smoothed)
    if low_band_avg >= low_band_threshold * 1.1 or mid_band_avg >= mid_band_threshold * 1.1:
        frame_index = (frame_index + 1) % 10
        parrot_grid[0] = frame_index
    if ticks_diff(ticks_ms(), clock_clock) >= states["clock_time"]:
        for idx, offset in enumerate([0, 25, 50, 75, 100]):
            horizontal_lines[idx].y = last_i + offset
            horizontal_lines[idx].pixel_shader = palette_blue
        for idx, offset in enumerate([0, 25, 50, 75, 100]):
            horizontal_lines[idx].y = i + offset
            horizontal_lines[idx].pixel_shader = palette_white
        clock_clock = ticks_add(clock_clock, states["clock_time"])
    display.refresh()
    states["frame_index"] = frame_index
    states["last_i"] = last_i
    states["i"] = i
    states["center_radius_smoothed"] = center_radius_smoothed
# ------ THE LOOP ------
while True:
    # read encoder - if value != then change mode
    position = -encoder.position
    if position != last_position:
        if position > last_position:
            mode = (mode + 1) % 3
        else:
            mode = (mode - 1) % 3
        new_mode = True
        last_position = position
    # encode button - switch between reading potentiometer
    # to control animations or using default values
    if not button.value and not button_held:
        button_held = True
        read_pots = not read_pots
        print("Button pressed")
    if button.value and button_held:
        button_held = False
        print("Button released")
    # if a new mode is selected, run init function
    if new_mode:
        new_mode = False
        print(f"switching modes! {mode}")
        del states
        gc.collect()
        display.refresh()
        if mode == 0:
            initialize_bars()
        if mode == 1:
            initialize_circles()
        if mode == 2:
            initialize_party()
    # mode 0 - bar graph visualizer
    if mode == 0:
        bars(mode0_values, read_pots)
        # pot 1 - control color of bouncing dot
        color = simpleio.map_range(val(pot1), 0, 65535, 0, 255)
        mode_vals[0][0] = color
        # pot 2 - raise/lower noise floor
        noise = simpleio.map_range(val(pot2), 0, 65535, 2.5, 4.5)
        mode_vals[0][1] = noise
        # pot 3 - smooth bar animation
        smooth = simpleio.map_range(val(pot3), 0, 65535, 0.5, 0.05)
        mode_vals[0][2] = smooth
    # mode 1 - bouncing circles visualizer
    if mode == 1:
        bouncing_circles(mode1_values, read_pots)
        # pot 1 - control color of center circle
        color = simpleio.map_range(val(pot1), 0, 65535, 0, 255)
        mode_vals[1][0] = color
        # pot 2 - raise/lower noise floor
        noise = simpleio.map_range(val(pot2), 0, 65535, 2.5, 4.5)
        mode_vals[1][1] = noise
        # pot 3 - smooth circle size change
        smooth = simpleio.map_range(val(pot3), 0, 65535, 0.8, 0.4)
        mode_vals[1][2] = smooth
    # mode 2 - party parrot synth wave
    if mode == 2:
        party_parrot(mode2_values, read_pots)
        # pot 1 - control color of side circles
        color = simpleio.map_range(val(pot1), 0, 65535, 0, 255)
        mode_vals[2][0] = color
        # pot 2 - mid & low end noise floor aka parrot sensitivity
        dynamic = simpleio.map_range(val(pot2), 0, 65535, 3.0, 6.0)
        mode_vals[2][1] = dynamic
        # pot 3 - size of side circles
        rad = simpleio.map_range(val(pot3), 0, 65535, 2, 12)
        mode_vals[2][2] = rad
