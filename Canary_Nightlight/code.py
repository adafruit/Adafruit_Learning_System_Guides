# SPDX-FileCopyrightText: 2023 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
CircuitPython Canary Day and Night Light with Optional Network-Down Detection

This project uses the QT Py ESP32-S3 with the NeoPixel 5x5 LED Grid BFF, along with
a 3D printed bird. The LEDs light up different colors based on the time.

In the event that the internet connection fails, it will begin blinking red to notify you.
If the initial test ping fails, and the subsequent pings fail over 30 times, the board
will reset. Otherwise, the blinking will continue until the connection is back up. This
feature is enabled by default. It can easily be disabled at the beginning of the code.
"""
import os
import ssl
import time
import ipaddress
import supervisor
import board
import wifi
import microcontroller
import socketpool
import adafruit_requests
import neopixel
from adafruit_io.adafruit_io import IO_HTTP

# ============ CUSTOMISATIONS ============
# Network-down detection enable or disable.
# By default, the network-down detection code, and the code that blinks when the
# network is down, are both enabled. If you wish to disable this feature,
# including the blinking, update this to False.
NETWORK_DOWN_DETECTION = True

# The basic canary colors.
# Red light at night is more conducive to sleep. Blue light in the morning is more
# conducive to waking up. The sleep color defaults to red to promote sleep. The wake
# color defaults to blue to promote wakefulness.
SLEEP_COLOR = (255, 0, 0)  # Red
WAKE_COLOR = (0, 0, 255)  # Blue

# The blink color.
# This is the color that the canary will blink to notify you that the network is down.
# Defaults to red.
BLINK_COLOR = (255, 0, 0)

# Canary brightness customisation.
# Both the options below must be a float between 0.0 and 1.0, where 0.0 is off, and 1.0 is max.
# This is the brightness of the canary during sleep time. It defaults to 0.2, or "20%".
# Increase or decrease this value to change the brightness.
SLEEP_BRIGHTNESS = 0.2
# This is the brightness of the canary during wake time. It defaults to 0.7, or "70%".
# Increase or decrease this value to change the brightness.
WAKE_BRIGHTNESS = 0.7

# Consecutive ping fail to blink.
# This value is the number of times ping will consecutively fail before the canary begins blinking.
# If the blinking is happening too often, or if the network is often flaky, this value can be
# increased to extend the number of failures it takes to begin blinking.
# Defaults to 10. Must be an integer greater than 1.
CONSECUTIVE_PING_FAIL_TO_BLINK = 10

# Ping interval while ping is successful.
# This is the interval at which the code will send a ping while the network is up and the pings
# are successful. If for any reason you would prefer to slow down the ping interval, this value
# can be updated. Defaults to 1 second. Must be a float greater than 1. Increase this value to
# increase the ping interval time. Do not decrease this value!
UP_PING_INTERVAL = 1

# Checks whether the successful ping interval is below the minimum value.
if UP_PING_INTERVAL < 1:
    # If is below the minimum, raise this error and stop the code.
    raise ValueError("UP_PING_INTERVAL must be a float greater than 1!")

# Sleep time.
# This is the hour in 24-hour time at which the light should change to the
# desired color for the time you intend to sleep.
# Must be an integer between 0 and 23. Defaults to 20 (8pm).
SLEEP_TIME = 20

# Wake time.
# This is the hour in 24-hour time at which the light should change to the
# desired color for the time you intend to be awake.
# Must be an integer between 0 and 23. Defaults to 6 (6am).
WAKE_TIME = 6

# Time check interval.
# This sets the time interval at which the code checks Adafruit IO for the current time.
# This is included because Adafruit IO has rate limiting. It ensures that you do not
# hit the rate limit, and the time check does not get throttled.
# Defaults to 300 seconds (5 minutes). Must be a float greater than 300. Increase
# this value to increase the time check interval. Do not decrease this value!
TIME_CHECK_INTERVAL = 300

# Checks whether the time check interval is below the minimum value.
if TIME_CHECK_INTERVAL < 300:
    # If is below the minimum, raise this error and stop the code.
    raise ValueError("TIME_CHECK_INTERVAL must be a float greater than 300!")

# IP address.
# This is the IP address used to ping to verify that network connectivity is still present.
# To switch to a different IP, update the following. Must be a valid IPV4 address as a
# string (in quotes). Defaults to one of the OpenDNS IPs.
PING_IP = "208.67.222.222"

# ============ HARDWARE AND CODE SET UP ============
# Instantiate the NeoPixel object.
pixels = neopixel.NeoPixel(board.A3, 25)


# Create helper functions
def reload_on_error(delay, error_content=None, reload_type="reload"):
    """
    Reset the board when an error is encountered.

    :param float delay: The delay in seconds before the board should reset.
    :param Exception error_content: The error encountered. Used to print the error before reset.
    :param str reload_type: The type of reload desired. Defaults to "reload", which invokes
                            ``supervisor.reload()`` to soft-reload the board. To hard reset
                            the board, set this to "reset", which invokes
                            ``microcontroller.reset()``.
    """
    if str(reload_type).lower().strip() not in ["reload", "reset"]:
        raise ValueError("Invalid reload type:", reload_type)
    if error_content:
        print("Error:\n", str(error_content))
    if delay:
        print(
            f"{reload_type[0].upper() + reload_type[1:]} microcontroller in {delay} seconds."
        )
    time.sleep(delay)
    if reload_type == "reload":
        supervisor.reload()
    if reload_type == "reset":
        microcontroller.reset()


def color_time(current_hour):
    """
    Verifies what color the LEDs should be based on the time.

    :param current_hour: Provide a time, hour only. The `tm_hour` part of the
                         `io.receive_time()` object is acceptable here.
    """
    if WAKE_TIME < SLEEP_TIME:
        if WAKE_TIME <= current_hour < SLEEP_TIME:
            pixels.brightness = WAKE_BRIGHTNESS
            return WAKE_COLOR
        pixels.brightness = SLEEP_BRIGHTNESS
        return SLEEP_COLOR
    if SLEEP_TIME <= current_hour < WAKE_TIME:
        pixels.brightness = SLEEP_BRIGHTNESS
        return SLEEP_COLOR
    pixels.brightness = WAKE_BRIGHTNESS
    return WAKE_COLOR


def blink(color):
    """
    Blink the NeoPixel LEDs a specific color.

    :param tuple color: The color the LEDs will blink.
    """
    if color_time(sundial.tm_hour) == SLEEP_COLOR:
        pixels.brightness = SLEEP_BRIGHTNESS
    else:
        pixels.brightness = WAKE_BRIGHTNESS
    pixels.fill(color)
    time.sleep(0.5)
    pixels.fill((0, 0, 0))
    time.sleep(0.5)


# Connect to WiFi. This process can fail for various reasons. It is included in a try/except
# block to ensure the project continues running when unattended.
try:
    wifi.radio.connect(os.getenv("wifi_ssid"), os.getenv("wifi_password"))
    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl.create_default_context())
except Exception as error:  # pylint: disable=broad-except
    # The exceptions raised by the `wifi` module are not always clear. If you're receiving errors,
    # check your SSID and password before continuing.
    print("Wifi connection failed.")
    reload_on_error(5, error)

# Set up IP address to use for pinging, as defined above.
ip_address = ipaddress.IPv4Address(PING_IP)
# Set up ping, and send initial ping.
wifi_ping = wifi.radio.ping(ip=ip_address)
# If the initial ping is unsuccessful, print the message.
if wifi_ping is None:
    print("Setup test-ping failed.")
    # Set `initial_ping` to False to indicate the failure.
    initial_ping = False
else:
    # Otherwise, set `initial_ping` to True to indicate success.
    initial_ping = True

# Set up Adafruit IO. This will provide the current time through `io.receive_time()`.
io = IO_HTTP(os.getenv("aio_username"), os.getenv("aio_key"), requests)

# Retrieve the time on startup. This is included to verify that the Adafruit IO set
# up was successful. This process can fail for various reasons. It is included in a
# try/except block to ensure the project continues to run when unattended.
try:
    sundial = io.receive_time()  # Create the sundial variable to keep the time.
except Exception as error:  # pylint: disable=broad-except
    # If the time retrieval fails with an error, print the message.
    print("Adafruit IO set up and/or time retrieval failed.")
    # Then wait 5 seconds, and soft reload the board.
    reload_on_error(5, error)

# Initialise various time tracking variables.
ping_time = 0
check_time = 0
ping_fail_time = time.time()

# Initialise ping fail count tracking.
ping_fail_count = 0

# ============ LOOP ============
while True:
    # Resets current_time to the current second every time through the loop.
    current_time = time.time()
    # WiFi and IO connections can fail arbitrarily. The bulk of the loop is included in a
    # try/except block to ensure the project will continue to run unattended if any
    # failures do occur.
    try:
        # If this is the first run of the code or `UP_PING_INTERVAL` time has passed, continue.
        if not ping_time or current_time - ping_time > UP_PING_INTERVAL:
            ping_time = time.time()
            # Ping to verify network connection.
            wifi_ping = wifi.radio.ping(ip=ip_address)
            if wifi_ping is not None:
                # If the ping is successful, print IP address and ping time.
                print(f"Pinging {ip_address}: {wifi_ping} ms")

        # If the ping is successful, continue with this code.
        if wifi_ping is not None:
            ping_fail_count = 0
            # If this is the first run of the code or `TIME_CHECK_INTERVAL` has passed, continue.
            if not check_time or current_time - check_time > TIME_CHECK_INTERVAL:
                check_time = time.time()
                # Retrieve the time and save it to sundial.
                sundial = io.receive_time()
                # Print the current date and time to the serial console.
                print(f"LED color time-check. Date and time: {sundial.tm_year}-{sundial.tm_mon}-" +
                      f"{sundial.tm_mday} {sundial.tm_hour}:{sundial.tm_min:02}")
                # Provides the current hour to the color_time function. This verifies the
                # current color based on time and returns that color, which is provided
                # to `fill()` to set the LED color.
                pixels.fill(color_time(sundial.tm_hour))

        # If the ping has failed, and it's been one second, continue with this code.
        if wifi_ping is None and current_time - ping_fail_time > 1:
            ping_fail_time = time.time()  # Reset the ping fail time to continue tracking.
            ping_fail_count += 1  # Add one to the fail count tracking.
            print(f"Ping failed {ping_fail_count} times")
            # If network down detection is enabled, run the following code.
            if NETWORK_DOWN_DETECTION:
                # If the ping fail count exceeds the value defined above, begin blinking the LED
                # to indicate that the network is down.
                if ping_fail_count > CONSECUTIVE_PING_FAIL_TO_BLINK:
                    blink(BLINK_COLOR)
                # If the initial setup ping failed, it means the network connection was failing
                # from the beginning, and might require reloading the board. So, if the initial
                # ping failed and the ping_fail_count is greater than 30, immediately soft reload
                # the board.
                if not initial_ping and ping_fail_count > 30:
                    reload_on_error(0)
                # If the initial ping succeeded, the blinking will continue until the connection
                # is reestablished and the pings are once again successful.

    # ============ ERROR HANDLING ============
    # Since network-related code can fail arbitrarily in a variety of ways, this final block is
    # included to reset the board when an error is encountered.
    # When the error is thrown, wait 10 seconds, and hard reset the board.
    except Exception as error:  # pylint: disable=broad-except
        reload_on_error(10, error, reload_type="reset")
