"""Circuit Playground Express Light Paintbrush"""
# Single images only. Filename is set in code,
# CPX buttons A&B are used to increase and decrease playback speed
# Touch pad A5 to trigger playback in one-shot mode
# Switch on CPX goes from one-shot to looping mode, requires reset
# images should be 30px high, up to 100px wide, 24-bit .bmp files

import gc
import time
import board
import touchio
import digitalio
from digitalio import DigitalInOut, Direction, Pull
from neopixel_write import neopixel_write

# uncomment one line only here to select bitmap
FILENAME = "bats.bmp" # BMP file to load from flash filesystem
#FILENAME = "jpw01.bmp"
#FILENAME = "digikey.bmp"
#FILENAME = "burger.bmp"
#FILENAME = "afbanner.bmp"
#FILENAME = "blinka.bmp"
#FILENAME = "ghost.bmp"
#FILENAME = "helix-32x30.bmp"
#FILENAME = "wales2-107x30.bmp"
#FILENAME = "pumpkin.bmp"
#FILENAME = "rainbow.bmp"
#FILENAME = "rainbowRoad.bmp"
#FILENAME = "rainbowZig.bmp"
#FILENAME = "skull.bmp"
#FILENAME = "adabot.bmp"
#FILENAME = "green_stripes.bmp"
#FILENAME = "red_blue.bmp"
#FILENAME = "minerva.bmp"

TOUCH = touchio.TouchIn(board.A5) #  capacitive touch pad
SPEED = 10000
SPEED_ADJUST = 2500               # This value changes the increment for button speed adjustments
BRIGHTNESS = 1.0                  # Set brightness here, NOT in NeoPixel constructor
GAMMA = 2.7                       # Adjusts perceived brighthess linearity
NUM_PIXELS = 30                   # NeoPixel strip length (in pixels)
NEOPIXEL_PIN = board.A1           # Pin where NeoPixels are connected
DELAY_TIME = 0.01                 # Timer delay before it starts
LOOP = False                      # Set to True for looping

# button setup
button_a = DigitalInOut(board.BUTTON_A)
button_a.direction = Direction.INPUT
button_a.pull = Pull.DOWN

button_b = DigitalInOut(board.BUTTON_B)
button_b.direction = Direction.INPUT
button_b.pull = Pull.DOWN

# switch setup
switch = DigitalInOut(board.SLIDE_SWITCH)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

#status led setup
led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT


if switch.value:
    LOOP = True
else:
    LOOP = False


# Enable NeoPixel pin as output and clear the strip
NEOPIXEL_PIN = digitalio.DigitalInOut(NEOPIXEL_PIN)
NEOPIXEL_PIN.direction = digitalio.Direction.OUTPUT
neopixel_write(NEOPIXEL_PIN, bytearray(NUM_PIXELS * 3))

def read_le(value):
    """Interpret multi-byte value from file as little-endian value"""
    result = 0
    shift = 0
    for byte in value:
        result += byte << shift
        shift += 8
    return result

class BMPError(Exception):
    """Error handler for BMP-loading function"""
    pass

def load_bmp(filename):
    """Load BMP file, return as list of column buffers"""
    # pylint: disable=too-many-locals, too-many-branches
    try:
        print("Loading", filename)
        with open("/" + filename, "rb") as bmp:
            print("File opened")
            if bmp.read(2) != b'BM':  # check signature
                raise BMPError("Not BitMap file")

            bmp.read(8) # Read & ignore file size and creator bytes

            bmp_image_offset = read_le(bmp.read(4)) # Start of image data
            bmp.read(4) # Read & ignore header size
            bmp_width = read_le(bmp.read(4))
            bmp_height = read_le(bmp.read(4))
            # BMPs are traditionally stored bottom-to-top.
            # If bmp_height is negative, image is in top-down order.
            # This is not BMP canon but has been observed in the wild!
            flip = True
            if bmp_height < 0:
                bmp_height = -bmp_height
                flip = False

            print("WxH: (%d,%d)" % (bmp_width, bmp_height))

            if read_le(bmp.read(2)) != 1:
                raise BMPError("Not single-plane")
            if read_le(bmp.read(2)) != 24: # bits per pixel
                raise BMPError("Not 24-bit")
            if read_le(bmp.read(2)) != 0:
                raise BMPError("Compressed file")

            print("Image format OK, reading data...")

            row_size = (bmp_width * 3 + 3) & ~3  # 32-bit line boundary

            # Constrain rows loaded to pixel strip length
            clipped_height = min(bmp_height, NUM_PIXELS)

            # Allocate per-column pixel buffers, sized for NeoPixel strip:
            columns = [bytearray(NUM_PIXELS * 3) for _ in range(bmp_width)]

            # Image is displayed at END (not start) of NeoPixel strip,
            # this index works incrementally backward in column buffers...
            idx = (NUM_PIXELS - 1) * 3
            for row in range(clipped_height):  # For each scanline...
                if flip:  # Bitmap is stored bottom-to-top order (normal BMP)
                    pos = bmp_image_offset + (bmp_height - 1 - row) * row_size
                else:  # Bitmap is stored top-to-bottom
                    pos = bmp_image_offset + row * row_size
                bmp.seek(pos) # Start of scanline
                for column in columns: # For each pixel of scanline...
                    # BMP files use BGR color order
                    blue, green, red = bmp.read(3)
                    # Rearrange into NeoPixel strip's color order,
                    # while handling brightness & gamma correction:
                    column[idx] = int(pow(green / 255, GAMMA) * BRIGHTNESS * 255 + 0.5)
                    column[idx+1] = int(pow(red / 255, GAMMA) * BRIGHTNESS * 255 + 0.5)
                    column[idx+2] = int(pow(blue / 255, GAMMA) * BRIGHTNESS * 255 + 0.5)
                idx -= 3  # Advance (back) one pixel

            # Add one more column with no color data loaded.  This is used
            # to turn the strip off at the end of the painting operation.
            if not LOOP:
                columns.append(bytearray(NUM_PIXELS * 3))

            print("Loaded OK!")
            gc.collect()  # Garbage-collect now so playback is smoother
            return columns

    except OSError as err:
        if err.args[0] == 28:
            raise OSError("OS Error 28 0.25")
        else:
            raise OSError("OS Error 0.5")
    except BMPError as err:
        print("Failed to parse BMP: " + err.args[0])


# Load BMP image, return 'columns' array:
COLUMNS = load_bmp(FILENAME)

print("Mem free:", gc.mem_free())

COLUMN_DELAY = SPEED / 65535.0 / 10.0  # 0.0 to 0.1 seconds
# print(COLUMN_DELAY)

led.value = True

while LOOP:
    for COLUMN in COLUMNS:
        neopixel_write(NEOPIXEL_PIN, COLUMN)
        time.sleep(COLUMN_DELAY)

while True:

    # Wait for touch pad input:
    # buttons increase and decrease speed of playback
    while not TOUCH.value:
        if button_a.value:
            if SPEED >= SPEED_ADJUST:
                led.value = False
                SPEED = SPEED - SPEED_ADJUST
                COLUMN_DELAY = SPEED / 65535.0 / 10.0  # 0.0 to 0.1 seconds
                time.sleep(0.25)  #debounce
                led.value = True
                # print(SPEED)
        if button_b.value:
            if SPEED < 100000:
                led.value = False
                SPEED = SPEED + SPEED_ADJUST
                COLUMN_DELAY = SPEED / 65535.0 / 10.0  # 0.0 to 0.1 seconds
                time.sleep(0.25)  #debounce
                led.value = True
                # print(SPEED)
        continue

    time.sleep(DELAY_TIME)

   # Play back color data loaded into each column:
    for COLUMN in COLUMNS:
        neopixel_write(NEOPIXEL_PIN, COLUMN)
        time.sleep(COLUMN_DELAY)
        # Last column is all 0's, no need to explicitly clear strip

    # Wait for touch pad release, just in case:
    while TOUCH.value:
        continue
