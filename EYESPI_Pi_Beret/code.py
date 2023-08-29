# SPDX-FileCopyrightText: 2021 Melissa LeBlanc Williams for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
EYESPI Pi Beret GIF Player Demo

Extracts the frames and other parameters from an animated gif
and then runs the animation on the display.

Save this file as eyespi_beret_gif_player.py to your Raspberry Pi.

Usage:
python3 eyespi_beret_gif_player.py

This example is for use on Raspberry Pi that are using CPython with
Adafruit Blinka to support CircuitPython libraries. CircuitPython does
not support PIL/pillow (python imaging library)!

Author(s): Melissa LeBlanc-Williams for Adafruit Industries
           Mike Mallett <mike@nerdcore.net>
"""
import os
import time
import digitalio
import board
from PIL import Image, ImageOps
import numpy  # pylint: disable=unused-import
from adafruit_rgb_display import ili9341
from adafruit_rgb_display import st7789  # pylint: disable=unused-import
from adafruit_rgb_display import hx8357  # pylint: disable=unused-import
from adafruit_rgb_display import st7735  # pylint: disable=unused-import
from adafruit_rgb_display import ssd1351  # pylint: disable=unused-import
from adafruit_rgb_display import ssd1331  # pylint: disable=unused-import

# Button pins for EYESPI Pi Beret
BUTTON_NEXT = board.D5
BUTTON_PREVIOUS = board.D6

# CS and DC pins for EYEPSPI Pi Beret:
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)

# Reset pin for EYESPI Pi Beret
reset_pin = digitalio.DigitalInOut(board.D27)

# Backlight pin for Pi Beret
backlight = digitalio.DigitalInOut(board.D18)
backlight.switch_to_output()
backlight.value = True

# Config for display baudrate (default max is 64mhz):
BAUDRATE = 64000000

# Setup SPI bus using hardware SPI:
spi = board.SPI()

# pylint: disable=line-too-long
# Create the display.

# disp = st7789.ST7789(spi, rotation=90,                            # 2.0" ST7789
# disp = st7789.ST7789(spi, height=240, y_offset=80, rotation=180,  # 1.3", 1.54" ST7789
# disp = st7789.ST7789(spi, rotation=90, width=135, height=240, x_offset=53, y_offset=40, # 1.14" ST7789
# disp = st7789.ST7789(spi, rotation=90, width=172, height=320, x_offset=34, # 1.47" ST7789
# disp = st7789.ST7789(spi, rotation=270, width=170, height=320, x_offset=35, # 1.9" ST7789
# disp = hx8357.HX8357(spi, rotation=180,                           # 3.5" HX8357
# disp = st7735.ST7735R(spi, rotation=90,                           # 1.8" ST7735R
# disp = st7735.ST7735R(spi, rotation=270, height=128, x_offset=2, y_offset=3,   # 1.44" ST7735R
# disp = st7735.ST7735R(spi, rotation=90, bgr=True, width=80,       # 0.96" MiniTFT Rev A ST7735R
# disp = st7735.ST7735R(spi, rotation=90, invert=True, width=80, x_offset=26, y_offset=1,  # 0.96" MiniTFT Rev B ST7735R
# disp = ssd1351.SSD1351(spi, rotation=180,                         # 1.5" SSD1351
# disp = ssd1351.SSD1351(spi, height=96, y_offset=32, rotation=180, # 1.27" SSD1351
# disp = ssd1331.SSD1331(spi, rotation=180,                         # 0.96" SSD1331
disp = ili9341.ILI9341(spi, rotation=90,                            # 2.2", 2.4", 2.8", 3.2" ILI9341
                       cs=cs_pin,
                       dc=dc_pin,
                       rst=reset_pin,
                       baudrate=BAUDRATE,
                       )
# pylint: enable=line-too-long


def init_button(pin):
    button = digitalio.DigitalInOut(pin)
    button.switch_to_input()
    button.pull = digitalio.Pull.UP
    return button


class Frame:  # pylint: disable=too-few-public-methods
    def __init__(self, duration=0):
        self.duration = duration
        self.image = None


class AnimatedGif:
    def __init__(self, display, width=None, height=None, folder=None):
        self._frame_count = 0
        self._loop = 0
        self._index = 0
        self._duration = 0
        self._gif_files = []
        self._frames = []

        if width is not None:
            self._width = width
        else:
            self._width = display.width
        if height is not None:
            self._height = height
        else:
            self._height = display.height
        self.display = display
        self.advance_button = init_button(BUTTON_NEXT)
        self.back_button = init_button(BUTTON_PREVIOUS)
        if folder is not None:
            self.load_files(folder)
            self.run()

    def advance(self):
        self._index = (self._index + 1) % len(self._gif_files)

    def back(self):
        self._index = (self._index - 1 + len(self._gif_files)) % len(self._gif_files)

    def load_files(self, folder):
        gif_files = [f for f in os.listdir(folder) if f.endswith(".gif")]
        for gif_file in gif_files:
            gif_file = os.path.join(folder, gif_file)
            image = Image.open(gif_file)
            # Only add animated Gifs
            if image.is_animated:
                self._gif_files.append(gif_file)

        print("Found", self._gif_files)
        if not self._gif_files:
            print("No Gif files found in current folder")
            exit()  # pylint: disable=consider-using-sys-exit

    def preload(self):
        image = Image.open(self._gif_files[self._index])
        print("Loading {}...".format(self._gif_files[self._index]))
        if "duration" in image.info:
            self._duration = image.info["duration"]
        else:
            self._duration = 0
        if "loop" in image.info:
            self._loop = image.info["loop"]
        else:
            self._loop = 1
        self._frame_count = image.n_frames
        self._frames.clear()
        for frame in range(self._frame_count):
            image.seek(frame)
            # Create blank image for drawing.
            # Make sure to create image with mode 'RGB' for full color.
            frame_object = Frame(duration=self._duration)
            if "duration" in image.info:
                frame_object.duration = image.info["duration"]
            frame_object.image = ImageOps.pad(  # pylint: disable=no-member
                image.convert("RGB"),
                (self._width, self._height),
                method=Image.NEAREST,
                color=(0, 0, 0),
                centering=(0.5, 0.5),
            )
            self._frames.append(frame_object)

    def play(self):
        self.preload()

        _prev_advance_btn_val = self.advance_button.value
        _prev_back_btn_val = self.back_button.value
        # Check if we have loaded any files first
        if not self._gif_files:
            print("There are no Gif Images loaded to Play")
            return False
        while True:
            for frame_object in self._frames:
                start_time = time.monotonic()
                self.display.image(frame_object.image)
                _cur_advance_btn_val = self.advance_button.value
                _cur_back_btn_val = self.back_button.value
                if not _cur_advance_btn_val and _prev_advance_btn_val:
                    self.advance()
                    return False
                if not _cur_back_btn_val and _prev_back_btn_val:
                    self.back()
                    return False

                _prev_back_btn_val = _cur_back_btn_val
                _prev_advance_btn_val = _cur_advance_btn_val
                while time.monotonic() < (start_time + frame_object.duration / 1000):
                    pass

            if self._loop == 1:
                return True
            if self._loop > 0:
                self._loop -= 1

    def run(self):
        while True:
            auto_advance = self.play()
            if auto_advance:
                self.advance()


if disp.rotation % 180 == 90:
    disp_height = disp.width  # we swap height/width to rotate it to landscape!
    disp_width = disp.height
else:
    disp_width = disp.width
    disp_height = disp.height

gif_player = AnimatedGif(disp, width=disp_width, height=disp_height, folder=".")
