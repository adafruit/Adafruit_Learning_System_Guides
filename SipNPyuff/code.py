import time
import board
import busio
import adafruit_lps35hw
from puff_detector import PuffDetector

i2c = busio.I2C(board.SCL, board.SDA)
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
prev_polarity = None
pressure_list = []
pressure_type = tuple()
prev_pressure_type = tuple()
puff_start = time.monotonic()
current_level = 0
prev_level = 0
puff_end = puff_start
prev_duration = 0
start_polarity = 0
prev_pressure = 0
PRINT_FLOOR = 5
if CONSOLE:
    print("CONSOLE?")
if DEBUG and CONSOLE:
    print("Debug Console")
counter = 0
while True:
    current_pressure = lps.pressure
    if not CONSOLE:
        print((current_pressure,))

    pressure_type = detector.catagorize_pressure(current_pressure, prev_pressure)
    polarity, level, direction = pressure_type
    # if (polarity != 0) or (level != 0):
    if abs(current_pressure) > PRINT_FLOOR:
        if counter % 4 == 0:
            if DEBUG and CONSOLE:
                print("\t\t\tpressure:", current_pressure)

    if level != 0 and start_polarity == 0:  ###
        start_polarity = polarity
        puff_start = time.monotonic()
        if CONSOLE:
            print("START", end=" ")
            if start_polarity == 1:
                print("PUFF")
            if start_polarity == -1:
                print("SIP")

    if (level == 0) and (start_polarity != 0):
        duration = time.monotonic() - puff_start
        if CONSOLE:
            print("END", end=" ")
            if start_polarity == 1:
                print("PUFF", "")
            if start_polarity == -1:
                print("SIP", "")
            print("Duration:", duration)
        start_polarity = 0
    prev_level = level
    prev_pressure = current_pressure
    time.sleep(0.01)
    counter += 1
