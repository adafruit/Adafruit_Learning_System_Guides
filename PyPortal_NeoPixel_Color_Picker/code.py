import time
import board
from adafruit_pyportal import PyPortal
from adafruit_button import Button
import neopixel
import analogio

# Set the background color
BACKGROUND_COLOR = 0x443355

# Set the NeoPixel brightness
BRIGHTNESS = 0.3

light_sensor = analogio.AnalogIn(board.LIGHT)

strip_1 = neopixel.NeoPixel(board.D4, 30, brightness=BRIGHTNESS)
strip_2 = neopixel.NeoPixel(board.D3, 30, brightness=BRIGHTNESS)

# Turn off NeoPixels to start
strip_1.fill(0)
strip_2.fill(0)

# Setup PyPortal without networking
pyportal = PyPortal(default_bg=BACKGROUND_COLOR)

# Button colors
RED = (255, 0, 0)
ORANGE = (255, 34, 0)
YELLOW = (255, 170, 0)
GREEN = (0, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
VIOLET = (153, 0, 255)
MAGENTA = (255, 0, 51)
PINK = (255, 51, 119)
AQUA = (85, 125, 255)
WHITE = (255, 255, 255)
OFF = (0, 0, 0)

spots = [
    {'label': "1", 'pos': (10, 10), 'size': (60, 60), 'color': RED},
    {'label': "2", 'pos': (90, 10), 'size': (60, 60), 'color': ORANGE},
    {'label': "3", 'pos': (170, 10), 'size': (60, 60), 'color': YELLOW},
    {'label': "4", 'pos': (250, 10), 'size': (60, 60), 'color': GREEN},
    {'label': "5", 'pos': (10, 90), 'size': (60, 60), 'color': CYAN},
    {'label': "6", 'pos': (90, 90), 'size': (60, 60), 'color': BLUE},
    {'label': "7", 'pos': (170, 90), 'size': (60, 60), 'color': VIOLET},
    {'label': "8", 'pos': (250, 90), 'size': (60, 60), 'color': MAGENTA},
    {'label': "9", 'pos': (10, 170), 'size': (60, 60), 'color': PINK},
    {'label': "10", 'pos': (90, 170), 'size': (60, 60), 'color': AQUA},
    {'label': "11", 'pos': (170, 170), 'size': (60, 60), 'color': WHITE},
    {'label': "12", 'pos': (250, 170), 'size': (60, 60), 'color': OFF}
    ]

buttons = []
for spot in spots:
    button = Button(x=spot['pos'][0], y=spot['pos'][1],
                    width=spot['size'][0], height=spot['size'][1],
                    style=Button.SHADOWROUNDRECT,
                    fill_color=spot['color'], outline_color=0x222222,
                    name=spot['label'])
    pyportal.splash.append(button.group)
    buttons.append(button)

mode = 0
mode_change = None

# Calibrate light sensor on start to deal with different lighting situations
# If the mode change isn't responding properly, reset your PyPortal to recalibrate
initial_light_value = light_sensor.value
while True:
    if light_sensor.value < (initial_light_value * 0.3) and mode_change is None:
        mode_change = "mode_change"
    if light_sensor.value > (initial_light_value * 0.5) and mode_change == "mode_change":
        mode += 1
        mode_change = None
        if mode > 2:
            mode = 0
        print(mode)
    touch = pyportal.touchscreen.touch_point
    if touch:
        for button in buttons:
            if button.contains(touch):
                print("Touched", button.name)
                if mode == 0:
                    strip_1.fill(button.fill_color)
                elif mode == 1:
                    strip_2.fill(button.fill_color)
                elif mode == 2:
                    strip_1.fill(button.fill_color)
                    strip_2.fill(button.fill_color)
                break
    time.sleep(0.05)
