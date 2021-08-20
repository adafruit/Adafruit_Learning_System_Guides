# SPDX-FileCopyrightText: 2021 Brent Rubell, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
import ssl
import board
import wifi
import socketpool
import adafruit_requests as requests
from adafruit_oauth2 import OAuth2
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from adafruit_magtag.magtag import Graphics
from adafruit_display_shapes.rect import Rect

# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("Credentials and tokens are kept in secrets.py, please add them there!")
    raise

print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!" % secrets["ssid"])

pool = socketpool.SocketPool(wifi.radio)
requests = requests.Session(pool, ssl.create_default_context())

# DisplayIO setup
font_small = bitmap_font.load_font("/fonts/Arial-12.pcf")
font_large = bitmap_font.load_font("/fonts/Arial-14.pcf")

graphics = Graphics(auto_refresh=False)
display = graphics.display

background = Rect(0, 0, 296, 128, fill=0xFFFFFF)
graphics.splash.append(background)

label_overview_text = Label(
    font_large,
    x=0,
    y=10,
    line_spacing=0.75,
    color=0x000000,
    text="Authorize this device with Google:",
)
graphics.splash.append(label_overview_text)

label_verification_url = Label(
    font_small, x=0, y=40, line_spacing=0.75, color=0x000000
)
graphics.splash.append(label_verification_url)

label_user_code = Label(
    font_small, x=0, y=80, color=0x000000, line_spacing=0.75
)
graphics.splash.append(label_user_code)

label_qr_code = Label(
    font_small, x=0, y=100, color=0x000000, text="Or scan the QR code:"
)
graphics.splash.append(label_qr_code)

# Set scope(s) of access required by the API you're using
scopes = ["https://www.googleapis.com/auth/calendar.readonly"]

# Initialize an OAuth2 object
google_auth = OAuth2(
    requests, secrets["google_client_id"], secrets["google_client_secret"], scopes
)

# Request device and user codes
# https://developers.google.com/identity/protocols/oauth2/limited-input-device#step-1:-request-device-and-user-codes
google_auth.request_codes()

# Display user code and verification url
# NOTE: If you are displaying this on a screen, ensure the text label fields are
# long enough to handle the user_code and verification_url.
# Details in link below:
# https://developers.google.com/identity/protocols/oauth2/limited-input-device#displayingthecode
print(
    "1) Navigate to the following URL in a web browser:", google_auth.verification_url
)
print("2) Enter the following code:", google_auth.user_code)
label_verification_url.text = (
    "1. On your computer or mobile device,\ngo to %s" % google_auth.verification_url
)
label_user_code.text = "2. Enter code: %s" % google_auth.user_code

graphics.qrcode(google_auth.verification_url.encode(), qr_size=2, x=240, y=70)
board.DISPLAY.show(graphics.splash)
display.refresh()

# Poll Google's authorization server
print("Waiting for browser authorization...")
if not google_auth.wait_for_authorization():
    raise RuntimeError("Timed out waiting for browser response!")

print("Successfully Authenticated with Google!")
print("Add the following lines to your secrets.py file:")
print("\t'google_access_token' " + ":" + " '%s'," % google_auth.access_token)
print("\t'google_refresh_token' " + ":" + " '%s'" % google_auth.refresh_token)

graphics.splash.pop()
graphics.splash.pop()
graphics.splash.pop()

label_overview_text.text = "Successfully Authenticated!"
label_verification_url.text = (
    "Check the REPL for tokens to add\n\tto your secrets.py file"
)
display.refresh()
