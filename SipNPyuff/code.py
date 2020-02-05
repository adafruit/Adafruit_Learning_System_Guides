import time
import board
import busio
import adafruit_lps35hw
from puff_detector import PuffDetector

i2c = busio.I2C(board.SCL, board.SDA)

lps = adafruit_lps35hw.LPS35HW(i2c, 0x5c)

lps.zero_pressure()
lps.data_rate = adafruit_lps35hw.DataRate.RATE_75_HZ
max_postive = 0
max_negative = 0

# sip/puff is "over" on keyup/pressure direction reversal
# averaging code

# find reasonable band estimatesV
def direction_reversed(self, measurement_array):

while True:
    pressure = lps.pressure
    if pressure > 0:
        if pressure > max_postive:
            max_postive = pressure
            print ("new max positive pressure: %0.2f"%pressure)
        if pressure > 10:
            print("PUFF")
    else:
        if pressure < max_negative:
            max_negative = pressure
            print ("new max negative pressure: %0.2f"%pressure)
        if pressure < -10:
            print("SIP")
    time.sleep(0.01)
