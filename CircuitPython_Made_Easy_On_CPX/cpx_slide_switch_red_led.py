from adafruit_circuitplayground.express import cpx

while True:
    if cpx.switch:
        cpx.red_led = True
    else:
        cpx.red_led = False
