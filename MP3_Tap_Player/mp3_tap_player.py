# MP3 playback with tap trigger
# Works on Feather M4 (or other M4 based boards) with Propmaker
import time
import board
import busio
import digitalio
import audioio
import audiomp3
import adafruit_lis3dh

startup_play = False  # set to True to play all samples once on startup

# Set up accelerometer on I2C bus
i2c = busio.I2C(board.SCL, board.SDA)
int1 = digitalio.DigitalInOut(board.D6)
accel = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)
accel.set_tap(1, 100)  # single or double-tap, threshold

# Set up speaker enable pin
enable = digitalio.DigitalInOut(board.D10)
enable.direction = digitalio.Direction.OUTPUT
enable.value = True

speaker = audioio.AudioOut(board.A0)

sample_number = 0

print("Lars says, 'Hello, CVT Joseph. Tap to play.'")

if startup_play:  # Play all on startup
    for i in range(10):
        sample = "/lars/lars_0{}.mp3".format(i)
        print("Now playing: '{}'".format(sample))
        mp3stream = audiomp3.MP3Decoder(open(sample, "rb"))
        speaker.play(mp3stream)

        while speaker.playing:
            time.sleep(0.1)
    enable.value = speaker.playing


while True:
    if accel.tapped and speaker.playing is False:
        sample = "/lars/lars_0{}.mp3".format(sample_number)
        print("Now playing: '{}'".format(sample))
        mp3stream = audiomp3.MP3Decoder(open(sample, "rb"))
        speaker.play(mp3stream)
        sample_number = (sample_number + 1) % 10
    enable.value = speaker.playing
