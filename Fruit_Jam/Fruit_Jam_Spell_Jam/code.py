# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT

import sys
import os
import time
import supervisor

from adafruit_fruitjam import FruitJam
from adafruit_fruitjam.peripherals import request_display_config
from displayio import OnDiskBitmap, TileGrid, Group
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.bitmap_label import Label

from launcher_config import LauncherConfig

# comment out one of these imports depending on which TTS engine you want to use
from tts_aws import WordFetcherTTS
# from tts_local import WordFetcherTTS

# read the user settings
launcher_config = LauncherConfig()

# constants
LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

# local variables
curword = ""
lastword = ""
sayword = False

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

if "audio" in launcher_config.data and "volume" in launcher_config.data["audio"]:
    volume_level = launcher_config.audio_volume
else:
    volume_level = 0.5

fj.peripherals.audio_output = launcher_config.audio_output
fj.peripherals.safe_volume_limit = launcher_config.audio_volume_override_danger

fj.peripherals.volume = volume_level
vol_int = round(volume_level * 100)

fj.neopixels.brightness = 0.1

word_fetcher = WordFetcherTTS(fj, launcher_config)

def say_and_spell_lastword():
    """
    Say the last word, then spell it out one letter at a time, finally say it once more.
    """
    if sayword:
        if word_fetcher.output_path[-4:] == ".mp3":
            fj.play_mp3_file(word_fetcher.output_path)
        elif word_fetcher.output_path[-4:] == ".wav":
            fj.play_file(word_fetcher.output_path)
        time.sleep(0.2)
    for letter in lastword:
        fj.play_mp3_file(f"spell_jam_assets/letter_mp3s/{letter.upper()}.mp3")
    time.sleep(0.2)
    if sayword:
        if word_fetcher.output_path[-4:] == ".mp3":
            fj.play_mp3_file(word_fetcher.output_path)
        elif word_fetcher.output_path[-4:] == ".wav":
            fj.play_file(word_fetcher.output_path)
    soundPath = None
    if 'words' in os.listdir('spell_jam_assets'):
        soundPath = 'spell_jam_assets/words/'
    else:
        try:
            sdAssets = os.listdir('/sd/spell_jam_assets/')
            soundPath = f"/sd/spell_jam_assets/{sdAssets[sdAssets.index('words')]}/"
        except ValueError:
            soundPath = None
        except OSError:
            soundPath = None

    if soundPath is not None:
        for sound in os.listdir(soundPath):
            if sound.upper()[:-4] == lastword.upper():
                if sound[-4:] == ".mp3":
                    fj.play_mp3_file(f'{soundPath}{sound}')
                elif sound[-4:] == ".wav":
                    fj.play_file(f'{soundPath}{sound}')
                break

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
                sayword = word_fetcher.fetch_word(lastword)
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
