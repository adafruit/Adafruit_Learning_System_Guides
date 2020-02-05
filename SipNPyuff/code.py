import time
import board
import busio
import adafruit_lps35hw
from puff_detector import PuffDetector
from adafruit_debug_i2c import DebugI2C

#pylint:disable:invalid-name
def pressure_str(pressure):
    pressure_type = ""
    pressure_level = 0

    if abs(pressure) > 10:
        pressure_level = 1
    if abs(pressure) > high_pressure:
        pressure_level = 2
    if pressure > 0:
        if pressure_level == 1:
            pressure_type = "Soft Puff"
        if pressure_level == 2:
            pressure_type = "Hard Puff"
    else:

        if pressure_level == 1:
            pressure_type = "Soft Sip"
        if pressure_level == 2:
            pressure_type = "Hard Sip"
    return pressure_type


i2c = busio.I2C(board.SCL, board.SDA)
# i2c = DebugI2C(i2c)
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
print("Filter enabled:", lps.low_pass_enabled)
lps.filter_enabled = True
print("Filter enabled:", lps.low_pass_enabled)

print("Filter Config:", lps.low_pass_config)
lps.filter_config = True
print("Filter Config:", lps.low_pass_config)

prev_direction = None
pressure_list = []
pressure_type = ""
prev_pressure_type = ""
puff_start = 0
puff_end = 0
while True:
    pressure = lps.pressure
    # print((pressure,))

    pressure_type = pressure_str(pressure)
    if pressure_type != prev_pressure_type:
        puff_end = time.monotonic()
        print("duration:", puff_end-puff_start)
        puff_start = puff_end
        print(pressure_type)
    prev_pressure_type = pressure_type
    time.sleep(0.01)