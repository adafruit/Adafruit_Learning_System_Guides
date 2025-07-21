# SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
# SPDX-FileCopyrightText: 2017 Tony DiCola for Adafruit Industries
# SPDX-FileCopyrightText: 2017 James DeVito for Adafruit Industries
# SPDX-FileCopyrightText: 2025 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT

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


import subprocess
import time

import requests
from board import SCL, SDA
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont

api_url = "http://localhost/api/stats/summary"

# Create the I2C interface.
i2c = busio.I2C(SCL, SDA)

# Create the SSD1306 OLED class.
disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

# Leaving the OLED on for a long period of time can damage it
DISPLAY_ON  = 10  # on time in seconds
DISPLAY_OFF = 50  # off time in seconds

# Clear display.
disp.fill(0)
disp.show()

# Create blank image for drawing.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=0)

padding = -2
top = padding
x = 0

# Load nice silkscreen font
font = ImageFont.truetype('/home/pi/slkscr.ttf', 8)

while True:
    # Clear the image buffer
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    # Shell scripts for system monitoring
    cmd = "hostname -I | cut -d' ' -f1 | tr -d '\\n'"
    IP = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "hostname | tr -d '\\n'"
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

    # Pi-Hole data!
    try:
        r = requests.get(api_url, timeout=2)
        r.raise_for_status()
        data = r.json()
        DNSQUERIES = data["queries"]["total"]
        ADSBLOCKED = data["queries"]["blocked"]
        CLIENTS    = data["clients"]["total"]
    except (KeyError, requests.RequestException):
        DNSQUERIES = 0
        ADSBLOCKED = 0
        CLIENTS    = 0

    draw.text((x, top),       "IP: " + IP + " (" + HOST + ")", font=font, fill=255)
    draw.text((x, top + 8),   "Ads Blocked: " + str(ADSBLOCKED),            font=font, fill=255)
    draw.text((x, top + 16),  "Clients:     " + str(CLIENTS),                 font=font, fill=255)
    draw.text((x, top + 24),  "DNS Queries: " + str(DNSQUERIES),               font=font, fill=255)

    # Display image.
    disp.image(image)
    disp.show()
    time.sleep(DISPLAY_ON)

    # Blank screen to prevent burn-in
    disp.fill(0)
    disp.show()
    time.sleep(DISPLAY_OFF)
