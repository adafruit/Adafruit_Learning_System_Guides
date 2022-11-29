# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import os
import re
import time
import ssl
import wifi
import socketpool
import microcontroller
import adafruit_requests

#  enter the hashtag that you want to follow
hashtag = "CircuitPython"

#  connect to SSID
wifi.radio.connect(os.getenv('WIFI_SSID'), os.getenv('WIFI_PASSWORD'))

#  add your mastodon token as 'mastodon_token' to your .env file
headers = {'Authorization': 'Bearer ' + os.getenv('mastodon_token') + 'read:statuses'}

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

#  initial request, gets most recent matching hashtag post
#  add your mastodon instance (mastodon.social, tech.lgbt, etc) to your .env file as mastodon_host
r = requests.get("https://%s/api/v1/timelines/tag/%s?limit=1" % (os.getenv('mastodon_host'), hashtag), headers=headers) # pylint: disable=line-too-long
json_data = r.json()
post_id = str(json_data[0]['id'])
print("A new #%s post from @%s:" % (hashtag, str(json_data[0]['account']['acct'])))
print(re.sub('<[^>]+>', '', json_data[0]['content']))
print()

while True:
    try:
        time.sleep(360)
        # compares post_id to see if a new post to the hashtag has been found
        r = requests.get("https://%s/api/v1/timelines/tag/%s?since_id=%s" % (os.getenv('mastodon_host'), hashtag, post_id), headers=headers) # pylint: disable=line-too-long
        json_data = r.json()
        json_length = len(json_data)
        # if the id's match, then the json array is empty (length of 0)
        # otherwise there is a new post
        if json_length > 0:
            post_id = str(json_data[0]['id'])
            print("A new #%s post from @%s:" % (hashtag, str(json_data[0]['account']['acct'])))
            print(re.sub('<[^>]+>', '', json_data[0]['content']))
            print()
        else:
            print("no new #%s posts" % hashtag)
            print(json_length)
            print()

    except Exception as e:  # pylint: disable=broad-except
        print("Error:\n", str(e))
        print("Resetting microcontroller in 10 seconds")
        time.sleep(10)
        microcontroller.reset()
