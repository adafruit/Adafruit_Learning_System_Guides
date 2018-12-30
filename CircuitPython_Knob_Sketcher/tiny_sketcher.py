import board
import busio
import adafruit_ssd1306
from simpleio import map_range
from analogio import AnalogIn
from digitalio import DigitalInOut

# Create the I2C bus
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

# Create the knobs
x_knob = AnalogIn(board.A0)
y_knob = AnalogIn(board.A1)

while True:
    x = map_range(x_knob.value, 0, 65535, WIDTH - 1, 0)
    y = map_range(y_knob.value, 0, 65535, 0, HEIGHT - 1)
    display.pixel(int(x), int(y), 1)
    display.show()
