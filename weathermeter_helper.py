"""
Helper file for
pyportal_weathermeter.py
"""
import time
import board
import audioio
import displayio
import digitalio
from adafruit_display_text.text_area import TextArea
from adafruit_bitmap_font import bitmap_font
from adafruit_io.adafruit_io import RESTClient, AdafruitIO_RequestError

cwd = ("/"+__file__).rsplit('/', 1)[0] # the current working directory (where this file is)

small_font = cwd+"/fonts/Arial-12.bdf"
medium_font = cwd+"/fonts/Arial-16.bdf"
large_font = cwd+"/fonts/Arial-Bold-24.bdf"
coll_font = cwd+"/fonts/Collegiate-24.bdf"

# TODO: Spec out a class for the anemometer a-to-d conversion

class WeatherMeter_IO():
    def __init__(self, user, key, wifi):
        """Lightweight helper class for Adafruit IO CircuitPython
        :param str user: Adafruit IO User
        :param str key: Adafruit IO Active Key
        :param WiFiManager wifi: WiFiManager Object 
        """
        self._io_client = RESTClient(user, key, wifi)
        try: # Attempt to get feeds from IO.
            self._temperature_feed = self._io_client.get_feed('temperature')
            self._gas_feed = self._io_client.get_feed('gas')
            self._humidity_feed = self._io_client.get_feed('humidity')
            self._pressure_feed = self._io_client.get_feed('pressure')
            self._altitude_feed = self._io_client.get_feed('altitude')
            self._uv_index_feed = self._io_client.get_feed('uvindex')
        except AdafruitIO_RequestError: # If feeds do not exist, create them
            self._temperature_feed = self._io_client.create_new_feed('temperature')
            self._gas_feed = self._io_client.create_new_feed('gas')
            self._humidity_feed = self._io_client.create_new_feed('humidity')
            self._pressure_feed = self._io_client.create_new_feed('pressure')
            self._altitude_feed = self._io_client.create_new_feed('altitude')
            self._uv_index_feed = self._io_client.create_new_feed('uvindex')

    def send_data(self, uv_index, sgp_data, bme_data):
        """Send data from weathermeter sensors to adafruit io
        """
        try:
            self._io_client.send_data(self._uv_index_feed['key'], uv_index)
            self._io_client.send_data(self._temperature_feed['key'], bme_data[0])
            self._io_client.send_data(self._humidity_feed['key'], bme_data[1])
            self._io_client.send_data(self._pressure_feed['key'], bme_data[2])
            self._io_client.send_data(self._altitude_feed['key'], bme_data[3])
            # TODO: Add SGP30 self._io_client.send_data(self._gas_feed['key'], sgp_data[0])
        except AdafruitIO_RequestError:
            raise AdafruitIO_RequestError('Could not send data to Adafruit IO!')

class WeatherMeter_GFX(displayio.Group):
    def __init__(self, celsius=True):
        # root group
        root_group = displayio.Group(max_size=9)
        board.DISPLAY.show(root_group)
        super().__init__(max_size=2)
        self._celsius = celsius

        # create background icon group
        self._icon_group = displayio.Group(max_size=1)
        self.append(self._icon_group)
        board.DISPLAY.show(self._icon_group)
        
        # create text object group
        self._text_group = displayio.Group(max_size=9)
        self.append(self._text_group)

        self._icon_sprite = None
        self._icon_file = None
        self._cwd = cwd
        self.set_icon(self._cwd+"/pyportal_splash.bmp")

        self.small_font = bitmap_font.load_font(small_font)
        self.medium_font = bitmap_font.load_font(medium_font)
        self.large_font = bitmap_font.load_font(large_font)
        glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,°.: '
        self.small_font.load_glyphs(glyphs)
        self.medium_font.load_glyphs(glyphs)
        self.large_font.load_glyphs(glyphs)
        
        # experiment with Collegiate-24.bdf font!
        self.c_font = bitmap_font.load_font(coll_font)
        self.c_font.load_glyphs(glyphs)

        # Set up TextAreas for labels and headers
        self.title_text = TextArea(self.c_font, width=30)
        self.title_text.x = 30
        self.title_text.y = 0
        self.title_text.color = 0xFFFFFF
        self._text_group.append(self.title_text)

        self.io_status_text = TextArea(self.c_font, width=30)
        self.io_status_text.x = 0
        self.io_status_text.y = 180
        self.io_status_text.color = 0xFFFFFF
        self._text_group.append(self.io_status_text)

        # Set up TextAreas to label sensor data
        self.veml_text = TextArea(self.medium_font, width=16)
        self.veml_text.x = 0
        self.veml_text.y = 40
        self.veml_text.color = 0xFFFFFF
        self._text_group.append(self.veml_text)

        self.bme_temp_humid_text = TextArea(self.medium_font, width = 70)
        self.bme_temp_humid_text.x = 0
        self.bme_temp_humid_text.y = 60
        self.bme_temp_humid_text.color = 0xFFFFFF
        self._text_group.append(self.bme_temp_humid_text)

        self.sgp_text = TextArea(self.medium_font, width=25)
        self.sgp_text.x = 0
        self.sgp_text.y = 80
        self.sgp_text.color = 0xFFFFFF
        self._text_group.append(self.sgp_text)

        self.bme_pres_alt_text = TextArea(self.medium_font, width=70)
        self.bme_pres_alt_text.x = 0
        self.bme_pres_alt_text.y = 100
        self.bme_pres_alt_text.color = 0xFFFFFF
        self._text_group.append(self.bme_pres_alt_text)

        self.wind_speed_text = TextArea(self.medium_font, width=70)
        self.wind_speed_text.x = 0
        self.wind_speed_text.y = 125
        self.wind_speed_text.color = 0xFFFFFF
        self._text_group.append(self.wind_speed_text)

        board.DISPLAY.show(self._text_group)
        self.title_text.text = "PyPortal Weather Station"


    def display_data(self, uv_index, bme_data, sgp_data, wind_speed, io_helper):
        """Displays the data from the sensors attached
        to the weathermeter pyportal and sends the data to Adafruit IO.

        :param float uv_index: VEML6075 uv index level.
        :param list sgp_data: ECO2 and TVOC data from SGP30 sensor.
        :param list bme_data: List of env. data from the BME280 sensor.
        :param float wind_speed: Wind speed from anemometer.
        :param WeatherMeter_IO io_helper: IO Helper object.
        """
        print('UV Index: ', uv_index)
        self.veml_text.text = 'UV Index: ' + str(uv_index)
        # Parse out the BME280 data ordered list and format for display
        temperature = round(bme_data[0], 1)
        print('Temperature: {0} C'.format(temperature))
        humidity = round(bme_data[1], 1)
        print('Humidity: {0}%'.format(humidity))
        if not self._celsius:
            temperature = (temperature * 9 / 5) + 32
            self.bme_temp_humid_text.text = 'Temp.: %0.1f°F, Humid: %0.1f%' % (str(temperature), humidity)
        else:
            self.bme_temp_humid_text.text = 'Temp.: %0.1f°C, Humid: 0.1f%' % (str(temperature), humidity)
        pressure = round(bme_data[2], 3)
        altitude = round(bme_data[3], 1)
        print('Altitude: %0.3f meters, Pressure: %0.2f hPa' % (altitude, pressure))
        self.bme_pres_alt_text.text = 'Alt: {0}m\nPres: {1}hPa'.format(altitude, pressure)

        # SGP30
        print("eCO2 = %d ppm \t TVOC = %d ppb" % (sgp_data[0], sgp_data[1]))
        self.sgp_text.text = "eCO2: %d ppm, TVOC: %d ppb" %  (sgp_data[0], sgp_data[1])

        # Anemometer
        print("Wind Speed: %f m/s" % wind_speed)
        self.wind_speed_text.text = "Wind Speed %0.2f m/s" % wind_speed

        # now that the data is displayed on the pyportal, let's send it to IO!
        try:
            print('Sending data to io...')
            self.io_status_text.text = "Sending data to Adafruit IO..."
            io_helper.send_data(uv_index, bme_data, sgp_data)
        except AdafruitIO_RequestError as E:
            raise AdafruitIO_RequestError('Error: ', e)
        self.set_icon(self._cwd+"/io_sending.bmp")
        print('Data sent!')
        self.io_status_text.text = "Data sent!"


    def set_icon(self, filename):
        """Sets the background image to a bitmap file.

        :param filename: The filename of the chosen icon
        """
        print("Set icon to ", filename)
        if self._icon_group:
            self._icon_group.pop()

        if not filename:
            return  # we're done, no icon desired
        if self._icon_file:
            self._icon_file.close()
        self._icon_file = open(filename, "rb")
        icon = displayio.OnDiskBitmap(self._icon_file)
        self._icon_sprite = displayio.TileGrid(icon,
                                               pixel_shader=displayio.ColorConverter(),
                                               position=(0, 0))

        self._icon_group.append(self._icon_sprite)
        board.DISPLAY.refresh_soon()
        board.DISPLAY.wait_for_frame()
