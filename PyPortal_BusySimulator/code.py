# SPDX-FileCopyrightText: 2020 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
PyPortal implementation of Busy Simulator notification sound looper.
"""
import time
import board
import displayio
import adafruit_touchscreen
from adafruit_displayio_layout.layouts.grid_layout import GridLayout
from adafruit_displayio_layout.widgets.icon_widget import IconWidget
from audiocore import WaveFile
from audioio import AudioOut

# How many seconds to wait between playing samples
# Lower time means it will play faster
WAIT_TIME = 3.0

# List that will hold indexes of notification samples to play
LOOP = []

# last time that we played a sample
LAST_PLAY_TIME = 0

CUR_LOOP_INDEX = 0

# touch events must have at least this long between them
COOLDOWN_TIME = 0.25  # seconds

# last time that the display was touched
# used for debouncing and cooldown enforcement
LAST_PRESS_TIME = -1

# Was any icon touched last iteration.
# Used for debouncing.
WAS_TOUCHED = False


def next_index():
    """
    return the next index in the LOOP that should get played
    """
    if CUR_LOOP_INDEX + 1 >= len(LOOP):
        return 0

    return CUR_LOOP_INDEX + 1


# list of icons to show
# each entry is a tuple containing:
# (Icon Label, Icon BMP image file, Notification sample wav file
_icons = [
    ("Outlook", "icons/outlook.bmp", "sounds/outlook.wav"),
    ("Phone", "icons/phone.bmp", "sounds/phone.wav"),
    ("Skype", "icons/skype.bmp", "sounds/skype.wav"),
    ("Teams", "icons/teams.bmp", "sounds/teams.wav"),
    ("Discord", "icons/discord.bmp", "sounds/discord.wav"),
    ("Apple Mail", "icons/applemail.bmp", "sounds/applemail.wav"),
    ("iMessage", "icons/imessage.bmp", "sounds/imessage.wav"),
    ("Slack", "icons/slack.bmp", "sounds/slack.wav"),
    ("G Calendar", "icons/gcal.bmp", "sounds/RE.wav"),
    ("G Chat", "icons/gchat.bmp", "sounds/gchat.wav"),
    ("Stop", "icons/stop.bmp", ""),
]

# Make the display context.
display = board.DISPLAY
main_group = displayio.Group()
display.show(main_group)

# Touchscreen initialization
ts = adafruit_touchscreen.Touchscreen(
    board.TOUCH_XL,
    board.TOUCH_XR,
    board.TOUCH_YD,
    board.TOUCH_YU,
    calibration=((5200, 59000), (5800, 57000)),
    size=(display.width, display.height),
)

# Setup the file as the bitmap data source
bg_bitmap = displayio.OnDiskBitmap("busysim_background.bmp")

# Create a TileGrid to hold the bitmap
bg_tile_grid = displayio.TileGrid(
    bg_bitmap,
    pixel_shader=getattr(bg_bitmap, "pixel_shader", displayio.ColorConverter()),
)

# add it to the group that is showing
main_group.append(bg_tile_grid)

# grid to hold the icons
layout = GridLayout(
    x=0,
    y=0,
    width=320,
    height=240,
    grid_size=(4, 3),
    cell_padding=20,
)

# initialize the icons in the grid
for i, icon in enumerate(_icons):
    icon_widget = IconWidget(
        icon[0],
        icon[1],
        x=0,
        y=0,
        on_disk=True,
        transparent_index=0,
        label_background=0x888888,
    )

    layout.add_content(icon_widget, grid_position=(i % 4, i // 4), cell_size=(1, 1))

# add the grid to the group showing on the display
main_group.append(layout)


def check_for_touch(_now):
    """
    Check the touchscreen and do any actions necessary if an
    icon has been touched. Applies debouncing and cool down
    enforcement to filter out unneeded touch events.

    :param int _now: The current time in seconds. Used for cool down enforcement
    """
    # pylint: disable=global-statement, too-many-nested-blocks, consider-using-enumerate
    global CUR_LOOP_INDEX
    global LOOP
    global LAST_PRESS_TIME
    global WAS_TOUCHED

    # read the touch data
    touch_point = ts.touch_point

    # if anything is touched
    if touch_point:
        # if the touch just began. We ignore further events until
        # after the touch has been lifted
        if not WAS_TOUCHED:

            # set the variable so we know to ignore future events until
            # touch is released
            WAS_TOUCHED = True

            # if it has been long enough time since previous touch event
            if _now - LAST_PRESS_TIME > COOLDOWN_TIME:

                LAST_PRESS_TIME = time.monotonic()

                # loop over the icons
                for _ in range(len(_icons)):
                    # lookup current icon in the grid layout
                    cur_icon = layout.get_cell((_ % 4, _ // 4))

                    # check if it's being touched
                    if cur_icon.contains(touch_point):
                        print("icon {} touched".format(_))

                        # if it's the stop icon
                        if _icons[_][0] == "Stop":

                            # empty out the loop
                            LOOP = []

                            # set current index back to 0
                            CUR_LOOP_INDEX = 0

                        else:  # any other icon
                            # insert the touched icons sample index into the loop
                            LOOP.insert(CUR_LOOP_INDEX, _)

                        # print(LOOP)

                        # break out of the for loop.
                        # if current icon is being touched then no others can be
                        break

    # nothing is touched
    else:
        # set variable back to false for debouncing
        WAS_TOUCHED = False


# main loop
while True:
    # store current time in variable for cool down enforcement
    _now = time.monotonic()

    # check for and process touch events
    check_for_touch(_now)

    # if it's time to play a sample
    if LAST_PLAY_TIME + WAIT_TIME <= _now:
        # print("time to play")

        # if there are any samples in the loop
        if len(LOOP) > 0:

            # open the sample wav file
            with open(_icons[LOOP[CUR_LOOP_INDEX]][2], "rb") as wave_file:
                print("playing: {}".format(_icons[LOOP[CUR_LOOP_INDEX]][2]))

                # initialize audio output pin
                audio = AudioOut(board.AUDIO_OUT)

                # initialize WaveFile object
                wave = WaveFile(wave_file)

                # play it
                audio.play(wave)

                # while it's still playing
                while audio.playing:
                    # update time variable
                    _now = time.monotonic()

                    # check for and process touch events
                    check_for_touch(_now)

                # after done playing. deinit audio output
                audio.deinit()

                # increment index counter
                CUR_LOOP_INDEX = next_index()

        # update variable for last time we attempted to play sample
        LAST_PLAY_TIME = _now
