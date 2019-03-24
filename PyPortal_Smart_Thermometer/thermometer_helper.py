"""
GFX helper file for
thermometer.py
"""
import board
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

cwd = ("/"+__file__).rsplit('/', 1)[0] # the current working directory (where this file is)

# Fonts within /fonts folder
info_font = cwd+"/fonts/Nunito-Black-17.bdf"
temperature_font = cwd+"/fonts/Nunito-Light-75.bdf"

class Thermometer_GFX(displayio.Group):
    def __init__(self, celsius=True, usa_date=True):
        """Creates a Thermometer_GFX object.
        :param bool celsius: Temperature displayed as F or C
        :param bool usa_date: Use mon/day/year date-time formatting.
        """
        # root displayio group
        root_group = displayio.Group(max_size=20)
        board.DISPLAY.show(root_group)
        super().__init__(max_size=20)

        self._celsius = celsius
        self._usa_date = usa_date

        # create background icon group
        self._icon_group = displayio.Group(max_size=1)
        self.append(self._icon_group)
        board.DISPLAY.show(self._icon_group)
        # create text object group
        self._text_group = displayio.Group(max_size=6)
        self.append(self._text_group)

        self._icon_sprite = None
        self._icon_file = None
        self._cwd = cwd
        self.set_icon(self._cwd+"/icons/pyportal_splash.bmp")

        print('loading fonts...')
        glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.:/ '
        self.info_font = bitmap_font.load_font(info_font)
        self.info_font.load_glyphs(glyphs)

        self.c_font = bitmap_font.load_font(temperature_font)
        self.c_font.load_glyphs(glyphs)
        self.c_font.load_glyphs(('°',)) # extra glyph for temperature font

        print('setting up labels...')
        self.title_text = Label(self.info_font, text="PyPortal Thermometer")
        self.title_text.x = 55
        self.title_text.y = 15
        self._text_group.append(self.title_text)

        self.subtitle_text = Label(self.info_font, text="Analog Devices ADT7410")
        self.subtitle_text.x = 43
        self.subtitle_text.y = 35
        self._text_group.append(self.subtitle_text)

        self.temp_text = Label(self.c_font, max_glyphs=8)
        self.temp_text.x = 25
        self.temp_text.y = 110
        self._text_group.append(self.temp_text)

        self.time_text = Label(self.info_font, max_glyphs=40)
        self.time_text.x = 240
        self.time_text.y = 150
        self._text_group.append(self.time_text)

        self.date_text = Label(self.info_font, max_glyphs=40)
        self.date_text.x = 30
        self.date_text.y = 160
        self._text_group.append(self.date_text)

        self.io_status_text = Label(self.info_font, max_glyphs=40)
        self.io_status_text.x = 100
        self.io_status_text.y = 220
        self._text_group.append(self.io_status_text)

        board.DISPLAY.show(self._text_group)


    def display_date_time(self, io_time):
        """Parses and displays the time obtained from Adafruit IO, based on IP
        :param struct_time io_time: Structure used for date/time, returned from Adafruit IO.
        """
        self.time_text.text = '%02d:%02d'%(io_time[3],io_time[4])
        if not self._usa_date:
            self.date_text.text = '{0}/{1}/{2}'.format(io_time[2], io_time[1], io_time[0])
        else:
            self.date_text.text = '{0}/{1}/{2}'.format(io_time[1], io_time[2], io_time[0])

    def display_io_status(self, status_text):
        """Displays the current Adafruit IO status.
        :param str status_text: Description of Adafruit IO status
        """
        self.io_status_text.text = status_text

    def display_temp(self, adt_data):
        """Displays the data from the ADT7410 on the.
        :param float adt_data: Value from the ADT7410
        """
        if not self._celsius:
            adt_data = (adt_data * 9 / 5) + 32
            print('Temperature: %0.2f°F'%adt_data)
            if adt_data >= 212:
                self.temp_text.color = 0xFD2EE
            elif adt_data <= 32:
                self.temp_text.color = 0xFF0000
            self.temp_text.text = '%0.2f°F'%adt_data
        else:
            print('Temperature: %0.2f°C'%adt_data)
            if adt_data <= 0:
                self.temp_text.color = 0xFD2EE
            elif adt_data >= 100:
                self.temp_text.color = 0xFF0000
            self.temp_text.text = '%0.2f°C'%adt_data

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
  