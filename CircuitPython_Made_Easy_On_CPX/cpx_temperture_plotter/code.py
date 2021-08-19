import time
from adafruit_circuitplayground.express import cpx

while True:
    print("Temperature C:", cpx.temperature)
    print("Temperature F:", cpx.temperature * 1.8 + 32)
    print((cpx.temperature, cpx.temperature * 1.8 + 32))
    time.sleep(1)
