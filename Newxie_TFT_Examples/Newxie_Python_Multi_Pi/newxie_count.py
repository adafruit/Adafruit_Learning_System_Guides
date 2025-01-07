# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from threading import Thread, Lock
from PIL import Image, ImageDraw, ImageFont
import digitalio
import board
import busio
from adafruit_rgb_display import st7789

BAUDRATE = 25000000
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
        time.sleep(0.1)

counter = 0
counter_lock = Lock()
# pylint: disable=global-statement
def increment_counter():
    global counter
    while True:
        with counter_lock:
            counter = (counter + 1) % 10000
        time.sleep(0.01)

def digit_0():
    with counter_lock:
        return (counter // 1000) % 10

def digit_1():
    with counter_lock:
        return (counter // 100) % 10

def digit_2():
    with counter_lock:
        return (counter // 10) % 10

def digit_3():
    with counter_lock:
        return counter % 10

Thread(target=increment_counter).start()
Thread(target=update_digit_display, args=(disp0, digit_0)).start()
Thread(target=update_digit_display, args=(disp1, digit_1)).start()
Thread(target=update_digit_display, args=(disp2, digit_2)).start()
Thread(target=update_digit_display, args=(disp3, digit_3)).start()
