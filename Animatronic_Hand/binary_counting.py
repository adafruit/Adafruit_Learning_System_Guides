#  Animatronic Hand
#  Binary Counting on four fingers up to 15
import time
from digitalio import DigitalInOut, Direction, Pull
import audioio
import audiocore
import board
from adafruit_crickit import crickit

#################### CPX switch
# use the CPX onboard switch to turn on/off (helps calibrate)
switch = DigitalInOut(board.SLIDE_SWITCH)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

#################### Audio setup
print("Let's count in binary.")
wavfiles = ("one.wav", "two.wav", "three.wav", "four.wav", "five.wav", "six.wav",
            "seven.wav", "eight.wav", "nine.wav", "ten.wav", "eleven.wav",
            "twelve.wav", "thirteen.wav", "fourteen.wav", "fifteen.wav")
introfile = "intro.wav"

cpx_audio = audioio.AudioOut(board.A0)
def play_file(wavfile):
    with open(wavfile, "rb") as f:
        wav = audiocore.WaveFile(f)
        cpx_audio.play(wav)
        while cpx_audio.playing:
            pass

#################### 4 Servos!
servos = (crickit.servo_1, crickit.servo_2, crickit.servo_3, crickit.servo_4)
for servo in servos:
    servo.angle = 180 # starting angle, open hand

# Which servos to actuate for each number
counting = (
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
)

play_file(introfile)

while True:
    if not switch.value:
        continue

    # the CPX switch is on, so do things
    for servo in servos:  # close the fist
        servo.angle = 0  # close the fingers
        print("Servo %d angle = 0" % (servos.index(servo)+1) )
        time.sleep(.2)

    time.sleep(1)  # pause a moment

    for i in range(len(counting)):
        # close all the counting fingers between numbers
        for servo in servos:
            servo.angle = 0  # close
            print("\t\tServo #%d angle 0" % (servos.index(servo)+1))
            time.sleep(0.3)

        print("Number #%d \tfingers: %s" % (i+1, counting[i]))

        # open just the indicated fingers when counting
        for finger in counting[i]:
            servos[finger].angle = 180  # open
            print("\t\tServo #%d angle 180" % (finger+1))
            time.sleep(0.3)
        # say it!
        play_file(wavfiles[i])
        # hold for a bit of time
        time.sleep(0.3)
        print("...")
