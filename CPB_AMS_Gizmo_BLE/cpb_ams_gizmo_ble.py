"""
This example solicits that apple devices that provide notifications connect to it, initiates
pairing, prints existing notifications and then prints any new ones as they arrive.
"""

import time
import displayio
import terminalio
from adafruit_gizmo import tft_gizmo
from adafruit_display_text.label import Label
from adafruit_display_shapes.rect import Rect
from adafruit_bitmap_font import bitmap_font
import adafruit_ble
from adafruit_ble.advertising.standard import SolicitServicesAdvertisement
from adafruit_ble_apple_media import AppleMediaService
from adafruit_circuitplayground import cp

BACKGROUND_COLOR = 0x444444 # Gray
TEXT_COLOR = 0xFF0000 # Red
BORDER_COLOR = 0xAAAAAA # Light Gray
STATUS_COLOR = BORDER_COLOR

# PyLint can't find BLERadio for some reason so special case it here.
radio = adafruit_ble.BLERadio() # pylint: disable=no-member
a = SolicitServicesAdvertisement()
a.solicited_services.append(AppleMediaService)
radio.start_advertising(a)

def wrap_in_tilegrid(open_file):
    odb = displayio.OnDiskBitmap(open_file)
    return displayio.TileGrid(odb, pixel_shader=displayio.ColorConverter())

def make_background(width, height, color):
    color_bitmap = displayio.Bitmap(width, height, 1)
    color_palette = displayio.Palette(1)
    color_palette[0] = color

    return displayio.TileGrid(color_bitmap,
                              pixel_shader=color_palette,
                              x=0, y=0)

def load_font(fontname, text):
    font = bitmap_font.load_font(fontname)
    font.load_glyphs(text.encode('utf-8'))
    return font

def make_label(text, x, y, color, font=terminalio.FONT):
    if isinstance(font, str):
        font = load_font(font, "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,?")
    text_area = Label(font, text=text, color=color, max_glyphs=30)
    text_area.x = x
    text_area.y = y
    return text_area

display = tft_gizmo.TFT_Gizmo()
group = displayio.Group(max_size=20)
display.show(group)

while True:
    if not radio.connected:
        group.append(wrap_in_tilegrid(open("/graphic_tfts_ams_connect.bmp", "rb")))

        while not radio.connected:
            pass

        group.pop()
    print("connected")

    known_notifications = set()

    # Draw the text fields
    print("Loading Font Glyphs...")
    title_label = make_label("None", 20, 20, TEXT_COLOR, font="/fonts/Arial-Bold-18.bdf")
    artist_label = make_label("None", 20, 50, TEXT_COLOR, font="/fonts/Arial-16.bdf")
    album_label = make_label("None", 20, 180, TEXT_COLOR, font="/fonts/Arial-16.bdf")
    status_label = make_label("None", 80, 220, STATUS_COLOR, font="/fonts/Arial-16.bdf")
    group.append(make_background(240, 240, BACKGROUND_COLOR))
    border = Rect(10, 8, 200, 190, outline=BORDER_COLOR, stroke=1)
    group.append(title_label)
    group.append(artist_label)
    group.append(album_label)
    group.append(status_label)
    group.append(border)

    while radio.connected:
        try:
            for connection in radio.connections:
                if not connection.paired:
                    connection.pair()
                    print("paired")

                ams = connection[AppleMediaService]
                title_label.text = "{}".format(ams.title)
                album_label.text = "{}".format(ams.album)
                artist_label.text = "{}".format(ams.artist)
                if ams.playing:
                    status_label.text = "Playing on {}".format(ams.player_name)
                elif ams.paused:
                    status_label.text = "Paused on {}".format(ams.player_name)
            if cp.button_a:
                ams.toggle_play_pause()
                time.sleep(0.1)

            if cp.button_b:
                if cp.switch:
                    ams.previous_track()
                else:
                    ams.next_track()
                time.sleep(0.1)
        except RuntimeError:
            # Skip Bad Packets, unknown commands, etc.
            pass

    print("disconnected")
    # Remove all layers
    while group.__len__():
        group.pop()
