# SPDX-FileCopyrightText: 2021 Brent Rubell, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense

from os import getenv
from adafruit_oauth2 import OAuth2
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
from adafruit_magtag.magtag import Graphics, Network
from adafruit_display_shapes.rect import Rect

# Get WiFi details, ensure these are setup in settings.toml
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")

if None in [ssid, password]:
    raise RuntimeError(
        "WiFi settings are kept in settings.toml, "
        "please add them there. The settings file must contain "
        "'CIRCUITPY_WIFI_SSID', 'CIRCUITPY_WIFI_PASSWORD', "
        "at a minimum."
    )

network = Network()
network.connect()

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

label_verification_url = Label(font_small, x=0, y=40, line_spacing=0.75, color=0x000000)
graphics.splash.append(label_verification_url)

label_user_code = Label(font_small, x=0, y=80, color=0x000000, line_spacing=0.75)
graphics.splash.append(label_user_code)

label_qr_code = Label(
    font_small, x=0, y=100, color=0x000000, text="Or scan the QR code:"
)
graphics.splash.append(label_qr_code)

# Set scope(s) of access required by the API you're using
scopes = ["https://www.googleapis.com/auth/calendar.readonly"]

# Initialize an OAuth2 object
google_auth = OAuth2(
    network.requests,
    getenv("google_client_id"),
    getenv("google_client_secret"),
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
label_verification_url.text = (
    "1. On your computer or mobile device,\ngo to %s" % google_auth.verification_url
)
label_user_code.text = "2. Enter code: %s" % google_auth.user_code

graphics.qrcode(google_auth.verification_url.encode(), qr_size=2, x=240, y=70)
graphics.display.root_group = graphics.splash
display.refresh()

# Poll Google's authorization server
print("Waiting for browser authorization...")
if not google_auth.wait_for_authorization():
    raise RuntimeError("Timed out waiting for browser response!")

print("Successfully Authenticated with Google!")
print("Add the following lines to your settings.toml file:")
print(f'google_access_token="{google_auth.access_token}"')
print(f'google_refresh_token="{google_auth.refresh_token}"')

graphics.splash.pop()
graphics.splash.pop()
graphics.splash.pop()

label_overview_text.text = "Successfully Authenticated!"
label_verification_url.text = (
    "Check the REPL for tokens to add\n\tto your settings.toml file"
)
display.refresh()
