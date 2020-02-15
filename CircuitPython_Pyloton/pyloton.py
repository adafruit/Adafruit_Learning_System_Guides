import time
import adafruit_ble
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.advertising.standard import SolicitServicesAdvertisement
import displayio
import adafruit_imageload
from adafruit_ble_cycling_speed_and_cadence import CyclingSpeedAndCadenceService
from adafruit_ble_heart_rate import HeartRateService
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label

from adafruit_ble_apple_media import AppleMediaService
import board
import digitalio
import gamepad
import touchio

class clue:
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
        self._b=digitalio.DigitalInOut(board.BUTTON_B)
        self._b.switch_to_input(pull=digitalio.Pull.UP)
        self._gamepad = gamepad.GamePad(self._a, self._b)

    def were_pressed(self):
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

    def touch_0(self):
        return self._touch(0)

    def touch_1(self):
        return self._touch(1)

    def touch_2(self):
        return self._touch(2)



class Pyloton:

    _previous_wheel = 0
    _previous_crank = 0

    _previous_revolutions = 0
    _previous_crank_rev = 0

    _previous_speed = 0
    _previous_cadence = 0

    _previous_heart = 0

    splash = displayio.Group(max_size=25)

    setup = False

    YELLOW = 0xFCFF00
    PURPLE = 0x64337E
    WHITE = 0xFFFFFF

    loading_group = displayio.Group()

    cyc_connections = []
    cyc_services = []

    start = time.time()

    track_artist = True

    i = 0
    j = 0

    def __init__(self, ble, display, circ, heart=True, speed=True, cad=True, ams=True, debug=False):
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
        self._load_fonts()

        self.sprite_sheet, self.palette = adafruit_imageload.load("/sprite_sheet.bmp",
                                                                  bitmap=displayio.Bitmap,
                                                                  palette=displayio.Palette)


    def show_splash(self):
        """
        Shows the loading screen
        """
        if self.debug:
            return
        with open('biketrace.bmp', 'rb') as bitmap_file:
            bitmap1 = displayio.OnDiskBitmap(bitmap_file)

            tile_grid = displayio.TileGrid(bitmap1, pixel_shader=displayio.ColorConverter())


            self.loading_group.append(tile_grid)

            self.display.show(self.loading_group)

            status_heading = label.Label(font=self.arial16, x=80, y=175,
                                         text="Status", color=self.YELLOW)

            rect = Rect(0, 165, 240, 75, fill=self.PURPLE)

            self.loading_group.append(rect)
            self.loading_group.append(status_heading)

            self.display.show(self.loading_group)
            time.sleep(.01)


    def _load_fonts(self):
        """
        Loads fonts
        """
        self.arial12 = bitmap_font.load_font("/fonts/Arial-12.bdf")
        self.arial16 = bitmap_font.load_font("/fonts/Arial-16.bdf")
        self.arial24 = bitmap_font.load_font("/fonts/Arial-Bold-24.bdf")


    def _status_update(self, message):
        """
        Displays status updates
        """
        if self.debug:
            print(message)
            return

        text_group = displayio.Group()
        if len(message) > 25:
            status = label.Label(font=self.arial12, x=10, y=200,
                                 text=message[:25], color=self.YELLOW)
            status1 = label.Label(font=self.arial12, x=10, y=220,
                                  text=message[25:], color=self.YELLOW)

            text_group.append(status)
            text_group.append(status1)
        else:
            status = label.Label(font=self.arial12, x=10, y=200, text=message, color=self.YELLOW)
            text_group.append(status)



        if len(self.loading_group) < 4:
            self.loading_group.append(text_group)
        else:
            self.loading_group[3] = text_group

        self.display.show(self.loading_group)
        time.sleep(0.01)


    def timeout(self):
        """
        Displays Timeout on screen when pyloton has been searching for a sensor for too long
        """
        self._status_update("Timeout")
        time.sleep(3)


    def heart_connect(self):
        """
        Connects to heart rate sensor
        """
        self._status_update("Scanning...")
        for adv in self.ble.start_scan(ProvideServicesAdvertisement, timeout=5):
            if HeartRateService in adv.services:
                self._status_update("Found a HeartRateService advertisement")
                self.hr_connection = self.ble.connect(adv)
                self._status_update("Connected")
                break
        self.ble.stop_scan()
        if self.hr_connection:
            self.hr_service = self.hr_connection[HeartRateService]
        return self.hr_connection

    def ams_connect(self):
        self._status_update("Connect your phone now")
        radio = adafruit_ble.BLERadio()
        a = SolicitServicesAdvertisement()
        a.solicited_services.append(AppleMediaService)
        radio.start_advertising(a)

        while not radio.connected:
            pass

        self._status_update("Connected")

        known_notifications = set()

        for connection in radio.connections:
            if not connection.paired:
                connection.pair()
                self._status_update("paired")

        self.ams = connection[AppleMediaService]

        self.radio = radio


    def speed_cad_connect(self):
        """
        Connects to speed and cadence sensor
        """
        self._status_update("Scanning...")
        # Save advertisements, indexed by address
        advs = {}
        for adv in self.ble.start_scan(ProvideServicesAdvertisement, timeout=5):
            if CyclingSpeedAndCadenceService in adv.services:
                self._status_update("found a CyclingSpeedAndCadenceService advertisement")
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
            self._status_update("Connected {}".format(len(self.cyc_connections)))


        self.cyc_services = []
        for conn in self.cyc_connections:

            self.cyc_services.append(conn[CyclingSpeedAndCadenceService])
        self._status_update("Finishing up...")
        return self.cyc_connections


    def read_s_and_c(self):
        """
        Reads data from the speed and cadence sensor
        """
        speed = self._previous_speed
        cadence = self._previous_cadence
        for conn, svc in zip(self.cyc_connections, self.cyc_services):
            if conn.connected:
                values = svc.measurement_values
                if values is not None:
                    if values.last_wheel_event_time:
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
                            self.i = 0
                        else:
                            self.i += 1
                            if self.i >= 3:
                                speed = 0
                        self._previous_wheel = values.last_wheel_event_time

                    if values.last_crank_event_time:
                        crank_diff = values.last_crank_event_time - self._previous_crank
                        crank_rev_diff =values.cumulative_crank_revolutions-self._previous_crank_rev

                        if crank_rev_diff:
                            # Rotations per minute is 60 times the amount of revolutions since the
                            # last update over the time since the last update
                            cadence = round(60*(crank_rev_diff/(crank_diff/1024)), 1)
                            if cadence < 0:
                                cadence = self._previous_cadence
                            self._previous_cadence = cadence
                            self._previous_crank_rev = values.cumulative_crank_revolutions
                            self.j = 0
                        else:
                            self.j += 1
                            if self.j >= 3:
                                cadence = 0
                        self._previous_crank = values.last_crank_event_time

                elif self.j >= 3 or self.i >= 3:
                    if self.j > 3:
                        cadence = 0
                    if self.i > 3:
                        speed = 0
            else:
                speed=cadence=0
        return speed, cadence


    def read_heart(self):
        """
        Reads date from the heart rate sensor
        """
        measurement = self.hr_service.measurement_values
        if measurement is None:
            heart = self._previous_heart
        else:
            heart = measurement.heart_rate
            self._previous_heart = measurement.heart_rate
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
        except RuntimeError:
            data = None

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
            self.heart_y = 45*(self.num_enabled - enabled) + 75
            enabled -= 1

        if self.speed_enabled:
            self.speed_y = 45*(self.num_enabled - enabled) + 75
            enabled -= 1

        if self.cadence_enabled:
            self.cad_y = 45*(self.num_enabled - enabled) + 75
            enabled -= 1

        if self.ams_enabled:
            self.ams_y = 45*(self.num_enabled - enabled) + 75
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
            heart_sprite = self.icon_maker(0, 2, self.heart_y - 20)
            sprites.append(heart_sprite)

        if self.speed_enabled:
            speed_sprite = self.icon_maker(1, 2, self.speed_y - 20)
            sprites.append(speed_sprite)

        if self.cadence_enabled:
            cadence_sprite = self.icon_maker(2, 2, self.cad_y - 20)
            sprites.append(cadence_sprite)

        if self.ams_enabled:
            ams_sprite = self.icon_maker(3, 2, self.ams_y - 20)
            sprites.append(ams_sprite)

        self.splash.append(sprites)

        self.display.show(self.splash)
        while len(self.loading_group):
            self.loading_group.pop()


    def update_display(self):
        """
        Updates the display to display the most recent values
        """
        if self.speed_enabled or self.cadence_enabled:
            speed, cadence = self.read_s_and_c()


        if self.heart_enabled:
            heart = self.read_heart()
            if not self.setup:
                self.hr_label = self._label_maker('{} bpm'.format(heart), 50, self.heart_y) # 75
                self.splash.append(self.hr_label)
            else:
                self.hr_label.text = '{} bpm'.format(heart)
                #self.splash[3-(4-self.num_enabled)] = self.hr_label


        if self.speed_enabled:
            if not self.setup:
                self.sp_label = self._label_maker('{} mph'.format(speed), 50, self.speed_y) # 120
                self.splash.append(self.sp_label)
            else:
                self.sp_label.text='{} mph'.format(speed)
                #self.splash[4-(4-self.num_enabled)] = self.sp_label


        if self.cadence_enabled:
            if not self.setup:
                self.cad_label = self._label_maker('{} rpm'.format(cadence), 50, self.cad_y) # 165
                self.splash.append(self.cad_label)
            else:
                self.cad_label.text = '{} rpm'.format(cadence)
                #self.splash[5-(4-self.num_enabled)] = self.cad_label


        if self.ams_enabled:
            ams = self.read_ams()
            if not self.setup:
                self.ams_label = self._label_maker('{}'.format(ams), 50, self.ams_y, font=self.arial16) # 210
                self.splash.append(self.ams_label)
            else:
                self.ams_label.text = '{}'.format(ams)
                #self.splash[6-(4-self.num_enabled)] = self.ams_label


        self.setup=True

#        self.display.show(self.splash)

    def ams_remote(self):
        # Capacitive touch pad marked 0 goes to the previous track
        if clue.touch_0:
            self.ams.previous_track()
            time.sleep(0.25)

        # Capacitive touch pad marked 1 toggles pause/play
        if clue.touch_1:
            self.ams.toggle_play_pause()
            time.sleep(0.25)

        # Capacitive touch pad marked 2 advances to the next track
        if clue.touch_2:
            self.ams.next_track()
            time.sleep(0.25)

        # If button B (on the right) is pressed, it increases the volume
        if 'B' in clue.were_pressed:
            self.ams.volume_up()
            time.sleep(0.1)

        # If button A (on the left) is pressed, the volume decreases
        if 'A' in clue.were_pressed:
            self.ams.volume_down()
            time.sleep(0.1)
