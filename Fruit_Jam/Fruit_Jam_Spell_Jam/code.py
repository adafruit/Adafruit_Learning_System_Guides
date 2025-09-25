# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
import os
import sys
import time

import supervisor
from adafruit_fruitjam import FruitJam
from adafruit_fruitjam.peripherals import request_display_config
import adafruit_connection_manager
import adafruit_requests
from displayio import OnDiskBitmap, TileGrid, Group
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.bitmap_label import Label

from aws_polly import text_to_speech_polly_http

# constants
LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

# local variables
curword = ""
lastword = ""

# setup display
request_display_config(320, 240)
display = supervisor.runtime.display

# setup background image
main_group = Group()
background = OnDiskBitmap("spell_jam_assets/background.bmp")
background_tg = TileGrid(background, pixel_shader=background.pixel_shader)
main_group.append(background_tg)

# setup 14-segment label used to display words
font = bitmap_font.load_font("spell_jam_assets/14segment_16.bdf")
screen_lbl = Label(text="Type a word", font=font, color=0x00FF00)
screen_lbl.anchor_point = (0.5, 0)
screen_lbl.anchored_position = (display.width // 2, 100)
main_group.append(screen_lbl)

# initialize Fruit Jam built-in hardware
fj = FruitJam()
fj.neopixels.brightness = 0.1
fj.peripherals.volume = 0.5
vol_int = 50

# AWS auth requires us to have accurate date/time
now = fj.sync_time()

# setup adafruit_requests session
# pylint: disable=protected-access
pool = adafruit_connection_manager.get_radio_socketpool(fj.network._wifi.esp)
ssl_context = adafruit_connection_manager.get_radio_ssl_context(fj.network._wifi.esp)
requests = adafruit_requests.Session(pool, ssl_context)

# read AWS keys from settings.toml
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")


def fetch_word(word, voice="Joanna"):
    """
    Fetch an MP3 saying a word from AWS Polly
    :param word: The word to speak
    :param voice: The AWS Polly voide ID to use
    :return: Boolean, whether the request was successful.
    """
    fj.neopixels.fill(0xFFFF00)
    success = text_to_speech_polly_http(
        requests,
        text=word,
        access_key=AWS_ACCESS_KEY,
        secret_key=AWS_SECRET_KEY,
        voice_id=voice,
    )
    fj.neopixels.fill(0x00FF00)
    return success


def say_and_spell_lastword():
    """
    Say the last word, then spell it out one letter at a time, finally say it once more.
    """
    fj.play_mp3_file("/saves/awspollyoutput.mp3")
    time.sleep(0.2)
    for letter in lastword:
        fj.play_mp3_file(f"spell_jam_assets/letter_mp3s/{letter.upper()}.mp3")
    time.sleep(0.2)
    fj.play_mp3_file("/saves/awspollyoutput.mp3")
    fj.neopixels.fill(0x000000)


display.root_group = main_group
while True:
    # check how many bytes are available
    available = supervisor.runtime.serial_bytes_available

    # if there are some bytes available
    if available:
        # read data from the keyboard input
        c = sys.stdin.read(available)
        # print the data that was read
        print(c, end="")

        if c in LETTERS:
            curword += c
            screen_lbl.text = curword
        elif c in {"\x7f", "\x08"}:  # backspace
            curword = curword[:-1]
            screen_lbl.text = curword
        elif c == "\n":
            if curword:
                lastword = curword
                fetch_word(lastword)
                say_and_spell_lastword()
                curword = ""
            else:
                # repeat last word
                say_and_spell_lastword()
        elif c.encode("utf-8") == b"\x1b[B":
            # down arrow
            vol_int = max(0, vol_int - 5)
            fj.peripherals.volume = vol_int / 100
            print(f"Volume: {fj.peripherals.volume}")
        elif c.encode("utf-8") == b"\x1b[A":
            # up arrow
            vol_int = min(fj.peripherals.safe_volume_limit * 100, vol_int + 5)
            fj.peripherals.volume = vol_int / 100
            print(f"Volume: {fj.peripherals.volume}")
        else:
            print(f"unused key: {c.encode('utf-8')}")
