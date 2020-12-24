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

# Set up where we'll be fetching data from
TWITTER_USERNAME = 'brentrubell'
DATA_SOURCE = "https://api.twitter.com/1.1/statuses/user_timeline.json?count=1&screen_name=%s"%TWITTER_USERNAME
TWEET_TEXT = [0, 'text']
TWEET_FULL_NAME = [0, 'user', 'name']
TWEET_HANDLE = [0, 'user', 'screen_name']

magtag = MagTag(
    url=DATA_SOURCE,
    json_path=(TWEET_HANDLE, TWEET_FULL_NAME, TWEET_TEXT)
)

# Set Twitter OAuth2.0 Bearer Token
bearer_token = secrets['twitter_bearer_token']
magtag.set_headers({'Authorization': 'Bearer ' + bearer_token})

# Twitter handle
magtag.add_text(
    text_position=(
        (magtag.graphics.display.width // 2) - 1,
        (magtag.graphics.display.height // 2) - 1,
    )
)

# Twitter full name
magtag.add_text(
    text_position=(
        (magtag.graphics.display.width // 2) - 1,
        (magtag.graphics.display.height // 2) - 1,
    )
)

# Tweet text
magtag.add_text(
    text_position=(0,0,)
)


try:
    value = magtag.fetch()
    print("Response is", value)
    magtag.set_text(value)
except (ValueError, RuntimeError) as e:
    print("Some error occured, retrying! -", e)
magtag.exit_and_deep_sleep(60)