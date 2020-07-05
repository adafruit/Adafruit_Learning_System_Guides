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
        self.set_icon(cwd+"/icons/electioncal.bmp")

        self.small_font = bitmap_font.load_font(small_font)
        self.medium_font = bitmap_font.load_font(medium_font)
        glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.: '
        self.small_font.load_glyphs(glyphs)
        self.medium_font.load_glyphs(glyphs)

        self.date_text = Label(self.small_font, max_glyphs=21)
        self.date_text.x = 15
        self.date_text.y = 195
        self.date_text.color = 0xFFFFFF
        self._text_group.append(self.date_text)

        self.url_text = Label(self.small_font, max_glyphs=35)
        self.url_text.x = 15
        self.url_text.y = 220
        self.url_text.color = 0xFFFFFF
        self._text_group.append(self.url_text)
        self.url_text.text = "Visit us at https://electioncal.us"

        self.state_text = Label(self.small_font, max_glyphs=60)
        self.state_text.x = 15
        self.state_text.y = 10
        self.state_text.color = 0xFFFFFF
        self._text_group.append(self.state_text)

        self.election_date_text = Label(self.medium_font, max_glyphs=11)
        self.election_date_text.x = 15
        self.election_date_text.y = 60
        self.election_date_text.color = 0xFFFFFF
        self._text_group.append(self.election_date_text)

        self.election_name_text = Label(self.small_font, max_glyphs=60)
        self.election_name_text.x = 15
        self.election_name_text.y = 95
        self.election_name_text.color = 0xFFFFFF
        self._text_group.append(self.election_name_text)

        self.election_name_text_line2 = Label(self.small_font, max_glyphs=60)
        self.election_name_text_line2.x = 15
        self.election_name_text_line2.y = 120
        self.election_name_text_line2.color = 0xFFFFFF
        self._text_group.append(self.election_name_text_line2)


    def load_data(self, election_data):
        try:
            self.electioncal = json.loads(election_data)
            self.state_text.text = self.electioncal["dates"][1]["county"] + ", " + self.electioncal["dates"][0]["state"]
        except ValueError:
            print("Error loading JSON data: Please check the configuration of county and state, in code.py")
            raise

    def elections_cycle(self):
        self.update_time()
        num_elections = len(self.electioncal["dates"])

        for i in range(0,num_elections):
            if self.date_text.text[10:] < self.electioncal["dates"][i]["date"]:
                self.election_date_text.text = self.electioncal["dates"][i]["date"]
                # splitting the line at around 40 chars seems ok for regular PyPortal
                self.election_name_text_line2.text, self.election_name_text.text = self.paragrapher(self.electioncal["dates"][i]["name"], 40)
                time.sleep(30)

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

    def paragrapher(self, text, cut):
        """ Cuts a long line into two, having spaces in mind.
        Note we return line2 first as it looks better to clear the line2
        before printing a line1 with empty line2
        We run from cut, backwards till we find a space.
        """
        if len(text) > cut:
            for i in range(cut,0,-1):
                if text[i] == " ":
                    break
            line1 = text[0:i]
            line2 = text[i+1:80]
        else:
            line1 = text
            line2 = ""
        return line2, line1

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