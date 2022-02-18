# SPDX-FileCopyrightText: 2020 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import busio
import neopixel
import adafruit_drv2605
import adafruit_led_animation.color as color
import adafruit_ble
from adafruit_ble.advertising.standard import SolicitServicesAdvertisement
from adafruit_ble.services.standard import CurrentTimeService
from adafruit_ble_apple_notification_center import AppleNotificationCenterService
from digitalio import DigitalInOut, Direction

#  setup for onboard NeoPixel
pixel_pin = board.NEOPIXEL
num_pixels = 1

pixel = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.3, auto_write=False)

#  setup for haptic motor driver
i2c = busio.I2C(board.SCL, board.SDA)
drv = adafruit_drv2605.DRV2605(i2c)

#  onboard blue LED
blue_led = DigitalInOut(board.BLUE_LED)
blue_led.direction = Direction.OUTPUT

#  setup for BLE
ble = adafruit_ble.BLERadio()
if ble.connected:
    for c in ble.connections:
        c.disconnect()

advertisement = SolicitServicesAdvertisement()

#  adds ANCS and current time services for BLE to advertise
advertisement.solicited_services.append(AppleNotificationCenterService)
advertisement.solicited_services.append(CurrentTimeService)

#  state machines
current_notification = None #  tracks the current notification from ANCS
current_notifications = {} #  array to hold all current notifications from ANCS
cleared = False #  state to track if notifications have been cleared from ANCS
notification_service = None #  holds the array of active notifications from ANCS
all_ids = [] #  array to hold all of the ids from ANCS
hour = 0 #  used to track when it is on the hour for the mindfulness reminder
mindful = False #  state used to track if it is time for mindfulness
vibration = 16 #  vibration effect being used for the haptic motor

APP_COLORS = {
    "com.basecamp.bc3-ios": color.YELLOW, #  Basecamp
    "com.apple.MobileSMS": color.GREEN, #  Texts
    "com.hammerandchisel.discord": color.PURPLE, #  Discord
    "com.apple.mobilecal": color.CYAN, #  Calendar
    "com.apple.mobilephone": color.GREEN, #  Phone
    "com.google.ios.youtube": color.ORANGE, #  YouTube
    "com.burbn.instagram": color.MAGENTA, #  Instagram
    "com.apple.mobilemail": color.CYAN #  Apple Email
}

#  function for blinking NeoPixel
#  blinks: # of blinks
#  speed: how fast/slow blinks
#  color1: first color
#  color2: second color
def blink_pixel(blinks, speed, color1, color2):
    for _ in range(0, blinks):
        pixel.fill(color1)
        pixel.show()
        time.sleep(speed)
        pixel.fill(color2)
        pixel.show()
        time.sleep(speed)

#  function for haptic motor vibration
#  num_zzz: # of times vibrates
#  effect: type of vibration
#  delay: time between vibrations
def vibe(num_zzz, effect, delay):
    drv.sequence[0] = adafruit_drv2605.Effect(effect)
    for _ in range(0, num_zzz):
        drv.play()  # play the effect
        time.sleep(delay)  # for 0.5 seconds
        drv.stop()

#  start BLE
ble.start_advertising(advertisement)

while True:

    blue_led.value = False
    print("Waiting for connection")

    #  NeoPixel is red when not connected to BLE
    while not ble.connected:
        blue_led.value = False
        pixel.fill(color.RED)
        pixel.show()
    print("Connected")

    while ble.connected:
        blue_led.value = True #  blue LED is on when connected
        all_ids.clear()
        for connection in ble.connections:
            if not connection.paired:
                #  pairs to phone
                connection.pair()
                print("paired")
            #  allows connection to CurrentTimeService
            cts = connection[CurrentTimeService]
            notification_service = connection[AppleNotificationCenterService]
        #  grabs notifications from ANCS
        current_notifications = notification_service.active_notifications

        for notif_id in current_notifications:
            #  adds notifications into array
            notification = current_notifications[notif_id]
            all_ids.append(notif_id)

        #  all_ids.sort(key=lambda x: current_notifications[x]._raw_date)

        if current_notification and current_notification.removed:
            # Stop showing the latest and show that there are no new notifications.
            current_notification = None
            pixel.fill(color.BLACK)
            pixel.show()

        if not current_notification and not all_ids and not cleared:
            #  updates cleared state for notification
            cleared = True
            #  turns off NeoPixel when notifications are clear
            pixel.fill(color.BLACK)
            pixel.show()

        elif all_ids:
            cleared = False
            if current_notification and current_notification.id in all_ids:
                index = all_ids.index(current_notification.id)
            else:
                index = len(all_ids) - 1
                notif_id = all_ids[index]
            #  if there is a notification:
            if not current_notification or current_notification.id != notif_id:
                current_notification = current_notifications[notif_id]
                #  if the notification is from an app that is not
                #  defined in APP_COLORS then the NeoPixel will be white
                if current_notification.app_id not in APP_COLORS:
                    notif_color = color.WHITE
                #  if the notification is from an app defined in
                #  APP_COLORS then the assigned color will show
                else:
                    notif_color = APP_COLORS[current_notification.app_id]
                #  parses notification info into a string
                category = str(notification).split(" ", 1)[0]
                #  haptic motor vibrates
                vibe(2, vibration, 0.5)
                #  all info for notification is printed to REPL
                print('-'*36)
                print("Msg #%d - Category %s" % (notification.id, category))
                print("From app:", notification.app_id)
                if notification.title:
                    print("Title:", notification.title)
                if notification.subtitle:
                    print("Subtitle:", notification.subtitle)
                if notification.message:
                    print("Message:", notification.message)
                #  NeoPixel blinks and then stays on until cleared
                blink_pixel(2, 0.5, notif_color, color.BLACK)
                pixel.fill(notif_color)
                pixel.show()
        #  if it's on the hour:
        if cts.current_time[4] == hour and not mindful:
            print(cts.current_time[4])
            print("mindful time")
            #  haptic motor vibrates
            vibe(5, vibration, 1)
            #  NeoPixel blinks and then stays on
            blink_pixel(5, 1, color.BLUE, color.BLACK)
            mindful = True
            pixel.fill(color.BLUE)
            pixel.show()
            print("hour = ", hour)
        #  if it's no longer on the hour:
        if cts.current_time[4] == (hour + 1) and mindful:
            #  NeoPixel turns off
            mindful = False
            pixel.fill(color.BLACK)
            pixel.show()
            print("mindful time over")

    #  if BLE becomes disconnected then blue LED turns off
    #  and BLE begins advertising again to reconnect
    print("Disconnected")
    blue_led.value = False
    print()
    ble.start_advertising(advertisement)
    notification_service = None
