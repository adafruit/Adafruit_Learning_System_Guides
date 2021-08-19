from adafruit_circuitplayground.express import cpx

cpx.pixels.brightness = 0.3

while True:
    cpx.pixels[0] = (255, 0, 0)
