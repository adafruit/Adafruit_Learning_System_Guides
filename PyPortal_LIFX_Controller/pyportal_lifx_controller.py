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

# LIFX lightbulb names and associated IDs
lifx_lights = { 'bedroom': 'id:d073d5378b20',
                'lamp': '0000'}

# Set this to your personal access token for private, beta use of the LIFX HTTP API to remotely control your lighting.
# (to obtain a token, visit: https://cloud.lifx.com/settings)
lifx_token = ''

auth_header = {"Authorization": "Bearer %s" % lifx_token,}

def enumerate_bulbs():
    response = wifi.get(
        url='https://api.lifx.com/v1/lights/all',
        headers=auth_header
    )
    print(response.json())
    response.close()

def toggle_bulbs(selector, all=False, duration=0):
    """Toggles current state of LIFX bulb.
    :param dict selector: Selector to control which bulbs are requested.
    :param bool all: Toggle all bulbs at once. Defaults to false.
    :param double duration: Time (in seconds) to spend performing a toggle. Defaults to 0.
    """
    response = wifi.post(
        url='https://api.lifx.com/v1/lights/'+selector+'/toggle',
        headers = auth_header,
        json = {'duration':duration},
    )
    resp = response.json()
    print(response.json())
    response.close()

print('enumerating all LIFX bulbs..')
enumerate_bulbs()

print('toggling bulb')
toggle_bulbs(lifx_lights['bedroom'], duration=0)
print('toggling bulb for 5seconds')
toggle_bulbs(lifx_lights['bedroom'], duration=5)