"""
A CircuitPython 'crank' USB HID demo
Uses a ItsyBitsy M0 + Rotary Encoder -> USB HID keyboard
"""

import board
from digitalio import DigitalInOut, Direction, Pull
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

# Encoder button is a digital input with pullup on D9
button = DigitalInOut(board.D9)
button.direction = Direction.INPUT
button.pull = Pull.UP

# Rotary encoder inputs with pullup on D10 & D11 on ItsyBitsy
rot_a = DigitalInOut(board.D10)
rot_a.direction = Direction.INPUT
rot_a.pull = Pull.UP
rot_b = DigitalInOut(board.D11)
rot_b.direction = Direction.INPUT
rot_b.pull = Pull.UP

# Used to do HID output, see below
kbd = Keyboard()

######################### MAIN LOOP ##############################

# the counter counts up and down, it can roll over! 16-bit value
encoder_counter = 0
# direction tells you the last tick which way it went
encoder_direction = 0

# constants to help us track what edge is what
A_POSITION = 0
B_POSITION = 1
UNKNOWN_POSITION = -1  # initial state so we know if something went wrong

rising_edge = falling_edge = UNKNOWN_POSITION

# get initial/prev state and store at beginning
last_button = button.value
rotary_prev_state = [rot_a.value, rot_b.value]

while True:
    # reset encoder and wait for the next turn
    encoder_direction = 0

    # take a 'snapshot' of the rotary encoder state at this time
    rotary_curr_state = [rot_a.value, rot_b.value]

    if rotary_curr_state != rotary_prev_state:
        #print("Changed")
        if rotary_prev_state == [True, True]:
            # we caught the first falling edge!
            if not rotary_curr_state[A_POSITION]:
                #print("Falling A")
                falling_edge = A_POSITION
            elif not rotary_curr_state[B_POSITION]:
                #print("Falling B")
                falling_edge = B_POSITION
            else:
                # uhh something went deeply wrong, lets start over
                continue

        if rotary_curr_state == [True, True]:
            # Ok we hit the final rising edge
            if not rotary_prev_state[B_POSITION]:
                rising_edge = B_POSITION
                # print("Rising B")
            elif not rotary_prev_state[A_POSITION]:
                rising_edge = A_POSITION
                # print("Rising A")
            else:
                # uhh something went deeply wrong, lets start over
                continue

            # check first and last edge
            if (rising_edge == A_POSITION) and (falling_edge == B_POSITION):
                encoder_counter -= 1
                encoder_direction = -1
                print("%d dec" % encoder_counter)
            elif (rising_edge == B_POSITION) and (falling_edge == A_POSITION):
                encoder_counter += 1
                encoder_direction = 1
                print("%d inc" % encoder_counter)
            else:
                # (shrug) something didn't work out, oh well!
                encoder_direction = 0

            # reset our edge tracking
            rising_edge = falling_edge = UNKNOWN_POSITION

    rotary_prev_state = rotary_curr_state

    # Check if rotary encoder went up
    if encoder_direction == 1:
        ConsumerControl().send(ConsumerControlCode.VOLUME_DECREMENT) #Volume Down
    #    kbd.press(Keycode.LEFT_ARROW)
    #    kbd.release_all()

    # Check if rotary encoder went down
    if encoder_direction == -1:
        ConsumerControl().send(ConsumerControlCode.VOLUME_INCREMENT) #Volume Up
    #    kbd.press(Keycode.RIGHT_ARROW)
    #    kbd.release_all()

    # Button was 'just pressed'
    if (not button.value) and last_button:
        print("Button pressed!")
        kbd.press(Keycode.SPACE) #Keycode for space bar
        kbd.release_all()

    elif button.value and (not last_button):
        print("Button Released!")