import neopixel
import analogio
import digitalio
import time
import board

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=1.0)
light = analogio.AnalogIn(board.LIGHT)

button_a = digitalio.DigitalInOut(board.BUTTON_A)
button_a.direction = digitalio.Direction.INPUT
button_a.pull = digitalio.Pull.DOWN
button_b = digitalio.DigitalInOut(board.BUTTON_B)
button_b.direction = digitalio.Direction.INPUT
button_b.pull = digitalio.Pull.DOWN

while True:
    pixels.fill((0, 0, 0))
    pixels[1] = (255, 0, 0)
    time.sleep(0.5)
    raw_red = light.value
    red = int(raw_red * (255/65535))
    pixels[1] = (0, 255, 0)
    time.sleep(0.5)
    raw_green = light.value
    green = int(raw_green * (255/65535))
    pixels[1] = (0, 0, 255)
    time.sleep(0.5)
    raw_blue = light.value
    blue = int(raw_blue * (255/65535))
    pixels.fill((0, 0, 0))
    print((green, blue, red))  # Printed to match the color lines on the Mu plotter! The orange line represents red.
