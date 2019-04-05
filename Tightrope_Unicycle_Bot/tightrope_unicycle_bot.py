import time
import board
import neopixel
import audioio
import adafruit_crickit

print("Adabot Tightrope Unicyclist!")
RED =   (16, 0, 0)
GREEN = (0, 16, 0)
BLACK = (0, 0, 0)

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness = 0.2)
pixels.fill(BLACK)

# Create a motor on Crickit Motor 1 port
motor = adafruit_crickit.crickit.dc_motor_1

############### User variables
run_time = 6
speed = 0.65

############### Music
cpx_audio = audioio.AudioOut(board.A0)  # speaker out on Crickit
def play_file(wavfile):
    with open(wavfile, "rb") as f:
        wav = audioio.WaveFile(f)
        cpx_audio.play(wav)
        while cpx_audio.playing:
            pass

wav_file_name = "circus.wav"
play_file(wav_file_name)

while True:
    # set NeoPixels green in direction of movement
    for i in range(5):
        pixels[i] = GREEN
    for i in range(5):
        pixels[i+5] = BLACK

    motor.throttle = speed  # full speed forward
    time.sleep(run_time)  # motor will run for this amount of time

    # set NeoPixels red when stopped
    pixels.fill(RED)
    motor.throttle = 0  # stop the motor

    # set NeoPixels green in direction of movement
    for i in range(5):
        pixels[i] = BLACK
    for i in range(5):
        pixels[i+5] = GREEN

    motor.throttle = -1 * speed  # full speed backward
    time.sleep(run_time)  # motor will run for this amount of time

    pixels.fill(RED)
    motor.throttle = 0  # stopped
