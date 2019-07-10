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

LED13 = digitalio.DigitalInOut(board.D13)
LED13.direction = digitalio.Direction.OUTPUT

pixel_pin = board.D5
num_pixels = 21
pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.8)
pixels.fill((0, 0, 0))
COLOR = (0, 200, 0)  # Green 

# Bitmap values for each value. These can be OR'ed together
THREE = 0b00000000000000000001
EIGHT = 0b00000000000000000010
ELEVEN = 0b00000000000000000100
TWO = 0b00000000000000001000
SIX = 0b00000000000000010000
FOUR = 0b00000000000000100000
SEVEN = 0b00000000000001000000
NOON = 0b00000000000010000000
TEN = 0b00000000000100000000
ONE = 0b00000000001000000000
FIVE = 0b00000000010000000000
MIDNIGHT = 0b00000000100000000000
NINE = 0b00000001000000000000
PAST = 0b00000010000000000000
TO = 0b00000100000000000000
FIVEMIN = 0b00001000000000000000
QUARTER = 0b00010000000000000000
TENMIN = 0b00100000000000000000
HALF = 0b01000000000000000000
TWENTY = 0b10000000000000000000

def writetime(the_hr, the_min):  # Pass in hour and minute, return LED bitmask
    value = 0b00000000000000000000
    if (the_hr == 24) and (the_min == 0):  # Special cases: Midnight and Noon
        return MIDNIGHT
    if (the_hr == 12) and (the_min == 0):
        return NOON
    # set minute
    if (the_min > 4) and (the_min < 10):
        value = value | FIVEMIN
    if (the_min > 9) and (the_min < 15):
        value = value | TENMIN
    if (the_min > 14) and (the_min < 20):
        value = value | QUARTER
    if (the_min > 19) and (the_min < 25):
        value = value | TWENTY
    if (the_min > 25) and (the_min < 30):
        value = value | TWENTY | FIVEMIN
    if (the_min > 29) and (the_min < 35):
        value = value | HALF
    if (the_min > 34) and (the_min < 40):
        value = value | TWENTY | FIVEMIN
    if (the_min > 39) and (the_min < 45):
        value = value | TWENTY
    if (the_min > 44) and (the_min < 50):
        value = value | QUARTER
    if (the_min > 49) and (the_min < 55):
        value = value | TENMIN
    if the_min > 54:
        value = value | FIVEMIN
    # before or after
    if the_min <= 30:
        value = value | PAST
    else:
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

# Main loop
LEDstate = 0

while True:
    t = rtc.datetime
    # print("The date is {} {}/{}/{}".format(days[int(t.tm_wday)],
    #        t.tm_mday, t.tm_mon, t.tm_year))
    # print("The time is {}:{:02}:{:02}".format(t.tm_hour, t.tm_min, t.tm_sec))
    hour = t.tm_hour
    minute = t.tm_min
    second = t.tm_sec
    if second == 59:
        print("The time is {}:{:02}".format(t.tm_hour, t.tm_min))
        pixels.fill((0, 0, 0))       # blank all pixels for change
        the_time = writetime(hour, minute)
        for i in range(1, 21):       # Check all 30 bits
            if the_time & 1 << i:    # If the bit is true
                pixels[i+1] = COLOR  # set pixel on (shift up 2 for buried one)
        pixels.show()
    if LEDstate == 0:       # Flash the D13 LED every other second for activity
        LED13.value = True
        LEDstate = 1
    else:
        LED13.value = False
        LEDstate = 0
    time.sleep(1)  # wait a second
