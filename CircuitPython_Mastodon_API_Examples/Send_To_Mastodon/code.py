# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import os
import ssl
import wifi
import socketpool
import adafruit_requests

# add your mastodon token as 'mastodon_token' to your .env file
headers = {'Authorization': 'Bearer ' + os.getenv('mastodon_token')}

# add your mastodon instance to your .env file as mastodon_host
url = 'https://' + os.getenv('mastodon_host') + '/api/v1/statuses'

# connect to SSID
wifi.radio.connect(os.getenv('WIFI_SSID'), os.getenv('WIFI_PASSWORD'))

pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool, ssl.create_default_context())

# you'll be prompted in the REPL to enter your post text
post = input("Please enter your Mastodon post text: ")
# pack the post for sending with the API
post_text = {"status": post}

# confirm in the REPL that you want to post by entering y for yes or n for no
send_check = input("Send post to Mastodon (y/n)?")

# if you type y
if send_check == "y":
    # send to mastodon with a POST request
    r = requests.post(url, data=post_text, headers=headers)
    print()
    print("You posted '%s' to Mastodon. Goodbye." % post)
# if you type n
else:
    print("You did not post to Mastodon. Goodbye.")
