# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Adafruit BBQ display works with ibbq protocol-based BLE temperature probes

import time

import displayio
import _bleio
import adafruit_ble
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble_ibbq import IBBQService
from adafruit_clue import clue
from adafruit_display_shapes.circle import Circle
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font

clue.display.brightness = 1.0
homescreen_screen = displayio.Group()
temperatures_screen = displayio.Group()

# define custom colors
GREEN = 0x00D929
BLUE = 0x0000FF
RED = 0xFF0000
ORANGE = 0xFF6A00
YELLOW = 0xFFFF00
PURPLE = 0xE400FF
BLACK = 0x000000
WHITE = 0xFFFFFF
BURNT = 0xBB4E00

unit_mode = False  # set the temperature unit_mode. True = centigrade, False = farenheit

# Setup homescreen
color_bitmap = displayio.Bitmap(120, 120, 1)
color_palette = displayio.Palette(1)
color_palette[0] = BURNT
bg_sprite = displayio.TileGrid(color_bitmap, x=120, y=0, pixel_shader=color_palette)
homescreen_screen.append(bg_sprite)

clue_color = [GREEN, BLUE, RED, ORANGE, YELLOW, PURPLE]

outer_circle = Circle(120, 120, 119, fill=BLACK, outline=BURNT)
homescreen_screen.append(outer_circle)


title_font = bitmap_font.load_font("/font/GothamBlack-50.bdf")
title_font.load_glyphs("BQLUE".encode("utf-8"))
title_label = label.Label(title_font, text="BBQLUE", color=clue.ORANGE)
title_label.x = 12
title_label.y = 120
homescreen_screen.append(title_label)

clue.display.root_group = homescreen_screen

# Setup temperatures screen
temp_font = bitmap_font.load_font("/font/GothamBlack-25.bdf")
temp_font.load_glyphs("0123456789FC.-<".encode("utf-8"))

my_labels_config = [
    (0, "", GREEN, 2, 100),
    (1, "", BLUE, 2, 150),
    (2, "", RED, 2, 200),
    (3, "", ORANGE, 135, 100),
    (4, "", YELLOW, 135, 150),
    (5, "", PURPLE, 135, 200),
]

my_labels = {}  # dictionary of configured my_labels

text_group = displayio.Group()

for label_config in my_labels_config:
    (name, text, color, x, y) = label_config  # unpack a tuple into five var names
    templabel = label.Label(temp_font, text=text, color=color)
    templabel.x = x
    templabel.y = y
    my_labels[name] = templabel
    text_group.append(templabel)

temperatures_screen.append(text_group)

temp_title_label = label.Label(title_font, text="BBQLUE", color=clue.ORANGE)
temp_title_label.x = 12
temp_title_label.y = 30
temperatures_screen.append(temp_title_label)

# PyLint can't find BLERadio for some reason so special case it here.
ble = adafruit_ble.BLERadio()  # pylint: disable=no-member

ibbq_connection = None

while True:
    # re-display homescreen here
    clue.display.root_group = homescreen_screen

    print("Scanning...")
    for adv in ble.start_scan(ProvideServicesAdvertisement, timeout=5):
        clue.pixel.fill((50, 50, 0))
        if IBBQService in adv.services:
            print("found an IBBq advertisement")
            ibbq_connection = ble.connect(adv)
            print("Connected")
            break

    # Stop scanning whether or not we are connected.
    ble.stop_scan()

    try:
        if ibbq_connection and ibbq_connection.connected:
            clue.pixel.fill((0, 0, 50))
            ibbq_service = ibbq_connection[IBBQService]
            ibbq_service.init()
            while ibbq_connection.connected:

                if clue.button_a:  # hold a to swap between C and F
                    print("unit_mode swapped")
                    unit_mode = not unit_mode
                    clue.red_led = True
                    clue.play_tone(1200, 0.1)
                    clue.red_led = False
                    time.sleep(0.1)  # debounce

                temps = ibbq_service.temperatures
                batt = ibbq_service.battery_level
                if temps is not None:
                    probe_count = len(temps)  # check how many probes there are
                    for i in range(probe_count):
                        if temps[i] != 0 and temps[i] < 1000:  # unplugged probes
                            if unit_mode:
                                clue.pixel.fill((50, 0, 0))
                                temp = temps[i]
                                my_labels[i].text = "{} C".format(temp)
                                clue.pixel.fill((0, 0, 0))
                                print("Probe", i + 1, "Temperature:", temp, "C")
                            else:  # F
                                clue.pixel.fill((50, 0, 0))
                                temp = temps[i] * 9 / 5 + 32
                                my_labels[i].text = "{} F".format(temp)
                                clue.pixel.fill((0, 0, 0))
                                print("Probe", i + 1, "Temperature:", temp, "F")
                        else:
                            print(
                                "Probe", i + 1, "is unplugged",
                            )
                            my_labels[i].text = "  ---"
                    clue.display.root_group = temperatures_screen

    except _bleio.ConnectionError:
        continue
