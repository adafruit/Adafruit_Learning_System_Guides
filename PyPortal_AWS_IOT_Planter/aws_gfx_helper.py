"""
GFX Helper for PyPortal AWS IoT Plant Monitor
"""
import board
import displayio
import terminalio
from adafruit_display_text.label import Label

 # the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]

# GFX Font
font = terminalio.FONT

class AWS_GFX(displayio.Group):
    def __init__(self, is_celsius=False):
        """Creates an AWS_GFX object for displaying plant
        and AWS IoT status.
        :param bool is_celsius: Temperature displayed in Celsius.
        """
        # root displayio group
        root_group = displayio.Group(max_size=23)
        self.display = board.DISPLAY
        self.display.show(root_group)
        super().__init__(max_size=15)

        # temperature display option
        self._is_celsius = is_celsius

        # create background icon group
        self._icon_group = displayio.Group(max_size=3)
        self.display.show(self._icon_group)
        # create text object group
        self._text_group = displayio.Group(max_size=40)

        print("Displaying splash screen")
        self._icon_sprite = None
        self._icon_file = None
        self._cwd = cwd
        self.set_icon(self._cwd+"/images/aws_splash.bmp")

        print('Setting up labels...')
        header_group = displayio.Group(scale=3)
        header_label = Label(font, text="    AWS IoT\n    Planter")
        header_label.x = (self.display.width // 2) // 22
        header_label.y = 15
        header_group.append(header_label)
        self._text_group.append(header_group)

        # Temperature Display
        temp_group = displayio.Group(scale=2, max_size=400)
        temp_label = Label(font, text="Temperature: ")
        temp_label.x = (self.display.width//2) // 11
        temp_label.y = 55
        temp_group.append(temp_label)

        self.temp_data_label = Label(font, text="75 F")
        self.temp_data_label.x = (self.display.width//3)
        self.temp_data_label.y = 55
        temp_group.append(self.temp_data_label)
        self._text_group.append(temp_group)

        # Water Level
        water_group = displayio.Group(scale=2, max_size=2)
        self.water_level = Label(font, text="Water Level: ")
        self.water_level.x = (self.display.width//2) // 11
        self.water_level.y = 75
        water_group.append(self.water_level)

        self.water_lvl_label = Label(font, text="350")
        self.water_lvl_label.x = (self.display.width//3)
        self.water_lvl_label.y = 75
        temp_group.append(self.water_lvl_label)
        self._text_group.append(water_group)

        # AWS Status
        status_group = displayio.Group()
        self.aws_status_label = Label(font, text="Connecting to AWS IoT...")
        self.aws_status_label.x = int(self.display.width//3.5)
        self.aws_status_label.y = 200
        status_group.append(self.aws_status_label)
        self._text_group.append(status_group)

        self.display.show(self._text_group)

    def show_aws_status(self, status_text):
        """Displays the system status on the PyPortal
        :param str status_text: Description of current AWS IoT status.
        """
        self.aws_status_label.text = status_text

    def show_water_level(self, water_data):
        """Displays the water level from the Stemma Soil Sensor.
        :param int water_data: water value
        """
        self.water_lvl_label.text = str(water_data)

    def show_temp(self, temp_data):
        """Displays the temperature from the Stemma Soil Sensor.
        :param float temp_data: Temperature value.
        """
        if not self._is_celsius:
            temp_data = (temp_data * 9 / 5) + 32 - 15
            print('Temperature: %0.0f°F'%temp_data)
            if temp_data >= 212:
                self.temp_data_label.color = 0xFD2EE
            elif temp_data <= 32:
                self.temp_data_label.color = 0xFF0000
            self.temp_data_label = '%0.0f°F'%temp_data
            temp_data = '%0.0f'%temp_data
            return int(temp_data)
        else:
            print('Temperature: %0.0f°C'%temp_data)
            if temp_data <= 0:
                self.temp_data_label.color = 0xFD2EE
            elif temp_data >= 100:
                self.temp_data_label.color = 0xFF0000
            self.temp_data_label.text = '%0.0f°C'%temp_data
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
