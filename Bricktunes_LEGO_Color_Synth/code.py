# SPDX-FileCopyrightText: 2023 John Park for Adafruit
# SPDX-License-Identifier: MIT

# Bricktunes LEGO Color Synth
# Feather RP2040 Prop-Maker + AS7341 Color Sensor
# Color comparison code and chime library by CGrover

import time
import math
import board
import digitalio
import audiobusio
from adafruit_as7341 import AS7341, Gain
import audiomixer
from cedargrove_chime import Chime, Voice, Material, Striker

DEBUG = False  # Useful for tuning reference color values by printing them
TOLERANCE = 800  # The color matching tolerance index (0 to 8 * max_sensor_count)

sensor = AS7341(board.STEMMA_I2C())
sensor.astep = 128  # (999) The integration time step size in 2.78 microsecond increments
sensor.atime = 50  # The integration time step count.
sensor.gain = Gain.GAIN_256X
sensor.led_current = 4  # increments in units of 4
sensor.led = True
max_sensor_count = (sensor.astep + 1) * (sensor.atime + 1)

# ===================================================
# color lists as 8-channel tuples (channels[0:8])
brick_full_spectrum_values = [
                                (94, 1310, 1736, 1075, 592, 437, 497, 383),  # Blue
                                (148, 324, 838, 2577, 2363, 1259, 929, 819),  # Bright Green
                                (381, 576, 850, 1619, 3688, 5532, 6291, 4250),  # Bright Lt Orange
                                (404, 2300, 2928, 2385, 2679, 3804, 5576, 4284),  # Bright Pink
                                (545, 1276, 1513, 1178, 2291, 6579, 6579, 6486),  # Coral
                                (136, 1055, 1223, 745, 748, 768, 1205, 1100),  # Dark Purple
                                (85, 731, 1375, 1604, 1019, 557, 533, 370),  # Dark Turquoise
                                (451, 2758, 3786, 2880, 3007, 3064, 4539, 3656),  # Lavender
                                (214, 300, 771, 1811, 3245, 2897, 2051, 1392),  # Lime
                                (188, 341, 435, 507, 625, 1703, 4361, 3692),  # Red
                                (182, 870, 1455, 1799, 2149, 1879, 1702, 1273),  # Sand Green
                                (461, 497, 878, 2412, 4699, 5935, 6579, 4677)  # Yellow
]

brick_color_names = [
                        "Blue",
                        "Bright Green",
                        "Bright Light Orange",
                        "Bright Pink",
                        "Coral",
                        "Dark Purple",
                        "Dark Turquoise",
                        "Lavender",
                        "Lime",
                        "Red",
                        "Sand Green",
                        "Yellow"
]

brick_states = [False] * (len(brick_color_names))
gap_state = False

# ===================================================
# audio setup
power = digitalio.DigitalInOut(board.EXTERNAL_POWER)
power.switch_to_output(value=True)
audio_output = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)

mixer = audiomixer.Mixer(sample_rate=11020, buffer_size=4096, voice_count=1, channel_count=1)
audio_output.play(mixer)
mixer.voice[0].level = 0.50  # adjust this for overall volume

brickscale = [
        "C5", "D5", "E5", "F5", "G5", "A5", "B5",
        "C6", "D6", "E6", "F6", "G6", "A6", "B6",
        "C7", "D7", "E7", "F7", "G7", "A7", "B7",
]

# Instantiate the chime synthesizer with custom parameters
chime = Chime(
                mixer.voice[0],
                scale=brickscale,
                material=Material.Brass,  # SteelEMT, Ceramic, Wood, Copper, Aluminum, Brass
                striker=Striker.HardWood,  # Metal, Plexiglas, SoftWood, HardWood
                voice=Voice.Tubular,  # bell, perfect, tubular
                scale_offset=-16
)

# Play scale notes sequentially
for index, note in enumerate(chime.scale):
    chime.strike(note, 1.0)
    time.sleep(0.1)
time.sleep(1)

def compare_n_channel_colors(color_1, color_2, tolerance=0):
    """Compares two integer multichannel count tuples using an unweighted linear
    Euclidean difference. If the color value difference is within the tolerance
    band of the reference, the method returns True.
    The difference value index `tolerance` is used to detect color similarity.
    Value range is an integer value from 0 to
    (maximum_channel_count * number_of_channels). Default is 0 (detects a
    single color value)."""
    # Create list of channel deltas using list comprehension
    deltas = [((color_1[idx] - count) ** 2) for idx, count in enumerate(color_2)]
    # Resolve squared deltas to a Euclidean difference
    # pylint: disable=c-extension-no-member
    delta_color = math.sqrt(sum(deltas))
    return bool(delta_color <= tolerance)

print("Bricktunes ready")


while True:
    sensor_color = sensor.all_channels
    # don't bother to check comparison when we're looking at a gap between bricks
    if sensor_color[0] <= 70:   # this checks for a minimum value on one channel
        if gap_state is False:
            print("no brick...")
            for i in range(len(brick_color_names)):
                brick_states[i] = False
            gap_state = True

    else:
        if DEBUG:
            print(sensor_color)
        for i in range(len(brick_full_spectrum_values)):
            color_match = compare_n_channel_colors(
                                                    sensor_color,
                                                    brick_full_spectrum_values[i],
                                                    TOLERANCE
            )

            if color_match is True:
                if brick_states[i] is False:
                    for n in range(5):
                        chime.strike(chime.scale[i+(n*2)], 1.0)
                        time.sleep(0.1)
                    brick_states[i] = True
                    gap_state = False
                    print("sensor color:", sensor_color, "| ref:", brick_full_spectrum_values[i])
                    print(brick_color_names[i])
                break
