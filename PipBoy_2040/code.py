# SPDX-FileCopyrightText: 2021 john park for Adafruit Industries
# SPDX-License-Identifier: MIT
import time
import board
from adafruit_simplemath import map_range
import displayio
from adafruit_seesaw.seesaw import Seesaw
import adafruit_imageload
from adafruit_st7789 import ST7789

displayio.release_displays()

i2c_bus = board.I2C()
ss = Seesaw(i2c_bus)

spi = board.SPI()  # setup for display over SPI
tft_cs = board.D5
tft_dc = board.D6
display_bus = displayio.FourWire(
    spi, command=tft_dc, chip_select=tft_cs, reset=board.D9
)

display = ST7789(display_bus, width=280, height=240, rowstart=20, rotation=270)

screen = displayio.Group()  # Create a Group to hold content
display.show(screen)  # Add it to the Display

# display image
image = displayio.OnDiskBitmap("/img/bootpip0.bmp")
palette = image.pixel_shader
background = displayio.TileGrid(image, pixel_shader=palette)
screen.append(background)

# load cursor on top
cursor_on = True
if cursor_on:
    image, palette = adafruit_imageload.load("/img/cursor_green.bmp")
    palette.make_transparent(0)
    cursor = displayio.TileGrid(image, pixel_shader=palette)
    screen.append(cursor)

    cursor.x = 0  # hide cursor during bootup
    cursor.y = 0

display.show(screen)

boot_file_names = [
    "/img/bootpip0.bmp",
    "/img/bootpip1.bmp",
    "/img/bootpip2.bmp",
    "/img/bootpip3.bmp",
    "/img/bootpip4.bmp",
    "/img/bootpip5.bmp",
    "/img/statpip0.bmp",
]

screenmap = {
    (0): (
        "/img/statpip0.bmp",
        "/img/statpip1.bmp",
        "/img/statpip2.bmp",
        "/img/statpip3.bmp",
        "/img/statpip4.bmp",
        "/img/statpip2.bmp",
        "/img/statpip6.bmp",
        "/img/statpip7.bmp",
        "/img/statpip8.bmp",
    ),
    (1): ("/img/invpip0.bmp", "/img/invpip1.bmp"),
    (2): ("/img/datapip0.bmp", "/img/datapip1.bmp", "/img/datapip2.bmp"),
    (3): ("/img/mappip0.bmp", "/img/mappip1.bmp", "/img/mappip2.bmp"),
    (4): ("/img/radiopip0.bmp", "/img/radiopip1.bmp"),
    (5): ("/img/holopip0.bmp", "/img/holopip1.bmp"),
}

BUTTON_UP = 6  # A is UP
BUTTON_RIGHT = 7  # B is RIGHT
BUTTON_DOWN = 9  # Y is DOWN
BUTTON_LEFT = 10  # X is LEFT
BUTTON_SEL = 14  # SEL button is unused
button_mask = (
    (1 << BUTTON_UP)
    | (1 << BUTTON_RIGHT)
    | (1 << BUTTON_DOWN)
    | (1 << BUTTON_LEFT)
    | (1 << BUTTON_SEL)
)

ss.pin_mode_bulk(button_mask, ss.INPUT_PULLUP)

tab_number = 0
sub_number = 0

def image_switch(direction):  # advance or go back through image list
    # pylint: disable=global-statement
    global tab_number
    # pylint: disable=global-statement
    global sub_number
    # pylint: disable=global-statement
    global image
    # pylint: disable=global-statement
    global palette
    if direction == 0:  # right
        tab_number = (tab_number + 1) % len(screenmap)
    if direction == 1:  # left
        tab_number = (tab_number - 1) % len(screenmap)
    if direction == 2:  # down
        sub_number = (sub_number + 1) % len((screenmap[tab_number]))
    if direction == 3:  # up
        sub_number = (sub_number - 1) % len((screenmap[tab_number]))

    image = displayio.OnDiskBitmap(screenmap[tab_number][sub_number])
    palette = image.pixel_shader
    screen[0] = displayio.TileGrid(image, pixel_shader=palette)


last_joy_x = 0
last_joy_y = 0

#  bootup images
for i in range(len(boot_file_names)):
    image = displayio.OnDiskBitmap(boot_file_names[i])
    palette = image.pixel_shader
    screen[0] = displayio.TileGrid(image, pixel_shader=palette)
    time.sleep(0.1)

while True:
    time.sleep(0.01)
    joy_x = ss.analog_read(2)
    joy_y = ss.analog_read(3)
    if (abs(joy_x - last_joy_x) > 3) or (abs(joy_y - last_joy_y) > 3):
        if cursor_on:
            cursor.x = int(map_range(joy_x, 10, 1023, 0, 264))
            cursor.y = int(map_range(joy_y, 10, 1023, 224, 0))
        last_joy_x = joy_x
        last_joy_y = joy_y

    buttons = ss.digital_read_bulk(button_mask)

    if not buttons & (1 << BUTTON_UP):
        image_switch(3)
        time.sleep(0.15)

    if not buttons & (1 << BUTTON_RIGHT):
        sub_number = 0  # go back to top level screen of tab grouping
        image_switch(0)
        time.sleep(0.15)

    if not buttons & (1 << BUTTON_DOWN):
        image_switch(2)
        time.sleep(0.15)

    if not buttons & (1 << BUTTON_LEFT):
        sub_number = 0
        image_switch(1)
        time.sleep(0.15)

    if not buttons & (1 << BUTTON_SEL):
        print("unused select button")
