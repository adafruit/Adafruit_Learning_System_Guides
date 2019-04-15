"""
PyPortal Philips Hue Lighting Controller

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

# Import Philips Hue Bridge
from adafruit_hue import Bridge

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

# Attempt to load bridge username and IP address from secrets.py
try:
    username = secrets['hue_username']
    bridge_ip = secrets['bridge_ip']
    my_bridge = Bridge(wifi, bridge_ip, username)
except:
    # Perform first-time bridge setup
    my_bridge = Bridge(wifi)
    print('Finding bridge address...')
    ip = my_bridge.discover_bridge()
    print('Attempting to register username, press the link button on your Hue Bridge now!')
    username = my_bridge.register_username()
    print('ADD THESE VALUES TO SECRETS.PY: \
                            \n\t"bridge_ip":"{0}", \
                            \n\t"hue_username":"{1}"'.format(ip, username))
    raise

# These pins are used as both analog and digital! XL, XR and YU must be analog
# and digital capable. YD just need to be digital
ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=((5200, 59000), (5800, 57000)),
                                      size=(320, 240))


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

print('loading colors...')
# color conversions (RGB to Philips Hue-compatible HSB)
red = my_bridge.rgb_to_hsb([255, 0, 0])
white = my_bridge.rgb_to_hsb([255, 255, 255])
orange = my_bridge.rgb_to_hsb([255, 165, 0])
yellow = my_bridge.rgb_to_hsb([255, 255, 0])
green = my_bridge.rgb_to_hsb([0, 255, 0])
blue = my_bridge.rgb_to_hsb([0, 0, 255])
purple = my_bridge.rgb_to_hsb([128, 0, 128])
pink = my_bridge.rgb_to_hsb([255, 192, 203])

hue_hsb = {'red': red, 'white': white, 'orange': orange,
           'yellow': yellow, 'green': green, 'blue': blue,
           'purple': purple, 'pink': pink}

print('loading buttons...')
# button fill colors
button_colors = {'red':0xFF0000, 'white':0xFFFFFF,
                 'orange':0xFF9900, 'yellow':0xFFFF00,
                 'green':0x00FF00, 'blue':0x0000FF,
                 'purple':0x9900FF, 'pink': 0xFF00FF}
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
    {'name':'room', 'pos':(195, 15), 'label':'room'},
    {'name':'lamp', 'pos':(255, 15), 'label':'lamp'}
]

# generate property buttons from prop_btn list
for i in prop_btn:
    button = Button(name=i['name'], x=i['pos'][0], y=i['pos'][1],
                    width=55, height=40, label=i['label'],
                    label_font=font, style=Button.SHADOWROUNDRECT)
    buttons.append(button)

# add buttons to the group
for b in buttons:
    button_group.append(b.group)

# Hue Light/Group Identifiers
hue_lights={'lamp': 1, 'livingroom': 2}
hue_selector = hue_lights['lamp']

# Default to 25% brightness
current_brightness = 25

while True:
    touch = ts.touch_point
    if touch:
        for i, button in enumerate(buttons):
            if button.contains(touch):
                button.selected = True
                if button.name == 'room':
                    hue_selector = hue_lights['livingroom']
                    print('Switching to ', hue_selector)
                elif button.name == 'lamp':
                    hue_selector = hue_lights['lamp']
                    print('Switching to ', hue_selector)
                elif button.name == 'onoff':
                    print('Toggling {0}...'.format(hue_selector))
                    my_bridge.toggle_light(int(hue_selector))
                elif button.name == 'up':
                    current_brightness += 25
                    print('Setting {0} brightness to {1}'.format(hue_selector, current_brightness))
                    my_bridge.set_light(int(hue_selector), bri=current_brightness)
                elif button.name == 'down':
                    current_brightness -= 25
                    print('Setting {0} brightness to {1}'.format(hue_selector, current_brightness))
                    my_bridge.set_light(int(hue_selector), bri=current_brightness)
                else:
                    print('Setting {0} color to {1}'.format(hue_selector, button.name))
                    my_bridge.set_light(light_id=int(hue_selector),
                                        hue=int(hue_hsb[button.name][0]),
                                        sat=int(hue_hsb[button.name][1]),
                                        bri=int(hue_hsb[button.name][2]))
                button.selected = False
            else:
                button.selected = False
