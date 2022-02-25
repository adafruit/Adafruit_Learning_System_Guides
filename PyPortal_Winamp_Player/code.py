# SPDX-FileCopyrightText: 2022 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
PyPortal winamp player
"""
import time
import sys
import storage
import board
import busio
import digitalio
import adafruit_touchscreen
import adafruit_sdcard
from winamp_helpers import WinampApplication

# which playlist to play
PLAYLIST_FILE = "playlist.json"

# which skin background to use
SKIN_IMAGE = "/base_240x320.bmp"

# skin configuration for color values
SKIN_CONFIG_FILE = "base_config.json"

# must wait at least this long between touch events
TOUCH_COOLDOWN = 0.5  # seconds

# display orientation. Must be 90 or 270.
ORIENTATION = 90

PYPORTAL_TITANO = False

if not PYPORTAL_TITANO:
    SIZE = (240, 320)
    if ORIENTATION == 270:
        # setup touch screen
        ts = adafruit_touchscreen.Touchscreen(
            board.TOUCH_YD,
            board.TOUCH_YU,
            board.TOUCH_XR,
            board.TOUCH_XL,
            calibration=((5200, 59000), (5800, 57000)),
            size=(240, 320),
        )
    elif ORIENTATION == 90:
        # setup touch screen
        ts = adafruit_touchscreen.Touchscreen(
            board.TOUCH_YU,
            board.TOUCH_YD,
            board.TOUCH_XL,
            board.TOUCH_XR,
            calibration=((5200, 59000), (5800, 57000)),
            size=(240, 320),
        )
    else:
        raise ValueError("ORIENTATION must be 90 or 270")
else:  # PyPortal Titano
    SIZE = (320, 480)
    if ORIENTATION == 270:
        # setup touch screen
        ts = adafruit_touchscreen.Touchscreen(
            board.TOUCH_YD,
            board.TOUCH_YU,
            board.TOUCH_XR,
            board.TOUCH_XL,
            calibration=((5200, 59000), (5800, 57000)),
            size=(320, 480),
        )
    elif ORIENTATION == 90:
        # setup touch screen
        ts = adafruit_touchscreen.Touchscreen(
            board.TOUCH_YU,
            board.TOUCH_YD,
            board.TOUCH_XL,
            board.TOUCH_XR,
            calibration=((5200, 59000), (5800, 57000)),
            size=(320, 480),
        )

# Initializations for SDCard
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
cs = digitalio.DigitalInOut(board.SD_CS)
sdcard = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")
sys.path.append("/sd")

# debugging, print files that exist on SDCard
# print(os.listdir("/sd"))

# get reference to the display
display = board.DISPLAY

# set rotation
display.rotation = ORIENTATION

# Initialize WinampApplication helper class
winamp_application = WinampApplication(
    playlist_file=PLAYLIST_FILE,
    skin_image=SKIN_IMAGE,
    skin_config_file=SKIN_CONFIG_FILE,
    pyportal_titano=PYPORTAL_TITANO,
)

# Add the Group to the Display
display.show(winamp_application)

# previous iteration touch events
_previous_touch = None

# last time a touch occured
_previous_touch_time = 0

# main loop
while True:
    # update winamp application
    winamp_application.update()

    # check for touch events
    p = ts.touch_point
    _now = time.monotonic()
    # if touch cooldown time has elapsed
    if _now >= _previous_touch_time + TOUCH_COOLDOWN:
        # if there is a touch
        if p and not _previous_touch:
            # store the time to compare with next iteration
            _previous_touch_time = _now
            # if touch is on bottom half
            if p[1] > SIZE[1] // 2:
                # if touch is on right half
                if p[0] >= SIZE[0] // 2:
                    winamp_application.next_track()

                # if touch is on left half
                else:
                    winamp_application.previous_track()
            # if touch is on top half
            else:
                # if currently playing song
                if winamp_application.CURRENT_STATE == winamp_application.STATE_PLAYING:
                    print("pausing")
                    winamp_application.pause()

                # if song is paused
                else:
                    print("resuming")
                    winamp_application.resume()

    # store previous touch event t compare with next iteration
    _previous_touch = p
