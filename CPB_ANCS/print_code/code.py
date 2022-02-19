# SPDX-FileCopyrightText: 2019 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""This demo shows the latest notification from a connected Apple device on the REPL and Gizmo"""
import time
import adafruit_ble
from adafruit_ble.advertising.standard import SolicitServicesAdvertisement
from adafruit_ble_apple_notification_center import AppleNotificationCenterService
from adafruit_gizmo import tft_gizmo

# This is a whitelist of apps to show notifications from.
#APPS = ["com.tinyspeck.chatlyio", "com.atebits.Tweetie2"]
APPS = []

DELAY_AFTER_PRESS = 15
DEBOUNCE = 0.1

def find_connection():
    for connection in radio.connections:
        if AppleNotificationCenterService not in connection:
            continue
        if not connection.paired:
            connection.pair()
        return connection, connection[AppleNotificationCenterService]
    return None, None

# Start advertising before messing with the display so that we can connect immediately.
radio = adafruit_ble.BLERadio()
advertisement = SolicitServicesAdvertisement()
advertisement.complete_name = "CIRCUITPY"
advertisement.solicited_services.append(AppleNotificationCenterService)

display = tft_gizmo.TFT_Gizmo()

current_notification = None
new_ids = []
displayed_ids = []
active_connection, notification_service = find_connection()
while True:
    if not active_connection:
        radio.start_advertising(advertisement)

    while not active_connection:
        print("waiting for connection...")
        active_connection, notification_service = find_connection()
        time.sleep(0.1)

    while active_connection.connected:
        current_notifications = notification_service.active_notifications
        for notification_id in current_notifications:
            if notification_id in displayed_ids:
                continue # already seen!
            notification = current_notifications[notification_id]
            print('-'*36)
            category = str(notification).split(" ", 1)[0]
            print("Msg #%d - Category %s" % (notification.id, category))
            print("From app:", notification.app_id)
            if notification.title:
                print("Title:", notification.title)
            if notification.subtitle:
                print("Subtitle:", notification.subtitle)
            if notification.message:
                print("Message:", notification.message)
            displayed_ids.append(id)
    active_connection = None
    notification_service = None
