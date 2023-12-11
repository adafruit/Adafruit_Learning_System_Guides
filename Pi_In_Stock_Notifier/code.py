# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import ssl
import wifi
import terminalio
import socketpool
import displayio
import board
from adafruit_display_text import bitmap_label,  wrap_text_to_lines
import adafruit_requests
from digitalio import DigitalInOut, Direction, Pull
from adafruit_debouncer import Debouncer

alarm_out = DigitalInOut(board.A1)
alarm_out.direction = Direction.OUTPUT
alarm_out.value = False

button_in = DigitalInOut(board.BUTTON)  # on-board Boot button on Feather ESP32-S2 TFT
button_in.pull = Pull.UP
button = Debouncer(button_in)


# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

print("Adafruit Raspberry Pi In Stock Tweet Listener")

#  import your bearer token
bear = secrets['bearer_token']

#  query URL for tweets. looking for hashtag partyparrot sent to a specific username
#  disabling line-too-long because queries for tweet_query & TIME_URL cannot have line breaks
#  pylint: disable=line-too-long
tweet_query = 'https://api.twitter.com/2/tweets/search/recent?query=In Stock at Adafruit from:rpilocator&tweet.fields=created_at'

headers = {'Authorization': 'Bearer ' + bear}

print("Connecting to %s"%secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!"%secrets["ssid"])
print("My IP address is", wifi.radio.ipv4_address)

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

#  gets and formats time from adafruit.io
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]
location = secrets.get("timezone", None)
TIME_URL = "https://io.adafruit.com/api/v2/%s/integrations/time/strftime?x-aio-key=%s" % (aio_username, aio_key)
TIME_URL += "&fmt=%25Y-%25m-%25dT%25H%3A%25M%3A%25S.%25L%25j%25u%25z%25Z"

display = board.DISPLAY

group = displayio.Group()
font = terminalio.FONT
text = ''
text_area = bitmap_label.Label(font, text=text, scale=2, color=0xFFFFFF)
text_area.x = 0
text_area.y = 15
clock = ''
clock_area = bitmap_label.Label(font, text=clock, color=0xFFFFFF)
clock_area.x = 125
clock_area.y = 128
group.append(text_area)
group.append(clock_area)
display.root_group = group

last_value = 0 #  checks last tweet's ID
check = 0 #  time.monotonic() holder

#  fetching current time
print("Fetching text from", TIME_URL)
current_time = requests.get(TIME_URL)
print("-" * 40)
print(current_time.text)
print("-" * 40)

alarm_out.value = False  # this starts the alarm so you can test turning it off w the boot button


while True:
    button.update()
    if button.fell:
        print("Alarm off")
        alarm_out.value = False

    #  every 30 seconds...
    if (check + 30) < time.monotonic():
        #  updates current time
        current_time = requests.get(TIME_URL)
        print(current_time.text)
        #  get tweets from rpilocator containing in stock at adafruit
        the_tweet = requests.request("GET", url=tweet_query, headers=headers)
        #  gets data portion of json
        data = the_tweet.json()['data']
        #  tweet ID number
        value = data[0]['id']
        #  tweet text
        stock_check = data[0]['text']
        #  timestamp
        timestamp = data[0]['created_at']
        #  reset time count
        check = time.monotonic()
        #  compare last tweet ID and current tweet ID
        if last_value != value:
            #  compares date of tweet timestamp with current date
            if timestamp.startswith(current_time.text[0 : 10]):
                print("match")
                #  grabs the hour of the tweet timestamp
                tweet_hour = int(timestamp[11:13])
                print(tweet_hour)
                #  grabs the current hour
                current_hour = int(current_time.text[11:13])
                print(current_hour)
                #  if it's been less than an hour since the tweet...
                if abs(current_hour - tweet_hour) < 1:
                    print("in the last hour")
                    #  displays tweet text and time on screen
                    text_area.text = "\n".join(wrap_text_to_lines(stock_check, 21))
                    print(stock_check)
                    clock_area.text = timestamp
                    print("Raspberry Pi in stock at Adafruit!")
                    alarm_out.value = True

                else:
                    #  if it's not new, then the wait continues
                    no_tweet_text = ("No stock in last hour :( Last stock: %s" % (timestamp))
                    text_area.text = "\n".join(wrap_text_to_lines(no_tweet_text, 21))
                    print("no new in stock notifications :(")
            #  updates tweet ID
            last_value = value
        #  if the tweet wasn't today
        else:
            #  if it's not new, then the wait continues
            no_tweet_text = ("No stock in last hour :( Last stock: %s" % (timestamp))
            text_area.text = "\n".join(wrap_text_to_lines(no_tweet_text, 21))
            print("no new in stock notifications :(")
