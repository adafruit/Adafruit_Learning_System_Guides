"""
GFX helper file for
wake_up_light.py.py
"""
import board
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

cwd = ("/"+__file__).rsplit('/', 1)[0] # the current working directory (where this file is)

# Fonts within /fonts folder
info_font = cwd+"/fonts/Nunito-Black-17.bdf"
time_font = cwd+"/fonts/Nunito-Light-75.bdf"

get_up_time = "6:30"
get_up_time_text = "Wake up at: " + get_up_time + "am"
light_on_time_text = "Light starting at: " # - 30 minutes? how?

class Thermometer_GFX(displayio.Group):
    def __init__(self, celsius=True, usa_date=True):
        """Creates a Thermometer_GFX object.
        :param bool usa_date: Use mon/day/year date-time formatting.
        """
        # root displayio group
        root_group = displayio.Group(max_size=20)
        board.DISPLAY.show(root_group)
        super().__init__(max_size=20)

        self._usa_date = usa_date

        # create text object group
        self._text_group = displayio.Group(max_size=6)
        self.append(self._text_group)

        self._cwd = cwd

        print('loading fonts...')
        glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.:/ '
        self.info_font = bitmap_font.load_font(info_font)
        self.info_font.load_glyphs(glyphs)

        self.time_font = bitmap_font.load_font(time_font)
        self.time_font.load_glyphs(glyphs)

        print('setting up labels...')
        self.title_text = Label(self.info_font, text="PyPortal Wake-Up Light")
        self.title_text.x = 15
        self.title_text.y = 15
        self._text_group.append(self.title_text)

        # Wake up time
        self.subtitle_text = Label(self.info_font, text= get_up_time_text)
        self.subtitle_text.x = 15
        self.subtitle_text.y = 200
        self._text_group.append(self.subtitle_text)

        #Light on time - how to subtract 30 min from time string
        self.subtitle2_text = Label(self.info_font, text= light_on_time_text)
        self.subtitle2_text.x = 15
        self.subtitle2_text.y = 240
        # self._text_group.append(self.subtitle2_text)

        # Time
        self.time_text = Label(self.time_font, max_glyphs=40)
        self.time_text.x = 65
        self.time_text.y = 120
        self._text_group.append(self.time_text)

        # Date
        self.date_text = Label(self.info_font, max_glyphs=40)
        self.date_text.x = 30
        self.date_text.y = 160
        self._text_group.append(self.date_text)

        board.DISPLAY.show(self._text_group)


    def display_date_time(self, io_time):
        """Parses and displays the time obtained from Adafruit IO, based on IP
        :param struct_time io_time: Structure used for date/time, returned from Adafruit IO.
        """
        self.time_text.text = '%02d:%02d'%(io_time[3],io_time[4])
        '''
        # not siplaying date just yet
        if not self._usa_date:
            self.date_text.text = '{0}/{1}/{2}'.format(io_time[2], io_time[1], io_time[0])
        else:
            self.date_text.text = '{0}/{1}/{2}'.format(io_time[1], io_time[2], io_time[0])
        '''