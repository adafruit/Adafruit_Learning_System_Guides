import time
from adafruit_circuitplayground.express import cpx

while True:
    print((cpx.temperature, ))
    time.sleep(0.1)
