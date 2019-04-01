import os
import board
import displayio
from adafruit_bitmap_font import bitmap_font
from adafruit_button import Button
import adafruit_touchscreen
from digitalio import DigitalInOut

import busio
import neopixel
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager

# import special lifx_helper file
import lifx_helper

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# ESP32 SPI
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# Set this to your personal access token for private, use of the LIFX HTTP API to remotely control your lighting.
# (to obtain a token, visit: https://cloud.lifx.com/settings)
lifx_token = secrets['lifx_token']

# Initialize the LIFX API Helper
lifx = lifx_helper.LIFX_API(wifi, lifx_token)

# Set these to your LIFX WiFi bulb identifiers
lifx_bulbs = { 'bedroom': 'label:Main Room',
                'lamp': 'label:lamp'}

# These pins are used as both analog and digital! XL, XR and YU must be analog
# and digital capable. YD just need to be digital
ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=((5200, 59000), (5800, 57000)),
                                      size=(320, 240))

# the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]
fonts = [file for file in os.listdir(cwd+"/fonts/")
         if (file.endswith(".bdf") and not file.startswith("._"))]
for i, filename in enumerate(fonts):
    fonts[i] = cwd+"/fonts/"+filename
print(fonts)
THE_FONT = "/fonts/Arial-12.bdf"
DISPLAY_STRING = "Button Text"

# Make the display context
button_group = displayio.Group(max_size=20)
board.DISPLAY.show(button_group)

# button properties
BUTTON_WIDTH = 60
BUTTON_HEIGHT = 60

# Load the font
font = bitmap_font.load_font(THE_FONT)

buttons = []

# Button Fill Colors, from https://api.developer.lifx.com/docs/colors
button_colors = {'red':0xFF0000, 'white':0xFFFFFF,
                 'orange':0xFF9900, 'yellow':0xFFFF00,
                 'cyan':0x00FFFF, 'green':0x00FF00,
                 'blue':0x0000FF, 'purple':0x9900FF,
                 'pink': 0xFF00FF}

# list of buttons and their properties
button_list = [
    {'name':'btn_red', 'position':(10, 30), 'color':button_colors['red']},
    {'name':'btn_white', 'position':(50, 30), 'color':button_colors['white']},
    {'name':'btn_orange', 'position':(110, 30), 'color':button_colors['orange']},
    {'name':'btn_yellow', 'position':(10, 70), 'color':button_colors['yellow']},
    {'name':'btn_cyan', 'position':(50, 70), 'color':button_colors['cyan']},
    {'name':'btn_green', 'position':(110, 70), 'color':button_colors['green']},
    {'name':'btn_blue', 'position':(10, 110), 'color':button_colors['blue']},
    {'name':'btn_purple', 'position':(50, 110), 'color':button_colors['purple']},
    {'name':'btn_pink', 'position':(110, 110), 'color':button_colors['pink']}
]

# color buttons
btn_red = Button(x=button_list[0]['position'][0], y=button_list[0]['position'][1],
                  width=BUTTON_WIDTH, height=BUTTON_HEIGHT,
                  fill_color=button_list[0]['color'], style=Button.ROUNDRECT)
buttons.append(btn_red)


# TODO: add buttons to select a specific light

# add buttons to the group
for b in buttons:
    button_group.append(b.group)


# set a default bulb
# TODO: maybe make this a dict list as well...
current_bulb = lifx_bulbs['bedroom']

while True:
    touch = ts.touch_point
    if touch:
        for i, b in enumerate(buttons):
            if b.contains(touch):
                if i == 0:
                  print('setting bulb to red...')
                  lifx.set_light(lifx_bulbs['bedroom'], 'on', 'red', 1.0)
                b.selected = True
            else:
                b.selected = False
