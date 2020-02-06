import time
import board
import adafruit_lps35hw

import displayio
import terminalio
from adafruit_display_text import label
import adafruit_displayio_ssd1306
from puff_detector import PuffDetector

displayio.release_displays()
oled_reset = board.D9

DISPLAY_WIDTH = 128
# DISPLAY_HEIGHT = 32
DISPLAY_HEIGHT = 64  # Change to 64 if needed
BORDER = 1
Y_OFFSET = 3
TEXT_HEIGHT = 8
BOTTOM_ROW = DISPLAY_HEIGHT - TEXT_HEIGHT - Y_OFFSET

i2c = board.I2C()
# 128x32
# display_bus = displayio.I2CDisplay(i2c, device_address=0x3C, reset=oled_reset)
# 128x64
display_bus = displayio.I2CDisplay(i2c, device_address=0x3D, reset=oled_reset)

display = adafruit_displayio_ssd1306.SSD1306(
    display_bus, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT
)


# i2c = DebugI2C(i2c)
lps = adafruit_lps35hw.LPS35HW(i2c, 0x5C)
CONSOLE = True
DEBUG = True

lps.zero_pressure()
lps.data_rate = adafruit_lps35hw.DataRate.RATE_75_HZ

min_pressure = 8
high_pressure = 20
# sip/puff is "over" on keyup/pressure polarity reversal
# averaging code

lps.filter_enabled = True
# if CONSOLE: print("Filter enabled:", lps.low_pass_enabled)

lps.filter_config = True
# if CONSOLE: print("Filter Config:", lps.low_pass_config)
detector = PuffDetector(min_pressure=8, high_pressure=40)
time.sleep(1)


puff_start = time.monotonic()


if CONSOLE:
    print("CONSOLE?")
if DEBUG and CONSOLE:
    print("Debug CONSOLE")

color = 0xFAFAFA

font = terminalio.FONT

banner_string = "PUFF-O-TRON-9000"
state_string = "  "
pressure_string = " "
input_type_string = " "

state_display_timeout = 1.0
state_display_start = 0
while True:
    ######################################
    splash = displayio.Group(max_size=10)
    # Set text, font, and color

    ######################################
    current_pressure = lps.pressure
    pressure_string = "Pressure: %0.3f" % current_pressure
    if not CONSOLE:
        print((current_pressure,))
    puff_polarity, puff_peak_level, puff_duration = detector.check_for_puff(
        current_pressure
    )

    if CONSOLE and puff_duration is None and puff_polarity:
        if puff_polarity == 1:
            state_string = "PUFF"
        if puff_polarity == -1:
            state_string = "SIP"
        state_string += " START"

    if CONSOLE and puff_duration:

        state_string = "DETECTED:"
        print(state_string)
        if puff_peak_level == 1:
            input_type_string = "SOFT"
        if puff_peak_level == 2:
            input_type_string = "HARD"

        if puff_polarity == 1:
            input_type_string += " PUFF"
        if puff_polarity == -1:
            input_type_string += " SIP"
        print("END", end=" ")
        print(input_type_string)
        duration_string = "Duration: %0.2f" % puff_duration
        print(duration_string)
    # Create the tet label
    if puff_polarity == 0:
        state_string = "Waiting for Input"
    banner = label.Label(font, text=banner_string, color=color)
    state = label.Label(font, text=state_string, color=color)
    detector_result = label.Label(font, text=input_type_string, color=color)
    text_area4 = label.Label(font, text=state_string, color=color)
    pressure_label = label.Label(font, text=pressure_string, color=color)

    banner.x = 0
    banner.y = 0 + Y_OFFSET

    state.x = 20
    state.y = 10 + Y_OFFSET
    detector_result.x = 20
    detector_result.y = 20 + Y_OFFSET

    x, y, w, h = pressure_label.bounding_box
    pressure_label.x = DISPLAY_WIDTH - w
    pressure_label.y = BOTTOM_ROW + Y_OFFSET

    splash.append(banner)
    splash.append(state)
    splash.append(detector_result)
    splash.append(pressure_label)
    # Show it
    display.show(splash)
    time.sleep(0.01)
