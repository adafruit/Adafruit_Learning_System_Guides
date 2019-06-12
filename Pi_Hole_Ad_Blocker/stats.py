# Copyright (c) 2017 Adafruit Industries
# Author: Ladyada, Tony DiCola & James DeVito
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# This example is for use on (Linux) computers that are using CPython with
# Adafruit Blinka to support CircuitPython libraries. CircuitPython does
# not support PIL/pillow (python imaging library)!

# Import Python System Libraries
import json
import subprocess
import time

# Import Requests Library
import requests

# Import Blinka
from board import SCL, SDA
import busio
import adafruit_ssd1306

# Import Python Imaging Library
from PIL import Image, ImageDraw, ImageFont

api_url = 'http://localhost/admin/api.php'

# Create the I2C interface.
i2c = busio.I2C(SCL, SDA)

# Create the SSD1306 OLED class.
# The first two parameters are the pixel width and pixel height.  Change these
# to the right size for your display!
disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

# Clear display.
disp.fill(0)
disp.show()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=0)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height - padding
# Move left to right keeping track of the current x position
# for drawing shapes.
x = 0

# Load nice silkscreen font
font = ImageFont.truetype('/home/pi/slkscr.ttf', 8)

while True:
    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    # Shell scripts for system monitoring from here :
    # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    cmd = "hostname -I | cut -d\' \' -f1 | tr -d \'\\n\'"
    IP = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "hostname | tr -d \'\\n\'"
    HOST = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "top -bn1 | grep load | awk " \
          "'{printf \"CPU Load: %.2f\", $(NF-2)}'"
    CPU = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "free -m | awk 'NR==2{printf " \
          "\"Mem: %s/%sMB %.2f%%\", $3,$2,$3*100/$2 }'"
    MemUsage = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "df -h | awk '$NF==\"/\"{printf " \
          "\"Disk: %d/%dGB %s\", $3,$2,$5}'"
    Disk = subprocess.check_output(cmd, shell=True).decode("utf-8")

    # Pi Hole data!
    try:
        r = requests.get(api_url)
        data = json.loads(r.text)
        DNSQUERIES = data['dns_queries_today']
        ADSBLOCKED = data['ads_blocked_today']
        CLIENTS = data['unique_clients']
    except KeyError:
        time.sleep(1)
        continue

    draw.text((x, top), "IP: " + str(IP) +
              "( " + HOST + ")", font=font, fill=255)
    draw.text((x, top + 8), "Ads Blocked: " +
              str(ADSBLOCKED), font=font, fill=255)
    draw.text((x, top + 16), "Clients:     " +
              str(CLIENTS), font=font, fill=255)
    draw.text((x, top + 24), "DNS Queries: " +
              str(DNSQUERIES), font=font, fill=255)

    # skip over original stats
    # draw.text((x, top+8),     str(CPU), font=font, fill=255)
    # draw.text((x, top+16),    str(MemUsage),  font=font, fill=255)
    # draw.text((x, top+25),    str(Disk),  font=font, fill=255)

    # Display image.
    disp.image(image)
    disp.show()
    time.sleep(.1)
