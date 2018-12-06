#  Launch Deck Trellis M4
#  USB HID button box for launching applications, media control, camera switching and more
#  Use it with your favorite keyboard controlled launcher, such as Quicksilver and AutoHotkey

import time
import random
import adafruit_trellism4
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

# Rotation of the trellis. 0 is when the USB is upself.
# The grid coordinates used below require portrait mode of 90 or 270
ROTATION = 270

# the two command types -- MEDIA for ConsumerControlCodes, KEY for Keycodes
# this allows button press to send the correct HID command for the type specified
MEDIA = 1
KEY = 2
# button mappings
# customize these for your desired postitions, colors, and keyboard combos
# specify (button coordinate): (color hex value, command type, command/keycodes)
keymap = {
    (0,0): (0x001100, MEDIA, ConsumerControlCode.PLAY_PAUSE),
    (1,0): (0x110011, MEDIA, ConsumerControlCode.SCAN_PREVIOUS_TRACK),
    (2,0): (0x110011, MEDIA, ConsumerControlCode.SCAN_NEXT_TRACK),
    (3,0): (0x000033, MEDIA, ConsumerControlCode.VOLUME_INCREMENT),

    (0,1): (0x110000, MEDIA, ConsumerControlCode.MUTE),
    # intentional blank button
    # intentional blank button
    (3,1): ((0,0,10), MEDIA, ConsumerControlCode.VOLUME_DECREMENT),

    (0,2): (0x551100, KEY, (Keycode.GUI, Keycode.ALT, Keycode.CONTROL, Keycode.ONE)),
    (1,2): (0x221100, KEY, (Keycode.CONTROL, Keycode.SHIFT, Keycode.TAB)),  # back cycle tabs
    (2,2): (0x221100, KEY, (Keycode.CONTROL, Keycode.TAB)),  # cycle tabs
    (3,2): (0x333300, KEY, (Keycode.GUI, Keycode.ALT, Keycode.CONTROL, Keycode.TWO)),

    (0,3): (0x001155, KEY, (Keycode.GUI, Keycode.ALT, Keycode.CONTROL, Keycode.THREE)),
    # intentional blank button
    # intentional blank button
    (3,3): (0x330000, KEY, (Keycode.GUI, Keycode.ALT, Keycode.CONTROL, Keycode.FOUR)),

    (0,4): (0x005511, KEY, (Keycode.GUI, Keycode.ALT, Keycode.CONTROL, Keycode.FIVE)),
    (1,4): (0x440000, KEY, (Keycode.GUI, Keycode.ALT, Keycode.CONTROL, Keycode.SIX)),
    # intentional blank button
    (3,4): (0x003300, KEY, (Keycode.GUI, Keycode.ALT, Keycode.CONTROL, Keycode.EIGHT)),

    (0,5): (0x222222, KEY, (Keycode.GUI, Keycode.ALT, Keycode.CONTROL, Keycode.W)),
    (1,5): (0x000044, KEY, (Keycode.GUI, Keycode.ALT, Keycode.CONTROL, Keycode.E)),
    # intentional blank button
    (3,5): (0x332211, KEY, (Keycode.GUI, Keycode.ALT, Keycode.CONTROL, Keycode.T)),

    (0,6): (0x001133, KEY, (Keycode.GUI, Keycode.ALT, Keycode.CONTROL, Keycode.C)),
    (1,6): (0x331100, KEY, (Keycode.GUI, Keycode.ALT, Keycode.CONTROL, Keycode.V)),
    (2,6): (0x111111, KEY, (Keycode.GUI, Keycode.SHIFT, Keycode.FOUR)),  # screen shot
    (3,6): (0x110000, KEY, (Keycode.GUI, Keycode.ALT, Keycode.CONTROL, Keycode.N)),

    (0,7): (0x060606, KEY, (Keycode.GUI, Keycode.H)),  # hide front app, all windows
    (1,7): (0x222200, KEY, (Keycode.GUI, Keycode.GRAVE_ACCENT)),  # cycle windows of app
    (2,7): (0x010001, KEY, (Keycode.GUI, Keycode.SHIFT, Keycode.TAB)),  # cycle apps backards
    (3,7): (0x010001, KEY, (Keycode.GUI, Keycode.TAB))}  # cycle apps forwards


# Time in seconds to stay lit before sleeping.
TIMEOUT = 90

# Time to take fading out all of the keys.
FADE_TIME = 1

# Once asleep, how much time to wait between "snores" which fade up and down one button.
SNORE_PAUSE = 0.5

# Time in seconds to take fading up the snoring LED.
SNORE_UP = 2

# Time in seconds to take fading down the snoring LED.
SNORE_DOWN = 1

TOTAL_SNORE = SNORE_PAUSE + SNORE_UP + SNORE_DOWN

kbd = Keyboard()
cc = ConsumerControl()

trellis = adafruit_trellism4.TrellisM4Express(rotation=ROTATION)
for button in keymap:
    trellis.pixels[button] = keymap[button][0]

current_press = set()
last_press = time.monotonic()
snore_count = -1
while True:
    pressed = set(trellis.pressed_keys)
    now = time.monotonic()
    sleep_time = now - last_press
    sleeping = sleep_time > TIMEOUT
    for down in pressed - current_press:
        if down in keymap and not sleeping:
            print("down", down)
            # Lower the brightness so that we don't draw too much current when we turn all of
            # the LEDs on.
            trellis.pixels.brightness = 0.2
            trellis.pixels.fill(keymap[down][0])
            if keymap[down][1] == KEY:
                kbd.press(*keymap[down][2])
            else:
                cc.send(keymap[down][2])
            # else if the entry starts with 'l' for layout.write
        last_press = now
    for up in current_press - pressed:
        if up in keymap:
            print("up", up)
            if keymap[up][1] == KEY:
                kbd.release(*keymap[up][2])

    # Reset the LEDs when there was something previously pressed (current_press) but nothing now
    # (pressed).
    if not pressed and current_press:
        trellis.pixels.brightness = 1
        trellis.pixels.fill((0, 0, 0))
        for button in keymap:
            trellis.pixels[button] = keymap[button][0]

    if not sleeping:
        snore_count = -1
    else:
        sleep_time -= TIMEOUT
        # Fade all out
        if sleep_time < FADE_TIME:
            brightness = (1 - sleep_time / FADE_TIME)
        # Snore by pausing and then fading a random button up and back down.
        else:
            sleep_time -= FADE_TIME
            current_snore = int(sleep_time / TOTAL_SNORE)
            # Detect a new snore and pick a new button
            if current_snore > snore_count:
                button = random.choice(list(keymap.keys()))
                trellis.pixels.fill((0, 0, 0))
                trellis.pixels[button] = keymap[button][0]
                snore_count = current_snore

            sleep_time = sleep_time % TOTAL_SNORE
            if sleep_time < SNORE_PAUSE:
                brightness = 0
            else:
                sleep_time -= SNORE_PAUSE
                if sleep_time < SNORE_UP:
                    brightness = sleep_time / SNORE_UP
                else:
                    sleep_time -= SNORE_UP
                    brightness = 1 - sleep_time / SNORE_DOWN
        trellis.pixels.brightness = brightness
    current_press = pressed
