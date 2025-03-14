# SPDX-FileCopyrightText: Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
CHEEKMATE: secret message receiver using WiFi, Adafruit IO and a haptic
buzzer. Periodically polls an Adafruit IO dashboard, converting new messages
to Morse code.
"""

from os import getenv
import gc
import time
import ssl
import adafruit_drv2605
import adafruit_requests
import board
import busio
import neopixel
import socketpool
import supervisor
import wifi
from adafruit_io.adafruit_io import IO_HTTP

# Get WiFi details and Adafruit IO keys, ensure these are setup in settings.toml
# (visit io.adafruit.com if you need to create an account, or if you need your Adafruit IO key.)
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")
aio_username = getenv("ADAFRUIT_AIO_USERNAME")
aio_key = getenv("ADAFRUIT_AIO_KEY")

if None in [ssid, password, aio_username, aio_key]:
    raise RuntimeError(
        "WiFi and Adafruit IO settings are kept in settings.toml, "
        "please add them there. The settings file must contain "
        "'CIRCUITPY_WIFI_SSID', 'CIRCUITPY_WIFI_PASSWORD', "
        "'ADAFRUIT_AIO_USERNAME' and 'ADAFRUIT_AIO_KEY' at a minimum."
    )

# CONFIGURABLE GLOBALS -----------------------------------------------------

FEED_KEY = "cheekmate"  #  Adafruit IO feed name
POLL = 10  #               Feed polling interval in seconds
REPS = 3  #                Max number of times to repeat new message
WPM = 15  #                Morse code words-per-minute
BUZZ = 255  #              Haptic buzzer amplitude, 0-255
LED_BRIGHTNESS = 0.2  #    NeoPixel brightness 0.0-1.0, or 0 to disable
LED_COLOR = (255, 0, 0)  # NeoPixel color (R, G, B), 0-255 ea.

# These values are derived from the 'WPM' setting above and do not require
# manual editing. The dot, dash and gap times are set according to accepted
# Morse code procedure.
DOT_LENGTH = 1.2 / WPM  #         Duration of one Morse dot
DASH_LENGTH = DOT_LENGTH * 3.0  # Duration of one Morse dash
SYMBOL_GAP = DOT_LENGTH  #        Duration of gap between dot or dash
CHARACTER_GAP = DOT_LENGTH * 3  # Duration of gap between characters
MEDIUM_GAP = DOT_LENGTH * 7  #    Duraction of gap between words

# Morse code symbol-to-mark conversion dictionary. This contains the
# standard A-Z and 0-9, and extra symbols "+" and "=" sometimes used
# in chess. If other symbols are needed for this or other games, they
# can be added to the end of the list.
MORSE = {
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    "0": "-----",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    "+": ".-.-.",
    "=": "-...-",
}

# SOME FUNCTIONS -----------------------------------------------------------


def buzz_on():
    """Turn on LED and haptic motor."""
    pixels[0] = LED_COLOR
    drv.mode = adafruit_drv2605.MODE_REALTIME


def buzz_off():
    """Turn off LED and haptic motor."""
    pixels[0] = 0
    drv.mode = adafruit_drv2605.MODE_INTTRIG


def play(string):
    """Convert a string to Morse code, output to both the onboard LED
       and the haptic motor."""
    gc.collect()
    for symbol in string.upper():
        if code := MORSE.get(symbol):  # find Morse code for character
            for mark in code:
                buzz_on()
                time.sleep(DASH_LENGTH if mark == "-" else DOT_LENGTH)
                buzz_off()
                time.sleep(SYMBOL_GAP)
            time.sleep(CHARACTER_GAP - SYMBOL_GAP)
        else:
            time.sleep(MEDIUM_GAP)


# NEOPIXEL INITIALIZATION --------------------------------------------------

# This assumes there is a board.NEOPIXEL, which is true for QT Py ESP32-S2
# and some other boards, but not ALL CircuitPython boards. If adapting the
# code to another board, you might use digitalio with board.LED or similar.
pixels = neopixel.NeoPixel(
    board.NEOPIXEL, 1, brightness=LED_BRIGHTNESS, auto_write=True
)

# HAPTIC MOTOR CONTROLLER INIT ---------------------------------------------

# board.SCL1 and SDA1 are the "extra" I2C interface on the QT Py ESP32-S2's
# STEMMA connector. If adapting to a different board, you might want
# board.SCL and SDA as the sole or primary I2C interface.
i2c = busio.I2C(board.SCL1, board.SDA1)
drv = adafruit_drv2605.DRV2605(i2c)

# "Real-time playback" (RTP) is an unusual mode of the DRV2605 that's not
# handled in the library by default, but is desirable here to get accurate
# Morse code timing. This requires bypassing the library for a moment and
# writing a couple of registers directly...
while not i2c.try_lock():
    pass
i2c.writeto(0x5A, bytes([0x1D, 0xA8]))  # Amplitude will be unsigned
i2c.writeto(0x5A, bytes([0x02, BUZZ]))  # Buzz amplitude
i2c.unlock()

# WIFI CONNECT -------------------------------------------------------------

try:
    print(f"Connecting to {ssid}...")
    wifi.radio.connect(ssid, password)
    print("OK")
    print(f"IP: {wifi.radio.ipv4_address}")

    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl.create_default_context())
    # WiFi uses error messages, not specific exceptions, so this is "broad":
except Exception as error:  # pylint: disable=broad-except
    print("error:", error, "\nBoard will reload in 15 seconds.")
    time.sleep(15)
    supervisor.reload()

# ADAFRUIT IO INITIALIZATION -----------------------------------------------

io = IO_HTTP(aio_username, aio_key, requests)

# SUCCESSFUL STARTUP, PROCEED INTO MAIN LOOP -------------------------------

buzz_on()
time.sleep(0.75)  # Long buzz indicates everything is OK
buzz_off()

current_message = ""  # No message on startup
rep = REPS  #           Act as though message is already played out
last_time = -POLL  #    Force initial Adafruit IO polling

while True:  # Repeat forever...

    now = time.monotonic()
    if now - last_time >= POLL:  #            Time to poll Adafruit IO feed?
        last_time = now  #                    Do it! Do it now!
        feed = io.get_feed(FEED_KEY)
        new_message = feed["last_value"]
        if new_message != current_message:  # If message has changed,
            current_message = new_message  #  Save it,
            rep = 0  #                        and reset the repeat counter

    # Play last message up to REPS times. If a new message has come along in
    # the interim, old message may repeat less than this, and new message
    # resets the count.
    if rep < REPS:
        play(current_message)
        time.sleep(MEDIUM_GAP)
        rep += 1
