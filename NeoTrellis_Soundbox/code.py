# NeoTrellis Soundbox Remix - CircuitPython
# Noe and Pedro Ruiz, code by Mike Barela
# for Adafruit Industries, MIT License

import time
import os
import random
import board
from board import SCL, SDA
import digitalio
import busio
import audioio
import adafruit_rgbled
from adafruit_neotrellis.neotrellis import NeoTrellis
import adafruit_lis3dh

# Color definitions
OFF = (0, 0, 0)
RED = (25, 0, 0)
YELLOW = (25, 15, 0)
GREEN = (0, 25, 0)
CYAN = (0, 25, 25)
BLUE = (0, 0, 25)
PURPLE = (18, 0, 25)
WHITE = (127, 127, 127)

# Create the i2c object for the trellis
# If you get an error, your PropMaker Shield needs to be snappped on
i2c_bus = busio.I2C(SCL, SDA)

# Create the trellis
trellis = NeoTrellis(i2c_bus)

print("NeoTrellis created")

# Enable PWR Pin to enable NeoPixels, audio amplifier and RGB LED
# See https://learn.adafruit.com/adafruit-prop-maker-featherwing/pinouts
enable = digitalio.DigitalInOut(board.D10)
enable.direction = digitalio.Direction.OUTPUT
enable.value = True

# Set up RGB for switch RGB LED
RED_LED = board.D11
GREEN_LED = board.D12
BLUE_LED = board.D13
led = adafruit_rgbled.RGBLED(RED_LED, GREEN_LED, BLUE_LED)
led.color = GREEN

# Enable button use on PropMaker Wing Switch input
push_switch = digitalio.DigitalInOut(board.D9)
push_switch.switch_to_input(pull=digitalio.Pull.UP)

# Set up Accelerometer on I2C bus
int1 = digitalio.DigitalInOut(board.D5)
accel = adafruit_lis3dh.LIS3DH_I2C(i2c_bus, int1=int1)
# See https://circuitpython.readthedocs.io/projects/lis3dh/en/
#  latest/api.html for adjusting settings for the accelerometer
accel.range = adafruit_lis3dh.RANGE_4_G
# accel.set_tap(1, 80)  # Single tap, second value is sensitivity

# Set up playing audio on A0 and interruptable playing
myaudio = audioio.AudioOut(board.A0)
audio_file = None

def play_file(audio_filename):
    global audio_file  # pylint: disable=global-statement
    if myaudio.playing:
        myaudio.stop()
    if audio_file:
        audio_file.close()
    audio_file = open("/sounds/"+audio_filename, "rb")
    wav = audioio.WaveFile(audio_file)
    print("Playing "+audio_filename+".")
    myaudio.play(wav)

# Process wav files in the flash drive sounds directory
wavefiles = [file for file in os.listdir("/sounds/")
             if (file.endswith(".wav") and not file.startswith("._"))]
if len(wavefiles) < 1:
    print("No wav files found in sounds directory")
else:
    print("Audio files found: ", wavefiles)

PUSH_COLOR = GREEN
ANIM_COLOR = WHITE

COLORS = ["RED", "YELLOW", "GREEN", "CYAN", "BLUE", "PURPLE", "WHITE"]
COLOR_TUPLES = [RED, YELLOW, GREEN, CYAN, BLUE, PURPLE, WHITE]

buttons = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
button_colors = [OFF, OFF, OFF, OFF, OFF, OFF, OFF, OFF,
                 OFF, OFF, OFF, OFF, OFF, OFF, OFF, OFF]
shuffled_colors = list(button_colors)
Shuffled = False

# Time to process the filenames using the special file name syntax
# Currently nn-color-name.wav where nn = 2 digit number 0 to 15
# color is lower or upper case color name from above and
# name can be anything. BUT these all must be separated by a "-"
# Example 02-blue-firetruck.wav is valid. Note leading 0 for 0 to 9
wavnames = ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
shuffled_names = list(wavnames)  # Duplicate list, wavnames is our reference
shuffled = False
for soundfile in wavefiles:
    print("Processing "+soundfile)
    pos = int(soundfile[0:2])
    if pos >= 0 and pos < 16:      # Valid filenames start with 00 to 15
        wavnames[pos] = soundfile  # Store soundfile in proper index
        shuffled_names[pos] = soundfile
        skip = soundfile[3:].find('-') + 3
        user_color = soundfile[3:skip].upper()  # Detect file color
        print("For file "+soundfile+", color is "+user_color+".")
        file_color = COLOR_TUPLES[COLORS.index(user_color)]
        button_colors[pos] = file_color
        shuffled_colors[pos] = file_color
    else:
        print("Filenames must start with a number from 00 to 15 - "+soundfile)

# this will be called when button events are received
def blink(event):
    # turn the LED on when a rising edge is detected
    if event.edge == NeoTrellis.EDGE_RISING:  # Trellis button pushed
        print("Button "+str(event.number)+" pushed")
        if event.number > 15:
            print("Event number out of range: ", event.number)
        trellis.pixels[event.number] = WHITE
        if shuffled_names[event.number] != "":
            play_file(shuffled_names[event.number])

    # turn the LED off when a rising edge is detected (button released)
    elif event.edge == NeoTrellis.EDGE_FALLING:
        trellis.pixels[event.number] = shuffled_colors[event.number]

for i in range(16):
    # activate rising edge events on all keys
    trellis.activate_key(i, NeoTrellis.EDGE_RISING)
    # activate falling edge events on all keysshuff
    trellis.activate_key(i, NeoTrellis.EDGE_FALLING)
    # set all keys to trigger the blink callback
    trellis.callbacks[i] = blink

    # cycle the LEDs on startup
    trellis.pixels[i] = ANIM_COLOR
    time.sleep(.05)

# On start, set the pixels on trellis to the file name colors chosen
for i in range(16):
    trellis.pixels[i] = shuffled_colors[i]
    time.sleep(.05)

while True:
    # call the sync function call any triggered callbacks
    trellis.sync()

    # Check push switch, reset trellis buttons randomization if pressed
    if not push_switch.value:
        myaudio.stop()  # Stop any audio playing
        print("RGB Switch Push - reset shuffle if needed")
        shuffled_names = list(wavnames)     # Reset with clean lists
        shuffled_colors = list(button_colors)
        for i in range(16):
            trellis.pixels[i] = shuffled_colors[i]
            time.sleep(.05)
        Shuffled = False
        led.color = GREEN
    # Check accelerometer
    if accel.shake(shake_threshold=15):   # Change shake(val) to tapped
        myaudio.stop()  # Stop any audio playing
        print("Unit Tapped - shuffle sound files to random buttons")
        shuffled_names = list(wavnames)       # Copy lists
        shuffled_colors = list(button_colors)
        for i in range(len(wavnames)):  # Do the shuffling
            random_i = random.randrange(len(wavnames))
            # Swap current name with a random slot
            name = shuffled_names[random_i]
            shuffled_names[random_i] = shuffled_names[i]
            shuffled_names[i] = name
            number = shuffled_colors[random_i]
            shuffled_colors[random_i] = shuffled_colors[i]
            shuffled_colors[i] = number
        for i in range(16):
            trellis.pixels[i] = shuffled_colors[i]
            time.sleep(.05)
        print(shuffled_names)
        print(shuffled_colors)
        shuffled = True
        led.color = RED
    # the trellis can only be read every 17 milliseconds or so
    time.sleep(.019)
