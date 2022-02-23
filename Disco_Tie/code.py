# SPDX-FileCopyrightText: 2019 Collin Cunningham for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
LED Disco Tie with Bluetooth
=========================================================
Give your suit an sound-reactive upgrade with Circuit
Playground Bluefruit & Neopixels. Set color and animation
mode using the Bluefruit LE Connect app.

Author: Collin Cunningham for Adafruit Industries, 2019
"""
# pylint: disable=global-statement

import time
import array
import math
import audiobusio
import board
from rainbowio import colorwheel
import neopixel

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
from adafruit_bluefruit_connect.packet import Packet
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_bluefruit_connect.button_packet import ButtonPacket

ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)

# User input vars
mode = 0 # 0=audio, 1=rainbow, 2=larsen_scanner, 3=solid
user_color= (127,0,0)

# Audio meter vars
PEAK_COLOR = (100, 0, 255)
NUM_PIXELS = 10
NEOPIXEL_PIN = board.A1
# Use this instead if you want to use the NeoPixels on the Circuit Playground Bluefruit.
# NEOPIXEL_PIN = board.NEOPIXEL
CURVE = 2
SCALE_EXPONENT = math.pow(10, CURVE * -0.1)
NUM_SAMPLES = 160

# Restrict value to be between floor and ceiling.
def constrain(value, floor, ceiling):
    return max(floor, min(value, ceiling))

# Scale input_value between output_min and output_max, exponentially.
def log_scale(input_value, input_min, input_max, output_min, output_max):
    normalized_input_value = (input_value - input_min) / \
                             (input_max - input_min)
    return output_min + \
        math.pow(normalized_input_value, SCALE_EXPONENT) \
        * (output_max - output_min)

# Remove DC bias before computing RMS.
def normalized_rms(values):
    minbuf = int(mean(values))
    samples_sum = sum(
        float(sample - minbuf) * (sample - minbuf)
        for sample in values
    )

    return math.sqrt(samples_sum / len(values))

def mean(values):
    return sum(values) / len(values)

def volume_color(volume):
    return 200, volume * (255 // NUM_PIXELS), 0

# Set up NeoPixels and turn them all off.
pixels = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=0.1, auto_write=False)
pixels.fill(0)
pixels.show()

mic = audiobusio.PDMIn(board.MICROPHONE_CLOCK, board.MICROPHONE_DATA,
                       sample_rate=16000, bit_depth=16)

# Record an initial sample to calibrate. Assume it's quiet when we start.
samples = array.array('H', [0] * NUM_SAMPLES)
mic.record(samples, len(samples))
# Set lowest level to expect, plus a little.
input_floor = normalized_rms(samples) + 10
# Corresponds to sensitivity: lower means more pixels light up with lower sound
input_ceiling = input_floor + 500
peak = 0


def rainbow_cycle(delay):
    for j in range(255):
        for i in range(NUM_PIXELS):
            pixel_index = (i * 256 // NUM_PIXELS) + j
            pixels[i] = colorwheel(pixel_index & 255)
        pixels.show()
        time.sleep(delay)


def audio_meter(new_peak):
    mic.record(samples, len(samples))
    magnitude = normalized_rms(samples)

    # Compute scaled logarithmic reading in the range 0 to NUM_PIXELS
    c = log_scale(constrain(magnitude, input_floor, input_ceiling),
                  input_floor, input_ceiling, 0, NUM_PIXELS)

    # Light up pixels that are below the scaled and interpolated magnitude.
    pixels.fill(0)
    for i in range(NUM_PIXELS):
        if i < c:
            pixels[i] = volume_color(i)
        # Light up the peak pixel and animate it slowly dropping.
        if c >= new_peak:
            new_peak = min(c, NUM_PIXELS - 1)
        elif new_peak > 0:
            new_peak = new_peak - 1
        if new_peak > 0:
            pixels[int(new_peak)] = PEAK_COLOR
    pixels.show()
    return new_peak

pos = 0  # position
direction = 1  # direction of "eye"

def larsen_set(index, color):
    if index < 0:
        return
    else:
        pixels[index] = color

def larsen(delay):
    global pos
    global direction
    color_dark = (int(user_color[0]/8), int(user_color[1]/8),
                  int(user_color[2]/8))
    color_med = (int(user_color[0]/2), int(user_color[1]/2),
                 int(user_color[2]/2))

    larsen_set(pos - 2, color_dark)
    larsen_set(pos - 1, color_med)
    larsen_set(pos, user_color)
    larsen_set(pos + 1, color_med)

    if (pos + 2) < NUM_PIXELS:
        # Dark red, do not exceed number of pixels
        larsen_set(pos + 2, color_dark)

    pixels.write()
    time.sleep(delay)

    # Erase all and draw a new one next time
    for j in range(-2, 2):
        larsen_set(pos + j, (0, 0, 0))
        if (pos + 2) < NUM_PIXELS:
            larsen_set(pos + 2, (0, 0, 0))

    # Bounce off ends of strip
    pos += direction
    if pos < 0:
        pos = 1
        direction = -direction
    elif pos >= (NUM_PIXELS - 1):
        pos = NUM_PIXELS - 2
        direction = -direction

def solid(new_color):
    pixels.fill(new_color)
    pixels.show()

def map_value(value, in_min, in_max, out_min, out_max):
    out_range = out_max - out_min
    in_range = in_max - in_min
    return out_min + out_range * ((value - in_min) / in_range)

speed = 6.0
wait = 0.097

def change_speed(mod, old_speed):
    new_speed = constrain(old_speed + mod, 1.0, 10.0)
    return(new_speed, map_value(new_speed, 10.0, 0.0, 0.01, 0.3))

def animate(pause, top):
    # Determine animation based on mode
    if mode == 0:
        top = audio_meter(top)
    elif mode == 1:
        rainbow_cycle(0.001)
    elif mode == 2:
        larsen(pause)
    elif mode == 3:
        solid(user_color)
    return top

while True:
    ble.start_advertising(advertisement)
    while not ble.connected:
        # Animate while disconnected
        peak = animate(wait, peak)

    # While BLE is connected
    while ble.connected:
        if uart_service.in_waiting:
            try:
                packet = Packet.from_stream(uart_service)
            # Ignore malformed packets.
            except ValueError:
                continue

            # Received ColorPacket
            if isinstance(packet, ColorPacket):
                user_color = packet.color

            # Received ButtonPacket
            elif isinstance(packet, ButtonPacket):
                if packet.pressed:
                    if packet.button == ButtonPacket.UP:
                        speed, wait = change_speed(1, speed)
                    elif packet.button == ButtonPacket.DOWN:
                        speed, wait = change_speed(-1, speed)
                    elif packet.button == ButtonPacket.BUTTON_1:
                        mode = 0
                    elif packet.button == ButtonPacket.BUTTON_2:
                        mode = 1
                    elif packet.button == ButtonPacket.BUTTON_3:
                        mode = 2
                    elif packet.button == ButtonPacket.BUTTON_4:
                        mode = 3

        # Animate while connected
        peak = animate(wait, peak)
