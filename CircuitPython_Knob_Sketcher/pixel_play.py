# Import the needed libraries
import time
import random
import board
import busio
from digitalio import DigitalInOut
import adafruit_ssd1306

# Create I2c bus
i2c = busio.I2C(board.SCL, board.SDA)

# Define display dimensions and I2C address
WIDTH = 128
HEIGHT = 64
ADDR = 0x3d

# Create the digital out used for display reset
rst = DigitalInOut(board.D7)

# Create the display
display = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=ADDR, reset=rst)
display.fill(0)
display.show()

# Loop forever drawing random pixels
while True:
    for _ in range(500):
        x = random.randrange(WIDTH)
        y = random.randrange(HEIGHT)
        display.pixel(x, y, 1)
    display.show()
    time.sleep(0.5)
    display.fill(0)
