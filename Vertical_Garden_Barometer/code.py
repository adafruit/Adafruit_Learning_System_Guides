"""
Read the barometric reading in the air
Visualize air reading changes over time as a color animation on a NeoPixel strip
Display a "sinking" or "rising" graphic on the screen along with recent reading data

Code by Erin St Blaine for Adafruit Industries :)
"""
import time
import board
import neopixel
from adafruit_clue import clue
import adafruit_fancyled.adafruit_fancyled as fancy
import displayio
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font

num_leds = 79 #number of LEDs in your strip
timeToCheck = 23400 # set the amount of time between sensor checks. 7800 is approx. 1 hour

# Barometer or Thermometer? Uncomment the section you want to use

#BAROMETER RANGES (hPa)
#set desired reading range -- the NeoPixel palette choice will be determined by these thresholds
deviceType = 0
min_reading = 960
med_reading = 965
high_reading= 970
max_reading = 975

"""
# THERMOMETER RANGES (C)
# set desired temperature range - NeoPixel palette choice determined by these thresholds
deviceType = 1
min_reading = 25
med_reading = 26
high_reading= 27
max_reading = 28
"""

# get an initial sensor reading
if deviceType ==0:
    reading = clue.pressure
else:
    reading = clue.temperature

#set up variables for "remembering" past readings
reading1 = reading
reading2 = reading1
reading3 = reading2
counter = 0
toggle = 1  # for on/off switch on button A
displayOn = 1  # to turn the display on and off with button B
button_b_pressed = False
button_a_pressed = False

clue.display.brightness = 0.8
clue_display = displayio.Group()

# draw the rising image
# CircuitPython 6 & 7 compatible
rising_file = open("rising.bmp", "rb")
rising_bmp = displayio.OnDiskBitmap(rising_file)
rising_sprite = displayio.TileGrid(rising_bmp, pixel_shader=getattr(rising_bmp, 'pixel_shader', displayio.ColorConverter()))

# # CircuitPython 7+ compatible
# rising_bmp = displayio.OnDiskBitmap("rising.bmp")
# rising_sprite = displayio.TileGrid(rising_bmp, pixel_shader=rising_bmp.pixel_shader)

clue_display.append(rising_sprite)

# draw the sinking image
# CircuitPython 6 & 7 compatible
sinking_file = open("sinking.bmp", "rb")
sinking_bmp = displayio.OnDiskBitmap(sinking_file)
sinking_sprite = displayio.TileGrid(sinking_bmp, pixel_shader=getattr(sinking_bmp, 'pixel_shader', displayio.ColorConverter()))

# # CircuitPython 7+ compatible
# sinking_bmp = displayio.OnDiskBitmap("sinking.bmp")
# sinking_sprite = displayio.TileGrid(sinking_bmp, pixel_shader=sinking_bmp.pixel_shader)

clue_display.append(sinking_sprite)

# Create text
# first create the group
text_group = displayio.Group()
# Make a label
reading_font = bitmap_font.load_font("/font/RacingSansOne-Regular-29.bdf")
reading_font.load_glyphs("0123456789ADSWabcdefghijklmnopqrstuvwxyz:!".encode('utf-8'))
reading_label = label.Label(reading_font, color=0xffffff)
reading_label.x = 10
reading_label.y = 24
text_group.append(reading_label)

reading2_label = label.Label(reading_font, color=0xdaf5f4)
reading2_label.x = 10
reading2_label.y = 54
text_group.append(reading2_label)

reading3_label = label.Label(reading_font, color=0x4f3ab1)
reading3_label.x = 10
reading3_label.y = 84
text_group.append(reading3_label)

timer_label = label.Label(reading_font, color=0x072170)
timer_label.x = 10
timer_label.y = 114
text_group.append(timer_label)

clue_display.append(text_group)
clue.display.show(clue_display)

# Define color Palettes
waterPalette = [0x00d9ff, 0x006f82, 0x43bfb9, 0x0066ff]
icePalette = [0x8080FF, 0x8080FF, 0x8080FF, 0x0000FF, 0xC88AFF]
sunPalette = [0xffaa00, 0xffdd00, 0x7d5b06, 0xfffca8]
firePalette = [0xff0000, 0xff5500, 0x8a3104, 0xffaa00 ]
forestPalette = [0x76DB00, 0x69f505, 0x05f551, 0x3B6D00]

# set up default initial palettes, just for startup
palette = forestPalette
palette2 = waterPalette
palette3 = icePalette

# Declare a NeoPixel object on pin A4 with num_leds pixels, no auto-write.
# Set brightness to max because we'll be using FancyLED's brightness control.
pixels = neopixel.NeoPixel(board.A4, num_leds, brightness=1.0,
                           auto_write=False)

offset = 0  # Positional offset into color palette to get it to 'spin'

while True:
    # use button A to toggle the NeoPixels on or off by changing brightness
    if clue.button_a and not button_a_pressed:  # If button A pressed...
        print("Button A pressed.")
        if toggle == 1:
            toggle = 0
            pixels.brightness = 0
            clue.display.brightness = 0
        elif toggle == 0:
            toggle = 1
            pixels.brightness = 1.0
            clue.display.brightness = 0.8
        button_a_pressed = True  # Set to True.
        time.sleep(0.03)  # Debounce.
    if not clue.button_a and button_a_pressed:  # On button release...
        button_a_pressed = False  # Set to False.
        time.sleep(0.03)  # Debounce.
    if clue.button_b and not button_b_pressed:  # If button B pressed...
        print("Button B pressed.")
        # Toggle only the display on and off
        if displayOn == 0:
            clue.display.brightness = 0.8
            displayOn = 1
        else:
            clue.display.brightness = 0
            displayOn = 0
        button_b_pressed = True  # Set to True.
        time.sleep(0.03)  # Debounce.
    if not clue.button_b and button_b_pressed:  # On button release...
        button_b_pressed = False  # Set to False.
        time.sleep(0.03)  # Debounce.

    # assign color palette to NeoPixel section 1 based on the current reading reading
    if reading1 < min_reading:
        palette = firePalette
    elif min_reading > reading1 > med_reading:
        palette = sunPalette
    elif med_reading > reading1 > high_reading:
        palette = forestPalette
    elif high_reading > reading1 > max_reading:
        palette = waterPalette
    else:
        palette = icePalette
    # Map colors to pixels. Adjust range numbers to light up specific pixels. This configuration
    # maps to a reflected gradient, with pixel 0 in the upper left corner
    # Load each pixel's color from the palette using an offset, run it
    # through the gamma function, pack RGB value and assign to pixel.
    for i in range(23, 31):  #center right -- present moment
        color = fancy.palette_lookup(palette, offset + i / num_leds)
        color = fancy.gamma_adjust(color, brightness=0.25)
        pixels[i] = color.pack()

    for i in range(63, 71): #center left -- present moment
        color = fancy.palette_lookup(palette, offset + i / num_leds)
        color = fancy.gamma_adjust(color, brightness=0.25)
        pixels[i] = color.pack()

    for i in range(16, 23): #top mid right  -- 1 cycle ago
        color = fancy.palette_lookup(palette2, offset + i / num_leds)
        color = fancy.gamma_adjust(color, brightness=0.25)
        pixels[i] = color.pack()

    for i in range(71, 78): #top mid left  -- 1 cycle ago
        color = fancy.palette_lookup(palette2, offset + i / num_leds)
        color = fancy.gamma_adjust(color, brightness=0.25)
        pixels[i] = color.pack()

    for i in range(31, 38): #bottom mid right  -- 1 cycle ago
        color = fancy.palette_lookup(palette2, offset + i / num_leds)
        color = fancy.gamma_adjust(color, brightness=0.25)
        pixels[i] = color.pack()

    for i in range(56, 63): #bottom mid left  -- 1 cycle ago
        color = fancy.palette_lookup(palette2, offset + i / num_leds)
        color = fancy.gamma_adjust(color, brightness=0.25)
        pixels[i] = color.pack()

    for i in range(0, 16): #top right  -- 2 cycles ago
        color = fancy.palette_lookup(palette3, offset + i / num_leds)
        color = fancy.gamma_adjust(color, brightness=0.25)
        pixels[i] = color.pack()

    for i in range(77, 79): #top left  -- 2 cycles ago
        color = fancy.palette_lookup(palette3, offset + i / num_leds)
        color = fancy.gamma_adjust(color, brightness=0.25)
        pixels[i] = color.pack()

    for i in range(38, 56): #bottom  -- 2 cycles ago
        color = fancy.palette_lookup(palette3, offset + i / num_leds)
        color = fancy.gamma_adjust(color, brightness=0.25)
        pixels[i] = color.pack()

    pixels.show()
    offset += 0.01  # Bigger number = faster spin

    reading_label.text = "Now  {:.1f}".format(reading1)
    reading2_label.text = "Last  {:.1f}".format(reading2)
    reading3_label.text = "Prev  {:.1f}".format(reading3)
    timer_label.text = "{}".format(counter)
    clue.display.show(clue_display)

    # Is it time to update?
    if counter > timeToCheck:
        # This moves the current data to the "1 hour old" section of pixels and the "1 hour old"
        # data to the "2 hours old" section of pixels
        palette3 = palette2
        palette2 = palette
        reading3 = reading2
        reading2 = reading1
        reading1 = reading
        # take a new sensor reading and reset the counter
        if deviceType == 0:
            reading = clue.pressure
        else:
            reading = clue.temperature
        counter = 0
        # if reading is rising, show rising image and position text at the bottom
        if reading1 > reading2:
            sinking_sprite.x = 300
            reading_label.y = 134
            reading2_label.y = 164
            reading3_label.y = 194
            timer_label.y = 224
        # if reading is falling, show sinking image and position text at the top
        elif reading1 < reading2:  #reading is falling
            sinking_sprite.x = 0
            reading_label.y = 24
            reading2_label.y = 54
            reading3_label.y = 84
            timer_label.y = 114
    # otherwise keep counting up
    else:
        counter = counter + 1
