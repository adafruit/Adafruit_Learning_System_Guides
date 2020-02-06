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


puff_start = time.monotonic()


if CONSOLE:
    print("CONSOLE?")
if DEBUG and CONSOLE:
    print("Debug CONSOLE")


while True:
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
