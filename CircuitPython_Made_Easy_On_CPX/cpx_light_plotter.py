import time
from adafruit_circuitplayground.express import cpx

while True:
    print("Lux:", cpx.light)
    print((cpx.light,))
    time.sleep(1)
