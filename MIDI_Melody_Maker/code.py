# SPDX-FileCopyrightText: 2020 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from random import randint
import board
import simpleio
import busio
import terminalio
import neopixel
from digitalio import DigitalInOut, Direction, Pull
from analogio import AnalogIn
import displayio
import adafruit_imageload
from adafruit_display_text import label
import adafruit_displayio_ssd1306
#  uncomment if using USB MIDI
#  import usb_midi
from adafruit_display_shapes.rect import Rect
import adafruit_midi
from adafruit_midi.note_on          import NoteOn
from adafruit_midi.note_off         import NoteOff
from adafruit_midi.control_change   import ControlChange

displayio.release_displays()

oled_reset = board.D9

#turn off on-board neopixel
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0)
pixel.fill((0, 0, 0))

# Use for I2C for STEMMA OLED
i2c = board.I2C()
display_bus = displayio.I2CDisplay(i2c, device_address=0x3D, reset=oled_reset)

#  STEMMA OLED dimensions. can have height of 64, but 32 makes text larger
WIDTH = 128
HEIGHT = 32
BORDER = 0

#  blinka sprite indexes
EMPTY = 0
BLINKA_1 = 1
BLINKA_2 = 2

#  setup for STEMMA OLED
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)

# create the displayio object
splash = displayio.Group()
display.show(splash)

#  text for BPM
bpm_text = "BPM:    "
bpm_text_area = label.Label(
    terminalio.FONT, text=bpm_text, color=0xFFFFFF, x=4, y=6
)
splash.append(bpm_text_area)

bpm_rect = Rect(0, 0, 50, 16, fill=None, outline=0xFFFFFF)
splash.append(bpm_rect)

#  text for key
key_text = "Key:    "
key_text_area = label.Label(
    terminalio.FONT, text=key_text, color=0xFFFFFF, x=4, y=21
)
splash.append(key_text_area)

key_rect = Rect(0, 15, 50, 16, fill=None, outline=0xFFFFFF)
splash.append(key_rect)

#  text for mode
mode_text = "Mode:           "
mode_text_area = label.Label(
    terminalio.FONT, text=mode_text, color=0xFFFFFF, x=54, y=21
)
splash.append(mode_text_area)

mode_rect = Rect(50, 15, 78, 16, fill=None, outline=0xFFFFFF)
splash.append(mode_rect)

#  text for beat division
beat_text = "Div:       "
beat_text_area = label.Label(
    terminalio.FONT, text=beat_text, color=0xFFFFFF, x=54, y=6
)
splash.append(beat_text_area)

beat_rect = Rect(50, 0, 78, 16, fill=None, outline=0xFFFFFF)
splash.append(beat_rect)

#  Blinka sprite setup
blinka, blinka_pal = adafruit_imageload.load("/spritesWhite.bmp",
                                             bitmap=displayio.Bitmap,
                                             palette=displayio.Palette)

#  creates a transparent background for Blinka
blinka_pal.make_transparent(7)
blinka_grid = displayio.TileGrid(blinka, pixel_shader=blinka_pal,
                                 width=1, height=1,
                                 tile_height=16, tile_width=16,
                                 default_tile=EMPTY)
blinka_grid.x = 112
blinka_grid.y = 0

splash.append(blinka_grid)

#  imports MIDI

#  USB MIDI:
#  midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)
#  UART MIDI:
midi = adafruit_midi.MIDI(midi_out=busio.UART(board.TX, board.RX, baudrate=31250), out_channel=0)

#  potentiometer pin setup
key_pot = AnalogIn(board.A1)
mode_pot = AnalogIn(board.A2)
beat_pot = AnalogIn(board.A3)
bpm_slider = AnalogIn(board.A4)
mod_pot = AnalogIn(board.A5)

#  run switch setup
run_switch = DigitalInOut(board.D5)
run_switch.direction = Direction.INPUT
run_switch.pull = Pull.UP

#  arrays of notes in each key
key_of_C = [60, 62, 64, 65, 67, 69, 71, 72]
key_of_Csharp = [61, 63, 65, 66, 68, 70, 72, 73]
key_of_D = [62, 64, 66, 67, 69, 71, 73, 74]
key_of_Dsharp = [63, 65, 67, 68, 70, 72, 74, 75]
key_of_E = [64, 66, 68, 69, 71, 73, 75, 76]
key_of_F = [65, 67, 69, 70, 72, 74, 76, 77]
key_of_Fsharp = [66, 68, 70, 71, 73, 75, 77, 78]
key_of_G = [67, 69, 71, 72, 74, 76, 78, 79]
key_of_Gsharp = [68, 70, 72, 73, 75, 77, 79, 80]
key_of_A = [69, 71, 73, 74, 76, 78, 80, 81]
key_of_Asharp = [70, 72, 74, 75, 77, 79, 81, 82]
key_of_B = [71, 73, 75, 76, 78, 80, 82, 83]

#  array of keys
keys = [key_of_C, key_of_Csharp, key_of_D, key_of_Dsharp, key_of_E, key_of_F, key_of_Fsharp,
        key_of_G, key_of_Gsharp, key_of_A, key_of_Asharp, key_of_B]

#  array of note indexes for modes
fifths = [0, 4, 3, 7, 2, 6, 4, 7]
major = [4, 2, 0, 3, 5, 7, 6, 4]
minor = [5, 7, 2, 4, 6, 5, 1, 3]
pedal = [5, 5, 5, 6, 5, 5, 5, 7]

#  defining variables for key name strings
C_name = "C"
Csharp_name = "C#"
D_name = "D"
Dsharp_name = "D#"
E_name = "E"
F_name = "F"
Fsharp_name = "F#"
G_name = "G"
Gsharp_name = "G#"
A_name = "A"
Asharp_name = "A#"
B_name = "B"

#  array of strings for key names for use with the display
key_names = [C_name, Csharp_name, D_name, Dsharp_name, E_name, F_name, Fsharp_name,
             G_name, Gsharp_name, A_name, Asharp_name, B_name]

#  function for reading analog inputs
def val(voltage):
    return voltage.value

#  comparitors for pots' values
mod_val2 = 0
beat_val2 = 0
bpm_val2 = 120
key_val2 = 0
mode_val2 = 0
#  time.monotonic for running the modes
run = 0
#  state for being on/off
run_state = False
#  indexes for modes
r = 0
b = 0
f = 0
p = 0
maj = 0
mi = 0
random = 0
#  mode states
play_pedal = False
play_fifths = False
play_maj = False
play_min = False
play_rando = False
play_scale = True
#  state for random beat division
rando = False
#  comparitors for states
last_r = 0
last_f = 0
last_maj = 0
last_min = 0
last_p = 0
last_random = 0
#  index for random beat division
hit = 0
#  default tempo
tempo = 60
#  beat division
sixteenth = 15 / tempo
eighth = 30 / tempo
quarter = 60 / tempo
half = 120 / tempo
whole = 240 / tempo
#  time.monotonic for blinka animation
slither = 0
#  blinka animation sprite index
g = 1

#  array for random beat division values
rando_div = [240, 120, 60, 30, 15]
#  array of beat division values
beat_division = [whole, half, quarter, eighth, sixteenth]
#  strings for beat division names
beat_division_name = ["1", "1/2", "1/4", "1/8", "1/16", "Random"]

while True:
    #  mapping analog pot values to the different parameters
    #  MIDI modulation 0-127
    mod_val1 = round(simpleio.map_range(val(mod_pot), 0, 65535, 0, 127))
    #  BPM range 60-220
    bpm_val1 = simpleio.map_range(val(bpm_slider), 0, 65535, 60, 220)
    #  6 options for beat division
    beat_val1 = round(simpleio.map_range(val(beat_pot), 0, 65535, 0, 5))
    #  12 options for key selection
    key_val1 = round(simpleio.map_range(val(key_pot), 0, 65535, 0, 11))
    #  6 options for mode selection
    mode_val1 = round(simpleio.map_range(val(mode_pot), 0, 65535, 0, 5))

    #  sending MIDI modulation
    if abs(mod_val1 - mod_val2) > 2:
        #  updates previous value to hold current value
        mod_val2 = mod_val1
        #  MIDI data has to be sent as an integer
        #  this converts the pot data into an int
        modulation = int(mod_val2)
        #  int is stored as a CC message
        modWheel = ControlChange(1, modulation)
        #  CC message is sent
        midi.send(modWheel)
        print(modWheel)
        #  delay to settle MIDI data
        time.sleep(0.001)

    #  sets beat division
    if abs(beat_val1 - beat_val2) > 0:
        #  updates previous value to hold current value
        beat_val2 = beat_val1
        print("beat div is", beat_val2)
        #  updates display
        beat_text_area.text = "Div:%s" % beat_division_name[beat_val2]
        #  sets random beat division state
        if beat_val2 == 5:
            rando = True
        else:
            rando = False
        time.sleep(0.001)

    #  mode selection
    if abs(mode_val1 - mode_val2) > 0:
        #  updates previous value to hold current value
        mode_val2 = mode_val1
        #  scale mode
        if mode_val2 == 0:
            play_scale = True
            play_maj = False
            play_min = False
            play_fifths = False
            play_pedal = False
            play_rando = False
            #  updates display
            mode_text_area.text = "Mode:Scale"
            print("scale")
        #  major triads mode
        if mode_val2 == 1:
            play_scale = False
            play_maj = True
            play_min = False
            play_fifths = False
            play_pedal = False
            play_rando = False
            print("major chords")
            #  updates display
            mode_text_area.text = "Mode:MajorTriads"
        #  minor triads mode
        if mode_val2 == 2:
            play_scale = False
            play_maj = False
            play_min = True
            play_fifths = False
            play_pedal = False
            play_rando = False
            print("minor")
            #  updates display
            mode_text_area.text = "Mode:MinorTriads"
        #  fifths mode
        if mode_val2 == 3:
            play_scale = False
            play_maj = False
            play_min = False
            play_fifths = True
            play_pedal = False
            play_rando = False
            print("fifths")
            #  updates display
            mode_text_area.text = "Mode:Fifths"
        #  pedal tone mode
        if mode_val2 == 4:
            play_scale = False
            play_maj = False
            play_min = False
            play_fifths = False
            play_pedal = True
            play_rando = False
            print("play random")
            #  updates display
            mode_text_area.text = 'Mode:Pedal'
        #  random mode
        if mode_val2 == 5:
            play_scale = False
            play_maj = False
            play_min = False
            play_fifths = False
            play_pedal = False
            play_rando = True
            print("play random")
            #  updates display
            mode_text_area.text = 'Mode:Random'
        time.sleep(0.001)

    #  key selection
    if abs(key_val1 - key_val2) > 0:
        #  updates previous value to hold current value
        key_val2 = key_val1
        #  indexes the notes in each key array
        for k in keys:
            o = keys.index(k)
            octave = keys[o]
        #  updates display
        key_text_area.text = 'Key:%s' % key_names[key_val2]
        print("o is", o)
        time.sleep(0.001)

    #  BPM adjustment
    if abs(bpm_val1 - bpm_val2) > 1:
        #  updates previous value to hold current value
        bpm_val2 = bpm_val1
        #  updates tempo
        tempo = int(bpm_val2)
        #  updates calculations for beat division
        sixteenth = 15 / tempo
        eighth = 30 / tempo
        quarter = 60 / tempo
        half = 120 / tempo
        whole = 240 / tempo
        #  updates array of beat divisions
        beat_division = [whole, half, quarter, eighth, sixteenth]
        #  updates display
        bpm_text_area.text = "BPM:%d" % tempo
        print("tempo is", tempo)
        time.sleep(0.05)

    #  if the run switch is pressed:
    if run_switch.value:
        run_state = True
        #  if random beat division, then beat_division index is randomized with index hit
        if rando:
            divide = beat_division[hit]
        #  if not random, then beat_division is the value of the pot
        else:
            divide = beat_division[beat_val2]
        #  blinka animation in time with BPM and beat division
        #  she will slither every time a note is played
        if (time.monotonic() - slither) >= divide:
            blinka_grid[0] = g
            g += 1
            slither = time.monotonic()
            if g > 2:
                g = 1
        #  holds key index
        octave = keys[key_val2]
        #  fifths mode
        if play_fifths:
            #  tracks time divided by the beat division
            if (time.monotonic() - run) >= divide:
                #  note index from mode, r counts index position
                f = fifths[r]
                #  sends NoteOn
                midi.send(NoteOn(octave[f]))
                #  turns previous note off
                midi.send(NoteOff(octave[last_f]))
                #  print(octave[r])
                run = time.monotonic()
                #  go to next note
                r += 1
                #  updates previous value to hold current value
                if r > 0:
                    last_r = r
                    last_f = f
                    hit = randint(2, 4)
                #  resets note index position
                if r > 7:
                    r = 0
                    last_r = r
                    last_f = f
                    hit = randint(2, 4)
        #  major triad mode
        if play_maj:
            #  tracks time divided by the beat division
            if (time.monotonic() - run) >= divide:
                #  note index from mode, r counts index position
                maj = major[r]
                #  sends NoteOn
                midi.send(NoteOn(octave[maj]))
                #  turns previous note off
                midi.send(NoteOff(octave[last_maj]))
                #  print(octave[r])
                run = time.monotonic()
                #  go to next note
                r += 1
                #  updates previous value to hold current value
                if r > 0:
                    last_r = r
                    last_maj = maj
                    hit = randint(2, 4)
                #  resets note index position
                if r > 7:
                    r = 0
                    last_r = r
                    last_maj = maj
                    hit = randint(2, 4)
        #  minor triad mode
        if play_min:
            #  tracks time divided by the beat division
            if (time.monotonic() - run) >= divide:
                #  note index from mode, r counts index position
                mi = minor[r]
                #  sends NoteOn
                midi.send(NoteOn(octave[mi]))
                #  turns previous note off
                midi.send(NoteOff(octave[last_min]))
                #  print(octave[r])
                run = time.monotonic()
                #  go to next note
                r += 1
                #  updates previous value to hold current value
                if r > 0:
                    last_r = r
                    last_min = mi
                    hit = randint(2, 4)
                #  resets note index position
                if r > 7:
                    r = 0
                    last_r = r
                    last_min = mi
                    hit = randint(2, 4)
        #  pedal tone mode
        if play_pedal:
            #  tracks time divided by the beat division
            if (time.monotonic() - run) >= divide:
                #  note index from mode, r counts index position
                p = pedal[r]
                #  sends NoteOn
                midi.send(NoteOn(octave[p]))
                #  turns previous note off
                midi.send(NoteOff(octave[last_p]))
                #  print(octave[r])
                run = time.monotonic()
                #  go to next note
                r += 1
                #  updates previous value to hold current value
                if r > 0:
                    last_r = r
                    last_p = p
                    hit = randint(2, 4)
                #  resets note index position
                if r > 7:
                    r = 0
                    last_r = r
                    last_p = p
                    hit = randint(2, 4)
        #  random note mode
        if play_rando:
            #  randomizes note indexes in key
            r = randint(0, 7)
            #  tracks time divided by the beat division
            if (time.monotonic() - run) >= divide:
                #  sends NoteOn
                midi.send(NoteOn(octave[r]))
                #  turns previous note off
                midi.send(NoteOff(octave[last_r]))
                #  print(octave[r])
                run = time.monotonic()
                #  updates previous value to hold current value
                if r > 0:
                    last_r = r
                    r = randint(0, 7)
                    hit = randint(2, 4)
        #  scale mode
        if play_scale:
            #  tracks time divided by the beat division
            if (time.monotonic() - run) >= divide:
                #  sends NoteOn
                midi.send(NoteOn(octave[r]))
                #  turns previous note off
                midi.send(NoteOff(octave[last_r]))
                #  print(octave[r])
                run = time.monotonic()
                #  go to next note
                r += 1
                #  updates previous value to hold current value
                if r > 0:
                    last_r = r
                    hit = randint(2, 4)
                #  resets note index position
                if r > 7:
                    r = 0
                    last_r = r
    if not run_switch.value:
        if run_state:
            all_note_off = ControlChange(123, 0)
            #  CC message is sent
            midi.send(all_note_off)
            run_state = False
            time.sleep(0.001)

    #  delay to settle MIDI data
    time.sleep(0.005)
