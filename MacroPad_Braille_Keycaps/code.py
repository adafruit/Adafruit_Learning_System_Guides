# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
Adafruit MacroPad shortcut macropad with light up keys that play a tone or wav file when a key is
pressed. Displays the associated key command being sent on key press in a grid matching the key
layout for easily viewing what command is associated with what key.

REQUIRES associated shortcuts.py file containing a dictionary with all the key info.
"""
import displayio
import terminalio
from rainbowio import colorwheel
from adafruit_displayio_layout.layouts.grid_layout import GridLayout
from adafruit_display_text import bitmap_label as label
from adafruit_macropad import MacroPad
from shortcuts import shortcut_keys

# Initialise MacroPad
macropad = MacroPad()

# Setup title and grid
main_group = displayio.Group()
macropad.display.show(main_group)
title = label.Label(
    y=4,
    font=terminalio.FONT,
    color=0x0,
    text="      SHORTCUTS       ",
    background_color=0xFFFFFF,
)
layout = GridLayout(x=0, y=10, width=128, height=54, grid_size=(3, 4), cell_padding=5)

# Extract data from shortcuts
key_sounds = [sound[0] for sound in shortcut_keys["macros"]]
label_names = [names[1] for names in shortcut_keys["macros"]]
keys = [keys[3] for keys in shortcut_keys["macros"]]

# Generate the labels based on the label names and add them to the appropriate grid cell
labels = []
for index in range(12):
    x = index % 3
    y = index // 3
    labels.append(label.Label(terminalio.FONT, text=label_names[index], max_glyphs=10))
    layout.add_content(labels[index], grid_position=(x, y), cell_size=(1, 1))

# Display the text
main_group.append(title)
main_group.append(layout)

while True:
    key_event = macropad.keys.events.get()  # Begin checking for key events.

    if key_event:  # If there is a key event, e.g. a key has been pressed...
        if key_event.pressed:  # And a key is currently being pressed...

            # ... light up the pressed key with a color from the rainbow.
            macropad.pixels[key_event.key_number] = colorwheel(
                int(255 / 12) * key_event.key_number
            )

            # If it's a Keycode...
            if "KC" in shortcut_keys["macros"][key_event.key_number][2]:
                # ... send the associated key command or sequence of key commands.
                for key in keys[key_event.key_number]:
                    macropad.keyboard.press(key)
                macropad.keyboard.release_all()

            # If it's a ConsumerControlCode...
            if "CC" in shortcut_keys["macros"][key_event.key_number][2]:
                # ... send the associated consumer control code.
                for key in keys[key_event.key_number]:
                    macropad.consumer_control.send(key)

            sounds = key_sounds[key_event.key_number]  # Assign the tones/wavs to the keys.
            if isinstance(sounds, int):  # If the sound is a tone in Hz...
                macropad.start_tone(sounds)  # ... play the tone while the key is pressed.
            if isinstance(sounds, str):  # If the sound is a wav file name as a string...
                macropad.play_file(sounds)  # ... play the wav file.
        else:
            # Otherwise, turn off the NeoPixels and stop the tone.
            macropad.pixels.fill(0)
            macropad.stop_tone()
