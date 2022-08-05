import gc
import time
import board
import keypad
from displayio import OnDiskBitmap, TileGrid, Group
import adafruit_imageload
from octopus_game_helpers import DiverPlayer, OctopusGame

# built-in display
display = board.DISPLAY

#display.brightness = 0.3

# main group that we'll show in the display
main_group = Group()

# create instance of OctopusGame
octopus_game = OctopusGame(high_score_type=OctopusGame.HIGH_SCORE_NVM)

# add octopus game to main group
main_group.append(octopus_game)

# initialize the shiftregister keys to read hardware buttons
buttons = keypad.ShiftRegisterKeys(
    clock=board.BUTTON_CLOCK,
    data=board.BUTTON_OUT,
    latch=board.BUTTON_LATCH,
    key_count=4,
    value_when_pressed=True,
)

# show the main group on the display
display.show(main_group)

# main loop
while True:

    # get event from hardware buttons
    event = buttons.events.get()

    # if anything is pressed
    if event:

        # if the event is for the start button
        if event.key_number == 2:
            # if it's a pressed event
            if event.pressed:
                # trigger the right button press action function
                octopus_game.right_button_press()

        # if the event is for the select button
        elif event.key_number == 3:
            # if it's a pressed event
            if event.pressed:
                # trigger the left button press action function
                octopus_game.left_button_press()

        # if the event is for the b button
        elif event.key_number == 0:
            # if it's a pressed event
            if event.pressed:
                # trigger the b button press action function
                octopus_game.b_button_press()

        # if the event is for the a button
        elif event.key_number == 1:
            # if it's a pressed event
            if event.pressed:
                # trigger the a button press action function
                octopus_game.a_button_press()

    # call the game tick function
    octopus_game.tick()