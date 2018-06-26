import time
import audioio
from digitalio import DigitalInOut, Direction
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import servo
from busio import I2C
import board

# Minerva Owl Robot

wavefiles = ["01.wav", "02.wav", "03.wav", "04.wav", "05.wav", "06.wav",
             "07.wav", "08.wav"]

# Create seesaw object
i2c = I2C(board.SCL, board.SDA)
seesaw = Seesaw(i2c)

led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT

# Servo angles
EYES_START = 90
EYES_LEFT = 110
EYES_RIGHT = 70
WINGS_START = 90
WINGS_END = 160

# 17 is labeled SERVO 1 on CRICKIT, 16 is SERVO 2
pwm1 = PWMOut(seesaw, 17)
pwm2 = PWMOut(seesaw, 16)

# must be 50 cannot change
pwm1.frequency = 50
pwm2.frequency = 50
# microservo usually is 400/2500 (tower pro sgr2r)
eye_servo = servo.Servo(pwm1, min_pulse=400, max_pulse=2500)
wing_servo = servo.Servo(pwm2, min_pulse=400, max_pulse=2500)
# Starting servo locations
eye_servo.angle = EYES_START
wing_servo.angle = WINGS_START
# Audio playback object and helper to play a full file
a = audioio.AudioOut(board.A0)


def play_file(wavfile):
    print("Playing", wavfile)
    with open(wavfile, "rb") as f:
        wav = audioio.WaveFile(f)
        a.play(wav)
        while a.playing:  # turn servos, motors, etc. during playback
            eye_servo.angle = EYES_LEFT
            time.sleep(.25)
            eye_servo.angle = EYES_START
            time.sleep(.25)
            wing_servo.angle = WINGS_END
            time.sleep(.2)
            wing_servo.angle = WINGS_START
            time.sleep(.2)
            eye_servo.angle = EYES_RIGHT
            time.sleep(.25)
            eye_servo.angle = EYES_START
            time.sleep(.25)


while True:
    for i in range(8):
        play_file(wavefiles[i])
        time.sleep(2.5)
