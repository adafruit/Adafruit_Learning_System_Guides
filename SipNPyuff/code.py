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
detector = PuffDetector(min_pressure=8, high_pressure=20)
time.sleep(1)


puff_start = time.monotonic()


if CONSOLE:
    print("CONSOLE?")
if DEBUG and CONSOLE:
    print("Debug CONSOLE")


while True:
    ######################################
    splash = displayio.Group(max_size=10)
    # Set text, font, and color
    font = terminalio.FONT
    color = 0xFFFFFF

    # Create the tet label
    text_area = label.Label(font, text="SIP-N-PYUFF", color=color)
    text_area2 = label.Label(font, text="STRING TWO", color=color)
    text_area3 = label.Label(font, text=str(time.monotonic()), color=color)

    # Set the location
    text_area.x = 0
    text_area.y = 0 + Y_OFFSET
    # Set the location

    text_area2.x = 20
    text_area2.y = 10 + Y_OFFSET
    x, y, w, h = text_area3.bounding_box
    text_area3.x = DISPLAY_WIDTH - w
    text_area3.y = BOTTOM_ROW + Y_OFFSET

    splash.append(text_area)
    splash.append(text_area2)
    splash.append(text_area3)
    # Show it
    display.show(splash)

    ######################################
    current_pressure = lps.pressure
    if not CONSOLE:
        print((current_pressure,))
    puff_polarity, puff_peak_level, puff_duration = detector.check_for_puff(
        current_pressure
    )

    if CONSOLE and puff_duration is None and puff_polarity:
        print("START", end=" ")
        if puff_polarity == 1:
            print("PUFF")
        if puff_polarity == -1:
            print("SIP")
    if CONSOLE and puff_duration:

        print("END", end=" ")
        if puff_peak_level == 1:
            print("SOFT", end=" ")
        if puff_peak_level == 2:
            print("HARD", end=" ")

        if puff_polarity == 1:
            print("PUFF")
        if puff_polarity == -1:
            print("SIP")

        print("Duration:", puff_duration)
    time.sleep(0.01)
