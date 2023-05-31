# SPDX-FileCopyrightText: 2023 John Park, Jeff Epler, and Tod Kurt for Adafruit Industries
# SPDX-License-Identifier: MIT
# Computer Perfection Synth
#  * 10 numbered buttons play notes
#  * SET button to increase LFO rate, long press to decrease LFO rate
#  * SCORE button to add lower octave
#  * MODE switch changes wavetable set
#  * SKILL switch toggles sustain
#  * GAME switch must stay in position 1 or it messes with the other switches

import time
import random
import board
import audiobusio
import audiomixer
import synthio
import ulab.numpy as np
import neopixel
import keypad


# NeoPixel setup
num_pixels = 34
pixels = neopixel.NeoPixel(board.D11, num_pixels, brightness=0.7, auto_write=False)
pixels.fill(0x0)
pixels.show()
time.sleep(0.25)
pix_map = [26, 23, 19, 16, 13, 10, 7, 4, 32, 29]  # map the LEDs to the numbered panel sections 0-9
for p in range(len(pix_map)):
    pixels[pix_map[p]] = 0xff0000
    pixels.show()
    time.sleep(0.1)


note_buttons = keypad.Keys(
                            (board.D0, board.D1, board.D2, board.D3, board.D4,
                             board.D5, board.D6, board.D7, board.D8, board.A5),
                            value_when_pressed=False,
                            pull=True
)
switches = keypad.Keys(
                        (board.A1, board.A0),
                        value_when_pressed=False,
                        pull=True
)
octave = 3  # octave multiplier
note_list = (0, 4, 6, 7, 9, 12, 16, 18, 19, 21)  # Lydian scale

mod_buttons = keypad.Keys(
                            (board.A4, board.A3),  # SET and SCORE buttons
                            value_when_pressed=False,
                            pull=True
)

SAMPLE_RATE = 48000  # clicks @ 36kHz & 48kHz on rp2040
SAMPLE_SIZE = 200
VOLUME = 12000

# Metro M7 pins for the I2S amp:
lck_pin, bck_pin, dat_pin = board.D9, board.D10, board.D12

# synth engine setup
waveform = np.zeros(SAMPLE_SIZE, dtype=np.int16)  # intially all zeros (silence)

amp_env = synthio.Envelope(  # default (0.1, 0.05, 0.2, 1, 0.8)
                            attack_time=1.0,
                            decay_time=0.05,
                            release_time=3.0,
                            attack_level=1.0,
                            sustain_level=0.8
)

synth = synthio.Synthesizer(sample_rate=SAMPLE_RATE, waveform=waveform, envelope=amp_env)
audio = audiobusio.I2SOut(bit_clock=bck_pin, word_select=lck_pin, data=dat_pin)
mixer = audiomixer.Mixer(voice_count=1, sample_rate=SAMPLE_RATE, channel_count=1,
                         bits_per_sample=16, samples_signed=True, buffer_size=8192)
audio.play(mixer)
mixer.voice[0].level = 0.55
mixer.voice[0].play(synth)

led = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.3)  # on board neopixel

# waveforms setup
wave_sine = np.array(np.sin(np.linspace(0, 2*np.pi, SAMPLE_SIZE, endpoint=False)) * VOLUME,
            dtype=np.int16)
wave_saw = np.linspace(VOLUME, -VOLUME, num=SAMPLE_SIZE, dtype=np.int16)
wave_weird1 = np.array((198,2776,5441,8031,10454,12653,14609,16333,17824,19130,20260,21227,22043,
                        22721,23269,23699,24019,24243,24385,24461,18630,-26956,-28048,-29175,-30249,
                        -31227,-32073,-32631,-32359,-31817,-30941,-29663,-27900,-25596,-22591,
                        -18834,-14291,-9016,-3212,2794,8624,13943,18544,22353,25408,27780,29553,
                        30855,31751,32315,32611,32687,32593,32351,31983,31491,30871,30097,28895,
                        -28240,-30489,-31343,-31975,-32431,-32697,-32767,-32615,-32217,-31525,
                        -30489,-29035,-27090,-24519,-21237,-17178,-12339,-6829,-902,5081,10748,
                        15805,20102,23615,26396,28510,30109,31245,31995,31955,31437,30729,29887,
                        28943,27908,26784,25560,24077,22781,-22207,-22735,-22709,-22471,-22065,
                        -21497,-20773,-19896,-18872,-17698,-16361,-14857,-13141,-11206,-9054,-6717,
                        -4259,-1796,522,2548,4167,5339,6079,6445,6503,6319,5949,5449,4847,4183,
                        3480,2756,2028,1304,590,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                        0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-478,-1168,-1882,-2596,
                        -3336,-4074,-4795,-5487,-6119,-6669,-7095,-7357,-7399,-7157,-6559,-5543,
                        -4076,-2132,), dtype=np.int16)
wave_noise = np.array([random.randint(-VOLUME, VOLUME) for i in range(SAMPLE_SIZE)], dtype=np.int16)

# map s range a1-a2 to b1-b2
def map_range(s, a1, a2, b1, b2):
    return b1 + ((s - a1) * (b2 - b1) / (a2 - a1))

# mix between values a and b, works with numpy arrays too, t ranges 0-1
def lerp(a, b, t):
    return (1-t)*a + t*b

waveform[:] = wave_saw
wave_mix = 0.0
lfo_rates = (0.1, 0.5, 0.8, 1.5, 3.0, 6.0, 7.0, 8.0)
lfo_index = 0
lfo1 = synthio.LFO(rate=(lfo_rates[lfo_index]), waveform=wave_sine)  # rate is in Hz
synth.lfos.append(lfo1)
hold = False  # state of note hold
octaves = False

def light_button_pixels(button_number):
    pixels[pix_map[button_number]+1] = 0xFF0000
    pixels[pix_map[button_number]-1] = 0xFF0000
    pixels.show()

def reset_button_pixels(button_number):
    pixels[pix_map[button_number]+1] = 0x000000
    pixels[pix_map[button_number]-1] = 0x000000
    pixels.show()

def clamp(v, low, high):
    return min(max(v, low), high)

print("-Computer Perfection Synth-")

note = None
mod_key = 0
last_mod_button_event_time = 0
waveset = 0


while True:
    # watch for mod buttons to be pressed
    mod_button_event = mod_buttons.events.get()
    if mod_button_event:
        mod_key = mod_button_event.key_number
        if mod_button_event.pressed:
            if mod_key == 0:  # SET switch
                last_mod_button_event_time = time.monotonic()

            if mod_key == 1:  # enable octaves
                octaves = True

        if mod_button_event.released:
            if last_mod_button_event_time and mod_key == 0:  # short press-release increase LFO rate
                lfo_index = clamp(lfo_index+1, 0, len(lfo_rates)-1)
                print(lfo_index)
                lfo_rate = lfo_rates[lfo_index]
                lfo1.rate = lfo_rate
                last_mod_button_event_time = 0
            if mod_key == 1:  # disable octaves
                octaves = False
    # long press slows the LFO rate
    if last_mod_button_event_time != 0 and time.monotonic() - last_mod_button_event_time > 1.0:
        last_mod_button_event_time = 0
        lfo_index = clamp(lfo_index-1, 0, len(lfo_rates)-1)
        lfo_rate = lfo_rates[lfo_index]
        lfo1.rate = lfo_rate

    # watch for note buttons to be pressed
    note_button_event = note_buttons.events.get()
    if note_button_event:
        i = note_button_event.key_number
        if note_button_event.pressed:
            if octaves:
                synth.press((note_list[i]+(octave*12), note_list[i]+(octave*12)-12))
            else:
                synth.press((note_list[i]+(octave*12),))
            light_button_pixels(i)
        if note_button_event.released:
            if not hold:
                reset_button_pixels(i)
                synth.release((note_list[i]+(octave*12), note_list[i]+(octave*12)-12))
                reset_button_pixels(i)

    # watch for switches to be changed
    switch_event = switches.events.get()
    if switch_event:
        sw = switch_event.key_number
        if switch_event.pressed:
            if sw == 0:  # MODE toggle right
                mixer.voice[0].level = 0.45
                # wave_mix = 0.5
                waveset = 0
            if sw == 1:  # SKILL toggle center
                hold = True

        if switch_event.released:
            if sw == 0:  # MODE toggle center
                mixer.voice[0].level = 0.95
                waveset = 1
            if sw == 1:  # SKILL toggle right or left
                hold = False
                for r in range(len(note_list)):  # turn off all notes
                    # if octaves:
                    synth.release((note_list[r]+(octave*12), note_list[r]+(octave*12)-12))
                for h in range(len(pix_map)):  # turn off held pixels
                    reset_button_pixels(h)

    lfo_val_for_lerp = map_range(lfo1.value, -1, 1, 0, 1)
    if waveset == 0:
        waveform[:] = lerp(wave_sine, wave_weird1, lfo_val_for_lerp)
    else:
        waveform[:] = lerp(wave_saw, wave_noise, lfo_val_for_lerp)
