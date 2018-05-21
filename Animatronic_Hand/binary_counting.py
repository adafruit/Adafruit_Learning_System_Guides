#  Animatronic Hand
#  Binary Counting on four fingers up to 15
from digitalio import DigitalInOut, Direction, Pull
import audioio
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import servo
from busio import I2C
import board
import time

# Create I2C and seesaw objuect
i2c = I2C(board.SCL, board.SDA)
ss = Seesaw(i2c)

#################### CPX switch
# use the CPX onboard switch to turn on/off (helps calibrate)
switch = DigitalInOut(board.SLIDE_SWITCH)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

#################### Audio setup
print("Let's count in binary.")
wavfiles = ["one.wav", "two.wav", "three.wav", "four.wav", "five.wav", "six.wav",
            "seven.wav", "eight.wav", "nine.wav", "ten.wav", "eleven.wav",
            "twelve.wav", "thirteen.wav", "fourteen.wav", "fifteen.wav"]
introfile = "intro.wav"

cpx_audio = audioio.AudioOut(board.A0)
def play_file(wavfile):
    with open(wavfile, "rb") as f:
        wav = audioio.WaveFile(f)
        cpx_audio.play(wav)
        while cpx_audio.playing:
            pass

#################### 4 Servos
servos = []
for ss_pin in (17, 16, 15, 14):
    pwm = PWMOut(ss, ss_pin)
    pwm.frequency = 50
    _servo = servo.Servo(pwm)
    _servo.angle = 90   # starting angle, middle
    servos.append(_servo)

# Which servos to actuate for each number
counting = [
    [3],
    [2],
    [3, 2],
    [1],
    [1, 3],
    [1, 2],
    [3, 2, 1],
    [0],
    [0, 3],
    [0, 2],
    [0, 3, 2],
    [0, 1],
    [0, 3, 1],
    [0, 2, 1],
    [0, 3, 2, 1]
]

play_file(introfile)

while True:
    if not switch.value:
        continue

    # the CPX switch is on, so do things
    for i in range(4):  # close the fist
        servos[i].angle = 0  # close the fingers
        print("Servo %s angle = 0" % i )
        time.sleep(.2)

    time.sleep(1)  # pause a moment

    for i in range(len(counting)):
        # close all the counting fingers between numbers
        for k in range(4):
            servos[k].angle = 0  # close
            print("\t\tServo #%d angle 0" % k)
            time.sleep(0.3)

        print("Number #%d \tfingers: %s" % (i+1, counting[i]))

        # open just the indicated fingers when counting
        for j in range(len(counting[i])):
            servos[counting[i][j]].angle = 180  # open
            print("\t\tServo #%d angle 180" % counting[i][j])
            time.sleep(0.3)
        # say it!
        play_file(wavfiles[i])
        # hold for a bit of time
        time.sleep(0.3)
        print("...")
