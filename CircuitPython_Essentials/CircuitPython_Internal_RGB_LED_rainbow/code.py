"""CircuitPython Essentials Internal RGB LED rainbow example"""
import time
import board
from rainbowio import colorwheel

# For Trinket M0, Gemma M0, ItsyBitsy M0 Express and ItsyBitsy M4 Express
import adafruit_dotstar
led = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1)
# For Feather M0 Express, Metro M0 Express, Metro M4 Express, Circuit Playground Express, QT Py M0
# import neopixel
# led = neopixel.NeoPixel(board.NEOPIXEL, 1)

led.brightness = 0.3

i = 0
while True:
    i = (i + 1) % 256  # run from 0 to 255
    led.fill(colorwheel(i))
    time.sleep(0.01)
