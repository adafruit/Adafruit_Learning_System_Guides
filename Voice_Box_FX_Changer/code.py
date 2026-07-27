# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Voice Box FX Changer
I2S Mic in -> .WAV file -> I2S DAC out
Effects controlled with analog inputs during looped playback
"""
import io
import time
import audiobusio
import board
import audioi2sin
import simpleio
import audiodelays
import audiofreeverb
import audiofilewriter
import audiofilters
import audiocore
import audiomixer
import keypad
from analogio import AnalogIn
import neopixel

pitch_slide = AnalogIn(board.A0)
reverb_slide = AnalogIn(board.A1)
dist_slide = AnalogIn(board.A2)
# record button on D24, play button on A3
keys = keypad.Keys((board.D24, board.A3), value_when_pressed=False, pull=True)

pixels = neopixel.NeoPixel(board.D12, 8, brightness=0.6, auto_write=True)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
PURPLE = (50, 0, 255)
OFF = (0, 0, 0)
# start-up purple marquee
for i in range(8):
    pixels[i] = PURPLE
    time.sleep(0.2)
time.sleep(0.5)

# recording config
SAMPLE_RATE = 16000
OUTPUT_PATH = "/recording.wav"
MAX_RECORD_SECONDS = 20
# mono 16-bit = 2 bytes/sample + room for the 44-byte WAV header
CAPTURE_ALLOC = SAMPLE_RATE * 2 * MAX_RECORD_SECONDS + 64
capture = None

# Mic
mic = audioi2sin.I2SIn(
    bit_clock=board.D5,
    word_select=board.D6,
    data=board.D9,
    sample_rate=SAMPLE_RATE,
    bit_depth=32,
    output_bit_depth=16,
    mono=True,
    left_justified=False, # using ICS43434
)


i2s   = audiobusio.I2SOut(board.D10, board.D11, board.SCL)
mixer = audiomixer.Mixer(
    voice_count=1,
    sample_rate=SAMPLE_RATE,
    channel_count=1,
    bits_per_sample=16, # matches output_bit_depth
    samples_signed=True,
)
i2s.play(mixer)
mixer.voice[0].level = 1.0

pitch_shift = audiodelays.PitchShift(
    semitones=0.0,
    mix=1.0,
    window=2048,
    overlap=256,
    buffer_size=1024,
    channel_count=1,
    sample_rate=SAMPLE_RATE,
)

reverb = audiofreeverb.Freeverb(
    roomsize=0.35,
    damp=0.25,
    buffer_size=1024,
    channel_count=1,
    sample_rate=SAMPLE_RATE,
    mix=0.0,
)

echo = audiodelays.Echo(
    max_delay_ms=1000,
    delay_ms=850,
    decay=0.0,
    buffer_size=1024,
    channel_count=1,
    sample_rate=SAMPLE_RATE,
    mix=1.0,
    freq_shift=False
)

amp = audiofilters.Distortion(
    pre_gain=15,
    drive=0.00,
    mode=audiofilters.DistortionMode.LOFI,
    soft_clip=True,
    mix=1.0,
    buffer_size=1024,
    sample_rate=SAMPLE_RATE,
    bits_per_sample=16,
    samples_signed=True,
    channel_count=1,
)

loop = False
recording = False
pixels.fill(OFF)

while True:
    event = keys.events.get()
    if event:
        key_number = event.key_number
        if event.pressed and key_number == 0: # record button
            if not recording: # press to record
                i2s.stop() # stopping i2s out mutes DAC
                pixels.fill(RED) # red means recording
                capture = io.BytesIO(CAPTURE_ALLOC) # write into memory
                writer = audiofilewriter.AudioFileWriter(capture)
                writer.play(mic)
                recording = True
            else: # press to stop
                writer.stop()
                pixels.fill(YELLOW) # yellow while writing
                print("captured", capture.tell(), "bytes")
                try:
                    capture.seek(0) # write from memory to wav on file system
                    with open(OUTPUT_PATH, "wb") as f:
                        while True:
                            chunk = capture.read(4096)
                            if not chunk:
                                break
                            f.write(chunk)
                    capture.seek(0)
                    recording = False
                    pixels.fill(OFF)
                except OSError as e:
                    pixels.fill(BLUE) # error = blue, but continues running
                    print(f"Read-only mode, can't save the file, flip the switch and reboot!: {e}")
                    time.sleep(2)
                    pixels.fill(OFF)
                    continue

        if event.pressed and key_number == 1: # play button
            if not loop: # press to play, looping
                i2s.play(mixer)
                try:
                    # opens wav file that was just written from memory
                    file = open("recording.wav", "rb")
                    wav = audiocore.WaveFile(file)
                    print("got file")
                    pixels.fill(GREEN) # playback is green
                except AttributeError as e:
                    pixels.fill(BLUE)
                    print(f"Missing recording.wav: {e}")
                    time.sleep(2)
                    pixels.fill(OFF)
                    continue
                loop = True
                pitch_shift.play(wav, loop=True) # effect chain, all have to loop
                reverb.play(pitch_shift, loop=True)
                echo.play(reverb, loop=True)
                amp.play(echo, loop=True) # gain boost
                mixer.voice[0].play(amp, loop=True)
            else: # press to stop
                mixer.voice[0].stop()
                loop = False
                pixels.fill(OFF)
    # controlling % of reverb in the mix
    verb = simpleio.map_range(reverb_slide.value, 100, 65536, 0.0, 1.0)
    reverb.mix = verb
    # controlling amount of echo decay
    echo_range = simpleio.map_range(dist_slide.value, 100, 65536, 0.0, 1.0)
    echo.decay = echo_range
    # an octave has 12 semitones, -13 and +13 gives full octave up and down
    pitch = simpleio.map_range(pitch_slide.value, 100, 65536, -13.0, 13.0)
    pitch_shift.semitones = int(pitch)
