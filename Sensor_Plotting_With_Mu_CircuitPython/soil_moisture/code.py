import time
from adafruit_circuitplayground.express import cpx
import touchio
import simpleio
import board

cpx.pixels.brightness = 0.2
touch = touchio.TouchIn(board.A1)

DRY_VALUE = 1500  # calibrate this by hand!
WET_VALUE = 2100  # calibrate this by hand!

while True:
    value_A1 = touch.raw_value
    print((value_A1,))

    # fill the pixels from red to green based on soil moisture
    percent_wet = int(simpleio.map_range(value_A1, DRY_VALUE, WET_VALUE, 0, 100))
    cpx.pixels.fill((100-percent_wet, percent_wet, 0))
    time.sleep(0.5)
