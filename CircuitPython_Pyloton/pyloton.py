"""
A library for completing the Pyloton bike computer learn guide utilizing the Adafruit CLUE.
"""

import time
import adafruit_ble
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.advertising.standard import SolicitServicesAdvertisement
import board
import digitalio
import displayio
import adafruit_imageload
from adafruit_ble_cycling_speed_and_cadence import CyclingSpeedAndCadenceService
from adafruit_ble_heart_rate import HeartRateService
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from adafruit_ble_apple_media import AppleMediaService
from adafruit_ble_apple_media import UnsupportedCommand
import gamepad
import touchio

class Clue:
    """
    A very minimal version of the CLUE library.
    The library requires the use of many sensor-specific
    libraries this project doesn't use, and they were
    taking up a lot of RAM.
    """
    def __init__(self):
        self._i2c = board.I2C()
        self._touches = [board.D0, board.D1, board.D2]
        self._touch_threshold_adjustment = 0
        self._a = digitalio.DigitalInOut(board.BUTTON_A)
        self._a.switch_to_input(pull=digitalio.Pull.UP)
        self._b = digitalio.DigitalInOut(board.BUTTON_B)
        self._b.switch_to_input(pull=digitalio.Pull.UP)
        self._gamepad = gamepad.GamePad(self._a, self._b)

    @property
    def were_pressed(self):
        """
        Returns a set of buttons that have been pressed since the last time were_pressed was run.
        """
        ret = set()
        pressed = self._gamepad.get_pressed()
        for button, mask in (('A', 0x01), ('B', 0x02)):
            if mask & pressed:
                ret.add(button)
        return ret

    def _touch(self, i):
        if not isinstance(self._touches[i], touchio.TouchIn):
            self._touches[i] = touchio.TouchIn(self._touches[i])
            self._touches[i].threshold += self._touch_threshold_adjustment
        return self._touches[i].value

    @property
    def touch_0(self):
        """
        Returns True when capacitive touchpad 0 is currently being pressed.
        """
        return self._touch(0)

    @property
    def touch_1(self):
        """
        Returns True when capacitive touchpad 1 is currently being pressed.
        """
        return self._touch(1)

    @property
    def touch_2(self):
        """
        Returns True when capacitive touchpad 2 is currently being pressed.
        """
        return self._touch(2)


class Pyloton:
    """
    Contains the various functions necessary for doing the Pyloton learn guide.
    """
    #pylint: disable=too-many-instance-attributes

    YELLOW = 0xFCFF00
    PURPLE = 0x64337E
    WHITE = 0xFFFFFF

    clue = Clue()

    def __init__(self, ble, display, circ, heart=True, speed=True, cad=True, ams=True, debug=False): #pylint: disable=too-many-arguments
        self.debug = debug
        self.ble = ble
        self.display = display
        self.circumference = circ

        self.heart_enabled = heart
        self.speed_enabled = speed
        self.cadence_enabled = cad
        self.ams_enabled = ams
        self.hr_connection = None

        self.num_enabled = heart + speed + cad + ams

        self._previous_wheel = 0
        self._previous_crank = 0
        self._previous_revolutions = 0
        self._previous_rev = 0
        self._previous_speed = 0
        self._previous_cadence = 0
        self._previous_heart = 0
        self._speed_failed = 0
        self._cadence_failed = 0
        self._setup = 0
        self._hr_label = None
        self._sp_label = None
        self._cadence_label = None
        self._ams_label = None
        self._hr_service = None
        self._heart_y = None
        self._speed_y = None
        self._cadence_y = None
        self._ams_y = None
        self.ams = None
        self.cyc_connections = None
        self.cyc_services = None
        self.track_artist = True

        self.start = time.time()

        self.splash = displayio.Group(max_size=25)
        self.loading_group = displayio.Group()

        self._load_fonts()

        self.sprite_sheet, self.palette = adafruit_imageload.load("/sprite_sheet.bmp",
                                                                  bitmap=displayio.Bitmap,
                                                                  palette=displayio.Palette)

        self.text_group = displayio.Group()
        self.status = label.Label(font=self.arial12, x=10, y=200,
                                  text='', color=self.YELLOW, max_glyphs=30)
        self.status1 = label.Label(font=self.arial12, x=10, y=220,
                                   text='', color=self.YELLOW, max_glyphs=30)

        self.text_group.append(self.status)
        self.text_group.append(self.status1)


    def show_splash(self):
        """
        Shows the loading screen
        """
        if self.debug:
            return
        with open('blinka-pyloton.bmp', 'rb') as bitmap_file:
            bitmap1 = displayio.OnDiskBitmap(bitmap_file)
            tile_grid = displayio.TileGrid(bitmap1, pixel_shader=getattr(bitmap1, 'pixel_shader', displayio.ColorConverter()))
            self.loading_group.append(tile_grid)
            self.display.show(self.loading_group)
            status_heading = label.Label(font=self.arial16, x=80, y=175,
                                         text="Status", color=self.YELLOW)
            rect = Rect(0, 165, 240, 75, fill=self.PURPLE)
            self.loading_group.append(rect)
            self.loading_group.append(status_heading)


    def _load_fonts(self):
        """
        Loads fonts
        """
        self.arial12 = bitmap_font.load_font("/fonts/Arial-12.bdf")
        self.arial16 = bitmap_font.load_font("/fonts/Arial-16.bdf")
        self.arial24 = bitmap_font.load_font("/fonts/Arial-Bold-24.bdf")

        glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-!,. "\'?!'
        self.arial12.load_glyphs(glyphs)
        self.arial16.load_glyphs(glyphs)
        self.arial24.load_glyphs(glyphs)


    def _status_update(self, message):
        """
        Displays status updates
        """
        if self.debug:
            print(message)
            return
        if self.text_group not in self.loading_group:
            self.loading_group.append(self.text_group)
        self.status.text = message[:25]
        self.status1.text = message[25:50]


    def timeout(self):
        """
        Displays Timeout on screen when pyloton has been searching for a sensor for too long
        """
        self._status_update("Pyloton: Timeout")
        time.sleep(3)


    def heart_connect(self):
        """
        Connects to heart rate sensor
        """
        self._status_update("Heart Rate: Scanning...")
        for adv in self.ble.start_scan(ProvideServicesAdvertisement, timeout=5):
            if HeartRateService in adv.services:
                self._status_update("Heart Rate: Found an advertisement")
                self.hr_connection = self.ble.connect(adv)
                self._status_update("Heart Rate: Connected")
                break
        self.ble.stop_scan()
        if self.hr_connection:
            self._hr_service = self.hr_connection[HeartRateService]
        return self.hr_connection


    @staticmethod
    def _has_timed_out(start, timeout):
        if time.time() - start >= timeout:
            return True
        return False

    def ams_connect(self, start=time.time(), timeout=30):
        """
        Connect to an Apple device using the ble_apple_media library
        """
        self._status_update("AppleMediaService: Connect your phone now")
        radio = adafruit_ble.BLERadio()
        a = SolicitServicesAdvertisement()
        a.solicited_services.append(AppleMediaService)
        radio.start_advertising(a)

        while not radio.connected and not self._has_timed_out(start, timeout):
            pass

        self._status_update("AppleMediaService: Connected")
        for connection in radio.connections:
            if not connection.paired:
                connection.pair()
                self._status_update("AppleMediaService: Paired")
            self.ams = connection[AppleMediaService]

        return radio


    def speed_cadence_connect(self):
        """
        Connects to speed and cadence sensor
        """
        self._status_update("Speed and Cadence: Scanning...")
        # Save advertisements, indexed by address
        advs = {}
        for adv in self.ble.start_scan(ProvideServicesAdvertisement, timeout=5):
            if CyclingSpeedAndCadenceService in adv.services:
                self._status_update("Speed and Cadence: Found an advertisement")
                # Save advertisement. Overwrite duplicates from same address (device).
                advs[adv.address] = adv

        self.ble.stop_scan()
        self._status_update("Speed and Cadence: Stopped scanning")
        if not advs:
            # Nothing found. Go back and keep looking.
            return []

        # Connect to all available CSC sensors.
        self.cyc_connections = []
        for adv in advs.values():
            self.cyc_connections.append(self.ble.connect(adv))
            self._status_update("Speed and Cadence: Connected {}".format(len(self.cyc_connections)))

        self.cyc_services = []
        for conn in self.cyc_connections:
            self.cyc_services.append(conn[CyclingSpeedAndCadenceService])
        self._status_update("Pyloton: Finishing up...")

        return self.cyc_connections


    def _compute_speed(self, values, speed):
        wheel_diff = values.last_wheel_event_time - self._previous_wheel
        rev_diff = values.cumulative_wheel_revolutions - self._previous_revolutions
        if wheel_diff:
            # Rotations per minute is 60 times the amount of revolutions since
            # the last update over the time since the last update
            rpm = 60*(rev_diff/(wheel_diff/1024))
            # We then mutiply it by the wheel's circumference and convert it to mph
            speed = round((rpm * self.circumference) * (60/63360), 1)
            if speed < 0:
                speed = self._previous_speed
            self._previous_speed = speed
            self._previous_revolutions = values.cumulative_wheel_revolutions
            self._speed_failed = 0
        else:
            self._speed_failed += 1
            if self._speed_failed >= 3:
                speed = 0
        self._previous_wheel = values.last_wheel_event_time

        return speed


    def _compute_cadence(self, values, cadence):
        crank_diff = values.last_crank_event_time - self._previous_crank
        crank_rev_diff = values.cumulative_crank_revolutions-self._previous_rev

        if crank_rev_diff:
            # Rotations per minute is 60 times the amount of revolutions since the
            # last update over the time since the last update
            cadence = round(60*(crank_rev_diff/(crank_diff/1024)), 1)
            if cadence < 0:
                cadence = self._previous_cadence
            self._previous_cadence = cadence
            self._previous_rev = values.cumulative_crank_revolutions
            self._cadence_failed = 0
        else:
            self._cadence_failed += 1
            if self._cadence_failed >= 3:
                cadence = 0
        self._previous_crank = values.last_crank_event_time

        return cadence


    def read_s_and_c(self):
        """
        Reads data from the speed and cadence sensor
        """
        speed = self._previous_speed
        cadence = self._previous_cadence
        for conn, svc in zip(self.cyc_connections, self.cyc_services):
            if not conn.connected:
                speed = cadence = 0
                continue
            values = svc.measurement_values
            if not values:
                if self._cadence_failed >= 3 or self._speed_failed >= 3:
                    if self._cadence_failed > 3:
                        cadence = 0
                    if self._speed_failed > 3:
                        speed = 0
                continue
            if not values.last_wheel_event_time:
                continue
            speed = self._compute_speed(values, speed)
            if not values.last_crank_event_time:
                continue
            cadence = self._compute_cadence(values, cadence)

        if speed:
            speed = str(speed)[:8]
        if cadence:
            cadence = str(cadence)[:8]

        return speed, cadence


    def read_heart(self):
        """
        Reads date from the heart rate sensor
        """
        measurement = self._hr_service.measurement_values
        if measurement is None:
            heart = self._previous_heart
        else:
            heart = measurement.heart_rate
            self._previous_heart = measurement.heart_rate

        if heart:
            heart = str(heart)[:4]

        return heart


    def read_ams(self):
        """
        Reads data from AppleMediaServices
        """
        current = time.time()
        try:
            if current - self.start > 3:
                self.track_artist = not self.track_artist
                self.start = time.time()
            if self.track_artist:
                data = self.ams.artist
            if not self.track_artist:
                data = self.ams.title
        except (RuntimeError, UnicodeError):
            data = None

        if data:
            data = data[:16] + (data[16:] and '..')

        return data


    def icon_maker(self, n, icon_x, icon_y):
        """
        Generates icons as sprites
        """
        sprite = displayio.TileGrid(self.sprite_sheet, pixel_shader=self.palette, width=1,
                                    height=1, tile_width=40, tile_height=40, default_tile=n,
                                    x=icon_x, y=icon_y)
        return sprite


    def _label_maker(self, text, x, y, font=None):
        """
        Generates labels
        """
        if not font:
            font = self.arial24
        return label.Label(font=font, x=x, y=y, text=text, color=self.WHITE, max_glyphs=30)


    def _get_y(self):
        """
        Helper function for setup_display. Gets the y values used for sprites and labels.
        """
        enabled = self.num_enabled

        if self.heart_enabled:
            self._heart_y = 45*(self.num_enabled - enabled) + 75
            enabled -= 1
        if self.speed_enabled:
            self._speed_y = 45*(self.num_enabled - enabled) + 75
            enabled -= 1
        if self.cadence_enabled:
            self._cadence_y = 45*(self.num_enabled - enabled) + 75
            enabled -= 1
        if self.ams_enabled:
            self._ams_y = 45*(self.num_enabled - enabled) + 75
            enabled -= 1


    def setup_display(self):
        """
        Prepares the display to show sensor values: Adds a header, a heading, and various sprites.
        """
        self._get_y()
        sprites = displayio.Group()

        rect = Rect(0, 0, 240, 50, fill=self.PURPLE)
        self.splash.append(rect)

        heading = label.Label(font=self.arial24, x=55, y=25, text="Pyloton", color=self.YELLOW)
        self.splash.append(heading)

        if self.heart_enabled:
            heart_sprite = self.icon_maker(0, 2, self._heart_y - 20)
            sprites.append(heart_sprite)

        if self.speed_enabled:
            speed_sprite = self.icon_maker(1, 2, self._speed_y - 20)
            sprites.append(speed_sprite)

        if self.cadence_enabled:
            cadence_sprite = self.icon_maker(2, 2, self._cadence_y - 20)
            sprites.append(cadence_sprite)

        if self.ams_enabled:
            ams_sprite = self.icon_maker(3, 2, self._ams_y - 20)
            sprites.append(ams_sprite)

        self.splash.append(sprites)

        self.display.show(self.splash)
        while self.loading_group:
            self.loading_group.pop()


    def update_display(self): #pylint: disable=too-many-branches
        """
        Updates the display to display the most recent values
        """
        if self.speed_enabled or self.cadence_enabled:
            speed, cadence = self.read_s_and_c()

        if self.heart_enabled:
            heart = self.read_heart()
            if not self._setup:
                self._hr_label = self._label_maker('{} bpm'.format(heart), 50, self._heart_y) # 75
                self.splash.append(self._hr_label)
            else:
                self._hr_label.text = '{} bpm'.format(heart)

        if self.speed_enabled:
            if not self._setup:
                self._sp_label = self._label_maker('{} mph'.format(speed), 50, self._speed_y) # 120
                self.splash.append(self._sp_label)
            else:
                self._sp_label.text = '{} mph'.format(speed)

        if self.cadence_enabled:
            if not self._setup:
                self._cadence_label = self._label_maker('{} rpm'.format(cadence), 50,
                                                        self._cadence_y)
                self.splash.append(self._cadence_label)
            else:
                self._cadence_label.text = '{} rpm'.format(cadence)

        if self.ams_enabled:
            ams = self.read_ams()
            if not self._setup:
                self._ams_label = self._label_maker('{}'.format(ams), 50, self._ams_y,
                                                    font=self.arial16)
                self.splash.append(self._ams_label)
            else:
                self._ams_label.text = '{}'.format(ams)

        self._setup = True


    def ams_remote(self):
        """
        Allows the 2 buttons and 3 capacitive touch pads in the CLUE to function as a media remote.
        """
        try:
            # Capacitive touch pad marked 0 goes to the previous track
            if self.clue.touch_0:
                self.ams.previous_track()
                time.sleep(0.25)

            # Capacitive touch pad marked 1 toggles pause/play
            if self.clue.touch_1:
                self.ams.toggle_play_pause()
                time.sleep(0.25)

            # Capacitive touch pad marked 2 advances to the next track
            if self.clue.touch_2:
                self.ams.next_track()
                time.sleep(0.25)

            # If button B (on the right) is pressed, it increases the volume
            if 'B' in self.clue.were_pressed:
                self.ams.volume_up()
                time.sleep(0.1)

            # If button A (on the left) is pressed, the volume decreases
            if 'A' in self.clue.were_pressed:
                self.ams.volume_down()
                time.sleep(0.1)
        except (RuntimeError, UnsupportedCommand, AttributeError):
            return
