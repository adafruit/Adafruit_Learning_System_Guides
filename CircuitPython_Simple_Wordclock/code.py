# Vertical Word Clock using the Adafruit Feather M4 and
#   the Adafruit DS3231 real-time clock FeatherWing

import time
import board
import busio as io
import digitalio
import adafruit_ds3231
import neopixel

i2c = io.I2C(board.SCL, board.SDA)

# Create the RTC instance:
rtc = adafruit_ds3231.DS3231(i2c)

# Set up Feather M4 onboard LED for output
LED13 = digitalio.DigitalInOut(board.D13)
LED13.direction = digitalio.Direction.OUTPUT

# Set digital 6 as an input for slide switch
Slide_Switch = digitalio.DigitalInOut(board.D6)
Slide_Switch.switch_to_input(pull=digitalio.Pull.UP)

pixel_pin = board.D5
num_pixels = 21
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=1.0,
                           auto_write=False)
pixels.fill((0, 0, 0))  # Blanking Display
COLOR = (0, 200, 0)     # Green for time later in code

# Bitmap values for each value. These can be OR'ed together
THREE = 1
EIGHT = 1 << 1
ELEVEN = 1 << 2
TWO = 1 << 3
SIX = 1 << 4
FOUR = 1 << 5
SEVEN = 1 << 6
NOON = 1 << 7
TEN = 1 << 8
ONE = 1 << 9
FIVE = 1 << 10
MIDNIGHT = 1 << 11
NINE = 1 << 12
PAST = 1 << 13
TO = 1 << 14
FIVEMIN = 1 << 15
QUARTER = 1 << 16
TENMIN = 1 << 17
HALF = 1 << 18
TWENTY = 1 << 19

# Pass in hour and minute, return LED bitmask
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
def writetime(the_hr, the_min):
    value = 0  # Start with zero, which is no words
    if (the_hr == 24) and (the_min == 0):  # Special cases: Midnight and Noon
        return MIDNIGHT
    if (the_hr == 12) and (the_min == 0):
        return NOON
    # set minute
    if (the_min > 3) and (the_min < 8):
        value = value | FIVEMIN
    if (the_min > 7) and (the_min < 13):
        value = value | TENMIN
    if (the_min > 12) and (the_min < 18):
        value = value | QUARTER
    if (the_min > 17) and (the_min < 23):
        value = value | TWENTY
    if (the_min > 22) and (the_min < 28):
        value = value | TWENTY | FIVEMIN
    if (the_min > 27) and (the_min < 33):
        value = value | HALF
    if (the_min > 32) and (the_min < 38):
        value = value | TWENTY | FIVEMIN
    if (the_min > 37) and (the_min < 43):
        value = value | TWENTY
    if (the_min > 42) and (the_min < 48):
        value = value | QUARTER
    if (the_min > 47) and (the_min <= 53):
        value = value | TENMIN
    if the_min >= 54:
        value = value | FIVEMIN
    # before or after
    if (the_min > 3) and (the_min <= 32):
        value = value | PAST
    if the_min >= 33:
        the_hr = the_hr + 1  # for the TO case
        value = value | TO
    # set hour
    if the_hr > 12:
        the_hr = the_hr - 12  # Convert 24 hour format to 12 hour
    if the_hr == 1:
        value = value | ONE
    if the_hr == 2:
        value = value | TWO
    if the_hr == 3:
        value = value | THREE
    if the_hr == 4:
        value = value | FOUR
    if the_hr == 5:
        value = value | FIVE
    if the_hr == 6:
        value = value | SIX
    if the_hr == 7:
        value = value | SEVEN
    if the_hr == 8:
        value = value | EIGHT
    if the_hr == 9:
        value = value | NINE
    if the_hr == 10:
        value = value | TEN
    if the_hr == 11:
        value = value | ELEVEN
    if the_hr == 0:
        value = value | MIDNIGHT
    if the_hr == 12:
        value = value | NOON
    return value
# end def
# pylint: enable=too-many-branches
# pylint: enable=too-many-statements

# Main loop
LEDstate = 0
Write_Now = True

while True:
    t = rtc.datetime
    # print("The date is {} {}/{}/{}".format(days[int(t.tm_wday)],
    #        t.tm_mday, t.tm_mon, t.tm_year))
    # print("The time is {}:{:02}:{:02}".format(t.tm_hour, t.tm_min, t.tm_sec))
    hour = t.tm_hour
    if not Slide_Switch.value:  # Slide switch activate = Daylight savings
        # print("Switch detected for daylight savings")
        if hour == 24:
            hour = 1
        else:
            hour += 1
        Write_Now = True  # Trigger a write
    minute = t.tm_min
    second = t.tm_sec
    if second == 59 or Write_Now:
        # print("The time is {}:{:02}".format(t.tm_hour, t.tm_min))
        pixels.fill((0, 0, 0))       # blank all pixels for change
        the_time = writetime(hour, minute)
        for i in range(0, 21):       # Check all bits
            if the_time & 1 << i:    # If the bit is true
                pixels[i+1] = COLOR  # set pixel on (shift up 2 for buried one)
        pixels.show()
    if LEDstate == 0:       # Flash the D13 LED every other second for activity
        LED13.value = True
        LEDstate = 1
    else:
        LED13.value = False
        LEDstate = 0
    Write_Now = False
    time.sleep(1)  # wait a second
