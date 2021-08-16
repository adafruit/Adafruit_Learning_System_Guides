import board
import displayio
import digitalio
from adafruit_st7789 import ST7789
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
import usb_midi
import adafruit_midi
from adafruit_midi.note_on          import NoteOn
from adafruit_midi.note_off         import NoteOff

#  if you want to use this as an HID keyboard, set keyboard_mode to True
#  otherwise, set it to False
keyboard_mode = True
#  if you want to use this as a MIDI keyboard, set midi_mode to True
#  otherwise, set it to False
midi_mode = False

#  change keyboard shortcuts here
#  defaults are shortcuts for save, cut, copy & paste
#  comment out ctrl depending on windows or macOS
if keyboard_mode:
    keyboard = Keyboard(usb_hid.devices)
    #  modifier for windows
    ctrl = Keycode.CONTROL
    #  modifier for macOS
    #  ctrl = Keycode.COMMAND
    key0 = Keycode.S
    key1 = Keycode.X
    key2 = Keycode.C
    key3 = Keycode.V
    shortcuts = [key0, key1, key2, key3]

#  change MIDI note numbers here
if midi_mode:
    midi = adafruit_midi.MIDI(midi_out=usb_midi.ports[1], out_channel=0)
    midi_notes = [60, 61, 62, 63]

# Release any resources currently in use for the displays
displayio.release_displays()

#  spi display setup
spi = board.SPI()
tft_cs = board.D7
tft_dc = board.D5

display_bus = displayio.FourWire(
    spi, command=tft_dc, chip_select=tft_cs, reset=board.D6
)

#  display setup
display = ST7789(display_bus, width=240, height=240, rowstart=80)

# CircuitPython 6 & 7 compatible
#  bitmap setup
bitmap = displayio.OnDiskBitmap(open("/parrot-240-sheet.bmp", "rb"))

# Create a TileGrid to hold the bitmap
parrot0_grid = displayio.TileGrid(bitmap, pixel_shader=getattr(bitmap, 'pixel_shader', displayio.ColorConverter()),
                                 tile_height=240, tile_width=240)

# # CircuitPython 7+ compatible
# bitmap = displayio.OnDiskBitmap("/parrot-240-sheet.bmp")

# Create a TileGrid to hold the bitmap
# parrot0_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader,
#                                tile_height=240, tile_width=240)

# Create a Group to hold the TileGrid
group = displayio.Group()

# Add the TileGrid to the Group
group.append(parrot0_grid)

# Add the Group to the Display
display.show(group)

#  digital pins for the buttons
key_pins = [board.A0, board.A1, board.A2, board.A3]

#  array for buttons
keys = []

#  setup buttons as inputs
for key in key_pins:
    key_pin = digitalio.DigitalInOut(key)
    key_pin.direction = digitalio.Direction.INPUT
    key_pin.pull = digitalio.Pull.UP
    keys.append(key_pin)

p = 0 #  variable for tilegrid index
a = 0 #  variable for tile position

#  states for buttons
key0_pressed = False
key1_pressed = False
key2_pressed = False
key3_pressed = False

#  array for button states
key_states = [key0_pressed, key1_pressed, key2_pressed, key3_pressed]

while True:
    #  default tile grid position
    parrot0_grid[a] = p

    #  iterate through 4 buttons
    for i in range(4):
        inputs = keys[i]
        #  if button is pressed...
        if not inputs.value and key_states[i] is False:
            #  tile grid advances by 1 frame
            p += 1
            #  update button state
            key_states[i] = True
            #  if a midi keyboard...
            if midi_mode:
                #  send NoteOn for corresponding MIDI note
                midi.send(NoteOn(midi_notes[i], 120))
            #  if an HID keyboard...
            if keyboard_mode:
                #  send keyboard output for corresponding keycode
                #  the default includes a modifier along with the keycode
                keyboard.send(ctrl, shortcuts[i])
            #  if the tile grid's index is at 9...
            if p > 9:
                #  reset the index to 0
                p = 0
        #  if the button is released...
        if inputs.value and key_states[i] is True:
            #  update button state
            key_states[i] = False
            #  if a midi keyboard...
            if midi_mode:
                #  send NoteOff for corresponding MIDI note
                midi.send(NoteOff(midi_notes[i], 120))
