"""
PyPortal Smart Lighting Controller
-------------------------------------------------------------
https://learn.adafruit.com/pyportal-smart-lighting-controller

Brent Rubell for Adafruit Industries, 2019
"""
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

# import lifx library
import adafruit_lifx

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

# These pins are used as both analog and digital! XL, XR and YU must be analog
# and digital capable. YD just need to be digital
ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=((5200, 59000), (5800, 57000)),
                                      size=(320, 240))

# Set this to your LIFX personal access token in secrets.py
# (to obtain a token, visit: https://cloud.lifx.com/settings)
lifx_token = secrets['lifx_token']

# Initialize the LIFX API Helper
lifx = adafruit_lifx.LIFX(wifi, lifx_token)

# Set these to your LIFX light selector (https://api.developer.lifx.com/docs/selectors)
lifx_lights = ['label:Lamp', 'label:Bedroom']
# set default light properties
current_light = lifx_lights[0]
light_brightness = 1.0

# Make the display context
button_group = displayio.Group(max_size=20)
board.DISPLAY.show(button_group)
# preload the font
print('loading font...')
font = bitmap_font.load_font("/fonts/Arial-12.bdf")
glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.: '
font.load_glyphs(glyphs)
# button properties
BUTTON_WIDTH = 60
BUTTON_HEIGHT = 60
buttons = []

# button fill colors (from https://api.developer.lifx.com/docs/colors)
button_colors = {'red':0xFF0000, 'white':0xFFFFFF,
                 'orange':0xFF9900, 'yellow':0xFFFF00,
                 'green':0x00FF00, 'blue':0x0000FF,
                 'purple':0x9900FF, 'pink': 0xFF00FF}

print('loading buttons...')

# list of color buttons and their properties
color_btn = [
    {'name':'red', 'pos':(15, 80), 'color':button_colors['red']},
    {'name':'white', 'pos':(85, 80), 'color':button_colors['white']},
    {'name':'orange', 'pos':(155, 80), 'color':button_colors['orange']},
    {'name':'yellow', 'pos':(225, 80), 'color':button_colors['yellow']},
    {'name':'pink', 'pos':(15, 155), 'color':button_colors['pink']},
    {'name':'green', 'pos':(85, 155), 'color':button_colors['green']},
    {'name':'blue', 'pos':(155, 155), 'color':button_colors['blue']},
    {'name':'purple', 'pos':(225, 155), 'color':button_colors['purple']}
]

# generate color buttons from color_btn list
for i in color_btn:
    button = Button(x=i['pos'][0], y=i['pos'][1],
                    width=BUTTON_WIDTH, height=BUTTON_HEIGHT, name=i['name'],
                    fill_color=i['color'], style=Button.ROUNDRECT)
    buttons.append(button)

# light property buttons and their properties
prop_btn = [
    {'name':'onoff', 'pos':(15, 15), 'label':'on/off'},
    {'name':'up', 'pos':(75, 15), 'label':'+'},
    {'name':'down', 'pos':(135, 15), 'label':'-'},
    {'name':'lamp', 'pos':(195, 15), 'label':'lamp'},
    {'name':'room', 'pos':(245, 15), 'label':'room'}
]

# generate property buttons from prop_btn list
for i in prop_btn:
    button = Button(name=i['name'], x=i['pos'][0], y=i['pos'][1],
                    width=40, height=40, label=i['label'],
                    label_font=font, style=Button.SHADOWROUNDRECT)
    buttons.append(button)

# add buttons to the group
for b in buttons:
    button_group.append(b.group)

while True:
    touch = ts.touch_point
    if touch:
        for i, button in enumerate(buttons):
            if button.contains(touch):
                button.selected = True
                if button.name == 'lamp':
                    current_light = lifx_lights[0]
                    print('Switching to ', current_light)
                elif button.name == 'room':
                    current_light = lifx_lights[1]
                    print('Switching to ', current_light)
                elif button.name == 'onoff':
                    print('Toggling {0}...'.format(current_light))
                    lifx.toggle_light(current_light)
                elif button.name == 'up':
                    light_brightness += 0.25
                    print('Setting {0} brightness to {1}'.format(current_light, light_brightness))
                    lifx.set_brightness(current_light, light_brightness)
                elif button.name == 'down':
                    light_brightness -= 0.25
                    print('Setting {0} brightness to {1}'.format(current_light, light_brightness))
                    lifx.set_brightness(current_light, light_brightness)
                else:
                    print('Setting {0} color to {1}'.format(current_light, button.name))
                    lifx.set_color(current_light, 'on', button.name, light_brightness)
                button.selected = False
            else:
                button.selected = False
