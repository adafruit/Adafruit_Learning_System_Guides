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
TWITTER_USERNAME = 'nytimes'

# Set to the amount of time to deep sleep for, in minutes
SLEEP_TIME = 15

# Set up where we'll be fetching data from
DATA_SOURCE="https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name=%s&count=1&tweet_mode=extended"%TWITTER_USERNAME
TWEET_TEXT = [0, 'full_text']
TWEET_FULL_NAME = [0, 'user', 'name']
TWEET_HANDLE = [0, 'user', 'screen_name']

magtag = MagTag(
    url=DATA_SOURCE,
    json_path=(TWEET_FULL_NAME, TWEET_HANDLE, TWEET_TEXT)
)
# Set Twitter OAuth2.0 Bearer Token
bearer_token = secrets['twitter_bearer_token']
magtag.set_headers({'Authorization': 'Bearer ' + bearer_token})

# Display setup
magtag.set_background("/images/background.bmp")

# Twitter name
magtag.add_text(
    text_position=(70, 10),
    text_font="/fonts/Arial-Bold-12.pcf",
)

# Twitter handle (@username)
magtag.add_text(
    text_position=(70, 30),
    text_font="/fonts/Arial-12.bdf",
    text_transform=lambda x: "@%s"%x,
)

# Tweet text
magtag.add_text(
    text_font="/fonts/Arial-Bold-12.pcf",
    text_wrap=30,
    text_maxlen=160,
    text_position=(
        5,
        (magtag.graphics.display.height // 2)+20,
    ),
    line_spacing=0.75,
)

# preload characters
magtag.preload_font()

try:
    value = magtag.fetch()
    print("Response is", value)
except (ValueError, RuntimeError) as e:
    print("Some error occured, retrying! -", e)

time.sleep(2)
print("Sleeping!")
magtag.exit_and_deep_sleep(SLEEP_TIME * 60)