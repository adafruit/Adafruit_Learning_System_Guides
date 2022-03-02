# SPDX-FileCopyrightText: 2020 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import struct
import displayio
import terminalio
from microcontroller import nvm
from adafruit_display_text import label
import adafruit_imageload
from adafruit_clue import clue

# ==| USER CONFIG |=====================
USE_METRIC = False
DISPLAY_UPDATE = 1
HOLD_TO_SET = 1
FONT = terminalio.FONT
BLUE = 0x53E4FF
ORANGE = 0xFCDF03
RED = 0xFA0000
DEBOUNCE = 0.05
SAMPLES = 10
DELAY = 0.05
STD_SLP = 1013.25
# ==| USER CONFIG |=====================

# configure pressure sensor (see Table 15 in datasheet)
clue._pressure.mode = 0x03  # normal
clue._pressure.overscan_pressure = 0x05  # x16
clue._pressure.overscan_temperature = 0x02  # x2
clue._pressure.iir_filter = 0x02  # 4
clue._pressure.standby_period = 0x01  # 62.5 ms

# restore saved sea level pressure from NVM
slp = struct.unpack("f", nvm[0:4])[0]
clue.sea_level_pressure = slp if 0 < slp < 2000 else STD_SLP

# --------------------------------------------------------------------
# D I S P L A Y    S E T U P
# --------------------------------------------------------------------

# create main display group
splash = displayio.Group()
clue.display.show(splash)

# background
bg_bmp, bg_pal = adafruit_imageload.load(
    "/network23.bmp", bitmap=displayio.Bitmap, palette=displayio.Palette
)
for i, color in enumerate(bg_pal):
    if color == 0xFF0000:
        bg_pal.make_transparent(i)
        break
background = displayio.TileGrid(bg_bmp, pixel_shader=bg_pal)

# a group for both altitude readouts
alti_readouts = displayio.Group(scale=6)

# altitude (corrected)
alti_disp = label.Label(FONT, text="12345", color=ORANGE)
alti_disp.anchor_point = (0, 0)
alti_disp.anchored_position = (7, 2)

# altitude (uncorrected)
alt2_disp = label.Label(FONT, text="12345", color=ORANGE)
alt2_disp.anchor_point = (0, 0)
alt2_disp.anchored_position = (7, 15)

# add both alti's to group
alti_readouts.append(alti_disp)
alti_readouts.append(alt2_disp)

# barometric pressure and temperature
aux_data = label.Label(FONT, text="P: 1234.56  T: 123.4", color=BLUE)
aux_data.anchor_point = (0, 0)
aux_data.anchored_position = (16, 212)

# calibration mode indicator
cal_mode = label.Label(FONT, text="   ", color=RED, scale=4, x=150, y=200)

# add everything to splash
splash.append(background)
splash.append(alti_readouts)
splash.append(aux_data)
splash.append(cal_mode)

# --------------------------------------------------------------------
# H E L P E R    F U N C T I O N S
# --------------------------------------------------------------------
def compute_altitude(barometric_pressure, sea_level_pressure):
    """Compute altitude (m) from barometric pressure (hPa) and sea level pressure (hPa)."""
    # https://www.weather.gov/media/epz/wxcalc/pressureAltitude.pdf
    return 44307.69396 * (1 - pow((barometric_pressure / sea_level_pressure), 0.190284))


def compute_sea_level_pressure(barometric_pressure, altitude):
    """Compute sea level pressure (hPa) from barometric pressure (hPa) and altitude (m)."""
    return barometric_pressure * pow((1 - (altitude / 44307.69396)), -5.2553)


def average_readings(samples=10, delay=0.05):
    """Return averaged readings for pressure and temperature."""
    pressure = 0
    temperature = 0
    for _ in range(samples):
        pressure += clue.pressure
        temperature += clue.temperature
        time.sleep(delay)
    return pressure / samples, temperature / samples


def recalibrate(current_sea_level_pressure=None):
    """Enter current altitude."""
    cal_mode.text = "CAL"
    alt2_disp.text = "-----"
    # wait for release if still being held
    while clue.button_a and clue.button_b:
        pass
    # get current value
    altitude = int(alti_disp.text)
    done = False
    while not done:
        now = time.monotonic()
        # increase
        if clue.button_a and not clue.button_b:
            altitude -= 1
            time.sleep(DEBOUNCE)
        # decrease
        elif clue.button_b and not clue.button_a:
            altitude += 1
            time.sleep(DEBOUNCE)
        # hold both to set
        elif clue.button_a and clue.button_b:
            while clue.button_a and clue.button_b:
                if time.monotonic() - now > HOLD_TO_SET:
                    print("done")
                    done = True
                    break
        alti_disp.text = "{:5d}".format(altitude)
    cal_mode.text = "   "
    # change clue settings
    if not USE_METRIC:
        altitude *= 0.3048
    # get current local pressure
    barometric_pressure, _ = average_readings(SAMPLES, DELAY)
    # compute sea level pressure and set
    clue.sea_level_pressure = compute_sea_level_pressure(barometric_pressure, altitude)
    # store in NVM for later use
    nvm[0:4] = struct.pack("f", clue.sea_level_pressure)


def update_display():
    """Update the display with latest info."""
    barometric_pressure, temperature = average_readings(SAMPLES, DELAY)
    altitude = compute_altitude(barometric_pressure, clue.sea_level_pressure)
    alt2tude = compute_altitude(barometric_pressure, STD_SLP)
    if not USE_METRIC:
        altitude *= 3.28084  # ft
        alt2tude *= 3.28084
        # barometric_pressure *= 0.0145038      # psi
        temperature = 32 + 1.8 * temperature  # deg F
    alti_disp.text = "{:5d}".format(int(altitude))
    alt2_disp.text = "{:5d}".format(int(alt2tude))
    aux_data.text = "P: {:7.2f}  T: {:5.1f}".format(barometric_pressure, temperature)


# --------------------------------------------------------------------
# M A I N    L O O P
# --------------------------------------------------------------------
last_update = time.monotonic()

while True:

    now = time.monotonic()

    # update display with latest info
    if now - last_update > DISPLAY_UPDATE:
        update_display()
        last_update = now

    # hold both to recalibrate
    if clue.button_a and clue.button_b:
        # accumulate hold time
        while clue.button_a and clue.button_b:
            if time.monotonic() - now > HOLD_TO_SET:
                print("set")
                recalibrate(clue.sea_level_pressure)
                break
        # wait for release if still being held
        while clue.button_a and clue.button_b:
            pass
