from adafruit_circuitplayground.express import cpx

while True:
    if cpx.button_a:
        cpx.red_led = True
