# SPDX-FileCopyrightText: 2023 Brent Rubell for Adafruit Industries
#
# An open-source IoT doorbell with the Adafruit MEMENTO camera and Adafruit IO
#
# SPDX-License-Identifier: Unlicense
import os
import time
import ssl
import binascii
import digitalio
import adafruit_pycamera
import board
import wifi
import socketpool
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP, AdafruitIO_RequestError

print("CircuitPython Doorbell Camera")

### WiFi ###
# Add settings.toml to your filesystem CIRCUITPY_WIFI_SSID and CIRCUITPY_WIFI_PASSWORD keys
# with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.

# Set your Adafruit IO Username, Key and Port in settings.toml
# (visit io.adafruit.com if you need to create an account,
# or if you need your Adafruit IO key.)
aio_username = os.getenv("ADAFRUIT_AIO_USERNAME")
aio_key = os.getenv("ADAFRUIT_AIO_KEY")

print(f"Connecting to {os.getenv('CIRCUITPY_WIFI_SSID')}")
wifi.radio.connect(
    os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
)
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}!")

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(os.getenv("ADAFRUIT_AIO_USERNAME"), os.getenv("ADAFRUIT_AIO_KEY"), requests)

# Adafruit IO feed configuration
try:
    # Get the 'camera' feed from Adafruit IO
    feed_camera = io.get_feed("camera")
except AdafruitIO_RequestError:
    # If no 'camera' feed exists, create one
    feed_camera = io.create_new_feed("camera")

# Initialize memento camera
pycam = adafruit_pycamera.PyCamera()
# Turn off TFT backlight
pycam.display.brightness = 0.0
# Deinitialize the MEMENTO's NeoPixels
# Why? The pixels use board.A1 and we want to use it to control the doorbell LED
pycam.pixels.deinit()

# Set up the button
pin_button = digitalio.DigitalInOut(board.A0)
pin_button.direction = digitalio.Direction.INPUT
pin_button.pull = digitalio.Pull.UP

# Set up the button's LED
led = digitalio.DigitalInOut(board.A1)
led.direction = digitalio.Direction.OUTPUT
led.value = True
print("Doorbell ready to be pressed!")

def capture_send_image():
    """Captures an image and send it to Adafruit IO."""
    # Force autofocus and capture a JPEG image
    pycam.autofocus()
    jpeg = pycam.capture_into_jpeg()
    print("Captured image!")
    if jpeg is not None:
        # Encode JPEG data into base64 for sending to Adafruit IO
        print("Encoding image...")
        encoded_data = binascii.b2a_base64(jpeg).strip()
        # Send encoded_data to Adafruit IO camera feed
        print("Sending image to Adafruit IO...")
        io.send_data(feed_camera["key"], encoded_data)
        print("Sent image to IO!")
    else:
        print("ERROR: JPEG frame capture failed!")


while True:
    # Wait until the doorbell is pressed
    if not pin_button.value:
        print("Doorbell pressed!")
        
        # Turn the doorbell LED off to signal that it has been pressed
        led.value = False
        
        # Play a doorbell tone using the speaker
        pycam.tone(95, 0.5)
        pycam.tone(70, 0.5)
        
        capture_send_image()
        
        print("DONE, waiting for next press..")

        # Turn the LED on to signal that the doorbell is ready to be pressed again
        led.value = True
    time.sleep(0.01)
