# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import gc
import board
import displayio
import fourwire
import terminalio
import adafruit_ble
from adafruit_ble.advertising.standard import SolicitServicesAdvertisement
from adafruit_ble_apple_media import AppleMediaService
from adafruit_bitmap_font import bitmap_font
from adafruit_button import Button
from adafruit_display_text import label, wrap_text_to_lines
import adafruit_hx8357
import adafruit_tsc2007

gc.collect()
displayio.release_displays()
small_font = bitmap_font.load_font("/Arial-16.bdf")

# display
spi = board.SPI()
tft_cs = board.D9
tft_dc = board.D10
display_bus = fourwire.FourWire(spi, command=tft_dc, chip_select=tft_cs)
display = adafruit_hx8357.HX8357(display_bus, width=480, height=320)
# touch
i2c = board.I2C()
tsc = adafruit_tsc2007.TSC2007(i2c, invert_x=True, swap_xy=True)
splash = displayio.Group()

def ble_media_command(conn, command):
    gc.collect()
    # print("function started")
    if not conn.paired:
        print("trying to pair")
        conn.pair()
        print("paired")
    # print("connected, getting ready")
    ams = conn[AppleMediaService]
    # print(ams)
    tries = 10
    for i in range(tries):
        try:
            # print("sending..")
            if command != "refresh":
                command(ams)
            time.sleep(2)
            # print("sent")
            song_text = f"{ams.title}"
            song_text = "\n".join(wrap_text_to_lines(song_text, 29))
            song_label.text = song_text
            album_label.text = f"Album: {ams.album}"
            artist_label.text = f"Artist: {ams.artist}"
            app_label.text = f"App: {ams.player_name}"
            if ams.playing:
                buttons[0].label = "Pause"
            elif ams.paused:
                buttons[0].label = "Play"
        except Exception as error: # pylint: disable = broad-except
            print(error)
            # time.sleep(2)
            if i < tries - 1:
                continue
        break
    gc.collect()

connection = None

# commands
commands = [
    lambda ams: ams.toggle_play_pause(),
    lambda ams: ams.next_track(),
    lambda ams: ams.previous_track(),
    lambda ams: ams.advance_repeat_mode(),
    lambda ams: ams.advance_shuffle_mode(),
    lambda ams: ams.volume_up(),
    lambda ams: ams.volume_down(),
]

# colors
RED = (255, 0, 0)
ORANGE = (255, 34, 0)
YELLOW = (255, 170, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
VIOLET = (153, 0, 255)
MAGENTA = (255, 0, 51)
PINK = (255, 51, 119)
AQUA = (85, 125, 255)
WHITE = (255, 255, 255)
OFF = (0, 0, 0)

gc.collect()
spots = [
    {'label': "Play/Pause", 'font': small_font,
     'pos': ((display.width // 2) - 60, display.height - 70),
     'size': (120, 60), 'color': RED,
     'control': lambda: ble_media_command(connection, commands[0])},
    {'label': ">>", 'font': small_font,
     'pos': ((display.width // 2) + 70, display.height - 70),
     'size': (60, 60), 'color': ORANGE,
     'control': lambda: ble_media_command(connection, commands[1])},
    {'label': "<<", 'font': small_font,
     'pos': ((display.width // 2) - 130, display.height - 70),
     'size': (60, 60), 'color': YELLOW,
     'control': lambda: ble_media_command(connection, commands[2])},
    {'label': "Repeat", 'font': terminalio.FONT,
     'pos': (10, 250), 'size': (60, 60), 'color': GREEN,
     'control': lambda: ble_media_command(connection, commands[3])},
    {'label': "Shuffle", 'font': terminalio.FONT,
     'pos': (410, 250), 'size': (60, 60), 'color': CYAN,
     'control': lambda: ble_media_command(connection, commands[4])},
    {'label': "Vol +", 'font': small_font, 'pos': (10, 10), 'size': (60, 120), 'color': BLUE,
     'control': lambda: ble_media_command(connection, commands[5])},
    {'label': "Vol -", 'font': small_font, 'pos': (410, 10), 'size': (60, 120), 'color': VIOLET,
     'control': lambda: ble_media_command(connection, commands[6])},
    {'label': "Refresh", 'font': small_font, 'pos': (70, 10), 'size': (340, display.height - 80),
     'color': None, 'control': lambda: ble_media_command(connection, "refresh")},
    ]

buttons = []
for spot in spots:
    button = Button(x=spot['pos'][0], y=spot['pos'][1],
                    width=spot['size'][0], height=spot['size'][1],
                    label=spot['label'], label_font=spot['font'],
                    style=Button.ROUNDRECT,
                    fill_color=spot['color'],
                    name=spot['label'])
    splash.append(button)
    buttons.append(button)

header_label = label.Label(small_font, text="Now Playing:", color=WHITE)
header_label.anchor_point = (0.5, 0.0)
header_label.anchored_position = (display.width / 2, 10)
splash.append(header_label)

song_label = label.Label(small_font, text=" ", color=WHITE)
song_label.anchor_point = (0.5, 0.0)
song_label.anchored_position = (display.width / 2, 40)
splash.append(song_label)
artist_label = label.Label(small_font, text="Artist: ", color=WHITE)
artist_label.anchor_point = (0.5, 0.0)
artist_label.anchored_position = (display.width / 2, 124)
splash.append(artist_label)
album_label = label.Label(small_font, text="Album: ", color=WHITE)
album_label.anchor_point = (0.5, 0.0)
album_label.anchored_position = (display.width / 2, 154)
splash.append(album_label)
app_label = label.Label(small_font, text="App: ", color=WHITE)
app_label.anchor_point = (0.5, 0.0)
app_label.anchored_position = (display.width / 2, 184)
splash.append(app_label)

touch_state = False

display.root_group = splash

def scale_touch_coordinates(raw_x, raw_y):
    # raw coordinate ranges
    raw_x_min = 275
    raw_x_max = 3900
    raw_y_min = 487
    raw_y_max = 3800
    # scale the raw coordinates to display coordinates
    display_x = (raw_x - raw_x_min) * display.width / (raw_x_max - raw_x_min)
    display_y = (raw_y - raw_y_min) * display.height / (raw_y_max - raw_y_min)
    # clamp values to ensure they stay within display bounds
    display_x = max(0, min(display_x, display.width))
    display_y = max(0, min(display_y, display.height))
    return int(display_x), int(display_y)

gc.collect()
# PyLint can't find BLERadio for some reason so special case it here.
radio = adafruit_ble.BLERadio()  # pylint: disable=no-member
a = SolicitServicesAdvertisement()
a.solicited_services.append(AppleMediaService)
if not radio.connected:
    print("advertising")
    radio.start_advertising(a)
else:
    print("already connected")
    print(radio.connected)
print(gc.mem_free())

while True:
    while not radio.connected:
        pass
    known_notifications = set()
    while radio.connected:
        if tsc.touched and not touch_state:
            gc.collect()
            touch_state = True
            p = tsc.touch
            point = scale_touch_coordinates(p["x"], p["y"])
            connection = radio.connections[0]
            for button in buttons:
                b = buttons.index(button)
                if button.contains(point):
                    print(gc.mem_free())
                    print("Touched", button.name)
                    spots[b]['control']()
        if not tsc.touched and touch_state:
            touch_state = False
    print("disconnected")
    print("advertising")
    radio.start_advertising(a)
    print("reconnected")
