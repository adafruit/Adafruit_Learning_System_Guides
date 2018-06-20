import os
import time
import random
import audioio
from digitalio import DigitalInOut, Pull, Direction
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import servo
from busio import I2C
import board

wavefiles = [file for file in os.listdir("/") if (file.endswith(".wav") and not file.startswith("._"))]
print("Audio files found: ", wavefiles)

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

# Servo angles
MOUTH_START = 100
MOUTH_END = 90

# 17 is labeled SERVO 1 on CRICKIT
pwm = PWMOut(seesaw, 17)
# must be 50 cannot change
pwm.frequency = 50
my_servo = servo.Servo(pwm)
# Starting servo locations
my_servo.angle = MOUTH_START

# Audio playback object and helper to play a full file
a = audioio.AudioOut(board.A0)

def play_file(wavfile):
    print("Playing", wavfile)
    with open(wavfile, "rb") as f:
        wav = audioio.WaveFile(f)
        a.play(wav)
        while a.playing:
            my_servo.angle = MOUTH_END
            time.sleep(0.15)
            my_servo.angle = MOUTH_START
            time.sleep(0.15)

while True:
    play_file(random.choice(wavefiles))

    time.sleep(3)