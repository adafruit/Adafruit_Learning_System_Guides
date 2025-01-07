# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from threading import Thread
from PIL import Image, ImageDraw, ImageFont
import digitalio
import board
import busio
from adafruit_rgb_display import st7789

BAUDRATE = 10000000
WIDTH = 135
HEIGHT = 240

cs_pin0 = digitalio.DigitalInOut(board.D23)
dc_pin0 = digitalio.DigitalInOut(board.D25)

cs_pin1 = digitalio.DigitalInOut(board.CE1)
dc_pin1 = digitalio.DigitalInOut(board.D24)

cs_pin2 = digitalio.DigitalInOut(board.D16)
dc_pin2 = digitalio.DigitalInOut(board.D26)

cs_pin3 = digitalio.DigitalInOut(board.D17)
dc_pin3 = digitalio.DigitalInOut(board.D27)

spi = board.SPI()
spi1 = busio.SPI(clock=board.D21, MOSI=board.D20)

disp0 = st7789.ST7789(spi, rotation=180, width=WIDTH, height=HEIGHT,
                      x_offset=53, y_offset=40, cs=cs_pin0, dc=dc_pin0, baudrate=BAUDRATE)
disp1 = st7789.ST7789(spi, rotation=180, width=WIDTH, height=HEIGHT,
                      x_offset=53, y_offset=40, cs=cs_pin1, dc=dc_pin1, baudrate=BAUDRATE)
disp2 = st7789.ST7789(spi1, rotation=180, width=WIDTH, height=HEIGHT,
                      x_offset=53, y_offset=40, cs=cs_pin2, dc=dc_pin2, baudrate=BAUDRATE)
disp3 = st7789.ST7789(spi1, rotation=180, width=WIDTH, height=HEIGHT,
                      x_offset=53, y_offset=40, cs=cs_pin3, dc=dc_pin3, baudrate=BAUDRATE)

def update_digit_display(disp, get_digit_func):
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
    while True:
        digit = get_digit_func()
        image = Image.new("RGB", (WIDTH, HEIGHT), "black")
        draw = ImageDraw.Draw(image)

        text = str(digit)
        text_width, text_height = draw.textsize(text, font=font)
        text_x = (WIDTH - text_width) // 2
        text_y = (HEIGHT - text_height) // 2
        draw.text((text_x, text_y), text, font=font, fill="white")

        disp.image(image)
        time.sleep(1)

def get_hour_tens():
    current_time = time.localtime()
    hour = current_time.tm_hour % 12 or 12
    return hour // 10

def get_hour_ones():
    current_time = time.localtime()
    hour = current_time.tm_hour % 12 or 12
    return hour % 10

def get_minute_tens():
    current_time = time.localtime()
    minute = current_time.tm_min
    return minute // 10

def get_minute_ones():
    current_time = time.localtime()
    minute = current_time.tm_min
    return minute % 10

Thread(target=update_digit_display, args=(disp0, get_hour_tens)).start()
Thread(target=update_digit_display, args=(disp1, get_hour_ones)).start()
Thread(target=update_digit_display, args=(disp2, get_minute_tens)).start()
Thread(target=update_digit_display, args=(disp3, get_minute_ones)).start()
