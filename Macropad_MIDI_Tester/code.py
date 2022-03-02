# SPDX-FileCopyrightText: 2022 John Park for Adafruit Industries
# SPDX-License-Identifier: MIT
# Macropad MIDI Tester
# Play MIDI notes with keys
# Click encoder to switch modes
# Turn encoder to adjust CC, ProgramChange, or PitchBend
from adafruit_macropad import MacroPad
from rainbowio import colorwheel

CC_NUM = 74  # select your CC number

macropad = MacroPad(rotation=180)  # create the macropad object, rotate orientation
macropad.display.auto_refresh = False  # avoid lag

# --- Pixel setup --- #
key_color = colorwheel(120)  # fill with cyan to start
macropad.pixels.brightness = 0.1
macropad.pixels.fill(key_color)

# --- MIDI variables ---
mode = 0
mode_text = ["Patch", ("CC #%s" % (CC_NUM)), "Pitch Bend"]
midi_values = [0, 16, 8]  # bank, cc value, pitch
# Chromatic scale starting with C3 as bottom left keyswitch (or use any notes you like)
midi_notes = [
            57, 58, 59,
            54, 55, 56,
            51, 52, 53,
            48, 49, 50
            ]

# --- Display text setup ---
text_lines = macropad.display_text("Macropad MIDI Tester")
text_lines[0].text = "Mode: Patch {}".format(midi_values[0]+1)  # Patch display offset by 1
text_lines[1].text = "Press knob for modes"
text_lines.show()

last_knob_pos = macropad.encoder  # store knob position state


while True:
    while macropad.keys.events:  # check for key press or release
        key_event = macropad.keys.events.get()
        if key_event:
            if key_event.pressed:
                key = key_event.key_number
                macropad.midi.send(macropad.NoteOn(midi_notes[key], 120))  # send midi noteon
                macropad.pixels[key] = colorwheel(90)  # light up green
                text_lines[1].text = "NoteOn:{}".format(midi_notes[key])

            if key_event.released:
                key = key_event.key_number
                macropad.midi.send(macropad.NoteOff(midi_notes[key], 0))
                macropad.pixels[key] = key_color  # return to color set by encoder bank value
                text_lines[1].text = "NoteOff:{}".format(midi_notes[key])

    macropad.encoder_switch_debounced.update()  # check the knob switch for press or release
    if macropad.encoder_switch_debounced.pressed:
        mode = (mode+1) % 3
        if mode == 0:
            text_lines[0].text = ("Mode: %s %d" % (mode_text[mode], midi_values[mode]+1))
        elif mode == 1:
            text_lines[0].text = ("Mode: %s %d" % (mode_text[mode], int(midi_values[mode]*4.1)))
        else:
            text_lines[0].text = ("Mode: %s %d" % (mode_text[mode], midi_values[mode]-8))
        macropad.red_led = macropad.encoder_switch
        text_lines[1].text = " "  # clear the note line

    if macropad.encoder_switch_debounced.released:
        macropad.red_led = macropad.encoder_switch

    if last_knob_pos is not macropad.encoder:  # knob has been turned
        knob_pos = macropad.encoder  # read encoder
        knob_delta = knob_pos - last_knob_pos  # compute knob_delta since last read
        last_knob_pos = knob_pos  # save new reading

        if mode == 0:  # ProgramChange
            midi_values[mode] = min(max(midi_values[mode] + knob_delta, 0), 127)  # delta + minmax
            macropad.midi.send(macropad.ProgramChange(midi_values[mode]))  # midi send ProgramChange
            key_color = colorwheel(midi_values[mode]+120)  # change key_color as patches change
            macropad.pixels.fill(key_color)
            text_lines[0].text = ("Mode: %s %d" % (mode_text[mode], midi_values[mode]+1))

        if mode == 1:  # CC
            midi_values[mode] = min(max(midi_values[mode] + knob_delta, 0), 31)  # scale the value
            macropad.midi.send(macropad.ControlChange(CC_NUM, int(midi_values[mode]*4.1)))
            text_lines[0].text = ("Mode: %s %d" % (mode_text[mode], int(midi_values[mode]*4.1)))

        if mode == 2:  # PitchBend
            midi_values[mode] = min(max(midi_values[mode] + knob_delta, 0), 15)  # smaller range
            macropad.midi.send(macropad.PitchBend((midi_values[mode]*1024)))  # range * mult = 16384
            text_lines[0].text = ("Mode: %s %d" % (mode_text[mode], midi_values[mode]-8))

        last_knob_pos = macropad.encoder

    macropad.display.refresh()
