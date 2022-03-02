# SPDX-FileCopyrightText: 2021 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Scramblepad - a random scramble keypad simulation for Adafruit MACROPAD.
"""
# SPDX-FileCopyrightText: Copyright (c) 2021 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import random
import board
from digitalio import DigitalInOut, Direction
import displayio
import terminalio
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from adafruit_macropad import MacroPad

# CONFIGURABLES ------------------------

# Password information
#  For higher security, place password in a separate file like secrets.py
PASSWORD = "2468"
PASSWORD_LENGTH = len(PASSWORD)

# States keypad may be in
STATE_ENTRY = 1
STATE_CLEAR = 2
STATE_RESET = 3

# Color defines for keys
WHITE = 0xFFFFFF
BLACK = 0x000000
RED = 0xFF0000
ORANGE = 0xFFA500
YELLOW = 0xFFFF00
GREEN = 0x00FF00
BLUE = 0x0000FF
PURPLE = 0x800080
PINK = 0xFFC0CB
TEAL = 0x2266AA
MAGENTA = 0xFF00FF
CYAN = 0x00FFFF

colors = [PINK, RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE, TEAL, MAGENTA, CYAN]
current_colors = []

# Define sounds the keypad makes
tones = (440, 220, 245, 330, 440)  # Initial tones while scrambling
press_tone = 660  # This tone is used when each key is pressed

# Initial key values - this list will be scrambled by the scramble function
key_values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

# Define the STEMMA QT I2C line SDA to be a digital output (nonstandard use)
# SDA will be used as a digital pin to trigger a transistor to
# axctivate a solenoid which will unlock, like a door
solenoid = DigitalInOut(board.SDA)
solenoid.direction = Direction.OUTPUT

# FUNCTIONS ------------------

def keys_clear():  # Set display in the Start mode, key LEDs off
    for i in range(12):
        macropad.pixels[i] = 0x000000
        group[i].text = " "
    macropad.pixels.show()
    group[9].text = "START"
    macropad.display.show(group)
    macropad.display.refresh()

def scramble():  # Scramble values of the keys and display on screen
    for times in range(5):
        # The following lines implement a random.shuffle method
        # See https://www.rosettacode.org/wiki/Knuth_shuffle#Python
        # random.shuffle(key_values)           # Shuffle the key array
        for i in range(len(key_values)-1, 0, -1):
            j = random.randrange(i + 1)
            key_values[i], key_values[j] = key_values[j], key_values[i]
        keys_display()
        macropad.play_tone(tones[times], 0.3)  # Play a tone each scramble iteration
        time.sleep(0.01)

def keys_display():   # Display the current values of the keys on screen
    for k in range(9):  # The first 9 keys
        group[k].text = str(key_values[k])
        macropad.pixels[k] = colors[key_values[k]]
    group[10].text = str(key_values[9])  # The 'Zero' position number
    group[9].text = " "   # Start blanks
    group[11].text = " "  # Status blanks
    macropad.pixels[10] = colors[key_values[9]]
    macropad.display.refresh()
    macropad.pixels.show()

# INITIALIZATION -----------------------

macropad = MacroPad()  # Set up MacroPad library and behavior
macropad.display.auto_refresh = False
macropad.pixels.auto_write = False

# Set up displayio group with all the labels
group = displayio.Group()
for key_index in range(12):
    x = key_index % 3
    y = key_index // 3
    group.append(label.Label(terminalio.FONT, text='', color=0xFFFFFF,
                             anchored_position=((macropad.display.width - 1) * x / 2,
                                                macropad.display.height - 1 -
                                                (3 - y) * 12),
                             anchor_point=(x / 2, 1.0)))
group.append(Rect(0, 0, macropad.display.width, 12, fill=0xFFFFFF))
group.append(label.Label(terminalio.FONT, text='ScramblePad', color=0x000000,
                         anchored_position=(macropad.display.width//2, -2),
                         anchor_point=(0.5, 0.0)))


# Initialize in a clear state
state = STATE_CLEAR
macropad.keyboard.release_all()
keys_clear()
solenoid.value = False

# MAIN LOOP ----------------------------

while True:
    if state == STATE_RESET:
        print("Reset state")
        macropad.keyboard.release_all()
        password_guess = ""  # Reset password entry
        state = STATE_CLEAR  # Reset state

    # Check for key presses/releases
    event = macropad.keys.events.get()
    if not event:
        continue
    key_number = event.key_number
    pressed = event.pressed

    if pressed:
        if state == STATE_CLEAR:
            if key_number != 9:  # Waiting to hit START
                print("You must press start, lower left")
                macropad.keyboard.release(key_number)
            else:                # START pressed
                print("START pressed, enter your password")
                macropad.keyboard.release(key_number)
                password_guess = ""
                scramble()
                state = STATE_ENTRY
            continue
        if state == STATE_ENTRY:
            if key_number == 9:  # Start key during entry
                print("Restart whole key entry")
                macropad.keyboard.release_all()
                password_guess = ""  # Reset password entry
                scramble()
                continue
        #
        # From here out is password entry, state is KEY_ENTRY
        #
        if key_number < 11:  # Ignore encoder and lower right button
            old_color = macropad.pixels[key_number]  # Save color of key pressed
            macropad.pixels[key_number] = 0xFFFFFF  # Turn key white while down
            macropad.pixels.show()                  # Show key as white
            macropad.play_tone(press_tone, 0.6)     # Play tone when key pressed
        # Process input - add the key pressed to the password entry
        if key_number == 10:  # The "0" position is shifted over, take one away
            password_guess = password_guess + str(key_values[key_number-1])
        else:                 # The 1-9 keys (index values 0 to 8)
            password_guess = password_guess + str(key_values[key_number])
        print(password_guess)
        if len(password_guess) == PASSWORD_LENGTH:  # We've entered all digits
            keys_clear()                    # Clear the keypad
            if password_guess == PASSWORD:  # Success
                group[9].text = " "
                group[11].text = "OPEN"
                macropad.display.show(group)
                macropad.display.refresh()
                macropad.pixels[11] = GREEN
                macropad.pixels.show()

                # Activate solenoid
                solenoid.value = True
                time.sleep(2)  # Limit time open to spare current in transistor
                solenoid.value = False
                # Reset
                time.sleep(5)
                macropad.pixels[11] = BLACK
                macropad.pixels.show()
            else:  # fail!
                group[11].text = "FAIL"
                group[9].text = " "
                macropad.display.show(group)
                macropad.display.refresh()
                for _ in range(3):  # Flash lower right 3 times red with beeps
                    macropad.pixels[11] = RED
                    macropad.pixels.show()
                    macropad.play_tone(880, 1)
                    time.sleep(0.1)
                    macropad.pixels[11] = BLACK
                    macropad.pixels.show()
                    time.sleep(0.1)
            # Reset state after both success and failure
            keys_clear()
            state = STATE_RESET

    else:  # Release any still-pressed keys
        macropad.keyboard.release(key_number)
        # Change key color back
        if state == STATE_ENTRY:
            if key_number in (0, 1, 2, 3, 4, 5, 6, 7, 8, 10):
                macropad.pixels[key_number] = old_color
                macropad.pixels.show()
