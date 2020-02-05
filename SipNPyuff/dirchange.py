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

prev_direction = None
pressure_list = []
while True:
    pressure = lps.pressure
    if pressure > 0:
        if pressure > max_postive:
            max_postive = pressure
            # print ("new max positive pressure: %0.2f"%pressure)
        if pressure > 10:
            # print("PUFF")
            pass
    else:
        if pressure < max_negative:
            max_negative = pressure
            #print ("new max negative pressure: %0.2f"%pressure)
        if pressure < -10:
            # print("SIP")
            pass
    time.sleep(0.01)
    pressure_list.append(pressure)
    # print("Pressure List:", pressure_list)
    # print("pressure list length:", len(pressure_list))
    if len(pressure_list) > 8:
        pressure_list.pop(0)

    if len(pressure_list)  == 8:
        direction = PuffDetector.direction(pressure_list)
        if prev_direction:
            direction_changed = PuffDetector.direction_changed(pressure_list, prev_direction)
            # print("Direction:", direction)
            # print("Direction changed:", direction_changed)
            if direction_changed:
                print("DIRECTION CHANGED!")
        prev_direction = direction