# SPDX-FileCopyrightText: Adafruit Industries
# SPDX-FileCopyrightText: 2026 Pedro Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Code written by Adafruit Industries
# Adafruit Circuit Playground Express Bluefruit

# pylint: disable=global-statement

import time
import math
import array
import board
import digitalio
import neopixel
import analogio
import audiobusio
import touchio
import busio
import adafruit_lis3dh

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_bluefruit_connect.button_packet import ButtonPacket
import adafruit_fancyled.adafruit_fancyled as fancy

# setup pixels
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=1, auto_write=True)

# name colors so you don't need to refer to numbers
RED = (255, 0, 0)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
PURPLE = (100, 0, 255)
BLUE = (0, 0, 255)

# Declare a 6-element RGB rainbow palette
PALETTE_RAINBOW = [fancy.CRGB(1.0, 0.0, 0.0), # Red
           fancy.CRGB(0.5, 0.5, 0.0), # Yellow
           fancy.CRGB(0.0, 1.0, 0.0), # Green
           fancy.CRGB(0.0, 0.5, 0.5), # Cyan
           fancy.CRGB(0.0, 0.0, 1.0), # Blue
           fancy.CRGB(0.5, 0.0, 0.5)] # Magenta

NUM_LEDS = 10
offset = 0  # animation position offset
active_palette = None  # currently running palette animation
active_color = None  # currently breathing solid color

def update_palette():
    """Advance one frame of the active palette animation."""
    global offset
    if active_palette is None:
        return
    for i in range(NUM_LEDS):
        color = fancy.palette_lookup(active_palette, offset + i / NUM_LEDS)
        color = fancy.gamma_adjust(color, brightness=0.25)
        pixels[i] = color.pack()
    pixels.show()
    offset += 0.05

def update_breathing():
    """Slowly breathe the active solid color between brightness 0.2 and 0.5."""
    if active_color is None:
        return
    # Sine wave oscillates 0-1, scale to 0.2-0.5 range
    brightness = 0.35 + 0.15 * math.sin(time.monotonic() * 1.5)
    r = int(active_color[0] * brightness)
    g = int(active_color[1] * brightness)
    b = int(active_color[2] * brightness)
    pixels.fill((r, g, b))

# --- VU Meter (audio reactive) setup ---
mic = audiobusio.PDMIn(
    board.MICROPHONE_CLOCK, board.MICROPHONE_DATA,
    sample_rate=16000, bit_depth=16)
samples = array.array('H', [0] * 320)

CURVE = 2
SCALE_EXPONENT = math.pow(10, CURVE * -0.1)

def constrain(value, floor, ceiling):
    return max(floor, min(value, ceiling))

def log_scale(input_value, input_min, input_max, output_min, output_max):
    normalized_input_value = (input_value - input_min) / (input_max - input_min)
    return output_min + math.pow(normalized_input_value, SCALE_EXPONENT) * (output_max - output_min)
last_vu_input = 0
active_vu = False  # VU meter mode flag

# VU meter colors mapped to 10 NeoPixels
VU_GREEN = (0, 127, 0)
VU_YELLOW = (127, 127, 0)
VU_RED = (127, 0, 0)
VU_OFF = (0, 0, 0)
vu_colors = [VU_GREEN, VU_GREEN, VU_GREEN, VU_GREEN,
             VU_YELLOW, VU_YELLOW, VU_YELLOW,
             VU_RED, VU_RED, VU_RED]

def mean(values):
    """Average of mic sample values."""
    return sum(values) / len(values)

def normalized_rms(values):
    """Return normalized RMS of mic samples."""
    minbuf = int(mean(values))
    samples_sum = sum(
        float(sample - minbuf) * (sample - minbuf)
        for sample in values
    )
    return math.sqrt(samples_sum / len(values))

vu_level = 0.0  # smoothed VU level

def update_vu():
    """Update NeoPixels based on mic input level with smooth rise and fall."""
    global last_vu_input, vu_level, input_floor, input_ceiling
    if not active_vu:
        return
    mic.record(samples, len(samples))
    magnitude = normalized_rms(samples)
    # Adaptive noise floor: continuously tracks ambient noise
    # (including BLE radio EMI) so the meter stays zeroed.
    if magnitude < input_floor:
        # Below floor — floor drifts down slowly
        input_floor = input_floor * 0.999 + magnitude * 0.001
    elif magnitude < input_floor + 4:
        # Near the floor — this is still noise, nudge floor up
        input_floor = input_floor * 0.9 + magnitude * 0.1
    input_ceiling = input_floor + 15.0
    # Compute scaled logarithmic reading in the range 0 to NUM_LEDS
    target = log_scale(
        constrain(magnitude, input_floor, input_ceiling),
        input_floor, input_ceiling, 0, NUM_LEDS)
    # Smooth: rise slowly, fall even slower
    if target > vu_level:
        vu_level = vu_level + (target - vu_level) * 0.3
    else:
        vu_level = vu_level + (target - vu_level) * 0.12
    input_val = int(vu_level)
    if last_vu_input != input_val:
        pixels.fill(VU_OFF)
        for i in range(min(input_val, NUM_LEDS)):
            pixels[i] = vu_colors[i]
        pixels.show()
        last_vu_input = input_val

# Sentinel for VU meter mode in animation list
VU_METER = "VU_METER"

# --- Light Sensor setup ---
light = analogio.AnalogIn(board.LIGHT)
active_light = False  # Light sensor mode flag
light_level = 0.0  # smoothed light level

# Light meter warm colors
LIGHT_DIM = (52, 5, 1)
LIGHT_BRIGHT = (9, 5, 4)

last_light_color = (0, 0, 0)  # track last written color

def update_light():
    """All 10 LEDs blend between dim and bright color based on light level."""
    global light_level, last_light_color
    if not active_light:
        return
    # 0.0 = dark room (dim color), 1.0 = bright room (bright warm color)
    raw = light.value
    target = max(0.0, min(1.0, (raw - 1000) / 1000.0))
    # Smooth: very gentle transitions
    if target > light_level:
        light_level = light_level + (target - light_level) * 0.02
    else:
        light_level = light_level + (target - light_level) * 0.015
    # Clamp to prevent drift
    light_level = max(0.0, min(1.0, light_level))
    t = light_level
    new_color = (int(LIGHT_DIM[0] + (LIGHT_BRIGHT[0] - LIGHT_DIM[0]) * t),
                 int(LIGHT_DIM[1] + (LIGHT_BRIGHT[1] - LIGHT_DIM[1]) * t),
                 int(LIGHT_DIM[2] + (LIGHT_BRIGHT[2] - LIGHT_DIM[2]) * t))
    # Only update pixels if the color actually changed
    if new_color != last_light_color:
        last_light_color = new_color
        pixels.fill(new_color)
        pixels.show()

# Sentinel for Light meter mode in animation list
LIGHT_METER = "LIGHT_METER"

# Calibrate: seed the adaptive noise floor
mic.record(samples, len(samples))
input_floor = normalized_rms(samples) + 10
input_ceiling = input_floor + 15.0

# setup bluetooth
ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)

# setup physical buttons
button_a = digitalio.DigitalInOut(board.D4)
button_a.direction = digitalio.Direction.INPUT
button_a.pull = digitalio.Pull.DOWN

button_b = digitalio.DigitalInOut(board.D5)
button_b.direction = digitalio.Direction.INPUT
button_b.pull = digitalio.Pull.DOWN

# Capacitive touch pads for brightness
touch_bright = touchio.TouchIn(board.A1)  # D6 - increase brightness
touch_dim = touchio.TouchIn(board.A2)     # D9 - decrease brightness
prev_touch_bright = False
prev_touch_dim = False

# Setup accelerometer for tap detection
accelo_i2c = busio.I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
accelo = adafruit_lis3dh.LIS3DH_I2C(accelo_i2c, address=0x19)
accelo.set_tap(1, 100)  # single tap, threshold 100 (medium tap)

# Lists for cycling
COLOR_LIST = [PURPLE, GREEN, RED, BLUE, LIGHT_METER]
PALETTE_LIST = [PALETTE_RAINBOW, VU_METER]
ALL_MODES = [PURPLE, GREEN, RED, BLUE, LIGHT_METER,
             PALETTE_RAINBOW, VU_METER]
color_index = 0
palette_index = 0
all_modes_index = ALL_MODES.index(LIGHT_METER) + 1  # next mode after light meter
BRIGHTNESS_STEP = 0.1
prev_button_a = False
prev_button_b = False

def apply_mode(selection):
    """Apply a mode from any list, clearing all other modes."""
    global active_palette, active_color, active_vu, active_light
    global vu_level, last_vu_input, light_level, last_light_color
    global input_floor, input_ceiling
    active_palette = None
    active_color = None
    active_vu = False
    active_light = False
    if selection == VU_METER:
        vu_level = 0.0
        last_vu_input = 0
        pixels.fill(VU_OFF)
        pixels.show()
        # Brief settle, then seed the adaptive floor
        time.sleep(0.15)
        for _ in range(3):
            mic.record(samples, len(samples))
        mic.record(samples, len(samples))
        input_floor = normalized_rms(samples) + 10
        input_ceiling = input_floor + 15.0
        active_vu = True
    elif selection == LIGHT_METER:
        light_level = 0.0
        last_light_color = (0, 0, 0)
        active_light = True
    elif isinstance(selection, list):
        active_palette = selection
    else:
        active_color = selection

while True:
    # set CPXb up so that it can be discovered by the app
    ble.start_advertising(advertisement)
    # Start with light meter mode
    apply_mode(LIGHT_METER)
    _ = accelo.tapped  # clear any startup tap
    time.sleep(0.5)    # brief delay to ignore boot vibration
    while not ble.connected:
        # Check physical buttons while waiting
        if button_a.value and not prev_button_a:
            apply_mode(COLOR_LIST[color_index])
            color_index = (color_index + 1) % len(COLOR_LIST)
        if button_b.value and not prev_button_b:
            apply_mode(PALETTE_LIST[palette_index])
            palette_index = (palette_index + 1) % len(PALETTE_LIST)
        prev_button_a = button_a.value
        prev_button_b = button_b.value
        # Check capacitive touch for brightness
        if touch_bright.value and not prev_touch_bright:
            pixels.brightness = min(1.0, pixels.brightness + BRIGHTNESS_STEP)
        if touch_dim.value and not prev_touch_dim:
            pixels.brightness = max(0.05, pixels.brightness - BRIGHTNESS_STEP)
        prev_touch_bright = touch_bright.value
        prev_touch_dim = touch_dim.value
        # Check accelerometer tap to cycle modes
        if accelo.tapped:
            apply_mode(ALL_MODES[all_modes_index])
            all_modes_index = (all_modes_index + 1) % len(ALL_MODES)
        update_palette()
        update_breathing()
        update_vu()
        update_light()
        time.sleep(0.02)

    # Now we're connected

    while ble.connected:
        # Check physical buttons
        if button_a.value and not prev_button_a:
            apply_mode(COLOR_LIST[color_index])
            color_index = (color_index + 1) % len(COLOR_LIST)
        if button_b.value and not prev_button_b:
            apply_mode(PALETTE_LIST[palette_index])
            palette_index = (palette_index + 1) % len(PALETTE_LIST)
        prev_button_a = button_a.value
        prev_button_b = button_b.value
        # Check capacitive touch for brightness
        if touch_bright.value and not prev_touch_bright:
            pixels.brightness = min(1.0, pixels.brightness + BRIGHTNESS_STEP)
        if touch_dim.value and not prev_touch_dim:
            pixels.brightness = max(0.05, pixels.brightness - BRIGHTNESS_STEP)
        prev_touch_bright = touch_bright.value
        prev_touch_dim = touch_dim.value
        # Check accelerometer tap to cycle modes
        if accelo.tapped:
            apply_mode(ALL_MODES[all_modes_index])
            all_modes_index = (all_modes_index + 1) % len(ALL_MODES)

        # Keep animating the active mode
        update_palette()
        update_breathing()
        update_vu()
        update_light()

        if uart_service.in_waiting:
            try:
                packet = Packet.from_stream(uart_service)
            except ValueError:
                continue # or pass.

            if isinstance(packet, ColorPacket): # check if a color was sent from color picker
                active_palette = None
                active_color = None
                active_vu = False
                active_light = False
                pixels.fill(packet.color)
            if isinstance(packet, ButtonPacket): # check if a button was pressed from control pad
                if packet.pressed:
                    if packet.button == ButtonPacket.BUTTON_1: # Rainbow palette
                        apply_mode(PALETTE_RAINBOW)
                    if packet.button == ButtonPacket.BUTTON_2: # VU Meter
                        apply_mode(VU_METER)
                    if packet.button == ButtonPacket.BUTTON_3: # Purple
                        apply_mode(PURPLE)
                    if packet.button == ButtonPacket.BUTTON_4: # Light Meter
                        apply_mode(LIGHT_METER)
                    if packet.button == ButtonPacket.UP: # Brighten
                        pixels.brightness = min(1.0, pixels.brightness + BRIGHTNESS_STEP)
                    if packet.button == ButtonPacket.DOWN: # Dim
                        pixels.brightness = max(0.05, pixels.brightness - BRIGHTNESS_STEP)
                    if packet.button == ButtonPacket.LEFT: # Cycle modes backward
                        all_modes_index = (all_modes_index - 1) % len(ALL_MODES)
                        apply_mode(ALL_MODES[all_modes_index])
                    if packet.button == ButtonPacket.RIGHT: # Cycle modes forward
                        apply_mode(ALL_MODES[all_modes_index])
                        all_modes_index = (all_modes_index + 1) % len(ALL_MODES)

        time.sleep(0.02)  # small delay for smooth animation
