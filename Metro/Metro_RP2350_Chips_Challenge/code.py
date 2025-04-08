# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams
#
# SPDX-License-Identifier: MIT

import time
import board
import picodvi
import framebufferio
import displayio
import adafruit_tlv320
import audiobusio
from audio import Audio
from game import Game
from definitions import SECOND_LENGTH, TICKS_PER_SECOND

# Disable auto-reload to prevent the game from restarting
#import supervisor
#supervisor.runtime.autoreload = False

# Change this to use a different data file
DATA_FILE = "CHIPS.DAT"

SOUND_EFFECTS = {
    "BUTTON_PUSHED": "/sounds/pop2.wav",
    "DOOR_OPENED": "/sounds/door.wav",
    "ITEM_COLLECTED": "/sounds/blip2.wav",
    "BOOTS_STOLEN": "/sounds/strike.wav",
    "WATER_SPLASH": "/sounds/water2.wav",
    "TELEPORT": "/sounds/teleport.wav",
    "CANT_MOVE": "/sounds/oof3.wav",
    "CHIP_LOSES": "/sounds/bummer.wav",
    "LEVEL_COMPLETE": "/sounds/ditty1.wav",
    "IC_COLLECTED": "/sounds/click3.wav",
    "BOMB_EXPLOSION": "/sounds/hit3.wav",
    "SOCKET_SOUND": "/sounds/chimes.wav",
    "TIME_LOW_TICK": "/sounds/click1.wav",
    "TIME_UP": "/sounds/bell.wav"
}

displayio.release_displays()

i2c = board.I2C()
dac = adafruit_tlv320.TLV320DAC3100(i2c)
dac.configure_clocks(sample_rate=44100, bit_depth=16)
dac.headphone_output = True
dac.headphone_volume = -15  # dB

audio_bus = audiobusio.I2SOut(board.D9, board.D10, board.D11)
audio = Audio(audio_bus, SOUND_EFFECTS)

fb = picodvi.Framebuffer(320, 240, clk_dp=board.CKP, clk_dn=board.CKN,
                                   red_dp=board.D0P, red_dn=board.D0N,
                                   green_dp=board.D1P, green_dn=board.D1N,
                                   blue_dp=board.D2P, blue_dn=board.D2N,
                                   color_depth=8)
display = framebufferio.FramebufferDisplay(fb)

game = Game(display, DATA_FILE, audio)
tick_length = SECOND_LENGTH / 1000 / TICKS_PER_SECOND
while True:
    start = time.monotonic()
    game.tick()
    while time.monotonic() - start < tick_length:
        pass
