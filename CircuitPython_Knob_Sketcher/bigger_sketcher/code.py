import board
import busio
import adafruit_ssd1306
from simpleio import map_range
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction, Pull

# Create SPI bus
spi = busio.SPI(board.SCK, board.MOSI)

# Create the display
WIDTH = 128
HEIGHT = 64
DC = DigitalInOut(board.D7)
CS = DigitalInOut(board.D9)
RST = DigitalInOut(board.D10)
display = adafruit_ssd1306.SSD1306_SPI(WIDTH, HEIGHT, spi, DC, RST, CS)
display.fill(0)
display.show()

# Create the knobs
READS = 5
x_knob = AnalogIn(board.A0)
y_knob = AnalogIn(board.A1)

# Create the clear button
clear_button = DigitalInOut(board.D12)
clear_button.direction = Direction.INPUT
clear_button.pull = Pull.UP

def read_knobs(reads):
    avg_x = avg_y = 0
    for _ in range(reads):
        avg_x += x_knob.value
        avg_y += y_knob.value
    avg_x /= reads
    avg_y /= reads
    x_screen = map_range(avg_x, 0, 65535, 0, WIDTH - 1)
    y_screen = map_range(avg_y, 0, 65535, 0, HEIGHT - 1)
    return int(x_screen), int(y_screen)

while True:
    while clear_button.value:
        x, y = read_knobs(READS)
        display.pixel(x, y, 1)
        display.show()
    display.fill(0)
    display.show()
