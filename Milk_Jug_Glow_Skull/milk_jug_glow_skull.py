import time
import board
import digitalio
import audioio
import neopixel

# user variables
pix_rate = 0.03  # Increase the number to slow down the color chase
blink_times = 2  # number of times the eyes blink between color chases
blink_speed = 0.1  # speed of the blinks, lower numbers are faster
rest_time = 3  # time between color changes e.g. '3' = 3 sec, '300'= 5 mins.

#  setup
NEOPIXEL_PIN = board.EXTERNAL_NEOPIXEL
NUM_PIXELS = 30
pixels = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS)


led = digitalio.DigitalInOut(board.D13)
led.direction = digitalio.Direction.OUTPUT
led.value = True
time.sleep(0.5)

ORANGE = (255, 30, 0)
PURPLE = (200, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)

COLORS = [ORANGE, PURPLE, RED, GREEN, ORANGE, PURPLE, RED]

pixels.fill(ORANGE)
pixels.show()

def color_chase(color, wait):
    for i in range(NUM_PIXELS):
        pixels[i] = color
        time.sleep(wait)
        pixels.show()


def blink(times, speed):
    for _ in range(times):
        led.value = False
        time.sleep(speed)
        led.value = True
        time.sleep(speed)

def play_waves(file_num):
    wave_file = open(wave_files[file_num], "rb")  # open a wav file
    wave = audioio.WaveFile(wave_file)
    audio.play(wave)  # play the wave file
    while audio.playing:  # allow the wav to finish playing
        pass
    wave_file.close()  # close the wav file

wave_files = ["alex_deepgrowl1.wav", "alex-highgrowl1.wav", "alex-squeal1.wav",
              "toni-deepgrowl.wav", "toni-highgrowl2.wav","toni-pigsqueal.wav",
              "toni-pitchedscream2.wav"]
audio = audioio.AudioOut(board.A0)

while True:
    for k in range(len(wave_files)):
        blink(blink_times, blink_speed)
        color_chase(COLORS[k], pix_rate)
        play_waves(k)
        time.sleep(rest_time)
