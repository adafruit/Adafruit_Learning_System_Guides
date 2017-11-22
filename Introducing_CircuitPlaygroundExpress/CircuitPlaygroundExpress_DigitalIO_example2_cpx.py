from adafruit_circuitplayground.express import cpx

while True:
    if cpx.button_a and cpx.button_b:
        cpx.red_led = True
    else:
        cpx.red_led = False
