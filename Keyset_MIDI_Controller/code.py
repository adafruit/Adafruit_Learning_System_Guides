# SPDX-FileCopyrightText: 2025 Liz Clark and Noe Ruiz for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import board
import simpleio
import displayio
import i2cdisplaybus
import adafruit_imageload
import rotaryio
import digitalio
import terminalio
import keypad
from digitalio import DigitalInOut, Direction
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
import adafruit_displayio_ssd1306
import usb_midi
import adafruit_midi
from adafruit_midi.note_on          import NoteOn
from adafruit_midi.note_off         import NoteOff
from adafruit_midi.control_change import ControlChange
from analogio import AnalogIn
from adafruit_debouncer import Button

# midi note names
MIDI_NOTE_NAMES = [
        "C-2", "C#-2", "D-2", "D#-2", "E-2", "F-2", "F#-2", "G-2", "G#-2", "A-2", "A#-2", "B-2",
        "C-1", "C#-1", "D-1", "D#-1", "E-1", "F-1", "F#-1", "G-1", "G#-1", "A-1", "A#-1", "B-1",
        "C0", "C#0", "D0", "D#0", "E0", "F0", "F#0", "G0", "G#0", "A0", "A#0", "B0",
        "C1", "C#1", "D1", "D#1", "E1", "F1", "F#1", "G1", "G#1", "A1", "A#1", "B1",
        "C2", "C#2", "D2", "D#2", "E2", "F2", "F#2", "G2", "G#2", "A2", "A#2", "B2",
        "C3", "C#3", "D3", "D#3", "E3", "F3", "F#3", "G3", "G#3", "A3", "A#3", "B3",
        "C4", "C#4", "D4", "D#4", "E4", "F4", "F#4", "G4", "G#4", "A4", "A#4", "B4",
        "C5", "C#5", "D5", "D#5", "E5", "F5", "F#5", "G5", "G#5", "A5", "A#5", "B5",
        "C6", "C#6", "D6", "D#6", "E6", "F6", "F#6", "G6", "G#6", "A6", "A#6", "B6",
        "C7", "C#7", "D7", "D#7", "E7", "F7", "F#7", "G7", "G#7", "A7", "A#7", "B7",
        "C8", "C#8", "D8", "D#8", "E8", "F8", "F#8", "G8", "G#8", "A8", "A#8", "B8",
        "C9", "C#9", "D9", "D#9", "E9", "F9", "F#9", "G9", "G#9", "A9", "A#9", "B9"
        ]


# Data structure to store all control settings
control_settings = {
    'pots': [
        {'cc_num': 1, 'range_min': 0, 'range_max': 127, 'channel': 0, 'current_val': 0},  # Pot A
        {'cc_num': 10, 'range_min': 0, 'range_max': 127, 'channel': 0, 'current_val': 0}, # Pot B
        {'cc_num': 11, 'range_min': 0, 'range_max': 127, 'channel': 0, 'current_val': 0}, # Pot C
    ],
    'keys': [
        {'note': 61, 'velocity': 120, 'channel': 0},  # Key 1
        {'note': 64, 'velocity': 120, 'channel': 0},  # Key 2
        {'note': 66, 'velocity': 120, 'channel': 0},  # Key 3
        {'note': 68, 'velocity': 120, 'channel': 0},  # Key 4
        {'note': 73, 'velocity': 120, 'channel': 0},  # Key 5
    ]
}

#  midi note numbers (will be replaced by control_settings)
midi_notes = [key['note'] for key in control_settings['keys']]


#rotary encoder and button
encoder = rotaryio.IncrementalEncoder(board.D3, board.D2)
last_position = 0

#  midi setup
midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)

# Create keypad object with the pins (removed encoder button)
keys = keypad.Keys(
    pins=(board.D4, board.D5, board.D6, board.D7, board.D8),
    value_when_pressed=False,  # Buttons pull to ground when pressed
    pull=True  # Enable internal pull-up resistors
)

# Set up encoder button with debouncer
encoder_button_pin = DigitalInOut(board.A3)
encoder_button_pin.direction = Direction.INPUT
encoder_button_pin.pull = digitalio.Pull.UP
encoder_button = Button(encoder_button_pin, value_when_pressed=False, long_duration_ms=500)

#  potentiometer setup
pot_A = AnalogIn(board.A2)
pot_B = AnalogIn(board.A1)
pot_C = AnalogIn(board.A0)

#display setup
i2c = board.STEMMA_I2C()
displayio.release_displays()

# oled
oled_reset = board.D9
display_bus = i2cdisplaybus.I2CDisplayBus(i2c, device_address=0x3D, reset=oled_reset)
WIDTH = 128
HEIGHT = 64
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

bitmap, palette = adafruit_imageload.load("/main.bmp",
                                          bitmap=displayio.Bitmap,
                                          palette=displayio.Palette)

# Create a TileGrid to hold the bitmap
bitmap_grid = displayio.TileGrid(bitmap, pixel_shader=palette)

# Create main page
maingroup = displayio.Group()

#dictionary for rectangle highlights
rect_dict = [
    {'pos': (0, 0), 'dim': (42, 32)},
    {'pos': (42, 0), 'dim': (42, 32)},
    {'pos': (84, 0), 'dim': (42, 32)},
    {'pos': (1, 32), 'dim': (25, 32)},
    {'pos': (26, 32), 'dim': (25, 32)},
    {'pos': (51, 32), 'dim': (25, 32)},
    {'pos': (76, 32), 'dim': (25, 32)},
    {'pos': (101, 32), 'dim': (25, 32)},
]

current_index = 0
rect_info = rect_dict[current_index]
x, y = rect_info['pos']
w, h = rect_info['dim']

# Create the rectangle (outline only, no fill)
rectangle = Rect(x, y, w, h, fill=None, outline=0xFFFFFF)

# Add rectangles to the Group
maingroup.append(bitmap_grid)
maingroup.append(rectangle)

#text container
keynote_maingroup = displayio.Group()
font = terminalio.FONT
color = 0x000000

keynotes = [
    {'num': control_settings['keys'][0]['note'], 'pos': (14, 42)},
    {'num': control_settings['keys'][1]['note'], 'pos': (39, 42)},
    {'num': control_settings['keys'][2]['note'], 'pos': (64, 42)},
    {'num': control_settings['keys'][3]['note'], 'pos': (89, 42)},
    {'num': control_settings['keys'][4]['note'], 'pos': (114, 42)},
]
keynote_labels = []
for keynote in keynotes:
    keynote_area = label.Label(terminalio.FONT,
                               text=MIDI_NOTE_NAMES[keynote['num']],
                               color=0x000000)
    keynote_area.anchor_point = (0.5, 0.0)
    keynote_area.anchored_position = (keynote['pos'][0], keynote['pos'][1])
    keynote_labels.append(keynote_area)
    keynote_maingroup.append(keynote_area)
maingroup.append(keynote_maingroup)

# labels for potentiometers

potval_maingroup = displayio.Group()
potvals = [
    {'num': "0", 'pos': (22, 10)},
    {'num': "0", 'pos': (64, 10)},
    {'num': "0", 'pos': (106, 10)},
]
potvals_labels = []

for potval in potvals:
    potval_area = label.Label(
        terminalio.FONT,
        text=potval['num'],
        color=0x000000,
    )
    potval_area.anchor_point = (0.5, 0.0)
    potval_area.anchored_position = (potval['pos'][0], potval['pos'][1])
    potvals_labels.append(potval_area)
    potval_maingroup.append(potval_area)
maingroup.append(potval_maingroup)

# Create edit page
editgroup = displayio.Group()

# Labels for Edit Page
header_area = label.Label(
    terminalio.FONT,
    text="",
    color=0x000000,
    x=0, y=10,
    background_color=0xFFFFFF,
    padding_left=34,
    padding_right=34,
    padding_top=2,
    padding_bottom=2,
    )
header_area.anchor_point = (0.5, 0.0)
header_area.anchored_position = (64, 2)

item1_area = label.Label(terminalio.FONT, text="", color=0xFFFFFF, x=4, y=25,)
item2_area = label.Label(terminalio.FONT, text="", color=0xFFFFFF, x=4, y=38,)
item3_area = label.Label(terminalio.FONT, text="", color=0xFFFFFF, x=4, y=52,)

# Create separate labels for range min and max
range_label = label.Label(terminalio.FONT, text="Range:", color=0xFFFFFF, x=4, y=38,)
range_min_label = label.Label(terminalio.FONT, text="", color=0xFFFFFF, x=65, y=38,)
range_dash_label = label.Label(terminalio.FONT, text="-", color=0xFFFFFF, x=85, y=38,)
range_max_label = label.Label(terminalio.FONT, text="", color=0xFFFFFF, x=95, y=38,)

item_areas = [item1_area, item2_area, item3_area]
edit_rectangle = Rect(0, 0, 128, 14, fill=None, outline=0xFFFFFF)
range_rectangle = Rect(0, 0, 20, 14, fill=0x000000, outline=0xFFFFFF)

editgroup.append(edit_rectangle)
editgroup.append(header_area)
editgroup.append(item1_area)
editgroup.append(item2_area)
editgroup.append(item3_area)
editgroup.append(range_rectangle)
range_rectangle.hidden = True

# Add the Group to the Display
display.root_group = maingroup

#  function to read analog input
def val(pin):
    return pin.value

# Function to update edit mode display
def update_edit_display(index):
    # First, remove the range components if they exist in editgroup
    if range_label in editgroup:
        editgroup.remove(range_label)
        editgroup.remove(range_min_label)
        editgroup.remove(range_dash_label)
        editgroup.remove(range_max_label)
    if index < 3:  # Potentiometer
        p = control_settings['pots'][index]
        header_area.text = f"EDIT POT {'ABC'[index]}"
        item1_area.text = f"CC Number:     {p['cc_num']}"
        # Clear item2_area text since we'll use separate labels
        item2_area.text = ""
        # Add range components
        editgroup.append(range_label)
        editgroup.append(range_min_label)
        editgroup.append(range_dash_label)
        editgroup.append(range_max_label)
        range_min_label.text = str(p['range_min'])
        range_max_label.text = str(p['range_max'])
        item3_area.text = f"MIDI Channel:  {p['channel'] + 1}"
    else:  # Button
        k = index - 3
        s = control_settings['keys'][k]
        note_name = MIDI_NOTE_NAMES[s['note']]
        header_area.text = f"EDIT KEY {k + 1}"
        item1_area.text = f"MIDI Note:     {note_name}"
        item2_area.text = f"Velocity:      {s['velocity']}"
        item3_area.text = f"MIDI Channel:  {s['channel'] + 1}"

#  variables for last read value
pot_A_val2 = 0
pot_B_val2 = 0
pot_C_val2 = 0

edit_mode = False
edit_current_index = 0
edit_active = False  # Whether we're actively editing a value
range_edit_selection = 0  # 0 for min, 1 for max
range_edit_active = False  # New variable to track if we're actively editing a range value

while True:
    # Update encoder button state
    encoder_button.update()

    # Handle encoder button presses
    if encoder_button.short_count == 1:
        if not edit_mode:
            # Short press enters edit mode
            update_edit_display(current_index)
            edit_current_index = 0
            edit_rectangle.x = 0
            edit_rectangle.y = item_areas[edit_current_index].y - 7
            edit_active = False
            range_rectangle.hidden = True
            display.root_group = editgroup
            edit_mode = True
        elif edit_mode and edit_active and current_index < 3 and edit_current_index == 1:
            # In range editing mode, short press switches between min/max
            range_edit_selection = 1 - range_edit_selection  # Toggle between 0 and 1
            if range_edit_selection == 0:
                range_rectangle.x = range_min_label.x - 2
            else:
                range_rectangle.x = range_max_label.x - 2
        else:
            # Short press exits edit mode
            display.root_group = maingroup
            edit_mode = False
            edit_active = False
            range_edit_active = False
            edit_rectangle.fill = None
            item_areas[edit_current_index].color = 0xFFFFFF
            if current_index < 3 and edit_current_index == 1:
                range_min_label.color = 0xFFFFFF
                range_max_label.color = 0xFFFFFF
                range_label.color = 0xFFFFFF
                range_dash_label.color = 0xFFFFFF
                range_rectangle.hidden = True
    if encoder_button.short_count == 2:
        # send midi panic
        panic = ControlChange(123, 120)
        #  send CC message
        midi.send(panic)

    # Handle long press in edit mode
    if edit_mode and encoder_button.long_press:
        if current_index < 3 and edit_current_index == 1:
            # We're on the Range line
            if not edit_active:
                # Not in range edit mode yet, enter it
                edit_active = True
                range_edit_active = False
                edit_rectangle.fill = 0xFFFFFF
                # Show the range rectangle
                range_rectangle.hidden = False
                range_rectangle.fill = None
                range_rectangle.outline = 0x000000
                range_edit_selection = 0  # Start with min
                # Position range rectangle over the min value
                range_rectangle.x = range_min_label.x - 2
                range_rectangle.y = range_min_label.y - 7
                range_label.color = 0x000000
                range_dash_label.color = 0x000000
                range_max_label.color = 0x000000
                range_min_label.color = 0x000000
            elif edit_active and not range_edit_active:
                # In selection mode, enter value editing mode
                range_edit_active = True
                range_rectangle.fill = 0x000000
                range_min_label.color = 0xFFFFFF
                range_max_label.color = 0xFFFFFF
            elif edit_active and range_edit_active:
                # In value editing mode, exit range editing completely
                edit_active = False
                range_edit_active = False
                edit_rectangle.fill = None
                # Hide range rectangle and restore colors
                range_rectangle.hidden = True
                range_label.color = 0xFFFFFF
                range_dash_label.color = 0xFFFFFF
                range_min_label.color = 0xFFFFFF
                range_max_label.color = 0xFFFFFF
        else:
            # Non-range items - simple toggle
            edit_active = not edit_active
            range_edit_active = False  # Reset range edit active state

            # Change rectangle color to indicate active editing
            if edit_active:
                edit_rectangle.fill = 0xFFFFFF
                # Make text black on white background for other items
                item_areas[edit_current_index].color = 0x000000
            else:
                edit_rectangle.fill = None
                # Make text white
                item_areas[edit_current_index].color = 0xFFFFFF

    event = keys.events.get()

    if event:
        # event.key_number gives you the index (0-4) of which button
        key_index = event.key_number

        if event.pressed:
            # Button was pressed - send NoteOn using settings
            key_settings = control_settings['keys'][key_index]
            midi.send(NoteOn(key_settings['note'], key_settings['velocity']))

        if event.released:
            # Button was released - send NoteOff using settings
            key_settings = control_settings['keys'][key_index]
            midi.send(NoteOff(key_settings['note'], key_settings['velocity']))

    position = encoder.position

    # Check if encoder moved
    if position != last_position:
        if not edit_mode:
            # Main menu navigation
            if position > last_position:
                current_index = (current_index + 1) % len(rect_dict)
            else:
                current_index = (current_index - 1) % len(rect_dict)

            rect_info = rect_dict[current_index]
            x, y = rect_info['pos']
            w, h = rect_info['dim']

            # Remove old rectangle and create new one with updated dimensions
            maingroup.remove(rectangle)
            rectangle = Rect(x, y, w, h, fill=None, outline=0xFFFFFF)
            maingroup.append(rectangle)
            last_position = position

        elif edit_mode and not edit_active:
            # Edit mode navigation - cycle through editable items
            # First restore previous item colors
            item_areas[edit_current_index].color = 0xFFFFFF

            if position > last_position:
                edit_current_index = (edit_current_index + 1) % len(item_areas)
            else:
                edit_current_index = (edit_current_index - 1) % len(item_areas)

            # Update rectangle position to highlight current item
            edit_rectangle.x = 0
            edit_rectangle.y = item_areas[edit_current_index].y - 7
            last_position = position

        elif edit_mode and edit_active:
            # Actively editing a value
            direction = 1 if position > last_position else -1

            if current_index < 3:  # Editing potentiometer
                pot_settings = control_settings['pots'][current_index]

                if edit_current_index == 0:  # CC Number
                    pot_settings['cc_num'] = (pot_settings['cc_num'] + direction) % 128
                    item1_area.text = f"CC Number:     {pot_settings['cc_num']}"
                elif edit_current_index == 1:  # Range editing
                    if range_edit_active:
                        # Actually edit the value
                        if range_edit_selection == 0:  # Editing min
                            pot_settings['range_min'] = (pot_settings['range_min'] +
                                                         direction) % 128
                            range_min_label.text = f"{pot_settings['range_min']}"
                        else:  # Editing max
                            pot_settings['range_max'] = (pot_settings['range_max'] +
                                                         direction) % 128
                            range_max_label.text = f"{pot_settings['range_max']}"
                    else:
                        # Special handling for range - switch between min and max
                        if direction > 0 and range_edit_selection == 0:
                            # Moving right from min, switch to max
                            range_edit_selection = 1
                            range_rectangle.x = range_max_label.x - 2
                        elif direction < 0 and range_edit_selection == 1:
                            # Moving left from max, switch to min
                            range_edit_selection = 0
                            range_rectangle.x = range_min_label.x - 2
                elif edit_current_index == 2:  # MIDI Channel
                    pot_settings['channel'] = (pot_settings['channel'] + direction) % 16
                    item3_area.text = f"MIDI Channel:  {pot_settings['channel'] + 1}"

            else:  # Editing key
                key_index = current_index - 3
                key_settings = control_settings['keys'][key_index]

                if edit_current_index == 0:  # MIDI Note
                    key_settings['note'] = (key_settings['note'] + direction) % len(MIDI_NOTE_NAMES)
                    key_note_name = MIDI_NOTE_NAMES[key_settings['note']]
                    item1_area.text = f"MIDI Note:     {key_note_name}"
                    # Update the main screen label too
                    keynote_labels[key_index].text = key_note_name
                elif edit_current_index == 1:  # Velocity
                    key_settings['velocity'] = (key_settings['velocity'] + direction) % 127
                    item2_area.text = f"Velocity:      {key_settings['velocity']}"
                elif edit_current_index == 2:  # MIDI Channel
                    key_settings['channel'] = (key_settings['channel'] + direction) % 16
                    item3_area.text = f"MIDI Channel:  {key_settings['channel'] + 1}"

            last_position = position

    pot_A_val1 = round(simpleio.map_range(val(pot_A), 65535, 0,
                                                      control_settings['pots'][0]['range_min'],
                                                      control_settings['pots'][0]['range_max']))
    pot_B_val1 = round(simpleio.map_range(val(pot_B), 65535, 0,
                                                      control_settings['pots'][1]['range_min'],
                                                      control_settings['pots'][1]['range_max']))
    pot_C_val1 = round(simpleio.map_range(val(pot_C), 65535, 0,
                                                      control_settings['pots'][2]['range_min'],
                                                      control_settings['pots'][2]['range_max']))

    #  if modulation value is updated...
    if abs(pot_A_val1 - pot_A_val2) > 1:
        #  update pot_A_val2
        pot_A_val2 = pot_A_val1
        #  create integer
        modulation = int(pot_A_val2)
        control_settings['pots'][0]['current_val'] = modulation
        potvals_labels[0].text = str(modulation)
        #  create CC message
        pot_settings = control_settings['pots'][0]
        modWheel = ControlChange(pot_settings['cc_num'], modulation)
        #  send CC message
        midi.send(modWheel)

    if abs(pot_B_val1 - pot_B_val2) > 1:
        #  update pot_B_val2
        pot_B_val2 = pot_B_val1
        #  create integer
        ControllerB = int(pot_B_val2)
        control_settings['pots'][1]['current_val'] = ControllerB
        potvals_labels[1].text = str(ControllerB)
        #  create CC message
        pot_settings = control_settings['pots'][1]
        ControlB = ControlChange(pot_settings['cc_num'], ControllerB)
        #  send CC message
        midi.send(ControlB)

    if abs(pot_C_val1 - pot_C_val2) > 1:
        #  update pot_c_val2
        pot_C_val2 = pot_C_val1
        #  create integer
        ControllerC = int(pot_C_val2)
        control_settings['pots'][2]['current_val'] = ControllerC
        potvals_labels[2].text = str(ControllerC)
        #  create CC message
        pot_settings = control_settings['pots'][2]
        ControlC = ControlChange(pot_settings['cc_num'], ControllerC)
        #  send CC message
        midi.send(ControlC)
