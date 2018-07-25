from adafruit_circuitplayground.express import cpx

while True:
    if cpx.button_a:
        cpx.pixels[0] = (0, 30, 0)
    else:
        cpx.pixels[0] = (0, 0, 0)

    if cpx.button_b:
        cpx.pixels[9] = (0, 30, 0)
    else:
        cpx.pixels[9] = (0, 0, 0)

    if cpx.switch:
        cpx.pixels[4] = (0, 0, 30)
        cpx.pixels[5] = (0, 0, 0)
    else:
        cpx.pixels[4] = (0, 0, 0)
        cpx.pixels[5] = (0, 0, 30)
