# SPDX-FileCopyrightText: 2021 Brent Rubell, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from adafruit_oauth2 import OAuth2
from adafruit_pyportal import Network, Graphics

# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

network = Network()
network.connect()

graphics = Graphics()

# DisplayIO Setup
# Set up fonts
font_small = bitmap_font.load_font("/fonts/Arial-12.pcf")
font_large = bitmap_font.load_font("/fonts/Arial-14.pcf")
# preload fonts
glyphs = b"0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.: "
font_small.load_glyphs(glyphs)
font_large.load_glyphs(glyphs)

label_overview_text = Label(
    font_large, x=0, y=45, text="To authorize this device with Google:"
)
graphics.splash.append(label_overview_text)

label_verification_url = Label(font_small, x=0, y=100, line_spacing=1)
graphics.splash.append(label_verification_url)

label_user_code = Label(font_small, x=0, y=150)
graphics.splash.append(label_user_code)

label_qr_code = Label(font_small, x=0, y=190, text="Or scan the QR code:")
graphics.splash.append(label_qr_code)

# Set scope(s) of access required by the API you're using
scopes = ["https://www.googleapis.com/auth/calendar.readonly"]

# Initialize an oauth2 object
google_auth = OAuth2(
    network.requests,
    secrets["google_client_id"],
    secrets["google_client_secret"],
    scopes,
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

# modify display labels to show verification URL and user code
label_verification_url.text = (
    "1. On your computer or mobile device,\n    go to: %s"
    % google_auth.verification_url
)
label_user_code.text = "2. Enter code: %s" % google_auth.user_code

# Create a QR code
graphics.qrcode(google_auth.verification_url.encode(), qr_size=2, x=170, y=165)
graphics.display.root_group = graphics.splash

# Poll Google's authorization server
print("Waiting for browser authorization...")
if not google_auth.wait_for_authorization():
    raise RuntimeError("Timed out waiting for browser response!")

print("Successfully Authenticated with Google!")

# print formatted keys for adding to secrets.py
print("Add the following lines to your secrets.py file:")
print("\t'google_access_token' " + ":" + " '%s'," % google_auth.access_token)
print("\t'google_refresh_token' " + ":" + " '%s'" % google_auth.refresh_token)
# Remove QR code and code/verification labels
graphics.splash.pop()
graphics.splash.pop()
graphics.splash.pop()

label_overview_text.text = "Successfully Authenticated!"
label_verification_url.text = (
    "Check the REPL for tokens to add\n\tto your secrets.py file"
)

# prevent exit
while True:
    pass
