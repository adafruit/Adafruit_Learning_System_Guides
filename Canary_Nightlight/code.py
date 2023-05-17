# SPDX-FileCopyrightText: 2023 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
CircuitPython Canary Day and Night Light with Optional Network-Down Detection

This project uses the QT Py ESP32-S3 with the NeoPixel 5x5 LED Grid BFF in a 3D printed bird.
The LEDs light up blue or red based on a user-definable time.

In the event that the internet connection fails, it will begin blinking red to notify you.
If the initial test ping fails, and the subsequent pings fail over 30 times, the board
will reset. Otherwise, the blinking will continue until the connection is back up. This
feature is enabled by default. It can easily be disabled at the beginning of the code,
if desired.
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

# This determines whether to run the network-down detection code, and therefore
# whether to run the code that blinks when the network is down.
# Defaults to True. Set to False to disable.
NETWORK_DOWN_DETECTION = True

# This is the number of times ping should fail before it begins blinking.
# If the blinking is happening too often, or if the network is often flaky,
# this value can be increased to extend the number of failures it takes to
# begin blinking. Defaults to 10.
PING_FAIL_NUMBER_TO_BLINK = 10

# Red light at night is more conducive to sleep. This light is designed
# to turn red at the chosen time to not disrupt sleep.
# This is the hour in 24-hour time at which the light should change to red.
# Must be an integer between 0 and 23. Defaults to 20 (8pm).
RED_TIME = 20

# Blue light in the morning is more conducive to waking up. This light is designed
# to turn blue at the chosen time to promote wakefulness.
# This is the hour in 24-hour time at which the light should change to blue.
# Must be an integer between 0 and 23. Defaults to 6 (6am).
BLUE_TIME = 6

# NeoPixel brightness configuration.
# Both the options below must be a float between 0.0 and 1.0, where 0.0 is off, and 1.0 is max.
# This is the brightness of the LEDs when they are red. As this is expected to be
# during a time when you are heading to sleep, it defaults to 0.2, or "20%".
# Increase or decrease this value to change the brightness.
RED_BRIGHTNESS = 0.2

# This is the brightness of the LEDs when they are blue. As this is expected to be
# during a time when you want wakefulness, it defaults to 0.7, or "70%".
# Increase or decrease this value to change the brightness.
BLUE_BRIGHTNESS = 0.7

# Define the light colors. The default colors are blue and red.
BLUE = (0, 0, 255)
RED = (255, 0, 0)

# Instantiate the NeoPixel object.
pixels = neopixel.NeoPixel(board.A3, 25)


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
    if BLUE_TIME < RED_TIME:
        if BLUE_TIME <= current_hour < RED_TIME:
            pixels.brightness = BLUE_BRIGHTNESS
            return BLUE
        pixels.brightness = RED_BRIGHTNESS
        return RED
    if RED_TIME <= current_hour < BLUE_TIME:
        pixels.brightness = RED_BRIGHTNESS
        return RED
    pixels.brightness = BLUE_BRIGHTNESS
    return BLUE


def blink(color):
    """
    Blink the NeoPixel LEDs a specific color.

    :param tuple color: The color the LEDs will blink.
    """
    if color_time(sundial.tm_hour) == RED:
        pixels.brightness = RED_BRIGHTNESS
    else:
        pixels.brightness = BLUE_BRIGHTNESS
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
    # The exceptions raised by the wifi module are not always clear. If you're receiving errors,
    # check your SSID and password before continuing.
    print("Wifi connection failed.")
    reload_on_error(5, error)

# Set up IP address to ping to test internet connection, and do an initial ping.
# This address is an OpenDNS IP.
ip_address = ipaddress.IPv4Address("208.67.222.222")
wifi_ping = wifi.radio.ping(ip=ip_address)
if wifi_ping is None:  # If the initial ping is unsuccessful...
    print("Setup test-ping failed.")  # ...print this message...
    initial_ping = False  # ...and set initial_ping to False to indicate the failure.
else:  # Otherwise...
    initial_ping = True  # ...set initial_ping to True to indicate success.

# Set up Adafruit IO. This will provide the current time through `io.receive_time()`.
io = IO_HTTP(os.getenv("aio_username"), os.getenv("aio_key"), requests)

# Retrieve the time on startup. This is included to verify that the Adafruit IO set
# up was successful. This process can fail for various reasons. It is included in a
# try/except block to ensure the project continues to run when unattended.
try:
    sundial = io.receive_time()  # Create the sundial variable to keep the time.
except Exception as error:  # pylint: disable=broad-except
    # If the time retrieval fails with an error...
    print(
        "Adafruit IO set up and/or time retrieval failed."
    )  # ...print this message...
    reload_on_error(5, error)  # ...wait 5 seconds, and soft reload the board.

# Set up various time intervals for tracking non-blocking time intervals
time_check_interval = 300
ping_interval = 1

# Initialise various time tracking variables
ping_time = 0
check_time = 0
ping_fail_time = time.monotonic()

# Initialise ping fail count tracking
ping_fail_count = 0
while True:
    # Resets current_time to the current time.monotonic() value every time through the loop.
    current_time = time.monotonic()
    # WiFi and IO connections can fail arbitrarily. The bulk of the loop is included in a
    # try/except block to ensure the project will continue to run unattended if any
    # failures do occur.
    try:
        # If the first run of the code, or ping_interval time has passed...
        if not ping_time or current_time - ping_time > ping_interval:
            ping_time = time.monotonic()
            wifi_ping = wifi.radio.ping(ip=ip_address)  # ...ping to verify network connection.
            if wifi_ping is not None:  # If the ping is successful...
                # ...print IP address and ping time.
                print(f"Pinging {ip_address}: {wifi_ping} ms")

        # If the ping is successful...
        if wifi_ping is not None:
            ping_fail_count = 0
            # If the first run of the code or time_check_interval has passed...
            if not check_time or current_time - check_time > time_check_interval:
                check_time = time.monotonic()
                sundial = io.receive_time()  # Retrieve the time and save it to sundial.
                # Print the current date and time to the serial console.
                print(f"LED color time-check. Date and time: {sundial.tm_year}-{sundial.tm_mon}-" +
                      f"{sundial.tm_mday} {sundial.tm_hour}:{sundial.tm_min:02}")
                # Provides the current hour to the color_time function. This verifies the
                # current color based on time and returns that color, which is provided
                # to `fill()` to set the LED color.
                pixels.fill(color_time(sundial.tm_hour))

        if wifi_ping is None and current_time - ping_fail_time > ping_interval:
            # If the ping has failed, and it's been one second (the same interval as the ping)...
            ping_fail_time = time.monotonic()  # Reset the ping fail time to continue tracking.
            ping_fail_count += 1  # Increase the fail count by one.
            print(f"Ping failed {ping_fail_count} times")
            # If network down detection is enabled, run the following code.
            if NETWORK_DOWN_DETECTION:
                # If the ping fail count exceeds the number configured above...
                if ping_fail_count > PING_FAIL_NUMBER_TO_BLINK:
                    blink(RED)  # ...begin blinking the LEDs red to indicate the network is down.
                # If the initial setup ping failed, it means the network connection was failing
                # from the beginning, and might require reloading the board. So, if the initial
                # ping failed and the ping_fail_count is greater than 30...
                if not initial_ping and ping_fail_count > 30:
                    reload_on_error(0)  # ...immediately soft reload the board.
                # If the initial ping succeeded, the blinking will continue until the connection
                # is reestablished and the pings are once again successful.

    # There is rarely an issue with pinging which causes the board to fail with a MemoryError.
    # The MemoryError is not necessarily related to the code, and the code continues to run
    # when this error is ignored. So, in this case, it catches this error separately...
    except MemoryError as error:
        pass  # ...ignores it, and tells the code to continue running.
    # Since network-related code can fail arbitrarily in a variety of ways, this final block is
    # included to reset the board when an error (other than the MemoryError) is encountered.
    # When the error is thrown...
    except Exception as error:  # pylint: disable=broad-except
        # ...wait 10 seconds and hard reset the board.
        reload_on_error(10, error, reload_type="reset")
