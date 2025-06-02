# SPDX-FileCopyrightText: 2019 Brent Rubell for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# -*- coding: utf-8 -*-
# Import Python System Libraries
import time
import json
import subprocess

# Import Requests Library
import requests

#Import Blinka
import digitalio
import board

# Import Python Imaging Library
from PIL import Image, ImageDraw, ImageFont
import adafruit_rgb_display.st7789 as st7789

API_URL = "http://pi.hole/api/stats/summary"

# Configuration for CS and DC pins (these are FeatherWing defaults on M0/M4):
cs_pin = digitalio.DigitalInOut(board.D17)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = None

# Config for display baudrate (default max is 24mhz):
BAUDRATE = 64000000

# Setup SPI bus using hardware SPI:
spi = board.SPI()

# Create the ST7789 display:
disp = st7789.ST7789(
    spi,
    dc_pin,
    cs_pin,
    reset_pin,
    135,
    240,
    baudrate=BAUDRATE,
    x_offset=53,
    y_offset=40,
    rotation=90
)

# Create blank image for drawing.
# Make sure to create image with mode 'RGB' for full color.
CANVAS_WIDTH  = disp.height
CANVAS_HEIGHT = disp.width
image = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT))
draw = ImageDraw.Draw(image)

# Load default font (or replace with a TTF if desired)
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font = ImageFont.truetype(FONT_PATH, 20)

buttonA = digitalio.DigitalInOut(board.D23)
buttonA.switch_to_input()

while True:
    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, CANVAS_WIDTH, CANVAS_HEIGHT), outline=0, fill=(0, 0, 0))

    # Shell scripts for system monitoring from here:
    # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    cmd = "hostname -I | cut -d' ' -f1"
    IP = "IP: " + subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    cmd = "hostname | tr -d '\\n'"
    HOST = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'"
    CPU = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB  %.2f%%\", $3,$2,$3*100/$2 }'"
    MemUsage = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "df -h | awk '$NF==\"/\"{printf \"Disk: %d/%d GB  %s\", $3,$2,$5}'"
    Disk = subprocess.check_output(cmd, shell=True).decode("utf-8")
    cmd = "cat /sys/class/thermal/thermal_zone0/temp |  awk '{printf \"CPU Temp: %.1f C\", $(NF-0) / 1000}'"
    Temp = subprocess.check_output(cmd, shell=True).decode("utf-8")

    # Pi Hole data!
    try:
        r = requests.get(API_URL, timeout=5)
        r.raise_for_status()
        data = r.json()
        DNSQUERIES = data["queries"]["total"]
        ADSBLOCKED = data["queries"]["blocked"]
        CLIENTS    = data["clients"]["total"]
    except (KeyError, requests.RequestException, json.JSONDecodeError):
        DNSQUERIES = None
        ADSBLOCKED = None
        CLIENTS    = None

    y = top = 5
    x = 5
    if not buttonA.value:  # just button A pressed
        draw.text((x, y), IP, font=font, fill="#FFFF00")
        y += font.getbbox(IP)[3]
        draw.text((x, y), CPU, font=font, fill="#FFFF00")
        y += font.getbbox(CPU)[3]
        draw.text((x, y), MemUsage, font=font, fill="#00FF00")
        y += font.getbbox(MemUsage)[3]
        draw.text((x, y), Disk, font=font, fill="#0000FF")
        y += font.getbbox(Disk)[3]
        draw.text((x, y), Temp, font=font, fill="#FF00FF")
        y += font.getbbox(Temp)[3]
    else:
        draw.text((x, y), IP, font=font, fill="#FFFF00")
        y += font.getbbox(IP)[3]
        draw.text((x, y), HOST, font=font, fill="#FFFF00")
        y += font.getbbox(HOST)[3]
        if ADSBLOCKED is not None:
            txt = f"Ads Blocked: {ADSBLOCKED}"
            draw.text((x, y), txt, font=font, fill="#00FF00")
            y += font.getbbox(txt)[3]
        if CLIENTS is not None:
            txt = f"Clients: {CLIENTS}"
            draw.text((x, y), txt, font=font, fill="#0000FF")
            y += font.getbbox(txt)[3]
        if DNSQUERIES is not None:
            txt = f"DNS Queries: {DNSQUERIES}"
            draw.text((x, y), txt, font=font, fill="#FF00FF")
            y += font.getbbox(txt)[3]

    # Display image.
    disp.image(image)
    time.sleep(.1)
