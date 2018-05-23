#  Animatronic Hand
#  CPX with CRICKIT and four servos
#  touch four cap pads to close the fingers

from digitalio import DigitalInOut, Direction, Pull
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import servo
from busio import I2C
import board

i2c = I2C(board.SCL, board.SDA)
ss = Seesaw(i2c)

#################### CPX switch
# use the CPX onboard switch to turn on/off (helps calibrate)
switch = DigitalInOut(board.SLIDE_SWITCH)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

#################### 4 Servos
servos = []
for ss_pin in (17, 16, 15, 14):
    pwm = PWMOut(ss, ss_pin)
    pwm.frequency = 50
    _servo = servo.Servo(pwm)
    _servo.angle = 90   # starting angle, middle
    servos.append(_servo)

CAPTOUCH_THRESH = 500  # threshold for touch detection

cap_state = [False, False, False, False]
cap_justtouched = [False, False, False, False]
cap_justreleased = [False, False, False, False]

curl_finger = [False, False, False, False]
finger_name = ['Index', 'Middle', 'Ring', 'Pinky']

while True:
    if not switch.value:  # the CPX switch is off, so do nothing
        continue
    # Check the cap touch sensors to see if they're being touched
    for i in range(4):
        touch_val = ss.touch_read(i)
        cap_justtouched[i] = False
        cap_justreleased[i] = False

        if touch_val > CAPTOUCH_THRESH:
            # print("CT" + str(i + 1) + " touched! value: " + str(touch_val))
            if not cap_state[i]:
                cap_justtouched[i] = True
                print("%s finger bent." % finger_name[i])
                servos[i].angle = 0
            cap_state[i] = True

        else:
            if cap_state[i]:
                cap_justreleased[i] = True
                print("%s finger straightened." % finger_name[i])
                servos[i].angle = 180
                # print("CT" + str(i + 1) + " released!")

            cap_state[i] = False

        if cap_justtouched[i]:
            curl_finger[i] = not curl_finger[i]
