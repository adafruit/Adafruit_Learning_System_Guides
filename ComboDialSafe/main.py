# CPX Combo Safe
from adafruit_circuitplayground.express import cpx
import time
import board
import simpleio

#  plug red servo wire to VOUT, brown to GND, yellow to A3
servo = simpleio.Servo(board.A3)

def dialCircle(R, G, B):
    for i in range(10):
        cpx.pixels[i] = ((R, G, B))
        time.sleep(.01)

cpx.pixels.brightness = 0.1  # set brightness value

correctCombo = ['A', 'D', 'A']  # this is where to set the combo
enteredCombo = []  # this will be used to store attempts
currentDialPosition = 'X'

def unlockServo():
    servo.angle = 180

def lockServo():
    servo.angle = 0

while True:
    cpx.red_led = 0  # turn off the on board LED

    xF, yF, zF = cpx.acceleration  # read acceleromter
    x = int(xF)  # make int of it
    y = int(yF)
    z = int(zF)

    # four simple rotation positions, A-D
    # the combination entries are based on which letter is facing up
    #
    #              A
    #            .___.
    #         .         .
    #     D  .           .  B
    #        .           .
    #         .         .
    #            .|_|.
    #              C

    if x == 0 and y == 9:
        currentDialPosition = 'A'  # used to store dial position
        dialCircle(25, 25, 0)

    if x == 9 and y == 0:
        currentDialPosition = 'B'
        dialCircle(25, 0, 25)

    if x == 0 and y == -9:
        currentDialPosition = 'C'
        dialCircle(0, 0, 50)

    if x == -9 and y == 0:
        currentDialPosition = 'D'
        dialCircle(0, 25, 25)

    # press the left button to enter the current position as a combo entry
    if cpx.button_a is True:  # this means the button has been pressed
        cpx.red_led = 1  # turn on the on-board LED
        # grab the currentDialPosition value and add to the list
        enteredCombo.append(currentDialPosition)
        dialMsg = 'Dial Position: ' + str(enteredCombo[(len(enteredCombo)-1)])
        print(dialMsg)
        time.sleep(1)  # slow down button checks

    # press the right button to lock the servo
    if cpx.button_b:  # this is a more Pythonic way to check button status
        cpx.red_led = 1
        dialCircle(47, 23, 40)
        lockServo()
        time.sleep(1)

    if len(enteredCombo) == 3:
        # print('full')
        if enteredCombo == correctCombo:  # they match!
            print('Correct! Unlocked.')
            dialCircle(0, 100, 0)
            unlockServo()
            time.sleep(3)
            enteredCombo = []  # clear this for next time around

        else:
            print('Incorret combination.')
            dialCircle(100, 0, 0)
            time.sleep(3)
            enteredCombo = []  # clear this for next time around
