"""
Helper file for
pyportal_thermometer.py
"""
import board
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

cwd = ("/"+__file__).rsplit('/', 1)[0] # the current working directory (where this file is)

# Fonts within /fonts folder
info_font = cwd+"/fonts/Arial-16.bdf"
temperature_font = cwd+"/fonts/Nunito-Light-75.bdf"
#pylint-ignore syntax-error
glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.:°'

class Thermometer_GFX(displayio.Group):

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
        self._text_group = displayio.Group(max_size=4)
        self.append(self._text_group)

        self._icon_sprite = None
        self._icon_file = None
        self._cwd = cwd
        self.set_icon(self._cwd+"/icons/pyportal_splash.bmp")

        print('loading fonts...')
        self.info_font = bitmap_font.load_font(info_font)
        self.c_font = bitmap_font.load_font(temperature_font)
        self.info_font.load_glyphs(glyphs)
        self.c_font.load_glyphs(glyphs)

        print('setting up Labels...')
        self.temp_text = Label(self.c_font, max_glyphs=8)
        self.temp_text.x = 20
        self.temp_text.y = 80
        self._text_group.append(self.temp_text)

        self.datetime_text = Label(self.info_font, max_glyphs=40)
        self.datetime_text.x = 10
        self.datetime_text.y = 150
        self._text_group.append(self.datetime_text)


        board.DISPLAY.show(self._text_group)

    def display_date_time(self, io_time):
        """Parses and displays the time obtained from Adafruit IO, based on IP
        :param struct_time io_time: Structure used for date/time, returned from 
        """
        print('{0}/{1}/{2}, {3}:{4}'.format(io_time[1], io_time[2],
                                            io_time[0], io_time[3], io_time[4]))

        self.datetime_text.text = '{0}/{1}/{2}, {3}:{4}'.format(io_time[1], io_time[2],
                                                            io_time[0], io_time[3], io_time[4])
        board.DISPLAY.refresh_soon()
        board.DISPLAY.wait_for_frame()

    def display_io_status(self, status_text):
        """Displays the current Adafruit IO status.
        :param str status_text: Description of Adafruit IO status
        """

        board.DISPLAY.refresh_soon()
        board.DISPLAY.wait_for_frame()

    def display_temp(self, adt_data):
        """Displays the data from the ADT7410 on the.

        :param float adt_data: Value from the ADT7410
        """
        self.set_icon(self._cwd+"/icons/pyportal_neutral.bmp")

        self.temp_text.text = '%0.2f°C'%adt_data

        # change the background based on the temperature
        if adt_data > 32:
            self.set_icon(self._cwd+"/icons/pyportal_hot.bmp")
        self.set_icon(self._cwd+"/icons/pyportal_neutral.bmp")
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