""" Example for using the AHT20 and OLED with CircuitPython and the Adafruit library"""

import time
import board
import busio
import adafruit_ahtx0

# OLED
import displayio
import terminalio
from adafruit_display_text import label
import adafruit_displayio_ssd1306

displayio.release_displays()

i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)

# Create library object using our Bus I2C port
#i2c = busio.I2C(board.SCL, board.SDA)
aht20 = adafruit_ahtx0.AHTx0(i2c)


#OLED
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=32)

# Make the display context
splash = displayio.Group()
display.show(splash)

text = "hello world"
text_area = label.Label(terminalio.FONT, color=0xFFFF00, x=15, y=0, max_glyphs=200)
splash.append(text_area)

while True:
    text_area.text = "temp: %0.1fC \nhumid: %0.1f%%" % (aht20.temperature, aht20.relative_humidity)
    print(text_area.text)
    time.sleep(1)
