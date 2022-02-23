# SPDX-FileCopyrightText: 2020 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Eddystone Beacon for CLUE
This example broadcasts our Mac Address as our Eddystone ID and a link to a URL of your choice.
Hold the A button to display QR code, use B button to pick URL from the list.
"""

import time
from adafruit_pybadger import pybadger
import adafruit_ble
from adafruit_ble_eddystone import uid, url

radio = adafruit_ble.BLERadio()

# Reuse the BLE address as our Eddystone instance id.
eddystone_uid = uid.EddystoneUID(radio.address_bytes)

# List of URLs to broadcast here:
ad_url = [("https://circuitpython.org", "CirPy"),
          ("https://adafru.it/discord","DISCORD"),
          ("https://forums.adafruit.com", "Forums"),
          ("https://learn.adafruit.com", "Learn")
         ]
pick = 0  # use to increment url choices

pybadger.play_tone(1600, 0.25)
pybadger.show_business_card(image_name="cluebeacon.bmp")

while True:
    pybadger.auto_dim_display(delay=3, movement_threshold=4)
    eddystone_url = url.EddystoneURL(ad_url[pick][0])

    if pybadger.button.a and not pybadger.button.b:  # Press button A to show QR code
        pybadger.play_tone(1200, 0.1)
        pybadger.brightness = 1
        pybadger.show_qr_code(data=ad_url[pick][0])  # Tests QR code
        time.sleep(0.1)  # Debounce

    elif pybadger.button.b and not pybadger.button.a:  # iterate through urls to broadcast
        pybadger.play_tone(1600, 0.2)
        pick = (pick + 1) % len(ad_url)
        pybadger.brightness = 1
        pybadger.show_business_card(image_name="bg.bmp", name_string=ad_url[pick][1], name_scale=5,
                                    email_string_one="", email_string_two=ad_url[pick][0])
        time.sleep(0.1)

    elif pybadger.button.a and pybadger.button.b:
        pybadger.play_tone(1000, 0.2)
        pybadger.brightness = 1
        pybadger.show_business_card(image_name="cluebeacon.bmp")
        time.sleep(0.1)

    # Alternate between advertising our ID and our URL.
    radio.start_advertising(eddystone_uid)
    time.sleep(0.5)
    radio.stop_advertising()

    radio.start_advertising(eddystone_url)
    time.sleep(0.5)
    radio.stop_advertising()

    time.sleep(1)
