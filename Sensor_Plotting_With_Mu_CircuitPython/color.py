import analogio
import board
import neopixel

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=1.0)
light = analogio.AnalogIn(board.LIGHT)

while True:
    pixels.fill((0, 0, 0))
    pixels[1] = (255, 0, 0)
    raw_red = light.value

    red = int(raw_red * (255 / 65535))
    pixels[1] = (0, 255, 0)
    raw_green = light.value

    green = int(raw_green * (255 / 65535))
    pixels[1] = (0, 0, 255)
    raw_blue = light.value

    blue = int(raw_blue * (255 / 65535))
    pixels.fill((0, 0, 0))

    # Printed to match the color lines on the Mu plotter!
    # The orange line represents red.
    print((green, blue, red))
