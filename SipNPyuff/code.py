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
min_pressure = 8
high_pressure = 20
# sip/puff is "over" on keyup/pressure direction reversal
# averaging code

# find reasonable band estimatesV

prev_direction = None
pressure_list = []
while True:
    pressure_level = 0
    pressure = lps.pressure
    if abs(pressure) > 10:
        pressure_level = 1
    if abs(pressure) > high_pressure:
        pressure_level = 2
    if pressure > 0:
       if pressure_level == 1:
           print("SOFT PUFF", end="\n\n")
       if pressure_level == 2:
           print("HARD PUFF", end="\n\n")
        
    else:
        # if pressure < max_negative:
        #     max_negative = pressure
        #     #print ("new max negative pressure: %0.2f"%pressure)
        if pressure_level == 1:
           print("SOFT SIP", end="\n\n")
        if pressure_level == 2:
           print("HARD SIP", end="\n\n")
        
    time.sleep(0.01)