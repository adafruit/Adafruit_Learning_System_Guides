"""
Helper file for
pyportal_weathermeter.py
"""
import board
import displayio
from adafruit_display_text.text_area import TextArea
from adafruit_bitmap_font import bitmap_font

cwd = ("/"+__file__).rsplit('/', 1)[0] # the current working directory (where this file is)

# Fonts within /fonts folder
medium_font = cwd+"/fonts/Arial-16.bdf"
header_font = cwd+"/fonts/Collegiate-24.bdf"

class WeatherMeter_GFX(displayio.Group):
    def __init__(self, celsius=True):
        # root displayio group
        root_group = displayio.Group(max_size=20)
        board.DISPLAY.show(root_group)
        super().__init__(max_size=20)
        self._celsius = celsius

        # create background icon group
        self._icon_group = displayio.Group(max_size=1)
        self.append(self._icon_group)
        board.DISPLAY.show(self._icon_group)
        
        # create text object group
        self._text_group = displayio.Group(max_size=8)
        self.append(self._text_group)

        self._icon_sprite = None
        self._icon_file = None
        self._cwd = cwd
        self.set_icon(self._cwd+"/pyportal_splash.bmp")

        print('loading fonts...')
        self.medium_font = bitmap_font.load_font(medium_font)
        self.c_font = bitmap_font.load_font(header_font)
        glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,°.: '
        self.medium_font.load_glyphs(glyphs)
        self.c_font.load_glyphs(glyphs)

        print('setting up textareas...')
        self.title_text = TextArea(self.c_font, width=30)
        self.title_text.x = 35
        self.title_text.y = 0
        self.title_text.color = 0xFFFFFF
        self._text_group.append(self.title_text)

        self.io_status_text = TextArea(self.c_font, width=30)
        self.io_status_text.x = 100
        self.io_status_text.y = 190
        self.io_status_text.color = 0xFFFFFF
        self._text_group.append(self.io_status_text)

        # Set up TextAreas to label sensor data
        self.veml_text = TextArea(self.medium_font, width=16)
        self.veml_text.x = 3
        self.veml_text.y = 40
        self.veml_text.color = 0xFFFFFF
        self._text_group.append(self.veml_text)

        self.bme_temp_humid_text = TextArea(self.medium_font, width = 70)
        self.bme_temp_humid_text.x = 0
        self.bme_temp_humid_text.y = 70
        self.bme_temp_humid_text.color = 0xFFFFFF
        self._text_group.append(self.bme_temp_humid_text)

        self.wind_speed_text = TextArea(self.medium_font, width=30)
        self.wind_speed_text.x = 0
        self.wind_speed_text.y = 100
        self.wind_speed_text.color = 0xFFFFFF
        self._text_group.append(self.wind_speed_text)

        self.bme_pres_alt_text = TextArea(self.medium_font, width=70)
        self.bme_pres_alt_text.x = 0
        self.bme_pres_alt_text.y = 130
        self.bme_pres_alt_text.color = 0xFFFFFF
        self._text_group.append(self.bme_pres_alt_text)

        self.sgp_text = TextArea(self.medium_font, width=70)
        self.sgp_text.x = 0
        self.sgp_text.y = 155
        self.sgp_text.color = 0xFFFFFF
        self._text_group.append(self.sgp_text)


        self.title_text.text = "PyPortal Weather Station"
        board.DISPLAY.show(self._text_group)
        print("Text area setup!")

    def display_io_status(self, status_text):
        """Displays the current IO status
        :param str status_text: Description of current IO status
        """
        self.io_status_text.text = status_text
        board.DISPLAY.refresh_soon()
        board.DISPLAY.wait_for_frame()

    def display_data(self, uv_index, bme_data, sgp_data, wind_speed):
        """Displays the data from the sensors attached
        to the weathermeter pyportal and sends the data to Adafruit IO.

        :param float uv_index: VEML6075 uv index level.
        :param list sgp_data: ECO2 and TVOC data from SGP30 sensor.
        :param list bme_data: List of env. data from the BME280 sensor.
        :param float wind_speed: Wind speed from anemometer.
        """
        # VEML6075
        print('UV Index: ', uv_index)
        self.veml_text.text = 'UV Index: %0.1f'%uv_index

        # Parse out the BME280 data ordered list and format for display
        temperature = round(bme_data[0], 1)
        print('Temperature: {0} C'.format(temperature))
        humidity = round(bme_data[1], 1)
        print('Humidity: {0}%'.format(humidity))
        if not self._celsius:
            temperature = (temperature * 9 / 5) + 32
            self.bme_temp_humid_text.text = 'Temp.: %0.1f°F, Humid: %0.1f%' % (str(temperature), humidity)
        else:
            self.bme_temp_humid_text.text = 'Temp.: {0}°C, Humid: {1}'.format(temperature, humidity)
        pressure = round(bme_data[2], 3)
        altitude = round(bme_data[3], 1)
        print('Altitude: %0.3f meters, Pressure: %0.2f hPa' % (altitude, pressure))
        self.bme_pres_alt_text.text = 'Alt: {0}m, Pres: {1}hPa'.format(altitude, pressure)

        # Anemometer
        print("Wind Speed: %f m/s" % wind_speed)
        self.wind_speed_text.text = "Wind Speed %0.2fm/s" % wind_speed

        # SGP30
        print("eCO2 = %d ppm \t TVOC = %d ppb" % (sgp_data[0], sgp_data[1]))
        self.sgp_text.text = "eCO2: %d ppm, TVOC: %d ppb" %  (sgp_data[0], sgp_data[1])
        board.DISPLAY.refresh_soon()
        board.DISPLAY.wait_for_frame()

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
