import time
import json
import board
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

cwd = ("/"+__file__).rsplit('/', 1)[0] # the current working directory (where this file is)

small_font = cwd+"/fonts/Arial-12.bdf"
medium_font = cwd+"/fonts/Arial-16.bdf"
large_font = cwd+"/fonts/Arial-Bold-24.bdf"

class OpenWeather_Graphics(displayio.Group):
    def __init__(self, root_group, *, am_pm=True, celsius=True):
        super().__init__(max_size=2)
        self.am_pm = am_pm
        self.celsius = celsius

        root_group.append(self)
        self._icon_group = displayio.Group(max_size=1)
        self.append(self._icon_group)
        self._text_group = displayio.Group(max_size=5)
        self.append(self._text_group)

        self._icon_sprite = None
        self._icon_file = None
        self.set_icon(cwd+"/weather_background.bmp")

        self.small_font = bitmap_font.load_font(small_font)
        self.medium_font = bitmap_font.load_font(medium_font)
        self.large_font = bitmap_font.load_font(large_font)
        glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.: '
        self.small_font.load_glyphs(glyphs)
        self.medium_font.load_glyphs(glyphs)
        self.large_font.load_glyphs(glyphs)
        self.large_font.load_glyphs(('°',))  # a non-ascii character we need for sure
        self.city_text = None

        self.time_text = Label(self.medium_font, max_glyphs=8)
        self.time_text.x = 200
        self.time_text.y = 12
        self.time_text.color = 0xFFFFFF
        self._text_group.append(self.time_text)

        self.temp_text = Label(self.large_font, max_glyphs=6)
        self.temp_text.x = 200
        self.temp_text.y = 195
        self.temp_text.color = 0xFFFFFF
        self._text_group.append(self.temp_text)

        self.main_text = Label(self.large_font, max_glyphs=20)
        self.main_text.x = 10
        self.main_text.y = 195
        self.main_text.color = 0xFFFFFF
        self._text_group.append(self.main_text)

        self.description_text = Label(self.small_font, max_glyphs=60)
        self.description_text.x = 10
        self.description_text.y = 225
        self.description_text.color = 0xFFFFFF
        self._text_group.append(self.description_text)

    def display_weather(self, weather):
        weather = json.loads(weather)

        # set the icon/background
        weather_icon = weather['weather'][0]['icon']
        self.set_icon(cwd+"/icons/"+weather_icon+".bmp")

        city_name =  weather['name'] + ", " + weather['sys']['country']
        print(city_name)
        if not self.city_text:
            self.city_text = Label(self.medium_font, text=city_name)
            self.city_text.x = 10
            self.city_text.y = 12
            self.city_text.color = 0xFFFFFF
            self._text_group.append(self.city_text)

        self.update_time()

        main_text = weather['weather'][0]['main']
        print(main_text)
        self.main_text.text = main_text

        temperature = weather['main']['temp'] - 273.15 # its...in kelvin
        print(temperature)
        if self.celsius:
            self.temp_text.text = "%d °C" % temperature
        else:
            self.temp_text.text = "%d °F" % ((temperature * 9 / 5) + 32)

        description = weather['weather'][0]['description']
        description = description[0].upper() + description[1:]
        print(description)
        self.description_text.text = description
        # "thunderstorm with heavy drizzle"

    def update_time(self):
        """Fetch the time.localtime(), parse it out and update the display text"""
        now = time.localtime()
        hour = now[3]
        minute = now[4]
        format_str = "%d:%02d"
        if self.am_pm:
            if hour >= 12:
                hour -= 12
                format_str = format_str+" PM"
            else:
                format_str = format_str+" AM"
            if hour == 0:
                hour = 12
        time_str = format_str % (hour, minute)
        print(time_str)
        self.time_text.text = time_str

    def set_icon(self, filename):
        """The background image to a bitmap file.

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
