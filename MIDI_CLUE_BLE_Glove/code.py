# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
CLUE BLE MIDI
Sends MIDI CC values based on accelerometer x & y and proximity sensor
Touch #0 switches Bank/Preset patches
Touch #1 picks among the three CC lines w A&B buttons adjusting CC numbers
Touch #2 starts/stops sending CC messages (still allows Program Change)
"""
import time
from adafruit_clue import clue
import adafruit_ble
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
import adafruit_ble_midi
import adafruit_midi
from adafruit_midi.control_change import ControlChange
from adafruit_midi.program_change import ProgramChange

# from adafruit_midi.note_on import NoteOn
# from adafruit_midi.pitch_bend import PitchBend
import simpleio
import displayio
import terminalio
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect

# --- Pick your midi out channel here ---
midi_channel = 1
# --- Pick your MIDI CC numbers here ---
cc_x_num = 71
cc_y_num = 72
cc_prox_num = 73
# --- Pick Bank & Preset pairs here ---
touch_patch = [  # first number is the Bank, second is the Preset
    (4, 16),  # minimoog: Leads > Original MINI
    (5, 8),  # Pads > Intergalactic Pass
    (0, 13),  # Bass > Kraft Bass
    (6, 9),  # Percussion > Space Hat
]

patch_count = len(touch_patch)
patch_index = (
    patch_count - 1
)  # start on the last one so first time it is pressed it goes to first

cc_x = 0
cc_y = 0
cc_prox = 0

# Use default HID descriptor
midi_service = adafruit_ble_midi.MIDIService()
advertisement = ProvideServicesAdvertisement(midi_service)

ble = adafruit_ble.BLERadio()
if ble.connected:
    for c in ble.connections:
        c.disconnect()

midi = adafruit_midi.MIDI(midi_out=midi_service, out_channel=midi_channel - 1)

print("advertising")
ble.name = "CLUE BLE MIDI"
ble.start_advertising(advertisement)

clue.display.brightness = 1.0
clue.pixel.brightness = 0.2
screen = displayio.Group()

ORANGE = 0xCE6136
GRAY = 0x080808
BLACK = 0x121212
BLUE = 0x668190
SILVER = 0xAAAAAA
BROWN = 0x805D40

# --- Setup screen ---
# BG
color_bitmap = displayio.Bitmap(240, 240, 1)
color_palette = displayio.Palette(1)
color_palette[0] = GRAY
bg_sprite = displayio.TileGrid(color_bitmap, x=0, y=0, pixel_shader=color_palette)
screen.append(bg_sprite)
column_a = 20
column_b = 168
# positions that are distributed relative to cc_x and cc_prox y positions
row_a = 80
row_c = 170
row_b = int(row_a + ((row_c - row_a) / 2))
line_row_a = int(row_a + ((row_b - row_a) / 2))
line_row_b = int(row_b + ((row_c - row_b) / 2))
picker_box_row = [row_a, row_b, row_c]

# trim
top_trim_box = Rect(0, 0, 240, 8, fill=BROWN, outline=None)
screen.append(top_trim_box)
bottom_trim_box = Rect(0, 232, 240, 8, fill=BROWN, outline=None)
screen.append(bottom_trim_box)

# title text
title_label = label.Label(terminalio.FONT, text="MIDI CLUE", scale=4, color=SILVER)
title_label.x = 14
title_label.y = 27
screen.append(title_label)

# title box
title_box = Rect(0, 54, 240, 8, fill=BROWN, outline=None)
screen.append(title_box)

# cc x num
cc_x_num_label = label.Label(
    terminalio.FONT,
    text=("CC {}".format(cc_x_num)),
    scale=3,
    color=ORANGE,
)
cc_x_num_label.x = column_a
cc_x_num_label.y = row_a
screen.append(cc_x_num_label)

# cc x value
cc_x_label = label.Label(terminalio.FONT, text=str(cc_x), scale=3, color=ORANGE)
cc_x_label.x = column_b
cc_x_label.y = row_a
screen.append(cc_x_label)

# picker box
picker_box = Rect(3, row_a, 6, 6, fill=ORANGE, outline=None)
screen.append(picker_box)

# mid line
mid_line_a = Rect(0, line_row_a, 240, 2, fill=SILVER, outline=None)
screen.append(mid_line_a)

# cc y num
cc_y_num_label = label.Label(
    terminalio.FONT, text=("CC {}".format(cc_y_num)), scale=3, color=BLUE
)
cc_y_num_label.x = column_a
cc_y_num_label.y = row_b
screen.append(cc_y_num_label)

# cc y value text
cc_y_label = label.Label(terminalio.FONT, text=str(cc_y), scale=3, color=BLUE)
cc_y_label.x = column_b
cc_y_label.y = row_b
screen.append(cc_y_label)

# mid line
mid_line_b = Rect(0, line_row_b, 240, 2, fill=SILVER, outline=None)
screen.append(mid_line_b)

# cc prox num text
cc_prox_num_label = label.Label(
    terminalio.FONT,
    text=("CC {}".format(cc_prox_num)),
    scale=3,
    color=SILVER,
)
cc_prox_num_label.x = column_a
cc_prox_num_label.y = row_c
screen.append(cc_prox_num_label)

# cc prox value text
cc_prox_label = label.Label(terminalio.FONT, text=str(cc_prox), scale=3, color=SILVER)
cc_prox_label.x = column_b
cc_prox_label.y = row_c
screen.append(cc_prox_label)

# footer line
footer_line = Rect(0, 192, 240, 2, fill=SILVER, outline=None)
screen.append(footer_line)


# patch label
patch_label = label.Label(terminalio.FONT, text="Patch _", scale=2, color=BLUE)
patch_label.x = 4
patch_label.y = 216
screen.append(patch_label)

# footer label
footer_label = label.Label(terminalio.FONT, text="connect BLE", scale=2, color=ORANGE)
footer_label.x = 102
footer_label.y = 216
screen.append(footer_label)

# show the screen
clue.display.show(screen)

cc_num_pick_toggle = 0  # which cc to adjust w buttons
cc_send_toggle = True  # to start and stop sending cc

debug = False  # set debug mode True to test raw values, set False to run BLE MIDI

while True:
    if debug:
        accel_data = clue.acceleration  # get accelerometer reading
        accel_x = accel_data[0]
        accel_y = accel_data[1]
        prox_data = clue.proximity
        print("x:{} y:{}".format(accel_x, accel_y,))
        print("proximity: {}".format(clue.proximity))
        time.sleep(0.2)

    else:
        print("Waiting for connection")
        while not ble.connected:
            pass
        print("Connected")
        footer_label.x = 80
        footer_label.color = BLUE
        footer_label.text = "BLE Connected"
        time.sleep(2)
        footer_label.x = 110
        footer_label.color = SILVER
        footer_label.text = "sending CC"

        while ble.connected:
            # Clue sensor readings to CC
            accel_data = clue.acceleration  # get accelerometer reading
            accel_x = accel_data[0]
            accel_y = accel_data[1]
            prox_data = clue.proximity

            # Remap analog readings to cc range
            cc_x = int(simpleio.map_range(accel_x, -9, 9, 0, 127))
            cc_y = int(simpleio.map_range(accel_y, 0, 9, 0, 127))
            cc_prox = int(simpleio.map_range(prox_data, 0, 255, 0, 127))

            # send all the midi messages in a list
            if cc_send_toggle:
                midi.send(
                    [
                        ControlChange(cc_x_num, cc_x),
                        ControlChange(cc_y_num, cc_y),
                        ControlChange(cc_prox_num, cc_prox),
                    ]
                )
            cc_x_label.text = str(cc_x)
            cc_y_label.text = str(cc_y)
            cc_prox_label.text = str(cc_prox)

            # If you want to send NoteOn or Pitch Bend, here are examples:
            # midi.send(NoteOn(44, 1column_a))  # G sharp 2nd octave
            # a_pitch_bend = PitchBend(random.randint(0, 16383))
            # midi.send(a_pitch_bend)

            if clue.button_a:
                if cc_num_pick_toggle == 0:
                    cc_x_num = cc_x_num - 1
                    cc_x_num_label.text = "CC {}".format(cc_x_num)
                    time.sleep(0.05)  # Debounce
                elif cc_num_pick_toggle == 1:
                    cc_y_num = cc_y_num - 1
                    cc_y_num_label.text = "CC {}".format(cc_y_num)
                    time.sleep(0.05)
                else:
                    cc_prox_num = cc_prox_num - 1
                    cc_prox_num_label.text = "CC {}".format(cc_prox_num)
                    time.sleep(0.05)

            if clue.button_b:
                if cc_num_pick_toggle == 0:
                    cc_x_num = cc_x_num + 1
                    cc_x_num_label.text = "CC {}".format(cc_x_num)
                    time.sleep(0.05)
                elif cc_num_pick_toggle == 1:
                    cc_y_num = cc_y_num + 1
                    cc_y_num_label.text = "CC {}".format(cc_y_num)
                    time.sleep(0.05)
                else:
                    cc_prox_num = cc_prox_num + 1
                    cc_prox_num_label.text = "CC {}".format(cc_prox_num)
                    time.sleep(0.05)

            if clue.touch_0:
                patch_index = (patch_index + 1) % patch_count
                midi.send(  # Bank select
                    [
                        ControlChange(0, 0),  # MSB
                        ControlChange(32, touch_patch[patch_index][0]),  # LSB
                    ]
                )
                midi.send(ProgramChange(touch_patch[patch_index][1]))  # Program Change
                patch_label.text = "Patch {}".format(patch_index + 1)
                time.sleep(0.2)

            if clue.touch_1:
                cc_num_pick_toggle = (cc_num_pick_toggle + 1) % 3
                picker_box.y = picker_box_row[cc_num_pick_toggle]
                time.sleep(0.1)

            if clue.touch_2:
                cc_send_toggle = not cc_send_toggle
                if cc_send_toggle:
                    footer_label.x = 110
                    footer_label.color = SILVER
                    footer_label.text = "sending CC"
                else:
                    footer_label.x = 114
                    footer_label.color = ORANGE
                    footer_label.text = "CC paused"
                time.sleep(0.1)

        print("Disconnected")
        print()
        ble.start_advertising(advertisement)
