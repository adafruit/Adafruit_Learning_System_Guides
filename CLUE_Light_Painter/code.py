"""
Light painting project for Adafruit CLUE using DotStar LED strip.
Images should be in 24-bit BMP format, with width matching the length
of the LED strip. The ulab module is used to assist with interpolation
and dithering, displayio for a minimal user interface.
"""

# pylint: disable=import-error
from math import modf
from time import monotonic, sleep
from os import statvfs
import gc
import board
import busio
import displayio
import ulab
from digitalio import DigitalInOut, Direction
from bmp2led import BMP2LED, BMPError
from richbutton import RichButton
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
from neopixel_write import neopixel_write
from terminalio import FONT # terminalio font is crude but fast to display
FONT_WIDTH, FONT_HEIGHT = FONT.get_bounding_box()


# These are permanent global settings, can only change by editing the code:

FLIP_SCREEN = False  # If True, turn CLUE screen & buttons upside-down
PATH = '/bmps-72px'  # Folder containing BMP images (or '' for root path)
GAMMA = 2.6          # Correction factor for perceptually linear brightness
NUM_PIXELS = 72      # LED strip length, half-meter is usu. 30 or 72 pixels
PIXEL_PINS = board.SDA, board.SCL # Data, clock pins for DotStars
PIXEL_ORDER = 'brg'               # Pixel color order


def centered_label(text, y_pos, scale):
    """
    Create a displayio label that's horizontally centered on screen.
    Arguments:
        text (string) : Label string.
        y_pos (int)   : Vertical position on screen.
        scale (int)   : Text scale.
    Returns: displayio group object.
    """
    group = displayio.Group(scale=scale, x=board.DISPLAY.width // 2)
    x_pos = len(text) * FONT_WIDTH // -2
    group.append(label.Label(FONT, text=text, x=x_pos, y=y_pos))
    return group


# pylint: disable=too-many-instance-attributes
class ClueLightPainter:
    """
    CLUE Light Painter is wrapped in this class to avoid a bunch more globals.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, flip, path, num_pixels, pixel_order, pixel_pins, gamma):
        """
        App constructor. Follow up with a call to ClueLightPainter.run().
        Arguments:
            flip (boolean)       : If True, CLUE display and buttons are
                                   flipped 180 degrees from normal (makes
                                   wiring easier in some situations).
            path (string)        : Directory containing BMP images.
            num_pixels (int)     : LED strip length.
            pixel_order (string) : LED data order, e.g. 'grb'.
            pixel_pins (tuple)   : Board pin(s) for LED data output. If a
                                   single value (int), a NeoPixel strip is
                                   being used. If two values (tuple or
                                   list), it's a DotStar strip (pins are
                                   data and clock of an SPI port).
            gamma (float)        : Correction for perceptual linearity.
        """
        self.bmp2led = BMP2LED(num_pixels, pixel_order, gamma)
        self.path = path

# Don't have these -- just pull from self.bmp2led when needed
#        self.num_pixels = num_pixels
#        self.gamma = gamma

        # Above values are permanently one-time set. The following values
        # can be reconfigured mid-run.
        self.image_num = 0    # Current image index in self.path
        self.loop = False     # Repeat image playback
        self.brightness = 1.0 # LED brightness, 0.0 (off) to 1.0 (bright)
        self.config_mode = 0  # Current setting being changed
        self.rect = None      # Multipurpose progress/setting rect
        self.speed = 0.6      # Paint speed, 0.0 (slow) to 1.0 (fast)

        # Using DotStar LEDs. The SPI peripheral is locked and config'd
        # once here and never relinquished, to save some time on every
        # column (need them ussued as fast as possible).
        self.spi = busio.SPI(pixel_pin[1], MOSI=pixel_pin[0])
        self.spi.try_lock()
        self.spi.configure(baudrate=8000000)

        # Configure hardware initial state
        self.button_left = RichButton(board.BUTTON_A)
        self.button_right = RichButton(board.BUTTON_B)
        if flip:
            board.DISPLAY.rotation = 180
            self.button_left, self.button_right = (self.button_right,
                                                   self.button_left)
        else:
            board.DISPLAY.rotation = 0
        # Turn off onboard NeoPixel and LED strip
        onboard_pixel_pin = digitalio.DigitalInOut(board.NEOPIXEL)
        onboard_pixel_pin.direction = digitalio.Direction.OUTPUT
        neopixel_write(onboard_pixel_pin, bytearray(3))
        self.clear_strip()

        # Get list of compatible BMP images in path
        self.images = self.neobmp.scandir(path)
        if not self.images:
            group = displayio.Group()
            group.append(centered_label('NO IMAGES', 40, 3))
            board.DISPLAY.show(group)
            while True:
                pass

        # Load first image in list
        self.load_image()

        # Clear display
        board.DISPLAY.show(displayio.Group())


    def dotstar_write(self, _, data):
        """
        DotStar strip data-writing wrapper. Accepts color data packed as
        3 bytes/pixel (a la NeoPixel), repackages it into DotStar format
        (header, per-pixel marker, footer) and outputs to self.spi.
        Arguments:
            _ (None)         : Unused but required argument, for 1:1 calling
                               parity with neopixel_write() (where the first
                               argument is a pin number). Allows a single
                               common function call anywhere LEDs are updated
                               rather than if/else in every location.
            data (bytearray) : Pixel data in LED strip's native color order,
                               3 bytes/pixel. Also takes ulab uint8 ndarray.
        """
        pixel_start = bytearray([255]) # Per-pixel marker
        data_bytes = [x for l in [pixel_start + data[i:i+3]
                                  for i in range(0, len(data), 3)] for x in l]
        # SPI is NOT locked or configured here -- the application performs
        # that once at startup and never relinquishes control of the port.
        # Anything to save a few cycles.
        self.spi.write(bytearray([0] * 4) + bytearray(data_bytes) +
                       bytearray([255] * (((len(data) // 3) + 15) // 16)))


    def clear_strip(self):
        """
        Turn off all LEDs of the NeoPixel/DotStar strip.
        """
        # Though most strips are 3 bytes/pixel, issue 4 bytes just in case
        # someone's using RGBW NeoPixel strip (the painting code never
        # uses the W byte, but handle it regardless, in case RGBW strip is
        # all someone has). So this will issue 1/3 more data than is really
        # needed in most cases (including DotStar), but little harm done as
        # this is only called when clearing the strip, not when painting.
        # The extra unused bits harmlessly fall off the end of the strip.
        self.write_func(self.neopixel_pin, bytearray(self.num_pixels * 4))


    def load_progress(self, amount):
        """
        Callback function for image loading, moves progress bar on display.
        Arguments:
            amount (float) : Current 'amount loaded' coefficient; 0.0 to 1.0
        """
        self.rect.x = int(board.DISPLAY.width * (amount - 1.0))


    def load_image(self):
        """
        Load BMP from image list, determined by variable self.image_num
        (not a passed argument). Data is converted and placed in variable
        self.columns[].
        """
        # Minimal progress display while image is loaded.
        group = displayio.Group()
        group.append(centered_label('LOADING...', 30, 3))
        self.rect = Rect(-board.DISPLAY.width, 120,
                         board.DISPLAY.width, 40, fill=0x00FF00)
        group.append(self.rect)
        board.DISPLAY.show(group)

        try:
            self.columns = self.neobmp.load(self.path + '/' +
                                            self.images[self.image_num],
                                            self.load_progress)
        except (MemoryError, BMPError):
            group = displayio.Group()
            group.append(centered_label('TOO BIG', 40, 3))
            board.DISPLAY.show(group)
            sleep(4)

        board.DISPLAY.show(displayio.Group()) # Clear display


    def paint(self):
        """
        Paint mode. Watch for button taps to start/stop image playback,
        or button hold to switch to config mode. During playback, do all
        the nifty image processing.
        """

        if not self.columns: # If no image loaded
            return           # Go back to config, can try another

        board.DISPLAY.brightness = 0 # Screen backlight OFF
        painting = False

        row_size = 4 + num_leds * 4 + ((num_leds + 15) // 16)
        # num_rows = was determined during conversion

        gc.collect() # Helps make playback a little smoother

        while True:
            action_set = {self.button_left.action(),
                          self.button_right.action()}
            if RichButton.TAP in action_set:
                if painting:            # If currently painting
                    self.clear_strip()  # Turn LEDs OFF
                else:
                    row = 0             # Start at beginning of file
                painting = not painting # Toggle paint mode on/off
            elif RichButton.HOLD in action_set:
                return # Exit painting, enter config mode

            if painting:
                file.seek(row * row_size)
                self.spi.write(file.read(row_size))
                row += 1
                if row >= num_rows:
                    if self.loop:
                        row = 0
                    else:
                        painting = False


    # Each config screen is broken out into its own function...
    # Generates its UI, handles button interactions, clears screen.
    # It was a toss-up between this and one big multimodal config
    # function. This way definitely generates less pylint gas pains.
    # Also, creating and destroying elements (rather than creating
    # them all up-front and showing or hiding elements as needed)
    # tends to use less RAM, leaving more for image.

    def make_ui_group(self, main_config, config_label, rect_val=None):
        """
        Generates and displays a displayio group containing several elements
        that all config screens have in common (or nearly in common).
        Arguments:
            main_config (boolean) : If true, function generates the main
                                    config screen elements, else makes
                                    elements for other config screens.
            config_label (string) : Text to appear at center(ish) of screen.
            rect_val (float)      : If specified, a Rect object is created
                                    whose width represents the value.
                                    0.0 = min, 1.0 = full display width.
        Returns: displayio group
        """
        group = displayio.Group(max_size=6)
        group.append(centered_label('TAP L/R to', 3, 2))
        group.append(centered_label('select item' if main_config else
                                    'select image' if self.config_mode is 0
                                    else 'change', 16, 2))
        group.append(centered_label('HOLD L: item config' if main_config else
                                    'HOLD L: back', 100, 2))
        group.append(centered_label('HOLD R: paint', 113, 2))
        if rect_val:
            self.rect = Rect(int(board.DISPLAY.width * (rect_val - 1.0)),
                             120, board.DISPLAY.width, 40, fill=0x00FF00)
            group.append(self.rect)
        # Config label always appears as last item in group
        # so calling func can pop() and replace it if need be.
        group.append(centered_label(config_label, 30 if rect_val else 40, 3))
        board.DISPLAY.show(group)
        return group


    def config_select(self):
        """
        Initial configuration screen, in which the user selects which
        setting will be changed. Tap L/R to select which setting,
        hold L to change that setting, or hold R to resume painting.
        """
        self.clear_strip()
        strings = ['IMAGE', 'SPEED', 'LOOP', 'BRIGHTNESS']
        funcs = [self.config_image, self.config_speed, self.config_loop,
                 self.config_brightness]
        group = self.make_ui_group(True, strings[self.config_mode])
        board.DISPLAY.brightness = 1 # Screen on
        prev_mode = self.config_mode
        reload_image = not self.columns

        while True:
            action_left, action_right = (self.button_left.action(),
                                         self.button_right.action())
            if action_left is RichButton.HOLD:
                # Call one of the configuration sub-menu functions.
                # These all return two booleans. One indicates whether
                # the setting change requires reloading the image,
                # other indicates if it was a R button hold, in which
                # case this should return to paint mode.
                reload, paint = funcs[self.config_mode]()
                # Image reload is not immediate, it can wait until
                # returning to paint.
                reload_image |= reload
                if paint:
                    break # Exit loop, resume paint
                else:
                    board.DISPLAY.show(group) # Put config UI back up
            elif action_right is RichButton.HOLD:
                break
            elif action_left is RichButton.TAP:
                self.config_mode = (self.config_mode - 1) % len(strings)
            elif action_right is RichButton.TAP:
                self.config_mode = (self.config_mode + 1) % len(strings)

            if self.config_mode is not prev_mode:
                # Create/destroy mode descriptions as needed
                group.pop()
                group.append(centered_label(strings[self.config_mode],
                                            40, 3))
                prev_mode = self.config_mode

        # Before exiting to paint mode, check if new image needs loaded
        if reload_image:
            self.load_image()


    def config_image(self):
        """
        Image select screen. Tap L/R to cycle among image filenames,
        hold L to go back to main config menu, hold R to paint.
        Returns: two booleans, first indicates whether image needs to
        be reloaded, second indicates if returning to paint mode vs
        more config.
        """
        orig_image = self.image_num
        prev_image = self.image_num
        group = self.make_ui_group(False, self.images[self.image_num])

        while True:
            action_left, action_right = (self.button_left.action(),
                                         self.button_right.action())
            if action_left is RichButton.HOLD:
                # Resume config
                return self.image_num is not orig_image, False
            if action_right is RichButton.HOLD:
                # Resume paint
                return self.image_num is not orig_image, True
            if action_left is RichButton.TAP:
                self.image_num = (self.image_num - 1) % len(self.images)
            elif action_right is RichButton.TAP:
                self.image_num = (self.image_num + 1) % len(self.images)

            if self.image_num is not prev_image:
                group.pop()
                group.append(centered_label(self.images[self.image_num],
                                            40, 3))
                prev_image = self.image_num


    def config_speed(self):
        """
        Speed select screen. Tap L/R to decrease/increase paint speed,
        hold L to go back to main config menu, hold R to paint.
        Returns: two booleans, first is always False, second indicates
        if returning to paint mode vs more config.
        """
        prev_speed = self.speed
        self.make_ui_group(False, 'Speed:', self.speed)

        while True:
            action_left, action_right = (self.button_left.action(),
                                         self.button_right.action())
            if action_left is RichButton.HOLD:
                return False, False # Resume config
            if action_right is RichButton.HOLD:
                return False, True  # Resume paint
            if action_left is RichButton.TAP:
                self.speed = max(0, self.speed - 0.1)
            elif action_right is RichButton.TAP:
                self.speed = min(10, self.speed + 0.1)

            if self.speed is not prev_speed:
                self.rect.x = int(board.DISPLAY.width * (self.speed - 1.0))
                prev_speed = self.speed


    def config_loop(self):
        """
        Loop select screen. Tap L/R to toggle looping on/off,
        hold L to go back to main config menu, hold R to paint.
        Returns: two booleans, first is always False, second indicates
        if returning to paint mode vs more config.
        """
        loop_label = ['Loop OFF', 'Loop ON']
        group = self.make_ui_group(False, loop_label[self.loop])

        while True:
            action_left, action_right = (self.button_left.action(),
                                         self.button_right.action())
            if action_left is RichButton.HOLD:
                return False, False # Resume config
            if action_right is RichButton.HOLD:
                return False, True  # Resume paint
            if RichButton.TAP in {action_left, action_right}:
                self.loop = not self.loop
                group.pop()
                group.append(centered_label(loop_label[self.loop], 40, 3))


    def config_brightness(self):
        """
        Brightness select screen. Tap L/R to decrease/increase brightness,
        hold L to go back to main config menu, hold R to paint.
        Returns: two booleans, first is always False, second indicates
        if returning to paint mode vs more config.
        """
        prev_brightness = self.brightness

        self.make_ui_group(False, 'Brightness:', self.brightness)

        while True:
            action_left, action_right = (self.button_left.action(),
                                         self.button_right.action())
            if action_left is RichButton.HOLD:
                return False, False # Resume config
            if action_right is RichButton.HOLD:
                return False, True  # Resume paint
            if action_left is RichButton.TAP:
                self.brightness = max(0.0, self.brightness - 0.1)
            elif action_right is RichButton.TAP:
                self.brightness = min(1.0, self.brightness + 0.1)

            if self.brightness is not prev_brightness:
                self.rect.x = int(board.DISPLAY.width * (self.brightness - 1.0))
                prev_brightness = self.brightness


    def run(self):
        """
        Application loop just consists of alternating paint and
        config modes. Each function has its own condition for return
        (switching to the opposite mode). Repeat forever.
        """
        while True:
            self.paint()
            self.config_select()


ClueLightPainter(FLIP_SCREEN, PATH,
                 NUM_PIXELS, PIXEL_ORDER, PIXEL_PINS, GAMMA).run()









# Note to future self: make program start in image-select mode,
# then when that returns, go into settings or paint depending
# on return status.



class foobar:
    def __init__(self, num_pixels, pins):
        self.num_pixels = num_pixels
        self.spi = busio.SPI(pins[1], MOSI=pins[0])
        self.spi.try_lock()
        self.spi.configure(baudrate=8000000)

        stats = os.statvfs('/')
        bytes_free = stats[0] * stats[4] # block size, free blocks
        self.row_size = 4 + num_pixels * 4 + ((num_pixels + 15) // 16)
        self.max_rows = bytes_free // self.row_size
        self.rows_per_second = 0

    def benchmark(self):
        with open('/tempfile', 'wb') as file:
            row_data = bytearray([0] * 4 +
                                 [255, 0, 0, 0] * self.num_pixels +
                                 [255] * ((self.num_pixels + 15) // 16))
            file.write(row_data)

        with open('/tempfile', 'rb') as file:
            test_duration = 1.0
            rows = 0
            gc.collect()
            start_time = monotonic()
            while monotonic() - start_time < test_duration:
                file.seek(0)
                self.spi.write(file.read(self.row_size))
                rows += 1
            self.rows_per_second = rows / test_duration
            print('Speed:', self.rows_per_second, 'rows/sec')

foobar(NUM_PIXELS, PIXEL_PINS).benchmark()

while True:
    pass





stats = os.statvfs('/')
bytes = stats[0] * stats[4] # block size * free blocks for unprivileged users
print(bytes, 'bytes free')

spi = busio.SPI(DOTSTAR_PINS[1], MOSI=DOTSTAR_PINS[0])
spi.try_lock()
# 8 MHz max SPI on nRF (32 MHz reserved for screen)
spi.configure(baudrate=8000000)

# Write a single-line file.
# also, determine max number of lines from free bytes and
# dotstar_num_bytes

#with open('/garbage', 'wb') as outfile:
column_buf = bytearray([0] * 4 + [255, 0, 0, 0] * NUM_PIXELS + [255] * ((NUM_PIXELS + 15) // 16))
dotstar_num_bytes = len(column_buf)
#    for i in range(ROWS):
#    outfile.write(column_buf)

# What if, instead of fixed number of rows, if it
# read data for one second.

# rows/sec will get more accurate the longer this runs, but that
# requires the user waiting. About 1 second gives a 'good enough' answer.
test_time = 1
rows = 0
gc.collect()
with open('/garbage', 'rb') as infile:
    start_time = monotonic()
    while monotonic() - start_time < test_time:
        infile.seek(0)
        spi.write(infile.read(dotstar_num_bytes))
        rows += 1
print('Speed:', rows / test_time, 'lines/sec')
print(rows, 'rows')
print(test_time, 'sec')

while True:
    pass




NEOPIXEL_PIN = board.D0
DOTSTAR_PINS = board.SDA, board.SCL

FILE = 'bigfile.jpg'
#FILE = 'Helvetica-Bold-16.bdf'

neopixel_num_bytes = NUM_PIXELS * 3
neopixel_data = bytearray(neopixel_num_bytes)
dotstar_num_bytes = 4 + NUM_PIXELS * 4 + (NUM_PIXELS + 15) // 16
dotstar_data = bytearray(dotstar_num_bytes)

neopixel_pin = digitalio.DigitalInOut(NEOPIXEL_PIN)
neopixel_pin.direction = digitalio.Direction.OUTPUT

spi = busio.SPI(DOTSTAR_PINS[1], MOSI=DOTSTAR_PINS[0])
spi.try_lock()
# 8 MHz max SPI on nRF (32 MHz reserved for screen)
spi.configure(baudrate=8000000)

# Trying header/footer as distinct things (not stored with data)
header = bytearray([0] * 4)
footer = bytearray([255] * ((NUM_PIXELS + 15) // 16))
dotstar_num_bytes = NUM_PIXELS * 4
# As single write: 1037 lines/sec
# As concatenated bytearrays: 769 lines/sec, oof.
# Okay then, build header and footer into the tempfile data.
# It'll produce a larger file, but it's quicker to issue.

passes = 0
with open(FILE, "rb") as file:
    start_time = monotonic()
    while True:
        #data = file.read(neopixel_num_bytes)
        data = file.read(dotstar_num_bytes)
        if not data:
            break
        #neopixel_write(neopixel_pin, data)
        spi.write(data)
        #spi.write(header + data + footer)
        passes += 1
    end_time = monotonic()
    elapsed = end_time - start_time
    print('Speed:', passes / elapsed, 'lines/sec')
    print(passes)

while True:
    pass

# 394K file
# Reading neopixel_num_bytes at a time: 2214 reads/sec
# Reading dotstar_num_bytes at a time: 1470

# 800K file w strip writes:
# NeoPixel: 328 lines/sec
# DotStar: 1087 lines/sec




DELAY = 0.000300 # 300 uS
DELAY = 0.003    # 3 ms (333 lines/sec)

for passes in (100, 1000, 10000):
    print(passes, 'passes')

    start_time = monotonic()
    for i in range(passes):
        neopixel_write(neopixel_pin, neopixel_data)
        sleep(DELAY)
    end_time = monotonic()
    elapsed = end_time - start_time
    print('NeoPixel speed:', passes / elapsed, 'writes/sec')

    start_time = monotonic()
    for i in range(passes):
        spi.write(dotstar_data)
        sleep(DELAY)
    end_time = monotonic()
    elapsed = end_time - start_time
    print('DotStar speed:', passes / elapsed, 'writes/sec')

# 72 pixel strip

# No delay between writes
# Writes  NeoPixel  DotStar
# 100     180       307 writes/sec
# 1000    335       1549
# 10000   367       2597

# 300 uS delay between writes
# Writes  NeoPixel  DotStar
# 100     178       306 writes/sec
# 1000    334       1501
# 10000   365       2463

# 3 mS delay between writes
# Writes  NeoPixel  DotStar
# 100     127       169 writes/sec
# 1000    189       304
# 10000   198       330




while True:
    pass
