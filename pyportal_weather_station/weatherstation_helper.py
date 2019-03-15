"""
Helper file for
pyportal_weatherstation.py
"""
import board
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

cwd = ("/"+__file__).rsplit('/', 1)[0] # the current working directory (where this file is)

# Fonts within /fonts folder
medium_font = cwd+"/fonts/Arial-16.bdf"
header_font = cwd+"/fonts/Collegiate-24.bdf"
glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.: '

class WeatherStation_GFX(displayio.Group):

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
        self.set_icon(self._cwd+"/icons/pyportal_splash.bmp")

        print('loading fonts...')
        self.medium_font = bitmap_font.load_font(medium_font)
        self.c_font = bitmap_font.load_font(header_font)
        self.medium_font.load_glyphs(glyphs)
        self.c_font.load_glyphs(glyphs)

        print('setting up Labels...')
        self.title_text = Label(self.c_font, text = "PyPortal Weather Station")
        self.title_text.x = 50
        self.title_text.y = 10
        self._text_group.append(self.title_text)

        self.io_status_text = Label(self.c_font, max_glyphs=30)
        self.io_status_text.x = 65
        self.io_status_text.y = 190
        self._text_group.append(self.io_status_text)

        # Set up Labels to label sensor data
        self.veml_text = Label(self.medium_font, max_glyphs=16)
        self.veml_text.x = 3
        self.veml_text.y = 40
        self._text_group.append(self.veml_text)

        self.bme_temp_humid_text = Label(self.medium_font, max_glyphs = 50)
        self.bme_temp_humid_text.x = 0
        self.bme_temp_humid_text.y = 70
        self._text_group.append(self.bme_temp_humid_text)

        self.wind_speed_text = Label(self.medium_font, max_glyphs=30)
        self.wind_speed_text.x = 0
        self.wind_speed_text.y = 100
        self._text_group.append(self.wind_speed_text)

        self.bme_pres_alt_text = Label(self.medium_font, max_glyphs=50)
        self.bme_pres_alt_text.x = 0
        self.bme_pres_alt_text.y = 130
        self._text_group.append(self.bme_pres_alt_text)

        self.sgp_text = Label(self.medium_font, max_glyphs=50)
        self.sgp_text.x = 0
        self.sgp_text.y = 155
        self._text_group.append(self.sgp_text)

        board.DISPLAY.show(self._text_group)

    def display_io_status(self, status_text):
        """Displays the current IO status.
        :param str status_text: Description of Adafruit IO status
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
        print('UV Index: ', uv_index)
        self.veml_text.text = 'UV Index: %0.1f'%uv_index

        temperature = round(bme_data[0], 1)
        print('Temperature: {0} C'.format(temperature))
        humidity = round(bme_data[1], 1)
        print('Humidity: {0}%'.format(humidity))
        if not self._celsius:
            temperature = (temperature * 9 / 5) + 32
            self.bme_temp_humid_text.text = 'Temp: {0}°F, Humid: {1}%'.format(temperature, humidity)
        else:
            self.bme_temp_humid_text.text = 'Temp: {0}°C, Humid: {1}%'.format(temperature, humidity)

        print("Wind Speed: %f m/s" % wind_speed)
        self.wind_speed_text.text = "Wind Speed %0.2fm/s" % wind_speed

        pressure = round(bme_data[2], 3)
        altitude = round(bme_data[3], 1)
        print('Altitude: %0.3f meters, Pressure: %0.2f hPa'%(altitude, pressure))
        self.bme_pres_alt_text.text = 'Alt: {0}m, Pres: {1}hPa'.format(altitude, pressure)

        print("eCO2 = %d ppm \t TVOC = %d ppb"%(sgp_data[0], sgp_data[1]))
        self.sgp_text.text = "eCO2: %d ppm, TVOC: %d ppb"%(sgp_data[0], sgp_data[1])

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
        try:
            self._icon_sprite = displayio.TileGrid(icon,
                                                   pixel_shader=displayio.ColorConverter())
        except TypeError:
            self._icon_sprite = displayio.TileGrid(icon,
                                                   pixel_shader=displayio.ColorConverter(),
                                                   position=(0,0))

        self._icon_group.append(self._icon_sprite)
        board.DISPLAY.refresh_soon()
        board.DISPLAY.wait_for_frame()
