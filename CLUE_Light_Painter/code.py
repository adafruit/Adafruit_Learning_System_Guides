"""
Light painting project for Adafruit CLUE using DotStar LED strip.
Images should be in 24-bit BMP format, with width matching the length
of the LED strip. Uses ulab module to assist with interpolation and
dithering, displayio for a minimal user interface.

TO RUN, boot.py MUST CONFIGURE FILESYSTEM FOR READ-WRITE MODE.
TO EDIT CODE, FILESYSTEM MUST BE IN READ-ONLY MODE.
boot.py sets up latter condition using a jumper from pin 0 to GND.
"""

# pylint: disable=import-error
import gc
from time import monotonic, sleep
import board
import busio
import displayio
from digitalio import DigitalInOut, Direction
from bmp2led import BMP2LED, BMPError
from neopixel_write import neopixel_write
from richbutton import RichButton
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
from terminalio import FONT # terminalio font is crude but fast to display
FONT_WIDTH, FONT_HEIGHT = FONT.get_bounding_box()


# These are permanent global settings, can only change by editing the code:

NUM_PIXELS = 72                   # LED strip length
PIXEL_PINS = board.SDA, board.SCL # Data, clock pins for DotStars
PIXEL_ORDER = 'brg'               # Pixel color order
PATH = '/bmps-72px'   # Folder containing BMP images (or '' for root path)
TEMPFILE = '/led.dat' # Working file for LED data (will be clobbered!)
FLIP_SCREEN = False   # If True, turn CLUE screen & buttons upside-down
GAMMA = 2.4           # Correction factor for perceptually linear brightness

# Temporary line during development, delete before use:
PIXEL_ORDER = 'gbr' # Old DotStar strip with different color order


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
    def __init__(self, flip, path, tempfile, num_pixels, pixel_order,
                 pixel_pins, gamma):
        """
        App constructor. Follow up with a call to ClueLightPainter.run().
        Arguments:
            flip (boolean)       : If True, CLUE display and buttons are
                                   flipped 180 degrees from normal (makes
                                   wiring easier in some situations).
            path (string)        : Directory containing BMP images.
            tempfile (string)    : Full path/filename of temporary working
                                   file for LED data (will be clobbered).
            num_pixels (int)     : LED strip length.
            pixel_order (string) : LED data order, e.g. 'grb'.
            pixel_pins (tuple)   : Board pin for LED data output (SPI data
                                   and clock pins respectively).
            gamma (float)        : Correction for perceptual linearity.
        """
        self.bmp2led = BMP2LED(num_pixels, pixel_order, gamma)
        self.path = path
        self.tempfile = tempfile

        # The SPI peripheral is locked and config'd once here and never
        # relinquished, to save some time on every row (need them issued
        # as fast as possible).
        self.spi = busio.SPI(pixel_pins[1], MOSI=pixel_pins[0])
        self.spi.try_lock()
        self.spi.configure(baudrate=8000000)

        # Determine filesystem-to-LEDs throughput (also clears LED strip)
        self.rows_per_second, self.row_size = self.benchmark()

        # Configure hardware initial state
        self.button_left = RichButton(board.BUTTON_A)
        self.button_right = RichButton(board.BUTTON_B)
        if flip:
            board.DISPLAY.rotation = 180
            self.button_left, self.button_right = (self.button_right,
                                                   self.button_left)
        else:
            board.DISPLAY.rotation = 0
        # Turn off onboard NeoPixel
        onboard_pixel_pin = DigitalInOut(board.NEOPIXEL)
        onboard_pixel_pin.direction = Direction.OUTPUT
        neopixel_write(onboard_pixel_pin, bytearray(3))

        # Get list of compatible BMP images in path
        self.images = self.bmp2led.scandir(path)
        if not self.images:
            group = displayio.Group()
            group.append(centered_label('NO IMAGES', 40, 3))
            board.DISPLAY.show(group)
            while True:
                pass

        self.image_num = 0    # Current selected image index in self.path
        self.loop = False     # Repeat image playback
        self.brightness = 1.0 # LED brightness, 0.0 (off) to 1.0 (bright)
        self.config_mode = 0  # Current setting being changed
        self.rect = None      # Multipurpose progress/setting rect
        self.speed = 0.8      # Paint speed, 0.0 (slow) to 1.0 (fast)
        self.num_rows = 0     # Nothing loaded yet


    def benchmark(self):
        """
        Estimate filesystem-to-LED-strip throughput.
        Returns: rows-per-second throughput (int), LED row size in bytes
        (including DotStar header and footer) (int).
        """
        # Generate a small temporary file equal to one full LED row,
        # all set 'off'.
        row_data = bytearray([0] * 4 +
                             [255, 0, 0, 0] * self.bmp2led.num_pixels +
                             [255] * ((self.bmp2led.num_pixels + 15) //
                                      16))
        row_size = len(row_data)
        with open(self.tempfile, 'wb') as file:
            file.write(row_data)

        # For a period of 1 second, repeatedly seek to start of file,
        # read row of data and write to LED strip as fast as possible.
        # Not super precise, but good-enough guess of light painting speed.
        # (Bonus, this will turn off LED strip on startup).
        rows = 0
        with open(self.tempfile, 'rb') as file:
            start_time = monotonic()
            while monotonic() - start_time < 1.0:
                file.seek(0)
                # using readinto() instead of read() reduces the amount
                # of work the garbage collector needs to do each row.
                file.readinto(row_data)
                self.spi.write(row_data)
                # Garbage collection is done on EVERY row...even though
                # this slows down painting a LOT, it keeps the timing more
                # consistent (else there would be conspicuous glitches).
                gc.collect()
                rows += 1

        return rows, row_size


    def clear_strip(self):
        """
        Turn off all LEDs of the DotStar strip.
        """
        self.spi.write(bytearray([0] * 4 +
                                 [255, 0, 0, 0] * self.bmp2led.num_pixels +
                                 [255] * ((self.bmp2led.num_pixels + 15) //
                                          16)))


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
        (not a passed argument). Data is converted and placed in
        self.tempfile.
        """
        # Minimal progress display while image is loaded.
        group = displayio.Group()
        group.append(centered_label('LOADING...', 30, 3))
        self.rect = Rect(-board.DISPLAY.width, 120,
                         board.DISPLAY.width, 40, fill=0x00FF00)
        group.append(self.rect)
        board.DISPLAY.show(group)

        # Playback time is about 1/2 to 6 seconds, non linearly spaced
        duration = 0.5 + 5.5 * ((1.0 - self.speed) ** 2)
        rows = int(duration * self.rows_per_second + 0.5)
        try:
            self.num_rows = self.bmp2led.process(self.path + '/' +
                                                 self.images[self.image_num],
                                                 self.tempfile,
                                                 rows,
                                                 self.brightness,
                                                 self.loop,
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
        or button hold to switch to config mode.
        """

        board.DISPLAY.brightness = 0 # Screen backlight OFF
        painting = False

        with open(self.tempfile, 'rb') as file:
            led_buffer = bytearray(self.row_size)
            gc.collect()

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
                    file.seek(row * self.row_size)
                    # using readinto() instead of read() reduces the amount
                    # of work the garbage collector needs to do each row.
                    file.readinto(led_buffer)
                    self.spi.write(led_buffer)
                    # Garbage collection is done on EVERY row...even though
                    # this slows down painting a LOT, it keeps the timing more
                    # consistent (else there would be conspicuous glitches).
                    gc.collect()
                    row += 1
                    if row >= self.num_rows:
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
    # tends to use less RAM.

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


    def config_select(self, first_run=False):
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
        reload_image = first_run

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
        group = self.make_ui_group(False,
                                   self.images[self.image_num].split('.')[0])
        orig_image, prev_image = self.image_num, self.image_num

        while True:
            action_left, action_right = (self.button_left.action(),
                                         self.button_right.action())
            if action_left is RichButton.HOLD:
                return self.image_num is not orig_image, False # Resume config
            if action_right is RichButton.HOLD:
                return self.image_num is not orig_image, True  # Resume paint
            if action_left is RichButton.TAP:
                self.image_num = (self.image_num - 1) % len(self.images)
            elif action_right is RichButton.TAP:
                self.image_num = (self.image_num + 1) % len(self.images)

            if self.image_num is not prev_image:
                group.pop()
                group.append(centered_label(
                    self.images[self.image_num].split('.')[0], 40, 3))
                prev_image = self.image_num


    def config_speed(self):
        """
        Speed select screen. Tap L/R to decrease/increase paint speed,
        hold L to go back to main config menu, hold R to paint.
        Returns: two booleans, first is always False, second indicates
        if returning to paint mode vs more config.
        """
        self.make_ui_group(False, 'Speed:', self.speed)
        orig_speed, prev_speed = self.speed, self.speed

        while True:
            action_left, action_right = (self.button_left.action(),
                                         self.button_right.action())
            if action_left is RichButton.HOLD:
                return self.speed is not orig_speed, False # Resume config
            if action_right is RichButton.HOLD:
                return self.speed is not orig_speed, True  # Resume paint
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
        orig_loop = self.loop

        while True:
            action_left, action_right = (self.button_left.action(),
                                         self.button_right.action())
            if action_left is RichButton.HOLD:
                return self.loop is not orig_loop, False # Resume config
            if action_right is RichButton.HOLD:
                return self.loop is not orig_loop, True  # Resume paint
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
        orig_brightness, prev_brightness = self.brightness, self.brightness
        self.make_ui_group(False, 'Brightness:', self.brightness)

        while True:
            action_left, action_right = (self.button_left.action(),
                                         self.button_right.action())
            if action_left is RichButton.HOLD:
                return self.brightness is not orig_brightness, False # Config
            if action_right is RichButton.HOLD:
                return self.brightness is not orig_brightness, True  # Paint
            if action_left is RichButton.TAP:
                self.brightness = max(0.0, self.brightness - 0.1)
            elif action_right is RichButton.TAP:
                self.brightness = min(1.0, self.brightness + 0.1)

            if self.brightness is not prev_brightness:
                self.rect.x = int(board.DISPLAY.width * (self.brightness - 1.0))
                prev_brightness = self.brightness


    def run(self):
        """
        Post-init application loop. After a one-time visit to image select
        (and possibly other config), just consists of alternating paint and
        config modes. Each function has its own condition for return
        (switching to the opposite mode). Repeat forever.
        """
        _, paint = self.config_image()
        if paint:
            self.load_image()
        else:
            self.config_select(True)

        while True:
            self.paint()
            self.config_select()


ClueLightPainter(FLIP_SCREEN, PATH, TEMPFILE,
                 NUM_PIXELS, PIXEL_ORDER, PIXEL_PINS, GAMMA).run()
