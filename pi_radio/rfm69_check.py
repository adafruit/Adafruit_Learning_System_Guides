"""
Wiring Check, Pi Radio w/RFM69

Learn Guide: https://learn.adafruit.com/lora-and-lorawan-for-raspberry-pi
Author: Brent Rubell for Adafruit Industries
"""
import time
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
import Adafruit_SSD1306
import adafruit_rfm69

# Button A
btnA = DigitalInOut(board.D26)
btnA.direction = Direction.INPUT
btnA.pull = Pull.UP

# Button B
btnB = DigitalInOut(board.D19)
btnB.direction = Direction.INPUT
btnB.pull = Pull.UP

# Button C
btnC = DigitalInOut(board.D13)
btnC.direction = Direction.INPUT
btnC.pull = Pull.UP

# 128x32 OLED Display
disp = Adafruit_SSD1306.SSD1306_128_32(rst=None)
# Initialize library.
disp.begin()
# Clear display.
disp.clear()
disp.display()
width = disp.width
height = disp.height
image = Image.new('1', (width, height))
draw = ImageDraw.Draw(image)
draw.rectangle((0,0,width,height), outline=0, fill=0)
padding = -2
top = padding
bottom = height-padding
x = 0
font = ImageFont.load_default()

# RFM69 Configuration
CS = DigitalInOut(board.D18)
RESET = DigitalInOut(board.D25)
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

while True:
    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width,height), outline=0, fill=0)

    # Attempt to set up the RFM69 Module
    try:
        rfm69 = adafruit_rfm69.RFM69(spi, CS, RESET, 915.0)
        draw.text((x+20, top+8), "RFM69: Detected", font=font, fill=255)
    except RuntimeError:
        # Thrown on version mismatch
        draw.text((x+20, top), "RFM69: ERROR", font=font, fill=255)

    # Check buttons
    if not btnA.value:
        # Button A Pressed
        draw.text((x, top+16),'Radio', font=font, fill=255)
        disp.image(image)
        disp.display()
        time.sleep(0.1)
    if not btnB.value:
        # Button B Pressed
        draw.text((x, top+16),'LoRa', font=font, fill=255)
        disp.image(image)
        disp.display()
    if not btnC.value:
      # Button C Pressed
        draw.text((x, top+16),'LoRaWAN', font=font, fill=255)
        disp.image(image)
        disp.display()

    disp.image(image)
    disp.display()
    time.sleep(0.1)
