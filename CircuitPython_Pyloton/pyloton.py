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
        return self.hr_connection

    def ams_connect(self):
        self.radio = adafruit_ble.BLERadio()
        a = SolicitServicesAdvertisement()
        a.solicited_services.append(AppleMediaService)
        self.radio.start_adversising(a)

        while not self.radio.connected:
            pass

        print("connected")

        for connection in self.radio.connections:
            if not connection.paired:
                connection.pair()
                print("paired")
        known_notifications = set()

        return self.radio


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
                            self._previous_speed = speed
                            self._previous_revolutions = values.cumulative_wheel_revolutions
                        self._previous_wheel = values.last_wheel_event_time

                    if values.last_crank_event_time:
                        crank_diff = values.last_crank_event_time - self._previous_crank
                        crank_rev_diff =values.cumulative_crank_revolutions-self._previous_crank_rev

                        if crank_rev_diff:
                            # Rotations per minute is 60 times the amount of revolutions since the
                            # last update over the time since the last update
                            cadence = round(60*(crank_rev_diff/(crank_diff/1024)), 1)
                            self._previous_cadence = cadence
                            self._previous_crank_rev = values.cumulative_crank_revolutions

                        self._previous_crank = values.last_crank_event_time
                return speed, cadence
            return 0, 0


    def read_heart(self, hr_service):
        """
        Reads date from the heart rate sensor
        """
        measurement = hr_service.measurement_values
        if measurement is None:
            heart = self._previous_heart
        else:
            heart = measurement.heart_rate
            self._previous_heart = measurement.heart_rate
        return heart


    def icon_maker(self, n, icon_x, icon_y):
        """
        Generates icons as sprites
        """
        sprite = displayio.TileGrid(self.sprite_sheet, pixel_shader=self.palette, width=1,
                                    height=1, tile_width=40, tile_height=40, default_tile=n,
                                    x=icon_x, y=icon_y)
        return sprite


    def _label_maker(self, text, x, y):
        """
        Generates labels
        """
        return label.Label(font=self.arial24, x=x, y=y, text=text, color=self.WHITE)


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

        heading = label.Label(font=self.arial24, x=55, y=25, text="PyLoton", color=self.YELLOW)
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


    def update_display(self, hr_service):
        """
        Updates the display to display the most recent values
        """
        heart = self.read_heart(hr_service)
        speed, cadence = self.read_s_and_c()

        if self.heart_enabled:
            hr_label = self._label_maker('{} bpm'.format(heart), 50, self.heart_y) # 75
            if self.setup:
                self.splash[3] = hr_label
            else:
                self.splash.append(hr_label)

        if self.speed_enabled:
            sp_label = self._label_maker('{} mph'.format(speed), 50, self.speed_y) # 120
            if self.setup:
                self.splash[4] = sp_label
            else:
                self.splash.append(sp_label)


        if self.cadence_enabled:
            cad_label = self._label_maker('{} rpm'.format(cadence), 50, self.cad_y) # 165
            if self.setup:
                self.splash[5] = cad_label
            else:
                self.splash.append(cad_label)

        if self.ams_enabled:
            ams_label = self._label_maker('None', 50, self.ams_y) # 210
            if self.setup:
                self.splash[6] = ams_label
            else:
                self.splash.append(ams_label)


        self.setup=True

        self.display.show(self.splash)
