import time
import board
import busio
import adafruit_lps35hw
from puff_detector import PuffDetector




i2c = busio.I2C(board.SCL, board.SDA)
# i2c = DebugI2C(i2c)
lps = adafruit_lps35hw.LPS35HW(i2c, 0x5C)

lps.zero_pressure()
lps.data_rate = adafruit_lps35hw.DataRate.RATE_75_HZ

min_pressure = 8
high_pressure = 20
# sip/puff is "over" on keyup/pressure direction reversal
# averaging code

lps.filter_enabled = True
# print("Filter enabled:", lps.low_pass_enabled)

lps.filter_config = True
# print("Filter Config:", lps.low_pass_config)
detector = PuffDetector(min_pressure=8, high_pressure=20)
time.sleep(1)
prev_direction = None
pressure_list = []
pressure_type = tuple()
prev_pressure_type = tuple()
puff_start = time.monotonic()
current_level = 0
prev_level = 0
puff_end = puff_start
prev_duration = 0
while True:
    current_pressure = lps.pressure
    # print((current_pressure,))

    pressure_type = detector.catagorize_pressure(current_pressure)

    if pressure_type != prev_pressure_type:
        puff_end = time.monotonic()
        puff_duration = puff_end - puff_start
        puff_start = puff_end
        # print("\tpressure type:", pressure_type)
        # print("duration:", puff_duration)
        direction, level = pressure_type
        # print("direction:", direction, "level:", level)

        if (direction == 1) and (prev_level > level):
            print("Down")
            puff_duration += prev_duration
            level = prev_level
        if (direction == -1) and (prev_level < level):
            print("Up")
            puff_duration += prev_duration
            level = prev_level

        # print("direction:", direction, "level:", level)
        if puff_duration > 0.2:
            print("direction:", direction, "level:", level)

            print("\tduration:", puff_duration)
            #   print(current_pressure)
            label = detector.pressure_string((direction, level))
            label = detector.pressure_string(pressure_type)
            print("\t\t\t\t", label)
            print("____________________")
        prev_pressure_type = pressure_type
        prev_duration = puff_duration
    prev_level = level
    time.sleep(0.01)
