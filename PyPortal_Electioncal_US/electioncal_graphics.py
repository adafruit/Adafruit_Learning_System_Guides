import time
import json
import displayio
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

cwd = ("/"+__file__).rsplit('/', 1)[0] # the current working directory (where this file is)

small_font = cwd+"/fonts/Arial-12.bdf"
medium_font = cwd+"/fonts/Arial-16.bdf"

class Electioncal_Graphics(displayio.Group):
    def __init__(self, root_group, *, am_pm=True):
        super().__init__(max_size=2)
        self.am_pm = am_pm
        root_group.append(self)
        self._icon_group = displayio.Group(max_size=1)
        self.append(self._icon_group)
        self._text_group = displayio.Group(max_size=9)
        self.append(self._text_group)

        self._icon_sprite = None
        self._icon_file = None
        self.set_icon(cwd+"/icons/us-sat.bmp")

        self.small_font = bitmap_font.load_font(small_font)
        self.medium_font = bitmap_font.load_font(medium_font)
        glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.: '
        self.small_font.load_glyphs(glyphs)
        self.medium_font.load_glyphs(glyphs)

        self.date_text = Label(self.small_font, max_glyphs=21)
        self.date_text.x = 10
        self.date_text.y = 220
        self.date_text.color = 0xFFFFFF
        self._text_group.append(self.date_text)

        self.state_text = Label(self.small_font, max_glyphs=60)
        self.state_text.x = 10
        self.state_text.y = 10
        self.state_text.color = 0xFFFFFF
        self._text_group.append(self.state_text)

        self.county_text = Label(self.small_font, max_glyphs=60)
        self.county_text.x = 10
        self.county_text.y = 35
        self.county_text.color = 0xFFFFFF
        self._text_group.append(self.county_text)

        self.date0_name_text = Label(self.small_font, max_glyphs=60)
        self.date0_name_text.x = 10
        self.date0_name_text.y = 80
        self.date0_name_text.color = 0xFFFFFF
        self._text_group.append(self.date0_name_text)

        self.date0_date_text = Label(self.medium_font, max_glyphs=11)
        self.date0_date_text.x = 10
        self.date0_date_text.y = 105
        self.date0_date_text.color = 0xFFFFFF
        self._text_group.append(self.date0_date_text)

        self.date1_name_text = Label(self.small_font, max_glyphs=60)
        self.date1_name_text.x = 10
        self.date1_name_text.y = 140
        self.date1_name_text.color = 0xFFFFFF
        self._text_group.append(self.date1_name_text)

        self.date1_date_text = Label(self.medium_font, max_glyphs=11)
        self.date1_date_text.x = 10
        self.date1_date_text.y = 165
        self.date1_date_text.color = 0xFFFFFF
        self._text_group.append(self.date1_date_text)

    def display_elections(self, electioncal_data, STATE, COUNTY):
        electioncal = json.loads(electioncal_data)

        self.update_time()
        self.state_text.text = "State: " + STATE
        self.county_text.text = "County: " + COUNTY
        self.date0_name_text.text = electioncal["dates"][0]["name"]
        self.date0_date_text.text = electioncal["dates"][0]["date"]
        self.date1_name_text.text = electioncal["dates"][1]["name"]
        self.date1_date_text.text = electioncal["dates"][1]["date"]

    def update_time(self):
        """Fetch the time.localtime(), parse it out and update the display text"""
        now = time.localtime()
        hour = now[3]
        minute = now[4]
        year = now[0]
        month = now[1]
        day = now[2]
        time_format_str = "%d:%02d"
        date_format_str = "%d-%02d-%02d"
        if self.am_pm:
            if hour >= 12:
                hour -= 12
                time_format_str = time_format_str+" PM"
            else:
                time_format_str = time_format_str+" AM"
            if hour == 0:
                hour = 12
        time_str = time_format_str % (hour, minute)
        date_str = date_format_str % (year, month, day)
        self.date_text.text = "Today is: " + date_str

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
