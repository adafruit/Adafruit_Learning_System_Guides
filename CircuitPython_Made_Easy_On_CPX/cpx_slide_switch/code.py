import time
from adafruit_circuitplayground.express import cpx

while True:
    print("Slide switch:", cpx.switch)
    time.sleep(0.1)
