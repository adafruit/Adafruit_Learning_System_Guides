import os
import time
import random
import board
from busio import I2C
import audioio
import adafruit_lis3dh
from adafruit_crickit import crickit

# Create accelerometer object for Circuit Playground Express
i2c1 = I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c1, address=0x19)
# Changing RANGE_4_G to RANGE_2_G is more sensitive, RANGE_8_G less sensitive

lis3dh.range = adafruit_lis3dh.RANGE_4_G

# Audio playback object and helper to play a full file
a = audioio.AudioOut(board.A0)

# Find all Wave files on the storage
wavefiles = [file for file in os.listdir("/")
             if (file.endswith(".wav") and not file.startswith("._"))]
print("Audio files found: ", wavefiles)

# mouth servo
mouth_servo = crickit.servo_1
# TowerPro servos like 500/2500 pulsewidths
mouth_servo.set_pulse_width_range(min_pulse=500, max_pulse=2500)

# Servo angles
MOUTH_START = 90
MOUTH_END = 80

# Starting servo location
mouth_servo.angle = MOUTH_START

# Play a wave file and move the mouth while its playing!
def play_file(wavfile):
    print("Playing", wavfile)
    with open(wavfile, "rb") as f:
        wav = audioio.WaveFile(f)
        a.play(wav)
        while a.playing:  # turn servos, motors, etc. during playback
            mouth_servo.angle = MOUTH_END
            time.sleep(0.15)
            mouth_servo.angle = MOUTH_START
            time.sleep(0.15)

while True:
    if lis3dh.shake(shake_threshold=10):  # can also adjust sensitivity here
        print("Shake detected!")
        play_file(random.choice(wavefiles))
    # hang out for tiny bit
    time.sleep(0.05)
