# Simple NeoPixel light painter for CPX.  Single image filename and speed are set
# in code, there's no interface for selecting items/speed/triggering etc.

import gc
import time
import board
import neopixel
import touchio
from analogio import AnalogIn

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

TOUCH = touchio.TouchIn(board.A5)      #  capacitive touch pad
SPEED = 50000
BRIGHTNESS = 1.0              # Set brightness here, NOT in NeoPixel constructor
GAMMA = 2.7                            # Adjusts perceived brighthess linearity
NUM_PIXELS = 30                        # NeoPixel strip length (in pixels)
NEOPIXEL_PIN = board.A1         # Pin where NeoPixels are connected
STRIP = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=1, auto_write=False)
DELAY_TIME = 0.01                         # Timer delay before it starts

# Interpret multi-byte value from file as little-endian value
def read_le(value):
    result = 0
    shift = 0
    for byte in value:
        result += byte << shift
        shift += 8
    return result

class BMPError(Exception):
    pass

def load_bmp(filename):
    try:
        print("Loading", filename)
        with open("/" + filename, "rb") as f:
            print("File opened")
            if f.read(2) != b'BM':  # check signature
                raise BMPError("Not BitMap file")

            bmpFileSize = read_le(f.read(4))
            f.read(4)  # Read & ignore creator bytes

            bmpImageoffset = read_le(f.read(4))  # Start of image data
            headerSize = read_le(f.read(4))
            bmpWidth = read_le(f.read(4))
            bmpHeight = read_le(f.read(4))
            # BMPs are traditionally stored bottom-to-top.
            # If bmpHeight is negative, image is in top-down order.
            # This is not BMP canon but has been observed in the wild!
            flip = True
            if bmpHeight < 0:
                bmpHeight = -bmpHeight
                flip = False

            # print("Size: %d\nImage offset: %d\nHeader size: %d" %
            #       (bmpFileSize, bmpImageoffset, headerSize))
            print("WxH: (%d,%d)" % (bmpWidth, bmpHeight))

            if read_le(f.read(2)) != 1:
                raise BMPError("Not single-plane")
            bmpDepth = read_le(f.read(2))  # bits per pixel
            # print("Bit depth: %d" % (bmpDepth))
            if bmpDepth != 24:
                raise BMPError("Not 24-bit")
            if read_le(f.read(2)) != 0:
                raise BMPError("Compressed file")

            print("Image format OK, reading data...")

            rowSize = (bmpWidth * 3 + 3) & ~3  # 32-bit line boundary

            # Constrain rows loaded to pixel strip length
            clippedHeight = bmpHeight
            if clippedHeight > NUM_PIXELS:
                clippedHeight = NUM_PIXELS

            # Allocate per-column pixel buffers, sized for NeoPixel strip:
            columns = [bytearray(NUM_PIXELS * STRIP.bpp) for i in range(bmpWidth)]

            # Image is displayed at END (not start) of NeoPixel strip,
            # this index works incrementally backward in column buffers...
            idx = (NUM_PIXELS - 1) * 3
            for row in range(clippedHeight):  # For each scanline...
                if flip:  # Bitmap is stored bottom-to-top order (normal BMP)
                    pos = bmpImageoffset + (bmpHeight - 1 - row) * rowSize
                else:  # Bitmap is stored top-to-bottom
                    pos = bmpImageoffset + row * rowSize
                f.seek(pos) # Start of scanline
                for c in columns:  # For each pixel of scanline...
                    # BMP files use BGR color order
                    # blue, green, red = bytearray(f.read(3))
                    blue, green, red = f.read(3)
                    # Rearrange into NeoPixel strip's color order,
                    # while handling brightness & gamma correction:
                    c[idx + STRIP.order[0]] = int(pow(red   / 255, GAMMA) * BRIGHTNESS * 255 + 0.5)
                    c[idx + STRIP.order[1]] = int(pow(green / 255, GAMMA) * BRIGHTNESS * 255 + 0.5)
                    c[idx + STRIP.order[2]] = int(pow(blue  / 255, GAMMA) * BRIGHTNESS * 255 + 0.5)
                idx -= 3  # Advance (back) one pixel

            # Add one more column, using the NeoPixel strip's normal buffer,
            # which is never assigned any color data.  This is used to turn
            # the strip off at the end of the painting operation.
            columns.append(STRIP.buf)

            print("Loaded OK!")
            gc.collect()  # Garbage-collect now so playback is smoother
            return columns

    except OSError as e:
        if e.args[0] == 28:
            raise OSError("OS Error 28 0.25")
        else:
            raise OSError("OS Error 0.5")
    except BMPError as e:
        print("Failed to parse BMP: " + e.args[0])


# Load BMP image, return 'columns' array:
columns = load_bmp(FILENAME)

print("Mem free:", gc.mem_free())

# Switch off onboard NeoPixel
neo = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0, auto_write=True)
neo.fill(0)

while True:

    # Wait for touch pad input:
    while not TOUCH.value:
        continue

    time.sleep(DELAY_TIME)
    column_delay = SPEED / 65535.0 / 10.0  # 0.0 to 0.1 seconds
    # print(column_delay)

    # Play back color data loaded into each column:
    for c in columns:
        # Rather than replace the data in the NeoPixel strip's buffer
        # pixel-by-pixel, which would be very slow, we just override
        # STRIP's buffer object with each column of precomputed data:
        STRIP.buf = c             # Substitute our data
        STRIP.show()              # Push to strip
        time.sleep(column_delay)  # Column-to-column delay
        # Last column is all 0's, no need to explicitly clear strip

    # Wait for touch pad release, just in case:
    while TOUCH.value:
        continue
