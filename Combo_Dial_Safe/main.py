# Combo Dial Safe
# for Adafruit Circuit Playground express
# with CircuitPython

from adafruit_circuitplayground.express import cpx
import time
import board
import simpleio

#  plug red servo wire to VOUT, brown to GND, yellow to A3
servo = simpleio.Servo(board.A3)

cpx.pixels.brightness = 0.05  # set brightness value

def unlockServo():
    servo.angle = 180

def lockServo():
    servo.angle = 90

correctCombo = ['B', 'D', 'C']  # this is where to set the combo
enteredCombo = []  # this will be used to store attempts
currentDialPosition = 'X'

cpx.red_led = 1  # turn off the on-board red LED while locked
lockServo()  # lock the servo

while True:

    x_float, y_float, z_float = cpx.acceleration  # read acceleromter
    x = int(x_float)  # make int of it
    y = int(y_float)
    z = int(z_float)

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
        cpx.pixels.fill((0, 0, 255))

    if x == 9 and y == 0:
        currentDialPosition = 'B'
        cpx.pixels.fill((80, 0, 80))

    if x == 0 and y == -9:
        currentDialPosition = 'C'
        cpx.pixels.fill((255, 70, 0))

    if x == -9 and y == 0:
        currentDialPosition = 'D'
        cpx.pixels.fill((255, 255, 255))

    # press the right/B button to lock the servo
    if cpx.button_b:  # this is a more Pythonic way to check button status
        print('Locked/Reset')
        cpx.red_led = 1
        cpx.pixels.fill((50, 10, 10))
        lockServo()
        cpx.play_tone(120, 0.4)
        cpx.pixels.fill((0, 0, 0))
        enteredCombo = []  # clear this for next time around
        time.sleep(1)

    # press the left/A button to enter the current position as a combo entry
    if cpx.button_a is True:  # this means the button has been pressed
        # grab the currentDialPosition value and add to the list
        enteredCombo.append(currentDialPosition)
        dialMsg = 'Dial Position: ' + str(enteredCombo[(len(enteredCombo)-1)])
        print(dialMsg)
        cpx.play_tone(320, 0.3)  # beep
        time.sleep(1)  # slow down button checks

    if len(enteredCombo) == 3:
        if enteredCombo == correctCombo:  # they match!
            print('Correct! Unlocked.')
            cpx.red_led = 0  # turn off the on board LED
            cpx.pixels.fill((0, 255, 0))
            unlockServo()
            cpx.play_tone(440, 1)
            time.sleep(3)
            enteredCombo = []  # clear this for next time around

        else:
            print('Incorret combination.')
            cpx.pixels.fill((255, 0, 0))
            cpx.play_tone(180, 0.3)  # beep
            cpx.play_tone(130, 1)  # boop
            time.sleep(3)
            enteredCombo = []  # clear this for next time around
