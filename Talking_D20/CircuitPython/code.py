# SPDX-FileCopyrightText: 2023 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Talking D20 for Adafruit RP2040 Prop-Maker Feather.
Required additions:
- 8 Ohm 1 watt speaker (Adafruit #4227)
- 400 mAh LiPoly battery (Adafruit #3898)
- 3D printed enclosure
Optional additions:
- Battery monitoring can be added with two 10K resistors in series.
  One end to BAT, one to GND, and center point to an analog pin (e.g. A3).
  Then set BATT_SENSE in configurables section, e.g. BATT_SENSE = board.A3
"""


# pylint: disable=import-error
from random import randint
import time
import adafruit_lis3dh
import analogio
import audiocore
import audiobusio
import board
from digitalio import DigitalInOut, Direction

# CONFIGURABLES ------------------------------------------------------------

WAV_PATH = "WAVs"
WAV_FILES = (
    "01",  # Index 0 (WAV for face 1)
    "02",  # Index 1 (WAV for face 2)
    "03",  # etc...
    "04",
    "05",
    "06",
    "07",
    "08",
    "09",
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
    "16",
    "17",
    "18",
    "19",
    "20",
    "annc1",  # Index 20
    "annc2",
    "annc3",
    "bad1",  # Index 23
    "bad2",
    "bad3",
    "good1",  # Index 26
    "good2",
    "good3",
    "startup",  # Index 29
    "03alt",
    "batt1",
    "batt2",
)

BATT_SENSE = None  # Assign analog pin if voltage divider present
BATT_LOW = 3.4  # Voltage for battery warning (if BATT_SENSE)
FREEFALL_THRESHOLD = 8.65  # Near-freefall = 0.3G ^ 2
FREEFALL_MIN_DURATION = 1 / 25  # Time (seconds) roll is in near-freefall
SETTLE_TIME = 0.5  # Time (seconds) to settle on a face
SETTLE_TIMEOUT = 3.0  # If unsettled by this, resume freefall check

FACE_VECTORS = (  # Accelerometer vectors, shouldn't need to edit
    (-3.50, 0.00, 9.16),  # Face 1 (index 0)
    (5.66, -5.66, -5.66),  # Face 2 (index 1)
    (-9.16, 3.50, 0.00),  # 3 etc...
    (9.16, 3.50, 0.00),
    (5.66, -5.66, 5.66),  # 5
    (0.00, 9.16, -3.50),
    (-5.66, -5.66, 5.66),
    (-3.50, 0.00, -9.16),
    (0.00, 9.16, 3.50),
    (-5.66, -5.66, -5.66),  # 10
    (5.66, 5.66, 5.66),
    (0.00, -9.16, -3.50),
    (3.50, 0.00, 9.16),
    (5.66, 5.66, -5.66),
    (0.00, -9.16, 3.50),  # 15
    (-5.66, 5.66, -5.66),
    (-9.16, -3.50, 0.00),
    (9.16, -3.50, 0.00),
    (-5.66, 5.66, 5.66),
    (3.50, 0.00, -9.16),  # 20
)

# HARDWARE SETUP -----------------------------------------------------------

# Enable power to audio amp, etc.
external_power = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value = True

# I2S audio out
audio = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)

# LIS3DH accelerometer
lis3dh = adafruit_lis3dh.LIS3DH_I2C(board.I2C())
lis3dh.range = adafruit_lis3dh.RANGE_4_G

# Battery monitor, if present (requires two 10K resistors)
if BATT_SENSE:
    adc = analogio.AnalogIn(BATT_SENSE)

# FUNCTIONS ----------------------------------------------------------------


def play(index, block=True):
    """Play one WAV file from the WAV_FILES table. Pass in table index (0-n)
    and optional 'block' flag (if True, function blocks until audio is
    finished playing)."""
    wave_file = open(f"{WAV_PATH}/{WAV_FILES[index]}.wav", "rb")
    wave = audiocore.WaveFile(wave_file)
    audio.play(wave)
    while block and audio.playing:
        pass


def freefall_wait():
    """Watch for freefall condition (low G for FREEFALL_MIN_DURATION)."""
    start_time = time.monotonic()
    while time.monotonic() - start_time < FREEFALL_MIN_DURATION:
        accel = lis3dh.acceleration
        if accel[0] ** 2 + accel[1] ** 2 + accel[2] ** 2 > FREEFALL_THRESHOLD:
            start_time = time.monotonic()


# pylint: disable=redefined-outer-name
def settle_wait():
    """Wait for die to stabilize (steady ~1G) on one number. Returns
    index of corresponding audio file (0-19 for faces 1-20), or -1
    if acceleration did not stabilize within SETTLE_TIMEOUT."""
    start_time = time.monotonic()
    prev_face = -1
    while time.monotonic() - start_time < SETTLE_TIMEOUT:
        accel = lis3dh.acceleration
        mag = accel[0] ** 2 + accel[1] ** 2 + accel[2] ** 2
        if 77.89 < mag < 116.35:  # ~1G
            face = -1
            min_dist = 1000000
            for index, vec in enumerate(FACE_VECTORS):
                dist_sq = (
                    (accel[0] - vec[0]) ** 2
                    + (accel[1] - vec[1]) ** 2
                    + (accel[2] - vec[2]) ** 2
                )
                if dist_sq < min_dist:  # New closest match?
                    min_dist = dist_sq  # Save closest distance^2
                    face = index  # Save index of closest match
            if face != prev_face:
                prev_face = face
                settle_start = time.monotonic()
            elif time.monotonic() - settle_start > SETTLE_TIME:
                return face
        else:
            prev_face = -1
    return -1


# STARTUP & MAIN LOOP ------------------------------------------------------

play(29, False)  # Play greeting (non-blocking)

# pylint: disable=invalid-name, used-before-assignment
while True:
    freefall_wait()  # Wait for roll
    face = settle_wait()  # Wait for landing (or timeout)
    if face >= 0:  # Not timeout...
        if face == 2:  # If '3' face
            if randint(0, 9) == 0:  # 1-in-10 chance of...
                face = 30  # Alternate 'face 3' track
        play(randint(20, 22))  # One of 3 random announcements
        play(face)  # Face number
        if face != 30:  # If not the alt face...
            if face <= 3:  # Index 0-3 (face 1-4) = bad
                play(randint(23, 25))  # Random jab
            elif face >= 16:  # index 16-19 (face 17-20) = good
                play(randint(26, 28))  # Random praise
        if BATT_SENSE:
            volts = adc.value / 65535 * 3.3 * 2
            if volts < BATT_LOW:
                time.sleep(0.5)
                play(randint(31, 32), False)
