import time
from adafruit_circuitplayground.express import cpx

while True:
    cpx.red_led = not cpx.red_led
    time.sleep(0.5)
