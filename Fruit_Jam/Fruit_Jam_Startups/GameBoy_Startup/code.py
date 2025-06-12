# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
import time
from audiocore import WaveFile
import audiobusio
import board
from displayio import Group, TileGrid, Bitmap, Palette
import supervisor
import adafruit_imageload
import adafruit_tlv320
from adafruit_fruitjam.peripherals import request_display_config


# how long between animation frames
ANIMATE_INTERVAL = 1 / 45

background_color = 0xE1F7CE

i2c = board.I2C()
dac = adafruit_tlv320.TLV320DAC3100(i2c)
dac.configure_clocks(sample_rate=44100, bit_depth=16)
# for headphone jack ouput
dac.headphone_output = True
dac.headphone_volume = -15  # dB
# for speaker JST output
# dac.speaker_output = True
# dac.speaker_volume = -15  # dB

wave_file = open("gameboy_startup/gameboy_pling.wav", "rb")
wave = WaveFile(wave_file)
audio = audiobusio.I2SOut(board.I2S_BCLK, board.I2S_WS, board.I2S_DIN)

# display setup
request_display_config(320, 240)
display = supervisor.runtime.display

# group to hold all visual elements
main_group = Group()

# Bitmap for background color
bg_bmp = Bitmap(display.width // 20, display.height // 20, 1)
bg_palette = Palette(1)
bg_palette[0] = background_color
bg_tg = TileGrid(bg_bmp, pixel_shader=bg_palette)

# group to scale the background bitmap up to display size
bg_group = Group(scale=20)
bg_group.append(bg_tg)
main_group.append(bg_group)

# Bitmap for logo
logo, palette = adafruit_imageload.load("gameboy_startup/gameboy_logo.bmp")
logo_tg = TileGrid(logo, pixel_shader=palette)
main_group.append(logo_tg)

# place it in the center horizontally and above the top of the display
logo_tg.x = display.width // 2 - logo_tg.tile_width // 2
logo_tg.y = -logo_tg.tile_height

# y pixel location to stop logo at
STOP_Y = display.height * 0.4 - logo_tg.tile_height // 2


display.root_group = main_group
time.sleep(1.5)
last_animate_time = time.monotonic()
played_audio = False
display.auto_refresh = False
while True:
    now = time.monotonic()

    # if it's time to animate and the logo isn't to the
    # stopping position yet
    if last_animate_time + ANIMATE_INTERVAL <= now and logo_tg.y < STOP_Y:

        # update the timestamp
        last_animate_time = now
        # move the logo down by a pixel
        logo_tg.y += 1
        display.refresh()

    # if the logo has reached the stop position
    if logo_tg.y >= STOP_Y and not played_audio:
        played_audio = True
        # play the audio pling
        audio.play(wave)
        while audio.playing:
            pass
