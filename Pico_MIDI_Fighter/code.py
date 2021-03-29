import time
import board
import displayio
import terminalio
import adafruit_aw9523
import busio
import adafruit_ssd1327
import digitalio
from adafruit_display_text import label
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.rect import Rect
import usb_midi
import adafruit_midi
from adafruit_midi.note_on          import NoteOn
from adafruit_midi.note_off         import NoteOff

displayio.release_displays()

# i2c setup, higher frequency for display refresh
i2c = busio.I2C(board.GP1, board.GP0, frequency=1000000)
#  i2c display setup
display_bus = displayio.I2CDisplay(i2c, device_address=0x3D)
#  i2c AW9523 GPIO expander setup
aw = adafruit_aw9523.AW9523(i2c)
#  MIDI setup as MIDI out device
midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)

# display dimensions
WIDTH = 128
HEIGHT = 128
#  display setup
display = adafruit_ssd1327.SSD1327(display_bus, width=WIDTH, height=HEIGHT, brightness = 0.01)

#  main display group, shows default GUI menu
splash = displayio.Group(max_size=60)
#  group for circle icons
circle_group = displayio.Group(max_size=30)
#  group for text labels on circles
text_group = displayio.Group(max_size=30)

#  list of circle positions
spots = (
    (16, 16),
    (48, 16),
    (80, 16),
    (112, 16),
    (16, 48),
    (48, 48),
    (80, 48),
    (112, 48),
    (16, 80),
    (48, 80),
    (80, 80),
    (112, 80),
    (16, 112),
    (48, 112),
    (80, 112),
    (112, 112),
    )

#  creating the circles & pulling in positions from spots
for spot in spots:
    circle = Circle(x0=spot[0], y0=spot[1], r=14, fill=0x888888)
	#  adding circles to their display group
    circle_group.append(circle)
#  square to show position on menu
rect = Rect(0, 0, 33, 33, fill=None, outline=0x00FF00, stroke = 3)

splash.append(circle_group)
splash.append(rect)

#  strings and positions for the MIDI note text labels
texts = [
    {'num': "60", 'pos': (12, 16)},
    {'num': "61", 'pos': (44, 16)},
    {'num': "62", 'pos': (76, 16)},
    {'num': "63", 'pos': (108, 16)},
    {'num': "64", 'pos': (12, 48)},
    {'num': "65", 'pos': (44, 48)},
    {'num': "66", 'pos': (76, 48)},
    {'num': "67", 'pos': (108, 48)},
    {'num': "68", 'pos': (12, 80)},
    {'num': "69", 'pos': (44, 80)},
    {'num': "70", 'pos': (76, 80)},
    {'num': "71", 'pos': (108, 80)},
    {'num': "72", 'pos': (12, 112)},
    {'num': "73", 'pos': (44, 112)},
    {'num': "74", 'pos': (76, 112)},
    {'num': "75", 'pos': (108, 112)},
    ]
text_labels = []

for text in texts:
    text_area = label.Label(terminalio.FONT, text=text['num'], color=0xFFFFFF)
    text_area.x = text['pos'][0]
    text_area.y = text['pos'][1]
    text_labels.append(text_area)
    text_group.append(text_area)
splash.append(text_group)

#  secondary display group, shows large circle when button is selected
big_splash = displayio.Group(max_size=60)
#  large circle to fill display
big_circle = Circle(x0=64, y0=64, r=62, fill=0x888888)
big_splash.append(big_circle)
#  large text to fill circle
big_text = label.Label(terminalio.FONT, text='   ', color=0xFFFFFF)
big_text.x = 43
big_text.y = 62
big_text.scale = 4
big_splash.append(big_text)

#  array for LEDs on AW9523
leds = []
led_pins = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
#  setup to create the AW9523 outputs for LEDs
for led in led_pins:
    led_pin = aw.get_pin(led)
    led_pin.direction = digitalio.Direction.OUTPUT
    leds.append(led_pin)



#  button pins, all pins in order skipping GP15
note_pins = [board.GP7, board.GP8, board.GP9, board.GP10, board.GP11,
             board.GP12, board.GP13, board.GP14, board.GP16, board.GP17,
             board.GP18, board.GP19, board.GP20, board.GP21, board.GP22, board.GP26]

note_buttons = []

for pin in note_pins:
    note_pin = digitalio.DigitalInOut(pin)
    note_pin.direction = digitalio.Direction.INPUT
    note_pin.pull = digitalio.Pull.UP
    note_buttons.append(note_pin)

#  note states
note0_pressed = False
note1_pressed = False
note2_pressed = False
note3_pressed = False
note4_pressed = False
note5_pressed = False
note6_pressed = False
note7_pressed = False
note8_pressed = False
note9_pressed = False
note10_pressed = False
note11_pressed = False
note12_pressed = False
note13_pressed = False
note14_pressed = False
note15_pressed = False
#  array of note states
note_states = [note0_pressed, note1_pressed, note2_pressed, note3_pressed,
               note4_pressed, note5_pressed, note6_pressed, note7_pressed,
               note8_pressed, note9_pressed, note10_pressed, note11_pressed,
               note12_pressed, note13_pressed, note14_pressed, note15_pressed]
#  pins for 5-way switch
select = digitalio.DigitalInOut(board.GP6)
up = digitalio.DigitalInOut(board.GP5)
down = digitalio.DigitalInOut(board.GP4)
left = digitalio.DigitalInOut(board.GP3)
right = digitalio.DigitalInOut(board.GP2)
#  array for 5-way switch
joystick = [select, up, down, left, right]

for joy in joystick:
    joy.direction = digitalio.Direction.INPUT
    joy.pull = digitalio.Pull.UP
#  states for 5-way switch
select_state = None
up_state = None
down_state = None
left_state = None
right_state = None
midi_state = None

#  coordinates for navigating main GUI
select_x = [0, 32, 64, 96]
select_y = [0, 32, 64, 96]

#  y coordinate for 5-way switch navigation
y_pos = 0
#  x coordinate for 5-way switch navigation
x_pos = 0
sub_state = False
#  default midi number
midi_num = 60
#  default MIDI button
button_num = 0
#  default MIDI button position
button_pos = 0
#  check for blinking LED
led_check = None
#  time.monotonic() device
clock = time.monotonic()

#  coordinates for tracking location of 5-way switch
up_scroll = 0
down_scroll = 0
left_scroll = 0
right_scroll = 0
switch_coordinates = [(0, 0), (1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1), (3, 1), (0, 2),
            (1, 2), (2, 2), (3, 2), (0, 3), (1, 3), (2, 3), (3, 3)]

#  array of default MIDI notes
midi_notes = [60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75]

#  show main display GUI
display.show(splash)

while True:

    #  debouncing for 5-way switch positions
    if up.value and up_state == "pressed":
        print("Button pressed.")
        up_state = None
    if down.value and down_state == "pressed":
        print("Button pressed.")
        down_state = None
    if left.value and left_state == "pressed":
        print("Button pressed.")
        left_state = None
    if right.value and right_state == "pressed":
        print("Button pressed.")
        right_state = None
    if select.value and select_state == "pressed":
        print("Button pressed.")
        select_state = None

    #  MIDI input
    for i in range(16):
        buttons = note_buttons[i]
        #  if button is pressed...
        if not buttons.value and note_states[i] is False:
            #  send the MIDI note and light up the LED
            midi.send(NoteOn(midi_notes[i], 120))
            note_states[i] = True
            leds[i].value = True
        #  if the button is released...
        if buttons.value and note_states[i] is True:
            #  stop sending the MIDI note and turn off the LED
            midi.send(NoteOff(midi_notes[i], 120))
            note_states[i] = False
            leds[i].value = False

    #  if we're on the main GUI page
    if not sub_state:
        #  if you press up on the 5-way switch...
        if not up.value and up_state is None:
            up_state = "pressed"
            #  track the switch's position
            up_scroll -= 1
            if up_scroll < 0:
                up_scroll = 3
            y_pos = up_scroll
            down_scroll = up_scroll
        #  if you press down on the 5-way switch...
        if not down.value and down_state is None:
            down_state = "pressed"
            #  track the switch's position
            down_scroll += 1
            if down_scroll > 3:
                down_scroll = 0
            y_pos = down_scroll
            up_scroll = down_scroll
        #  if you press left on the 5-way switch...
        if not left.value and left_state is None:
            # print("scroll", down_scroll)
            left_state = "pressed"
            #  track the switch's position
            left_scroll -= 1
            if left_scroll < 0:
                left_scroll = 3
            x_pos = left_scroll
            right_scroll = left_scroll
        #  if you press right on the 5-way switch...
        if not right.value and right_state is None:
            # print("scroll", down_scroll)
            right_state = "pressed"
            #  track the switch's position
            right_scroll += 1
            if right_scroll > 3:
                right_scroll = 0
            x_pos = right_scroll
            left_scroll = right_scroll

        #  update square's position on the GUI
        rect.y = select_y[y_pos]
        rect.x = select_x[x_pos]

        #  update the currently highlighted button on the GUI
        for coords in switch_coordinates:
            if x_pos == coords[0] and y_pos == coords[1]:
                button_pos = switch_coordinates.index(coords)
                #  print(button_pos)
        button_num = text_labels[button_pos].text

        #  if you press select on the 5-way switch...
        if not select.value and select_state is None:
            select_state = "pressed"
            #  grab the selected button's MIDI note
            midi_num = int(button_num)
            #  change into the secondary GUI menu
            sub_state = True

    #  if an arcade button is selected to change the MIDI note...
    if sub_state:
        #  display the secondary GUI menu
        display.show(big_splash)
        #  display the selected button's MIDI note
        big_text.text = str(midi_num)

        #  blink the selected button's LED without pausing the loop
        if (time.monotonic() > (clock + 1)) and led_check is None:
            leds[button_pos].value = True
            led_check = True
            clock = time.monotonic()
        if (time.monotonic() > (clock + 1)) and led_check is True:
            leds[button_pos].value = False
            led_check = None
            clock = time.monotonic()

        #  blocks the MIDI number from being set above 128
        if midi_num >= 128:
            midi_num = 128
        #  blocks the MIDI number from being set below 0
        if midi_num <= 0:
            midi_num = 0

        #  if you press right on the 5-way switch...
        if not right.value and right_state is None:
            #  increase the MIDI number
            midi_num += 1
            right_state = "pressed"
        #  if you press up on the 5-way switch...
        if not up.value and up_state is None:
            #  increase the MIDI number
            midi_num += 1
            up_state = "pressed"
        #  if you press left on the 5-way switch...
        if not left.value and left_state is None:
            #  decrease the MIDI number
            midi_num -= 1
            left_state = "pressed"
        #  if you press down on the 5-way switch...
        if not down.value and down_state is None:
            #  decrease the MIDI number
            midi_num -= 1
            down_state = "pressed"

        #  update arcade button's MIDI note
        #  allows you to check note while you're adjusting it
        midi_notes[button_pos] = midi_num

        #  if you press select on the 5-way switch...
        if not select.value and select_state is None:
            select_state = "pressed"
            #  change back to main menu mode
            sub_state = False
            #  update new MIDI number text label
            text_labels[button_pos].text = str(midi_num)
            #  show main GUI display
            display.show(splash)
            #  turn off blinking LED
            leds[button_pos].value = False
