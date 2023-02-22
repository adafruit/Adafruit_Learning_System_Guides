# SPDX-FileCopyrightText: 2023 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Faux Floppy Disk with LCD Screen
# Display file icons on screen

import os
import time
import board
import displayio
import adafruit_imageload
import terminalio
import adafruit_touchscreen
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect

# Get a dictionary of filenames at the passed base directory
#    each entry is a tuple (filename, bool) where bool = true
#    means the filename is a directory, else false.
def get_files(base):
    files = os.listdir(base)
    file_names = []
    for file in enumerate(files):
        if not file.startswith("."):
            if file not in ('boot_out.txt', 'System Volume Information'):
                stats = os.stat(base + file)
                isdir = stats[0] & 0x4000
                if isdir:
                    file_names.append((file, True))
                else:
                    file_names.append((file, False))
    return filenames

def get_touch(screen):
    p = None
    while p is None:
        time.sleep(0.05)
        p = screen.touch_point
    return p[0]

# Icon Positions
ICONSIZE = 48
SPACING = 18
LEFTSPACE = 38
TOPSPACE = 10
TEXTSPACE = 10
ICONSACROSS = 4
ICONSDOWN = 3
PAGEMAXFILES = ICONSACROSS * ICONSDOWN  # For the chosen display, this is the
#                                     maximum number of file icons that will fit
#                                     on the display at once (display dependent)
# File Types
BLANK = 0
FILE = 1
DIR = 2
BMP = 3
WAV = 4
PY = 5
RIGHT = 6
LEFT = 7

# Use the builtin display
display = board.DISPLAY
WIDTH = board.DISPLAY.width
HEIGHT = board.DISPLAY.height
ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=((5200, 59000), (5800, 57000)),
                                      size=(WIDTH, HEIGHT))

# Create base display group
displaygroup = displayio.Group()

# Load the bitmap (this is the "spritesheet")
sprite_sheet, palette = adafruit_imageload.load("/icons.bmp")

background = Rect(0, 0, WIDTH - 1, HEIGHT - 1, fill=0x000000)
displaygroup.append(background)

# Create enough sprites & labels for the icons that will fit on screen
sprites = []
labels = []
for _ in range(PAGEMAXFILES):
    sprite = displayio.TileGrid(sprite_sheet, pixel_shader=palette,
                                width=1, height=1, tile_height=48,
                                tile_width=48,)
    sprites.append(sprite)  # Append the sprite to the sprite array
    displaygroup.append(sprite)
    filelabel = label.Label(terminalio.FONT, color=0xFFFFFF)
    labels.append(filelabel)
    displaygroup.append(filelabel)

# Make the more files and less files icons (> <)
moresprite = displayio.TileGrid(sprite_sheet, pixel_shader=palette,
                                width=1, height=1, tile_height=48,
                                tile_width=48,)
displaygroup.append(moresprite)
moresprite.x = WIDTH - ICONSIZE + TEXTSPACE
moresprite.y = int((HEIGHT - ICONSIZE) / 2)
lesssprite = displayio.TileGrid(sprite_sheet, pixel_shader=palette,
                                width=1, height=1, tile_height=48,
                                tile_width=48,)
displaygroup.append(lesssprite)
lesssprite.x = -10
lesssprite.y = int((HEIGHT - ICONSIZE) / 2)

display.show(displaygroup)

filecount = 0
xpos = LEFTSPACE
ypos = TOPSPACE

displaybase = "/"  # Get file names in base directory
filenames = get_files(displaybase)

currentfile = 0  # Which file is being processed in all files
spot = 0  # Which spot on the screen is getting a file icon
PAGE = 1  # Which page of icons is displayed on screen, 1 is first

while True:
    if currentfile < len(filenames) and spot < PAGEMAXFILES:
        filename, dirfile = filenames[currentfile]
        if dirfile:
            filetype = DIR
        elif filename.endswith(".bmp"):
            filetype = BMP
        elif filename.endswith(".wav"):
            filetype = WAV
        elif filename.endswith(".py"):
            filetype = PY
        else:
            filetype = FILE
        # Set icon location information and icon type
        sprites[spot].x = xpos
        sprites[spot].y = ypos
        sprites[spot][0] = filetype
        #
        # Set filename
        labels[spot].x = xpos
        labels[spot].y = ypos + ICONSIZE + TEXTSPACE
        # The next line gets the filename without the extension, first 11 chars
        labels[spot].text = filename.rsplit('.', 1)[0][0:10]

    currentpage = PAGE

    # Pagination Handling
    if spot >= PAGEMAXFILES - 1:
        if currentfile < (len(filenames) + 1):
            # Need to display the greater than touch sprite
            moresprite[0] = RIGHT
        else:
            # Blank out more and extra icon spaces
            moresprite[0] = BLANK
        if PAGE > 1:  # Need to display the less than touch sprite
            lesssprite[0] = LEFT
        else:
            lesssprite[0] = BLANK

        # Time to check for user touch of screen (BLOCKING)
        touch_x = get_touch(ts)
        print("Touch Registered ")
        # Check if touch_x is around the LEFT or RIGHT arrow
        currentpage = PAGE
        if touch_x >= int(WIDTH - ICONSIZE):    # > Touched
            if moresprite[0] != BLANK:          # Ensure there are more
                if spot == (PAGEMAXFILES - 1):  # Page full
                    if currentfile < (len(filenames)):  # and more files
                        PAGE = PAGE + 1         # Increment page
        if touch_x <= ICONSIZE:                 # < Touched
            if PAGE > 1:
                PAGE = PAGE - 1                 # Decrement page
            else:
                lesssprite[0] = BLANK        # Not show < for first page
        print("Page ", PAGE)
    # Icon Positioning

    if PAGE != currentpage:  # We have a page change
        # Reset icon locations to upper left
        xpos = LEFTSPACE
        ypos = TOPSPACE
        spot = 0
        if currentpage > PAGE:
            # Decrement files by a page (current page & previous page)
            currentfile = currentfile - (PAGEMAXFILES * 2) + 1
        else:
            # Forward go to the next file
            currentfile = currentfile + 1
    else:
        currentfile += 1             # Increment file counter
        spot += 1                    # Increment icon space counter
        if spot == PAGEMAXFILES:     # Last page ended with
            print("hit")
        # calculate next icon location
        if spot % ICONSACROSS:       # not at end of icon row
            xpos += SPACING + ICONSIZE
        else:                        # start new icon row
            ypos += ICONSIZE + SPACING + TEXTSPACE
            xpos = LEFTSPACE
    # End If Changed Page
    # Blank out rest if needed
    if currentfile == len(filenames):
        for i in range(spot, PAGEMAXFILES):
            sprites[i][0] = BLANK
            labels[i].text = " "
# End while
