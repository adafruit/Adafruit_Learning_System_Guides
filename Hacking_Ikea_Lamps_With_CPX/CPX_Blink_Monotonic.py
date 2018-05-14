import time

from adafruit_circuitplayground.express import cpx

blink_speed = 0.5

cpx.pixels[0] = (0, 0, 0)

initial_time = time.monotonic()
while True:
    current_time = time.monotonic()
    if current_time - initial_time > blink_speed:
        initial_time = current_time
        cpx.pixels[0] = (abs(cpx.pixels[0][0] - 255), 0, 0)
