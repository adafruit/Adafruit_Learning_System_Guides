# SPDX-FileCopyrightText: 2021 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT
# Ableton Live Macropad Launcher
# In Ableton, choose "Launchpad Mini Mk3" as controller with MacroPad 2040 as in and out
# Use empty fifth scene to allow "unlaunching" of tracks with encoder modifier
import board
from adafruit_macropad import MacroPad
import displayio
import terminalio
from adafruit_simplemath import constrain
from adafruit_display_text import label
import usb_midi
import adafruit_midi
from adafruit_midi.control_change import ControlChange
from adafruit_midi.note_off import NoteOff
from adafruit_midi.note_on import NoteOn
from adafruit_midi.midi_message import MIDIUnknownEvent

macropad = MacroPad()

TITLE_TEXT = "Live Launcher 2040"
print(TITLE_TEXT)
TRACK_NAMES = ["DRUM", "BASS", "SYNTH"]  # Customize these
LIVE_CC_NUMBER = 74  # CC number to send w encoder
FADER_TEXT = "cutoff"  # change for intended CC name

# --- MIDI recieve is complex, so not using macropad.midi
midi = adafruit_midi.MIDI(
                        midi_in=usb_midi.ports[0],
                        in_channel=(0, 1, 2),
                        midi_out=usb_midi.ports[1],
                        out_channel=0
)


# ---Official Launchpad colors---
LP_COLORS = (
    0x000000, 0x101010, 0x202020, 0x3f3f3f, 0x3f0f0f, 0x3f0000, 0x200000, 0x100000,
    0x3f2e1a, 0x3f0f00, 0x200800, 0x100400, 0x3f2b0b, 0x3f3f00, 0x202000, 0x101000,
    0x213f0c, 0x143f00, 0x0a2000, 0x051000, 0x123f12, 0x003f00, 0x002000, 0x001000,
    0x123f17, 0x003f06, 0x002003, 0x001001, 0x123f16, 0x003f15, 0x00200b, 0x001006,
    0x123f2d, 0x003f25, 0x002012, 0x001009, 0x12303f, 0x00293f, 0x001520, 0x000b10,
    0x12213f, 0x00153f, 0x000b20, 0x000610, 0x0b093f, 0x00003f, 0x000020, 0x000010,
    0x1a0d3e, 0x0b003f, 0x060020, 0x030010, 0x3f0f3f, 0x3f003f, 0x200020, 0x100010,
    0x3f101b, 0x3f0014, 0x20000a, 0x100005, 0x3f0300, 0x250d00, 0x1d1400, 0x080d01,
    0x000e00, 0x001206, 0x00051b, 0x00003f, 0x001113, 0x040032, 0x1f1f1f, 0x070707,
    0x3f0000, 0x2e3f0b, 0x2b3a01, 0x183f02, 0x032200, 0x003f17, 0x00293f, 0x000a3f,
    0x06003f, 0x16003f, 0x2b061e, 0x0a0400, 0x3f0c00, 0x213701, 0x1c3f05, 0x003f00,
    0x0e3f09, 0x153f1b, 0x0d3f32, 0x16223f, 0x0c1430, 0x1a1439, 0x34073f, 0x3f0016,
    0x3f1100, 0x2d2900, 0x233f00, 0x201601, 0x0e0a00, 0x001203, 0x031308, 0x05050a,
    0x050716, 0x190e06, 0x200000, 0x36100a, 0x351204, 0x3f2f09, 0x27370b, 0x192c03,
    0x05050b, 0x36341a, 0x1f3a22, 0x26253f, 0x23193f, 0x0f0f0f, 0x1c1c1c, 0x373f3f,
    0x270000, 0x0d0000, 0x063300, 0x011000, 0x2d2b00, 0x0f0c00, 0x2c1400, 0x120500,
)

LP_PADS = {
    81: 0, 82: 1, 83: 2,
    71: 3, 72: 4, 73: 5,
    61: 6, 62: 7, 63: 8,
    51: 9, 52: 10, 53: 11
}

LIVE_NOTES = [81, 82, 83, 71, 72, 73, 61, 62, 63, 51, 52, 53]
CC_OFFSET = 20
modifier = False  # use to add encoder switch modifier to keys for clip mute
MODIFIER_NOTES = [41, 42, 43, 41, 42, 43, 41, 42, 43, 41, 42, 43]  # blank row in Live

last_position = 0  # encoder position state

# ---NeoPixel setup---
BRIGHT = 0.125
DIM = 0.0625
macropad.pixels.brightness = BRIGHT

# ---Display setup---
display = board.DISPLAY
screen = displayio.Group()
display.show(screen)
WIDTH = 128
HEIGHT = 64
FONT = terminalio.FONT
# Draw a title label
title = TITLE_TEXT
title_area = label.Label(FONT, text=title, color=0xFFFFFF, x=6, y=3)
screen.append(title_area)

# --- create display strings and positions
x1 = 5
x2 = 35
x3 = 65
y1 = 17
y2 = 27
y3 = 37
y4 = 47
y5 = 57

# ---Push knob text setup
push_text_area = label.Label(FONT, text="[o]", color=0xffffff, x=WIDTH-22, y=y2)
screen.append(push_text_area)

# ---CC knob text setup
fader_text_area = label.Label(FONT, text=FADER_TEXT, color=0xffffff, x=WIDTH - 42, y=y4)
screen.append(fader_text_area)
# --- cc value display
cc_val_text = str(CC_OFFSET)
cc_val_text_area = label.Label(FONT, text=cc_val_text, color=0xffffff, x=WIDTH - 20, y=y5)
screen.append(cc_val_text_area)

label_data = (
    # text, x, y
    (TRACK_NAMES[0], x1, y1), (TRACK_NAMES[1], x2, y1), (TRACK_NAMES[2], x3, y1),
    (".", x1, y2), (".", x2, y2), (".", x3, y2),
    (".", x1, y3), (".", x2, y3), (".", x3, y3),
    (".", x1, y4), (".", x2, y4), (".", x3, y4),
    (".", x1, y5), (".", x2, y5), (".", x3, y5)
)

labels = []

for data in label_data:
    text, x, y = data
    label_area = label.Label(FONT, text=text, color=0xffffff)
    group = displayio.Group(x=x, y=y)
    group.append(label_area)
    screen.append(group)
    labels.append(label_area)  # these are individually addressed later

num = 1

while True:
    msg_in = midi.receive()
    if isinstance(msg_in, NoteOn) and msg_in.velocity != 0:
        print(
            "received NoteOn",
            "from channel",
            msg_in.channel + 1,
            "MIDI note",
            msg_in.note,
            "velocity",
            msg_in.velocity,
            "\n"
        )
    # send neopixel lightup code to key, text to display
        if msg_in.note in LP_PADS:
            macropad.pixels[LP_PADS[msg_in.note]] = LP_COLORS[msg_in.velocity]
            macropad.pixels.show()
            if msg_in.velocity == 21:  # active pad is indicated by Live as vel 21
                labels[LP_PADS[msg_in.note]+3].text = "o"
            else:
                labels[LP_PADS[msg_in.note]+3].text = "."

    elif isinstance(msg_in, NoteOff):
        print(
            "received NoteOff",
            "from channel",
            msg_in.channel + 1,
            "\n"
        )

    elif isinstance(msg_in, NoteOn) and msg_in.velocity == 0:
        print(
            "received NoteOff",
            "from channel",
            msg_in.channel + 1,
            "MIDI note",
            msg_in.note,
            "velocity",
            msg_in.velocity,
            "\n"
        )

    elif isinstance(msg_in, ControlChange):
        print(
            "received CC",
            "from channel",
            msg_in.channel + 1,
            "controller",
            msg_in.control,
            "value",
            msg_in.value,
            "\n"
        )

    elif isinstance(msg_in, MIDIUnknownEvent):
        # Message are only known if they are imported
        print("Unknown MIDI event status ", msg_in.status)

    elif msg_in is not None:
        midi.send(msg_in)

    key_event = macropad.keys.events.get()  # check for keypad events

    if not key_event:  # Event is None; no keypad event happened, do other stuff

        position = macropad.encoder  # store encoder position state
        cc_position = int(constrain((position + CC_OFFSET), 0, 127))  # lock to cc range
        if last_position is None or position != last_position:

            if position < last_position:
                midi.send(ControlChange(LIVE_CC_NUMBER, cc_position))
                print("CC", cc_position)
                cc_val_text_area.text = str(cc_position)

            elif position > last_position:
                midi.send(ControlChange(LIVE_CC_NUMBER, cc_position))
                print("CC", cc_position)
                cc_val_text_area.text = str(cc_position)
        last_position = position

        macropad.encoder_switch_debounced.update()  # check the encoder switch w debouncer
        if macropad.encoder_switch_debounced.pressed:
            print("Mod")
            push_text_area.text = "[.]"
            modifier = True
            macropad.pixels.brightness = DIM

        if macropad.encoder_switch_debounced.released:
            modifier = False
            push_text_area.text = "[o]"
            macropad.pixels.brightness = BRIGHT

        continue

    num = key_event.key_number

    if key_event.pressed and not modifier:
        midi.send(NoteOn(LIVE_NOTES[num], 127))
        print("\nsent note", LIVE_NOTES[num], "\n")

    if key_event.pressed and modifier:
        midi.send(NoteOn(MODIFIER_NOTES[num], 127))

    if key_event.released and not modifier:
        midi.send(NoteOff(LIVE_NOTES[num], 0))

    if key_event.released and modifier:
        midi.send(NoteOff(MODIFIER_NOTES[num], 0))

    macropad.pixels.show()
