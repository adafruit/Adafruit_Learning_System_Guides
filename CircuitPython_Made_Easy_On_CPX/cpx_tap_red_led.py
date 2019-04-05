import time
from adafruit_circuitplayground.express import cpx

cpx.detect_taps = 2

while True:
    if cpx.tapped:
        print("Tapped!")
        cpx.red_led = True
        time.sleep(0.1)
    else:
        cpx.red_led = False
