# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT
'''Prop-It CircuitPython code. Feather Prop Maker RP2040 with MX key, hall effect sensor,
toggle switch, slide potentiometer and onboard accelerometer. Background music plays in loop
and individual sound effects for each input play with audio mixer'''

import random
import board
import neopixel
import audiobusio
import audiomixer
import audiocore
import audiospeed
import adafruit_lis3dh
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction, Pull
from adafruit_ht16k33 import segments
from rainbowio import colorwheel
import simpleio
from adafruit_ticks import ticks_ms, ticks_diff, ticks_add

# external power
external_power           = DigitalInOut(board.EXTERNAL_POWER)
external_power.direction = Direction.OUTPUT
external_power.value     = True

# alphanumeric display
display = segments.Seg14x4(board.STEMMA_I2C())

# neopixel strip
pixels = neopixel.NeoPixel(board.EXTERNAL_NEOPIXELS, 8, brightness=0.6, auto_write=True)

# accelerometer
i2c = board.I2C()
int1 = DigitalInOut(board.ACCELEROMETER_INTERRUPT)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)
lis3dh.range = adafruit_lis3dh.RANGE_2_G
SHAKE_THRESHOLD = 15

key = DigitalInOut(board.D5) # mx key
key.direction = Direction.INPUT
key.pull = Pull.UP
toggle = DigitalInOut(board.EXTERNAL_BUTTON) # toggle switch
toggle.direction = Direction.INPUT
toggle.pull = Pull.UP
hall = DigitalInOut(board.EXTERNAL_SERVO) # hall effect sensor
hall.direction = Direction.INPUT
hall.pull = Pull.UP

# potentiometer
slider = AnalogIn(board.A0)
last_slider_zone = [0]

def get_slider_zone(): # helper for slider to read it as a zone
    raw = slider.value
    zone = int(simpleio.map_range(raw, 0, 65535, 0, 4))
    if abs(zone - last_slider_zone[0]) >= 2:
        last_slider_zone[0] = zone
    return last_slider_zone[0]

TEXT_FILES = ["/sfx_files/push.wav", "/sfx_files/flip.wav", "/sfx_files/spin.wav", "/sfx_files/slide.wav", "/sfx_files/shake.wav"]
SFX_FILES = ["/sfx_files/push_it_fx.wav", "/sfx_files/flip_it_fx.wav", "/sfx_files/spin_it_fx.wav", "/sfx_files/slide_it_fx.wav", "/sfx_files/shake_it_fx.wav"]
inputs = [
    {'label': "PUSH", 'current_state': False, 'last_state': False, 'txt_file': TEXT_FILES[0],
     'sfx_file': SFX_FILES[0], 'check': lambda: key.value},
    {'label': "FLIP", 'current_state': False, 'last_state': False, 'txt_file': TEXT_FILES[1],
     'sfx_file': SFX_FILES[1], 'check': lambda: toggle.value},
    {'label': "SPIN", 'current_state': False, 'last_state': False, 'txt_file': TEXT_FILES[2],
     'sfx_file': SFX_FILES[2], 'check': lambda: hall.value},
    {'label': "SLDE", 'current_state': False, 'last_state': False, 'txt_file': TEXT_FILES[3],
     'sfx_file': SFX_FILES[3], 'check': get_slider_zone},
    {'label': "SHKE", 'current_state': False, 'last_state': False, 'txt_file': TEXT_FILES[4],
     'sfx_file': SFX_FILES[4], 'check': lambda: lis3dh.shake(shake_threshold=SHAKE_THRESHOLD)},
]

# audio mixer setup - import wav files

try:
    bg_file = open("/sfx_files/Beat.wav", "rb")
    wav = audiocore.WaveFile(bg_file)
    wav_bg = audiospeed.SpeedChanger(wav, rate=1.0)
except OSError as e:
    print(f"Missing Beat.wav: {e}")

try:
    txt_file = open(TEXT_FILES[0], "rb")
    wav_sfx  = audiocore.WaveFile(txt_file)
except OSError as e:
    print(f"Missing {TEXT_FILES[0]}: {e}")
SAMPLE_RATE = 22050
i2s   = audiobusio.I2SOut(board.I2S_BIT_CLOCK, board.I2S_WORD_SELECT, board.I2S_DATA)
mixer = audiomixer.Mixer(
    voice_count=2,
    sample_rate=SAMPLE_RATE,
    channel_count=1,
    bits_per_sample=16,
    buffer_size=2048
)
i2s.play(mixer)
mixer.voice[0].level = 0.4
mixer.voice[0].play(wav_bg, loop=True) # background music loops
mixer.voice[1].level = 0.5

def play_sfx(file): # helper to play sfx
    sfx = open(file, "rb")
    w = audiocore.WaveFile(sfx)
    mixer.voice[1].play(w, loop=False)

def scroll_text(txt, scroll_x, count = 0, counting = False):
    padded = "    " + txt + "    "
    display.print(padded[scroll_x:scroll_x + 4])
    display.show()
    scroll_x = (scroll_x + 1) % (4 + len(txt))
    if scroll_x == 0:
        count += 1
    if counting:
        return scroll_x, count
    else:
        return scroll_x

state_changed = False # check for correct input
wrong_input = False # check for wrong input
seed = 0 # random seed
hue = 0 # neopixel hue
game_start = True # first run
TRIGGER_INTERVAL = 2500 # time between seeds
TRIGGER_LIMIT = 1000 # shortest time between seeds
STATE_CHANGE_TIMEOUT = 2000 # time for inputs
STATE_CHANGE_LIMIT = 1000 # shortest time for inputs
INTERVAL_CHANGE = 150 # amount of time subtracted every 5 turns
speed = 0.5 # music speed
wav_bg.rate = speed
score = 0 # game score
scroll_x_pos = 0 # text scroll position
scroll_count = 0 # text scroll count
timer = ticks_ms()
IGNORE_MAP = { # don't check for spin during shake, vice versa
    4: [2],
    2: [4],
}

for i in range(len(inputs)): # reset all input states before game start
    inputs[i]['last_state'] = inputs[i]['check']()
    inputs[i]['current_state'] = False

while True:
    if game_start: # scroll start text, wait for button input to start
        if ticks_diff(ticks_ms(), timer) >= 250:
            scroll_x_pos = scroll_text("START?", scroll_x_pos)
            hue = (hue + 2) % 256
            pixels.fill(colorwheel(hue))
            timer = ticks_add(timer, 250)
        if not inputs[0]['check']() and not inputs[0]['current_state']:
            inputs[0]['current_state'] = True
        if inputs[0]['check']() and inputs[0]['current_state']:
            inputs[0]['current_state'] = False
            play_sfx("/sfx_files/game_start.wav")
            scroll_x_pos = 0
            display.print("****")
            display.show()
            timer = ticks_ms()
            game_start = False  # go into game
    else:
        if ticks_diff(ticks_ms(), timer) >= TRIGGER_INTERVAL:
            pixels.fill((0, 0, 0))
            for inp in inputs: # reset states and read all pins
                inp['last_state'] = inp['check']()
                inp['current_state'] = False
            seed = random.randint(0, 4) # pick seed
            play_sfx(inputs[seed]['txt_file']) # play audio clip
            display.print(inputs[seed]['label']) # update display
            display.show()
            secondary_timer = ticks_ms()
            # while the game timer is running..
            while ticks_diff(ticks_ms(), secondary_timer) < STATE_CHANGE_TIMEOUT:
                time_left = ticks_diff(ticks_ms(), secondary_timer) # countdown pixels with timer
                num_pixels = simpleio.map_range(time_left, 0, STATE_CHANGE_TIMEOUT, 0, 7)
                for i in range(num_pixels):
                    pixels[i] = ((255, 0, 255))
                # check for state change
                if inputs[seed]['check']() != inputs[seed]['last_state']:
                    pixels.fill((0, 255, 0))
                    state_changed = True
                    break
                if state_changed:
                    break
                # check wrong inputs
                for i, inp in enumerate(inputs):
                    if i == seed:
                        continue
                    if i in IGNORE_MAP.get(seed, []):
                        # don't check for spin during shake, vice versa
                        continue
                    if inp['check']() != inp['last_state']: # wrong input, game over
                        pixels.fill((255, 0, 0))
                        wrong_input = True
                        break
                if wrong_input:
                    break

            if state_changed: # you scored!
                play_sfx(inputs[seed]['sfx_file'])
                score += 1
                display.print(f"{score:>4}")
                display.show()
                if score % 5 == 0: # every 5 turns, increase speed
                    TRIGGER_INTERVAL -= INTERVAL_CHANGE
                    TRIGGER_INTERVAL = max(TRIGGER_INTERVAL, TRIGGER_LIMIT)
                    STATE_CHANGE_TIMEOUT -= INTERVAL_CHANGE
                    STATE_CHANGE_TIMEOUT = max(STATE_CHANGE_TIMEOUT, STATE_CHANGE_LIMIT)
                    speed = simpleio.map_range(
                                     STATE_CHANGE_TIMEOUT, STATE_CHANGE_LIMIT, 2000, 2.0, 0.5)
                    wav_bg.rate = speed # music speeds up too
                state_changed = False # reset state and clock
                timer = ticks_ms()
            else:
                timer = ticks_ms()
                speed = 0.5 # reset music speed
                wav_bg.rate = speed
                play_sfx("/sfx_files/game_over.wav")
                pixels.fill((255, 0, 0))
                while scroll_count < 2: # scroll game over and score text 2x
                    if ticks_diff(ticks_ms(), timer) >= 250:
                        scroll_x_pos, scroll_count = scroll_text(
                                                     f"GAME OVER - SCORE: {score}", scroll_x_pos,
                                                     scroll_count, counting = True)
                        timer = ticks_add(timer, 250)
                scroll_count = 0 # reset all the states to restart game
                scroll_x_pos = 0
                score = 0
                TRIGGER_INTERVAL = 2500
                STATE_CHANGE_TIMEOUT = 2000
                wrong_input = False
                game_start = True
                timer = ticks_ms()
