# CircuitPython 3.0 CRICKIT demo

import gc
import time

import audioio
import audiocore
import board
from adafruit_motor import servo
from adafruit_seesaw.pwmout import PWMOut
from adafruit_seesaw.seesaw import Seesaw
from busio import I2C

i2c = I2C(board.SCL, board.SDA)
ss = Seesaw(i2c)

print("Feynbot demo!")

# 1 Servo
pwm = PWMOut(ss, 17)
pwm.frequency = 50
myservo = servo.Servo(pwm)
myservo.angle = 180  # starting angle, highest

# 2 Drivers
drives = []
for ss_pin in (13, 12):
    _pwm = PWMOut(ss, ss_pin)
    _pwm.frequency = 1000
    drives.append(_pwm)

# Audio files
wavfiles = ["01.wav", "02.wav", "03.wav", "04.wav", "05.wav"]
a = audioio.AudioOut(board.A0)


# Start playing the file (in the background)
def play_file(wavfile):
    f = open(wavfile, "rb")
    wav = audiocore.WaveFile(f)
    a.play(wav)


# Tap the solenoids back and forth
def bongo(t):
    for _ in range(t):
        drives[0].duty_cycle = 0xFFFF
        time.sleep(0.1)
        drives[0].duty_cycle = 0
        time.sleep(0.1)
        drives[1].duty_cycle = 0xFFFF
        time.sleep(0.1)
        drives[1].duty_cycle = 0
        time.sleep(0.1)


# Move mouth back and forth
def talk(t):
    for _ in range(t):
        myservo.angle = 150
        time.sleep(0.1)
        myservo.angle = 180
        time.sleep(0.1)


filenum = 0  # counter to play all files

while True:
    gc.collect()
    print(gc.mem_free())

    # time to play the bongos!
    bongo(5)
    time.sleep(1)

    # OK say something insightful
    play_file(wavfiles[filenum])
    # and move the mouth while it does
    while a.playing:
        talk(1)

    # Done being insightful, take a break
    time.sleep(1)

    # If we went thru all the files, JAM OUT!
    filenum += 1
    if filenum >= len(wavfiles):
        bongo(20)
        filenum = 0
