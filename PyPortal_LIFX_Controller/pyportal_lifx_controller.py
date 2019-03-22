"""
PyPortal LIFX Controller

Control your Wi-Fi LED Smart Lights using your PyPortal
with the LIFX HTTP API and CircuitPython

by Brent Rubell for Adafruit Industries, 2019
"""
import board
import busio
from digitalio import DigitalInOut
import neopixel
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# PyPortal ESP32 SPI
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2) # Uncomment for Most Boards
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# Set this to your personal access token in `secrets.py`
# (to obtain a token, visit: https://cloud.lifx.com/settings)
lifx_token = secrets['lifx_token']

# Set these to your LIFX WiFi bulb identifiers
# Format: {'descriptive_room_key':'id:bulb_id_string'}
lifx_bulbs = { 'bedroom': 'label:Main Light',
               'lamp': 'label:Lamp'}

auth_header = {"Authorization": "Bearer %s" % lifx_token,}
lifx_url = 'https://api.lifx.com/v1/lights/'

def list_bulbs():
    """Enumerates all the bulbs associated with the LIFX Cloud Account
    """
    response = wifi.get(
        url=lifx_url+'all',
        headers=auth_header
    )
    resp = response.json()
    print(resp)
    response.close()

def toggle_bulbs(selector, all_bulbs=False, duration=0):
    """Toggles current state of LIFX bulb(s).
    :param dict selector: Selector to control which bulbs are requested.
    :param bool all: Toggle all bulbs at once. Defaults to false.
    :param double duration: Time (in seconds) to spend performing a toggle. Defaults to 0.
    """
    if all_bulbs:
        selector = 'all'
    response = wifi.post(
        url=lifx_url+selector+'/toggle',
        headers = auth_header,
        json = {'duration':duration},
    )
    resp = response.json()
    # check the response
    if response.status_code == 422:
        raise Exception('Error, bulb(s) could not be toggled: '+ resp['error'])
    print(resp)
    response.close()

def set_bulb(selector, power, color, brightness, duration, fast_mode=False):
    """Sets the state of the lights within the selector.
    :param dict selector: Selector to control which bulbs are requested.
    :param str power: Sets the power state of the bulb (on/off).
    :param str color: Color to set the bulb to (https://api.developer.lifx.com/v1/docs/colors).
    :param double brightness: Brightness level of the bulb, from 0.0 to 1.0.
    :param double duration: How long (in seconds) you want the power action to take.
    :param bool fast: Executes fast mode, no initial state check or waiting for results.
    """
    response = wifi.put(
        url=lifx_url+selector+'/state',
        headers=auth_header,
        json={'power':power,
              'color':color,
              'brightness':brightness,
              'duration':duration,
              'fast':fast_mode
              }
    )
    resp = response.json()
    # check the response
    if response.status_code == 422:
        raise Exception('Error, bulb could not be set: '+ resp['error'])
    print(resp)
    response.close()

def move_effect(selector, move_direction, period, cycles, power_on):
    """Performs a linear move effect on a bulb, or bulbs.
    :param str move_direction: Move direction, forward or backward.
    :param double period: Time in second per effect cycle.
    :param float cycles: Number of times to move the pattern.
    :param bool power_on: Turn on a bulb before performing the move.
    """
    response = wifi.post(
        url=lifx_url+selector+'/effects/move',
        headers = auth_header,
        json = {'direction':move_direction,
                'period':period,
                'cycles':cycles,
                'power_on':power_on},
    )
    resp = response.json()
    # check the response
    if response.status_code == 422:
        raise Exception('Error: '+ resp['error'])
    print(resp)
    response.close()

def effects_off(selector):
    """Turns off any running effects on the selected device.
    :param dict selector: Selector to control which bulbs are requested.
    """
    response = wifi.post(
        url=lifx_url+selector+'/effects/off',
        headers=auth_header
    )
    resp = response.json()
    # check the response
    if response.status_code == 422:
        raise Exception('Error: '+ resp['error'])
    print(resp)
    response.close()


print('Toggling bulb for 5seconds')
toggle_bulbs(lifx_bulbs['bedroom'], duration=5)

print('set lamp to purple!')
set_bulb(lifx_bulbs['lamp'], 'on', 'purple', 0.5, 0.0)
