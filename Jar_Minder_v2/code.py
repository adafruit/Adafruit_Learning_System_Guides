import digitalio
import board

done = digitalio.DigitalInOut(board.A4)
done.direction = digitalio.Direction.OUTPUT
done.value = False

#pylint: disable=wrong-import-position,wrong-import-order
import time
import pulseio
import busio
from adafruit_epd.epd import Adafruit_EPD
from adafruit_epd.il0373 import Adafruit_IL0373
import adafruit_si7021
import font

#--------------------------------------------------
# Setup

spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
ecs = digitalio.DigitalInOut(board.D11)
dc = digitalio.DigitalInOut(board.D10)
srcs = digitalio.DigitalInOut(board.D9)
rst = digitalio.DigitalInOut(board.D6)
busy = digitalio.DigitalInOut(board.D12)
display = Adafruit_IL0373(152, 152, rst, dc, busy, srcs, ecs, spi)

i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_si7021.SI7021(i2c)

ON = 2**15
OFF = 0

buzzer = pulseio.PWMOut(board.D5, variable_frequency=True)
buzzer.duty_cycle = OFF

silence_button = digitalio.DigitalInOut(board.A5)
silence_button.direction = digitalio.Direction.INPUT
silence_button.pull = digitalio.Pull.UP

#--------------------------------------------------
# Default parameter values

settings = {}
settings['temperature_range'] = (15, 30)
settings['humidity_range'] = (60, 70)
settings['title'] = 'Weed Minder'
settings['alarm_frequency'] = 4000
settings['alarm_number_of_beeps'] = 3
settings['alarm_seconds_beep_on'] = 0.5
settings['alarm_seconds_between_beeps'] = 0.5
settings['alarm_seconds_between_alarms'] = 5.0
settings['alarm_timeout'] = 60.0

#--------------------------------------------------
# Support functions

def render_character(x, y, ch, color=Adafruit_EPD.BLACK):
    """Render a character.
    :param int x: horizontal position of the left edge of the character
    :param int y: vertical position of the top edge of the character
    :param str ch: a single character string to be displayed
    :param Adafruit_EPD.* color: BLACK or RED, background is always white
    """

    if x < 144 and y < 144:
        bitmap = font.bitmaps[ord(ch)]
        for row_num in range(8):
            row = bitmap[row_num]
            for column_num in range(8):
                if (row & 1) == 0:
                    display.draw_pixel(x + column_num, y + row_num, Adafruit_EPD.WHITE)
                else:
                    display.draw_pixel(x + column_num, y + row_num, color)
                row >>= 1


def render_string(x, y, s, color=Adafruit_EPD.BLACK):
    """Render a string.
    :param int x: horizontal position of the left edge of the string
    :param int y: vertical position of the top edge of the string
    :param str ch: a string to be displayed
    :param Adafruit_EPD.* color: BLACK or RED, background is always white
    """

    x_pos = x
    for ch in s:
        render_character(x_pos, y, ch, color)
        x_pos += 8


def centered(s):
    """Computer the X position to center a string.
    :param str s: the string to center
    """

    return 75 - (4 * len(s))


def to_int_tuple(a):
    """Convert an array of strings to a tuple of ints.
    :param [int] a: array of strings to convert
    """

    return tuple([int(x.strip()) for x in a])


def check_for_push(button, duration):
    """Wait for a time, regularly checking for a button push.
    :param DigitalInOut button: the button input to check
    :param float duration: seconds to wait
    Return True if the button is pushed, False if the time passes
    """

    stop_at = time.monotonic() + duration
    while time.monotonic() < stop_at:
        if not button.value:
            return True
        time.sleep(0.1)
    return False


def sound_alarm():
    """Sound the alarm based on the settings."""

    buzzer.frequency = settings['alarm_frequency']
    for _ in range(settings['alarm_number_of_beeps']):
        buzzer.duty_cycle = ON
        if check_for_push(silence_button, settings['alarm_seconds_beep_on']):
            buzzer.duty_cycle = OFF
            return True
        buzzer.duty_cycle = OFF
        if check_for_push(silence_button, settings['alarm_seconds_between_beeps']):
            return True
    return False



def out_of_range(t, h):
    """Check if either temperature and humidity is out of range.
    :param float t: temperature reading
    :param float h: humidity reading
    """

    if t < settings['temperature_range'][0]:
        return True
    if t > settings['temperature_range'][1]:
        return True
    if h < settings['humidity_range'][0]:
        return True
    if h > settings['humidity_range'][1]:
        return True
    return False


#--------------------------------------------------
# Handle edit mode: allow the user to edit description and settings
# This is done by waking the device while holding the silence button pressed
# A low beep indicated entry and the display will indicate it as well

if not silence_button.value:
    buzzer.frequency = 440
    buzzer.duty_cycle = ON
    time.sleep(0.5)
    buzzer.duty_cycle = OFF
    display.clear_buffer()
    render_string(39, 64, 'EDIT MODE')
    display.display()
    while not silence_button.value:       # wait for button to be released
        pass
    while silence_button.value:           # wait for button to be pressed
        pass
    buzzer.duty_cycle = ON
    time.sleep(0.5)
    buzzer.duty_cycle = OFF

# Pressing the silence button again reverts to monitor mode
# A low beep indicates this

#--------------------------------------------------
# Main script

# Read settings file into setting dictionary
with open('settings.txt', 'r') as f:
    for line in f:
        key, value = [x.strip() for x in line.strip().split(':')]
        values = value.split('-')
        if key == 'temperature_range':
            setting = to_int_tuple(values)
        elif key == 'humidity_range':
            setting = to_int_tuple(values)
        elif key == 'title':
            setting = value
        elif key == 'alarm_frequency':
            setting = int(value)
        elif key == 'alarm_number_of_beeps':
            setting = int(value)
        elif key == 'alarm_seconds_beep_on':
            setting = float(value)
        elif key == 'alarm_seconds_between_beeps':
            setting = float(value)
        elif key == 'alarm_timeout':
            setting = float(value)
        settings[key] = setting

        # Get text
with open('description.txt', 'r') as f:
    text = [line.strip() for line in f]

display.clear_buffer()
render_string(centered(settings['title']), 12, settings['title'])

# Display text
row_index = 64
for line in text:
    if row_index > 112:
        break
    render_string(centered(line), row_index, line)
    row_index += 10

temperature = int(sensor.temperature)
humidity = int(sensor.relative_humidity)
render_string(8, 32, '{0:2d} C'.format(temperature))
render_string(112, 32, '{0:2d} %'.format(humidity))

if temperature < settings['temperature_range'][0]:
    temperature_message = 'LOW TEMPERATURE'
elif temperature > settings['temperature_range'][1]:
    temperature_message = 'HIGH TEMPERATURE'
else:
    temperature_message = ''

if humidity < settings['humidity_range'][0]:
    humidity_message = 'LOW HUMIDITY'
elif humidity > settings['humidity_range'][1]:
    humidity_message = 'HIGH HUMIDITY'
else:
    humidity_message = ''

if temperature_message:
    render_string(centered(temperature_message), 122, temperature_message, Adafruit_EPD.RED)
if humidity_message:
    render_string(centered(humidity_message), 132, humidity_message, Adafruit_EPD.RED)

if temperature_message or humidity_message:
    display.fill_rect(0, 0, 152, 10, Adafruit_EPD.RED)
    display.fill_rect(0, 142, 152, 10, Adafruit_EPD.RED)

display.display()

timeout = time.monotonic() + settings['alarm_timeout']

while out_of_range(temperature, humidity) and time.monotonic() < timeout:
    if sound_alarm():
        break
    if check_for_push(silence_button, settings['alarm_seconds_between_alarms']):
        break

done.value = True
