# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import os
import ssl
import wifi
import socketpool
import microcontroller
import adafruit_requests

#  query URL for tweets. looking for tweets from Adafruit that have the text "NEW GUIDE"
#  disabling line-too-long because queries for tweet_query & TIME_URL cannot have line breaks
#  pylint: disable=line-too-long
tweet_query = 'https://api.twitter.com/2/tweets/search/recent?query=NEW GUIDE from:adafruit&tweet.fields=created_at'

headers = {'Authorization': 'Bearer ' + os.getenv('bearer_token')}

wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

last_id = 0 #  checks last tweet's ID
check = 0 #  time.monotonic() holder

while True:
    try:
        if (check + 30) < time.monotonic():
            #  updates current time
            #  get tweets from rpilocator containing in stock at adafruit
            twitter_response = requests.get(url=tweet_query, headers=headers)
            #  gets data portion of json
            twitter_json = twitter_response.json()
            twitter_json = twitter_json['data']
            #  to see the entire json feed, uncomment 'print(twitter_json)'
            #  print(twitter_json)
            #  tweet ID number
            tweet_id = twitter_json[0]['id']
            #  tweet text
            tweet = twitter_json[0]['text']
            #  timestamp
            timestamp = twitter_json[0]['created_at']
            if last_id != tweet_id:
                print("New Learn Guide!")
                print(tweet)
                print(timestamp)
                last_id = tweet_id
            check = time.monotonic()
    # pylint: disable=broad-except
    #  any errors, reset Pico W
    except Exception as e:
        print("Error:\n", str(e))
        print("Resetting microcontroller in 10 seconds")
        time.sleep(10)
        microcontroller.reset()
