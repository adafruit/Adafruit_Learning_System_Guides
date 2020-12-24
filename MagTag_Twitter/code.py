# SPDX-FileCopyrightText: 2019 Dave Astels for Adafruit Industries.
# SPDX-FileCopyrightText: 2020 Brent Rubell for Adafruit Industries.
#
# SPDX-License-Identifier: Unlicense
import time
from adafruit_magtag.magtag import MagTag

try:
    from secrets import secrets
except ImportError:
    print("""WiFi settings are kept in secrets.py, please add them there!
the secrets dictionary must contain 'ssid' and 'password' at a minimum""")
    raise

# Set to the twitter username you'd like to fetch tweets from
TWITTER_USERNAME = 'cnn'

# Set up where we'll be fetching data from
DATA_SOURCE = "https://api.twitter.com/1.1/statuses/user_timeline.json?count=1&screen_name=%s"%TWITTER_USERNAME
TWEET_TEXT = [0, 'text']
TWEET_FULL_NAME = [0, 'user', 'name']
TWEET_HANDLE = [0, 'user', 'screen_name']

magtag = MagTag(
    url=DATA_SOURCE,
    json_path=(TWEET_FULL_NAME, TWEET_HANDLE, TWEET_TEXT)
)
magtag.set_background("/images/background.bmp")

# Set Twitter OAuth2.0 Bearer Token
bearer_token = secrets['twitter_bearer_token']
magtag.set_headers({'Authorization': 'Bearer ' + bearer_token})

print('W: ', magtag.graphics.display.width)
print('H: ', magtag.graphics.display.height)

# Twitter full name
magtag.add_text(
    text_position=(70, 10),
    text_font="/fonts/Arial-Bold-12.pcf",
)

# Twitter handle (@username)
magtag.add_text(
    text_position=(70, 30),
    text_font="/fonts/Arial-Bold-12.pcf",
    text_transform=lambda x: "@%s"%x,
)

# Tweet text
magtag.add_text(
    text_position=(
        (magtag.graphics.display.width // 2),
        (magtag.graphics.display.height // 2) - 50,
    ),
    text_font="/fonts/Arial-Italic-12.bdf",
    text_wrap=28,
    line_spacing = 0.75,
    text_maxlen=140,
    text_anchor_point=(0.5, 0.5)
)

try:
    value = magtag.fetch()
    print("Response is", value)
except (ValueError, RuntimeError) as e:
    print("Some error occured, retrying! -", e)
magtag.exit_and_deep_sleep(60)