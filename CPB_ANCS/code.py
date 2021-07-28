"""
This demo shows the latest icons from a connected Apple device on a TFT Gizmo screen.

The A and B buttons on the CircuitPlayground Bluefruit can be used to scroll through all active
notifications. The screen's backlight will turn off after a certain number of seconds to save power.
New notifications or pressing the buttons should turn it back on.
"""

import time
import board
import digitalio
import displayio
import adafruit_ble
from adafruit_ble.advertising.standard import SolicitServicesAdvertisement
from adafruit_ble_apple_notification_center import AppleNotificationCenterService
from adafruit_gizmo import tft_gizmo
from audiocore import WaveFile
from audiopwmio import PWMAudioOut as AudioOut

# Enable the speaker
speaker_enable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
speaker_enable.direction = digitalio.Direction.OUTPUT
speaker_enable.value = True

audio = AudioOut(board.SPEAKER)

# This is a whitelist of apps to show notifications from.
APP_ICONS = {
    "com.tinyspeck.chatlyio": "/ancs_slack.bmp",
    "com.basecamp.bc3-ios": "/ancs_basecamp.bmp",
    "com.apple.MobileSMS": "/ancs_sms.bmp",
    "com.hammerandchisel.discord": "/ancs_discord.bmp",
    "com.apple.mobilecal": "/ancs_ical.bmp",
    "com.apple.mobilephone": "/ancs_phone.bmp"
}

BLOCKLIST = []
DELAY_AFTER_PRESS = 15
DEBOUNCE = 0.1
DIM_TIMEOUT = 20   # Amount of timeout to turn off backlight
DIM_LEVEL = 0.05

a = digitalio.DigitalInOut(board.BUTTON_A)
a.switch_to_input(pull=digitalio.Pull.DOWN)
b = digitalio.DigitalInOut(board.BUTTON_B)
b.switch_to_input(pull=digitalio.Pull.DOWN)

file = open("/triode_rise.wav", "rb")
wave = WaveFile(file)

def play_sound():
    audio.play(wave)
    time.sleep(1)

def find_connection():
    for connection in radio.connections:
        if AppleNotificationCenterService not in connection:
            continue
        if not connection.paired:
            connection.pair()
        return connection, connection[AppleNotificationCenterService]
    return None, None

class Dimmer:
    def __init__(self):
        self._update_time = time.monotonic()
        self._level = DIM_LEVEL
        self._timeout = DIM_TIMEOUT

    def update(self):
        self._update_time = time.monotonic()

    def check_timeout(self):
        if a.value or b.value:
            self._update_time = time.monotonic()
        if time.monotonic() - self._update_time > self._timeout:
            if display.brightness > self._level:
                display.brightness = self._level
        else:
            if display.brightness == self._level:
                display.brightness = 1.0

dimmer = Dimmer()

# Start advertising before messing with the display so that we can connect immediately.
radio = adafruit_ble.BLERadio()
advertisement = SolicitServicesAdvertisement()
advertisement.complete_name = "CIRCUITPY"
advertisement.solicited_services.append(AppleNotificationCenterService)

def wrap_in_tilegrid(filename:str):
    # CircuitPython 6 & 7 compatible
    odb = displayio.OnDiskBitmap(open(filename, "rb"))
    return displayio.TileGrid(
        odb, pixel_shader=getattr(odb, 'pixel_shader', displayio.ColorConverter())
    )

    # # CircuitPython 7+ compatible
    # odb = displayio.OnDiskBitmap(filename)
    # return displayio.TileGrid(odb, pixel_shader=odb.pixel_shader)

display = tft_gizmo.TFT_Gizmo()
group = displayio.Group()
group.append(wrap_in_tilegrid("/ancs_connect.bmp"))
display.show(group)

current_notification = None
current_notifications = {}
all_ids = []
last_press = time.monotonic()
active_connection, notification_service = find_connection()
cleared = False

while True:
    if not active_connection:
        radio.start_advertising(advertisement)

    while not active_connection:
        active_connection, notification_service = find_connection()
        dimmer.check_timeout()

    # Connected
    dimmer.update()
    play_sound()

    no_notifications = "/ancs_none.bmp"
    group.append(wrap_in_tilegrid(no_notifications))
    while active_connection.connected:
        all_ids.clear()
        current_notifications = notification_service.active_notifications
        for notif_id in current_notifications:
            notification = current_notifications[notif_id]
            if notification.app_id not in APP_ICONS or notification.app_id in BLOCKLIST:
                continue
            all_ids.append(notif_id)

        # pylint: disable=protected-access
        all_ids.sort(key=lambda x: current_notifications[x]._raw_date)
        # pylint: enable=protected-access

        if current_notification and current_notification.removed:
            # Stop showing the latest and show that there are no new notifications.
            current_notification = None

        if not current_notification and not all_ids and not cleared:
            cleared = True
            dimmer.update()
            group[1] = wrap_in_tilegrid(no_notifications)
        elif all_ids:
            cleared = False
            now = time.monotonic()
            if current_notification and current_notification.id in all_ids and \
                now - last_press < DELAY_AFTER_PRESS:
                index = all_ids.index(current_notification.id)
            else:
                index = len(all_ids) - 1
            if now - last_press >= DEBOUNCE:
                if b.value and index > 0:
                    last_press = now
                    index += -1
                if a.value and index < len(all_ids) - 1:
                    last_press = now
                    index += 1
            notif_id = all_ids[index]
            if not current_notification or current_notification.id != notif_id:
                dimmer.update()
                current_notification = current_notifications[notif_id]
                # pylint: disable=protected-access
                print(current_notification._raw_date, current_notification)
                # pylint: enable=protected-access
                group[1] = wrap_in_tilegrid(APP_ICONS[current_notification.app_id])

        dimmer.check_timeout()

    # Bluetooth Disconnected
    group.pop()
    dimmer.update()
    active_connection = None
    notification_service = None
