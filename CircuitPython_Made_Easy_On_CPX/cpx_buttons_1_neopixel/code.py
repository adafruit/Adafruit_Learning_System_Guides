from adafruit_circuitplayground.express import cpx

cpx.pixels.brightness = 0.3

while True:
    if cpx.button_a:
        cpx.pixels[2] = (0, 255, 0)
    elif cpx.button_b:
        cpx.pixels[7] = (0, 0, 255)
    else:
        cpx.pixels.fill((0, 0, 0))
