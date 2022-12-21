# SPDX-FileCopyrightText: 2020 Collin Cunningham for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
from adafruit_debouncer import Debouncer
import digitalio
import displayio
from adafruit_display_text import label
import adafruit_displayio_ssd1306
from adafruit_bitmap_font import bitmap_font

displayio.release_displays()

# Set up button pins
pin_a = digitalio.DigitalInOut(board.D9)
pin_a.direction = digitalio.Direction.INPUT
pin_a.pull = digitalio.Pull.UP

pin_b = digitalio.DigitalInOut(board.D6)
pin_b.direction = digitalio.Direction.INPUT
pin_b.pull = digitalio.Pull.UP

pin_c = digitalio.DigitalInOut(board.D5)
pin_c.direction = digitalio.Direction.INPUT
pin_c.pull = digitalio.Pull.UP

button_a = Debouncer(pin_a) #9
button_b = Debouncer(pin_b) #6
button_c = Debouncer(pin_c) #5

# Load font
font = bitmap_font.load_font('/mround-31.bdf')

# Set up display & add group
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=32)
group = displayio.Group()
display.show(group)

# Add content to group
default_text = "I VOTE  !"
text_area = label.Label(font, text=default_text, color=0xFFFFFF, x=0, y=17)
group.append(text_area)

while True:

    # Debounce buttons
    button_a.update()
    button_b.update()
    button_c.update()

    # Check for button presses & set text
    if button_a.fell:
        text_area.text = default_text
        text_area.x = 0
    elif button_b.fell:
        text_area.text = "I VOTED!"
        text_area.x = 0
    elif button_c.fell:
        text_area.text = "DID U?"
        text_area.x = 18

    display.show(group)
