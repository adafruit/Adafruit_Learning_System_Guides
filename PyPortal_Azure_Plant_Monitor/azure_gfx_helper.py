"""
GFX Helper for PyPortal Azure IoT Plant Monitor
"""
import board
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

cwd = ("/"+__file__).rsplit('/', 1)[0] # the current working directory (where this file is)

# Fonts within /fonts folder
main_font = cwd+"/fonts/EarthHeart-26.bdf"
data_font = cwd+"/fonts/Collegiate-50.bdf"

class Azure_GFX(displayio.Group):
    def __init__(self, is_celsius=True):
        """Creates an Azure_GFX object.
        :param bool is_celsius: Temperature displayed in Celsius.
        """
        # root displayio group
        root_group = displayio.Group(max_size=23)
        board.DISPLAY.show(root_group)
        super().__init__(max_size=15)

        # temperature display option
        self._is_celsius = is_celsius

        # create background icon group
        self._icon_group = displayio.Group(max_size=3)
        self.append(self._icon_group)
        board.DISPLAY.show(self._icon_group)
        # create text object group
        self._text_group = displayio.Group(max_size=9)
        self.append(self._text_group)

        self._icon_sprite = None
        self._icon_file = None
        self._cwd = cwd
        self.set_icon(self._cwd+"/images/azure_splash.bmp")

        print('loading fonts...')
        glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.: '
        data_glyphs = b'012345678-,.:/FC'
        self.main_font = bitmap_font.load_font(main_font)
        self.main_font.load_glyphs(glyphs)
        self.data_font = bitmap_font.load_font(data_font)
        self.data_font.load_glyphs(data_glyphs)
        self.data_font.load_glyphs(('°',)) # extra glyph for temperature font

        print('setting up labels...')
        self.title_text = Label(self.main_font, text="Azure Plant Monitor")
        self.title_text.x = 35
        self.title_text.y = 25
        self._text_group.append(self.title_text)

        self.temp_label = Label(self.main_font, text="Temperature")
        self.temp_label.x = 0
        self.temp_label.y = 65
        self._text_group.append(self.temp_label)

        self.temp_text = Label(self.data_font, max_glyphs=10)
        self.temp_text.x = 200
        self.temp_text.y = 85
        self._text_group.append(self.temp_text)

        self.moisture_label = Label(self.main_font, text="Moisture Level")
        self.moisture_label.x = 0
        self.moisture_label.y = 135
        self._text_group.append(self.moisture_label)

        self.moisture_text = Label(self.data_font, max_glyphs=10)
        self.moisture_text.x = 200
        self.moisture_text.y = 175
        self._text_group.append(self.moisture_text)

        self.azure_status_text = Label(self.main_font, max_glyphs=15)
        self.azure_status_text.x = 65
        self.azure_status_text.y = 225
        self._text_group.append(self.azure_status_text)

        board.DISPLAY.show(self._text_group)


    def display_azure_status(self, status_text):
        """Displays the system status on the PyPortal
        :param str status_text: Description of Azure IoT status
        """
        self.azure_status_text.text = status_text

    def display_moisture(self, moisture_data):
        """Displays the moisture from the Stemma Soil Sensor.
        :param int moisture_data: Moisture value
        """
        print('Moisture Level: ', moisture_data)
        self.moisture_text.text = str(moisture_data)

    def display_temp(self, temp_data):
        """Displays the temperature from the Stemma Soil Sensor.
        :param float temp_data: Temperature value.
        """
        if not self._is_celsius:
            temp_data = (temp_data * 9 / 5) + 32 - 15
            print('Temperature: %0.0f°F'%temp_data)
            if temp_data >= 212:
                self.temp_text.color = 0xFD2EE
            elif temp_data <= 32:
                self.temp_text.color = 0xFF0000
            self.temp_text.text = '%0.0f°F'%temp_data
            temp_data = '%0.0f'%temp_data
            return int(temp_data)
        else:
            print('Temperature: %0.0f°C'%temp_data)
            if temp_data <= 0:
                self.temp_text.color = 0xFD2EE
            elif temp_data >= 100:
                self.temp_text.color = 0xFF0000
            self.temp_text.text = '%0.0f°C'%temp_data
            temp_data = '%0.0f'%temp_data
            return int(temp_data)

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
  