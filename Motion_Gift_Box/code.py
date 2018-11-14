import time
import random
import audioio
import board
import neopixel
from adafruit_crickit import crickit

# NeoPixels on the Circuit Playground Express
pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=0.3)
pixels.fill(0)                # Off to start

# PIR sensor on signal #1
PIR_SENSOR = crickit.SIGNAL1
crickit.seesaw.pin_mode(PIR_SENSOR, crickit.seesaw.INPUT)

# Set audio out on speaker
speaker = audioio.AudioOut(board.A0)
audio_files = ["evillaugh3.wav", "laugh.wav"]

# One motor
motor_1 = crickit.dc_motor_1
motor_1.throttle = 0             # off to start

while True:
    pixels.fill(0)
    print("Waiting for trigger")
    while not crickit.seesaw.digital_read(PIR_SENSOR):
        pass
    print("PIR triggered")
    pixels.fill((100, 0, 0))    # NeoPixels red

    # Start playing the file (in the background)
    audio_file = open(random.choice(audio_files), "rb")   # muahaha
    wav = audioio.WaveFile(audio_file)
    speaker.play(wav)

    # move motor back and forth for 3 seconds total
    timestamp = time.monotonic()
    while time.monotonic() - timestamp < 3:
        motor_1.throttle = 1        # full speed forward
        time.sleep(0.25 + random.random())  # random delay from 0.25 to 1.25 seconds
        motor_1.throttle = -1        # full speed backward
        time.sleep(0.25 + random.random())  # random delay from 0.25 to 1.25 seconds
    motor_1.throttle = 0        # stop!

    # wait for audio to stop
    while speaker.playing:
        pass
    # clean up and close file
    audio_file.close()
