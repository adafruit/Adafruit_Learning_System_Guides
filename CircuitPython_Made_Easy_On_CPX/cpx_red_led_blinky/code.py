import time
from adafruit_circuitplayground.express import cpx

while True:
    cpx.red_led = True
    time.sleep(0.5)
    cpx.red_led = False
    time.sleep(0.5)
