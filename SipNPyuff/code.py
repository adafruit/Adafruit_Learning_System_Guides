import time
import board
import busio
import adafruit_lps35hw
from puff_detector import PuffDetector
from adafruit_debug_i2c import DebugI2C




    # if pressure > 0:
    #     if pressure_level == 1:
    #         pressure_type = "Soft Puff"
    #     if pressure_level == 2:
    #         pressure_type = "Hard Puff"
    # else:

    #     if pressure_level == 1:
    #         pressure_type = "Soft Sip"
    #     if pressure_level == 2:
    #         pressure_type = "Hard Sip"
#pylint:disable:invalid-name

def catagorize_pressure(pressure):
    """determine the strength and polarity of the pressure reading"""
    level = 0
    direction = 0
    abs_pressure = abs(pressure)

    if abs_pressure > min_pressure:
        level = 1
    if abs_pressure > high_pressure:
        level = 2

    if level != 0:
        if pressure > 0:
            direction = 1
        else:
            direction = -1

    return (direction, level)

def pressure_string(pressure_type):
    dir, level =  pressure_type
    pressure_str = ""
    print("pressure level:", level)
    if level == 1:
        pressure_str = "LOW"
    elif level == 2:
        presure_str = "HIGH"

    if dir == 1:
        pressure_str += "PUFF"
    elif dir == -1:
        pressure_str += "SIP"
    return pressure_str

i2c = busio.I2C(board.SCL, board.SDA)
# i2c = DebugI2C(i2c)
lps = adafruit_lps35hw.LPS35HW(i2c, 0x5c)

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

    pressure_type = catagorize_pressure(current_pressure)

    if pressure_type != prev_pressure_type:
        puff_end = time.monotonic()
        puff_duration = puff_end-puff_start
        puff_start = puff_end
        print("\tpressure type:", pressure_type)
        print("duration:", puff_duration)
        direction, level = pressure_type
        print("direction:", direction, "level:", level)

        if (direction == 1) and (prev_level > level):
            print("\tDown")
            puff_duration += prev_duration
            level = prev_level
        if (direction == -1) and (prev_level < level):
            print("\tUp")
            puff_duration += prev_duration
            level = prev_level
        
        print("direction:", direction, "level:", level)
        if puff_duration > 0.2:
            print("\tduration:", puff_duration)
            print(current_pressure)
            label = pressure_string(pressure_type)
            print(label)
            print("____________________")
        prev_pressure_type = pressure_type
        prev_duration = puff_duration
    prev_level = level
    time.sleep(0.01)