from busio import I2C
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import motor
import board
import neopixel
import time
import audioio

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

print("Adabot Tightrope Unicyclist!")
RED = 0x100000  # (0x10, 0, 0) also works
GREEN = (0, 0x10, 0)
BLACK = (0, 0, 0)

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness = 0.2)
pixels.fill((0, 0, 0))
pixels.show()

# Create one motor on seesaw PWM pins 22 & 23, Crickit Motor 1 port
motor_a = motor.DCMotor(PWMOut(seesaw, 22), PWMOut(seesaw, 23))

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

wavfile = "circus.wav"
play_file(wavfile)

while True:
    # set NeoPixels green in direction of movement
    for i in range(5):
        pixels[i] = GREEN
    for i in range(5):
        pixels[i+5] = BLACK

    motor_a.throttle = speed  # full speed forward
    time.sleep(run_time)  # motor will run for this amount of time

    # set NeoPixels red when stopped
    for i in range(len(pixels)):
        pixels[i] = RED

    motor_a.throttle = 0  # stop the motor

    # set NeoPixels green in direction of movement
    for i in range(5):
        pixels[i] = BLACK
    for i in range(5):
        pixels[i+5] = GREEN

    motor_a.throttle = -1 * speed  # full speed backward
    time.sleep(run_time)  # motor will run for this amount of time

    for i in range(len(pixels)):
        pixels[i] = RED

    motor_a.throttle = 0  # stopped
