"""
PyPortal LIFX Controller

Control your Wi-Fi LED Smart Lights using your PyPortal
with the LIFX HTTP API and CircuitPython

by Brent Rubell for Adafruit Industries, 2019
"""
import time
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

# ESP32 SPI
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2) # Uncomment for Most Boards
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# Set this to your personal access token for private, beta use of the LIFX HTTP API to remotely control your lighting.
# (to obtain a token, visit: https://cloud.lifx.com/settings)
lifx_token = ''

# Set these to your LIFX WiFi bulb identifiers
# Format: {'descriptive_room_key':'id:bulb_id_string'}
lifx_bulbs = { 'bedroom': 'id:d073d5378b20',
                'lamp': 'id:d0000000000'}

auth_header = {"Authorization": "Bearer %s" % lifx_token,}
lifx_url = 'https://api.lifx.com/v1/lights/'

def enumerate_bulbs():
    """Enumerates all the bulbs associated with the LIFX Cloud Account
    """
    response = wifi.get(
        url=lifx_url+'all',
        headers=auth_header
    )
    resp = response.json()
    print(response.json())
    response.close()

def toggle_bulbs(selector, all=False, duration=0):
    """Toggles current state of LIFX bulb.
    :param dict selector: Selector to control which bulbs are requested.
    :param bool all: Toggle all bulbs at once. Defaults to false.
    :param double duration: Time (in seconds) to spend performing a toggle. Defaults to 0.
    """
    response = wifi.post(
        url=lifx_url+selector+'/toggle',
        headers = auth_header,
        json = {'duration':duration},
    )
    resp = response.json()
    print(response.json())
    response.close()

def set_bulb(selector, power=None, color=None, brightness=None, duration=None, fast_mode=False):
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
        json={'power':"",
                'color':color,
                'brightness':brightness,
                'duration':duration,
                'fast':fast_mode
        }
    )
    resp = response.json()
    print(response.json())
    response.close()

print('enumerating all LIFX bulbs..')
enumerate_bulbs()

print('toggling bulb for 5seconds')
toggle_bulbs(lifx_bulbs['bedroom'], duration=5)

print('setting the bedroomb bulb to deep red')
set_bulb(lifx_bulbs['bedroom'], '#ff0000', '0.3')