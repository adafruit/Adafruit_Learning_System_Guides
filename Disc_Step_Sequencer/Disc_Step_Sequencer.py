"""
Opto Mechanical Disc Step Sequencer from John Park's Workshop
 Crickit Feather M4 Express, Crickit FeatherWing, continuous servo,
 four reflection sensors, speaker

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

import audioio
import board
from digitalio import DigitalInOut, Direction
from adafruit_crickit import crickit
from adafruit_debouncer import Debouncer

#  You get 4 samples, they must all have the same sample rate and must
#  all be mono or stereo (no mix-n-match!)
#  mixer info https://circuitpython.readthedocs.io/en/latest/shared-bindings/audioio/Mixer.html

VOICES = ["bd_tek.wav", "elec_hi_snare.wav", "ch_01.wav", "clap_01.wav"]
# Parse the first file to figure out what format its in
with open(VOICES[0], "rb") as f:
    wav = audioio.WaveFile(f)
    print("%d channels, %d bits per sample, %d Hz sample rate " %
          (wav.channel_count, wav.bits_per_sample, wav.sample_rate))

    # Audio playback object - we'll go with either mono or stereo depending on
    # what we see in the first file
    if wav.channel_count == 1:
        audio = audioio.AudioOut(board.A0)
    elif wav.channel_count == 2:
        # audio = audioio.AudioOut(board.A0, right_channel=board.A0)
        audio = audioio.AudioOut(board.A0)
    else:
        raise RuntimeError("Must be mono or stereo waves!")
    mixer = audioio.Mixer(voice_count=4,
                          sample_rate=wav.sample_rate,
                          channel_count=wav.channel_count,
                          bits_per_sample=wav.bits_per_sample,
                          samples_signed=True)
    audio.play(mixer)

samples = []
# Read the 4 wave files, convert to stereo samples, and store
# (show load status on neopixels and play audio once loaded too!)
for v in VOICES:
    wave_file = open(v, "rb")
    print(v)
    # OK we managed to open the wave OK
    sample = audioio.WaveFile(wave_file)
    # debug play back on load!
    mixer.play(sample, voice=0)
    while mixer.playing:
        pass
    samples.append(sample)


led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

# For signal control, we'll chat directly with seesaw, use 'ss' to shorten typing!
ss = crickit.seesaw

# define and set up inputs to use the debouncer
def make_criket_signal_debouncer(pin):  # create pin signal objects
    ss.pin_mode(pin, ss.INPUT_PULLUP)
    return Debouncer(lambda : ss.digital_read(pin))

# The IR sensors on are pullups, connect to ground to activate
clock_pin = make_criket_signal_debouncer(crickit.SIGNAL1)
voice_1_pin = make_criket_signal_debouncer(crickit.SIGNAL2)
voice_2_pin = make_criket_signal_debouncer(crickit.SIGNAL3)
voice_3_pin = make_criket_signal_debouncer(crickit.SIGNAL4)
voice_4_pin = make_criket_signal_debouncer(crickit.SIGNAL5)
# Crickit capacitive touch pads
touch_1_pad = Debouncer(lambda: crickit.touch_1.value)
touch_4_pad = Debouncer(lambda: crickit.touch_4.value)
touch_2_3_pad = Debouncer(lambda:  crickit.touch_2.value and crickit.touch_3.value)

crickit.continuous_servo_1.set_pulse_width_range(min_pulse=500, max_pulse=2500)
speed = -0.04  #this is clockwise/forward at a moderate tempo


def play_voice(vo):
    mixer.stop_voice(vo)
    mixer.play(samples[vo], voice=vo, loop=False)

while True:
    clock_pin.update()  #debouncer at work
    voice_1_pin.update()
    voice_2_pin.update()
    voice_3_pin.update()
    voice_4_pin.update()
    touch_1_pad.update()
    touch_4_pad.update()
    touch_2_3_pad.update()

    crickit.continuous_servo_1.throttle = speed  # spin the disc at speed defined by touch pads

    if clock_pin.fell:  # sensor noticed change from white (reflection) to black (no reflection)
                        # this means a clock tick has begun, time to check if any steps will play
        led.value = 0

        if voice_1_pin.value:  # a black step (no reflection) mark during clock tick, play a sound!
            led.value = 1  # light up LED when step is read
            # print('|   .kick.    |             |                  |            |')
            play_voice(0)

        if voice_2_pin.value:
            led.value = 1
            # print('|             |   .snare.   |                  |            |')
            play_voice(1)

        if voice_3_pin.value:
            led.value = 1
            # print('|             |             |   .closed hat.   |            |')
            play_voice(2)

        if voice_4_pin.value:
            led.value = 1
            # print('|             |             |                  |   .clap.   |')
            play_voice(3)

    if touch_4_pad.rose:  # speed it up
        speed -= 0.001
        # print("speed: %s" % speed)

    if touch_1_pad.rose:  #  slow it down
        speed += 0.001
        # you can comment out the next two lines if you want to go backwards
        # however, the clock ticks may not register with the default template spacing
        if speed >= 0: # to prevent backwards
            speed = 0
        # print("speed: %s" % speed)

    if touch_2_3_pad.rose:  # stop the disc
        speed = 0
        # print("speed: %s" % speed)
