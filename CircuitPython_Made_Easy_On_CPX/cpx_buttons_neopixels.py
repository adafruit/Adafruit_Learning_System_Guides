from adafruit_circuitplayground.express import cpx

cpx.pixels.brightness = 0.3

while True:
    if cpx.button_a:
        cpx.pixels[0:5] = [(255, 0, 0)] * 5
    elif cpx.button_b:
        cpx.pixels[5:10] = [(0, 255, 0)] * 5
    else:
        cpx.pixels.fill((0, 0, 0))
