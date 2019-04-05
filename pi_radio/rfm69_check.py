"""
Wiring Check, Pi Radio w/RFM69

Learn Guide: https://learn.adafruit.com/lora-and-lorawan-for-raspberry-pi
Author: Brent Rubell for Adafruit Industries
"""
import time
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
# Import the SSD1306 module.
import adafruit_ssd1306
# Import the RFM69 radio module.
import adafruit_rfm69

# Button A
btnA = DigitalInOut(board.D5)
btnA.direction = Direction.INPUT
btnA.pull = Pull.UP

# Button B
btnB = DigitalInOut(board.D6)
btnB.direction = Direction.INPUT
btnB.pull = Pull.UP

# Button C
btnC = DigitalInOut(board.D12)
btnC.direction = Direction.INPUT
btnC.pull = Pull.UP

# Create the I2C interface.
i2c = busio.I2C(board.SCL, board.SDA)

# 128x32 OLED Display
display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, addr=0x3c)
# Clear the display.
display.fill(0)
display.show()
width = display.width
height = display.height


# RFM69 Configuration
CS = DigitalInOut(board.CE1)
RESET = DigitalInOut(board.D25)
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

while True:
    # Draw a black filled box to clear the image.
    display.fill(0)

    # Attempt to set up the RFM69 Module
    try:
        rfm69 = adafruit_rfm69.RFM69(spi, CS, RESET, 915.0)
        display.text('RFM69: Detected', 0, 0, 1)
    except RuntimeError:
        # Thrown on version mismatch
        display.text('RFM69: ERROR', 0, 0, 1)

    # Check buttons
    if not btnA.value:
        # Button A Pressed
        display.text('Ada', width-85, height-7, 1)
        display.show()
        time.sleep(0.1)
    if not btnB.value:
        # Button B Pressed
        display.text('Fruit', width-75, height-7, 1)
        display.show()
        time.sleep(0.1)
    if not btnC.value:
        # Button C Pressed
        display.text('Radio', width-65, height-7, 1)
        display.show()
        time.sleep(0.1)

    display.show()
    time.sleep(0.1)
