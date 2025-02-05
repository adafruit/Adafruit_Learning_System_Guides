# SPDX-FileCopyrightText: 2025 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''
Espresso Tank Meter
Feather ESP32-S2 with RCWL-1601 Ultrasonic distance sensor
'''

import time
import os
import ssl
import microcontroller
import supervisor
import socketpool
import wifi
import board
import alarm
import neopixel
import adafruit_hcsr04
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT
import adafruit_requests
import adafruit_max1704x

# Initialize the sonar sensor
sonar = adafruit_hcsr04.HCSR04(trigger_pin=board.A0, echo_pin=board.A1)

# Initialize the battery monitor
i2c = board.I2C()  # uses board.SCL and board.SDA
battery_monitor = adafruit_max1704x.MAX17048(i2c)

# Define colors (hex values)
WHITE = 0xFFFFFF
BLUE = 0x0000FF
GREEN = 0x00FF00
YELLOW = 0xFFFF00
RED = 0xFF0000
PINK = 0xbb00bb
CYAN = 0x00bbbb
OFF = 0x000000

# Initialize the NeoPixel
pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.25)
# Show yellow on startup
pixel.fill(YELLOW)

# Operating hours (24-hour format with minutes, e.g., "6:35" and "16:00")
OPENING_TIME = "6:00"
CLOSING_TIME = "22:30"
# Normal operation check interval
NORMAL_CHECK_MINUTES = 5
# Sleep duration in seconds during operating hours
SLEEP_DURATION = 60 * NORMAL_CHECK_MINUTES
# Display duration in seconds
DISPLAY_DURATION = 1
# Number of samples to average
NUM_SAMPLES = 5

def parse_time(time_str):
    """Convert time string (HH:MM format) to hours and minutes."""
    # pylint: disable=redefined-outer-name
    parts = time_str.split(':')
    return int(parts[0]), int(parts[1])

def get_average_distance():
    """Take multiple distance readings and return the average."""
    distances = []
    for _ in range(NUM_SAMPLES):
        try:
            distance = sonar.distance
            distances.append(distance)
            time.sleep(0.1)  # Short delay between readings
        except RuntimeError:
            print("Error reading distance")
            continue

    # Only average valid readings
    if distances:
        return sum(distances) / len(distances)
    return None

def set_pixel_color(distance):
    """Set NeoPixel color based on distance."""
    if distance is None:
        pixel.fill(OFF)
        return

    if distance < 2:
        pixel.fill(WHITE)
    elif 2 <= distance < 10:
        pixel.fill(BLUE)
    elif 10 <= distance < 16:
        pixel.fill(GREEN)
    elif 18 <= distance < 20:
        pixel.fill(YELLOW)
    else:  # distance >= 22
        pixel.fill(RED)

# Wait for things to settle before reading sonar
time.sleep(0.1)

# Get average distance
avg_distance = get_average_distance()

if avg_distance is not None:

    if avg_distance >= 22:
        # pylint: disable=invalid-name
        avg_distance = 22
    print(f"Average distance: {avg_distance:.1f} cm")
    # Set color based on average distance
    set_pixel_color(avg_distance)

    # Check battery status
    battery_voltage = battery_monitor.cell_voltage
    battery_percent = battery_monitor.cell_percent
    print(f"Battery: {battery_percent:.1f}% ({battery_voltage:.2f}V)")

    # Try connecting to WiFi
    try:

        print("Connecting to %s" % os.getenv("CIRCUITPY_WIFI_SSID"))
        # Show pink while attempting to connect
        pixel.fill(PINK)
        wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
        print("Connected to %s" % os.getenv("CIRCUITPY_WIFI_SSID"))
        # Show cyan on successful connection
        pixel.fill(CYAN)
        time.sleep(1)  # Brief pause to show the connection success

    except Exception as e:
        print("Failed to connect to WiFi. Error:", e, "\nBoard will hard reset in 30 seconds.")
        pixel.fill(OFF)
        time.sleep(10)
        microcontroller.reset()

    # Create a socket pool
    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl.create_default_context())

    # Initialize a new MQTT Client object
    mqtt_client = MQTT.MQTT(
        broker="io.adafruit.com",
        username=os.getenv("ADAFRUIT_AIO_USERNAME"),
        password=os.getenv("ADAFRUIT_AIO_KEY"),
        socket_pool=pool,
        ssl_context=ssl.create_default_context(),
    )

    # Initialize Adafruit IO MQTT "helper"
    io = IO_MQTT(mqtt_client)

    try:
        # If Adafruit IO is not connected...
        if not io.is_connected:
            print("Connecting to Adafruit IO...")
            io.connect()

        # Get current time from AIO time service
        aio_username = os.getenv("ADAFRUIT_AIO_USERNAME")
        aio_key = os.getenv("ADAFRUIT_AIO_KEY")
        timezone = os.getenv("TIMEZONE")
        # pylint: disable=line-too-long
        TIME_URL = f"https://io.adafruit.com/api/v2/{aio_username}/integrations/time/strftime?x-aio-key={aio_key}&tz={timezone}"
        TIME_URL += "&fmt=%25Y-%25m-%25d+%25H%3A%25M%3A%25S.%25L+%25j+%25u+%25z+%25Z"

        print("Getting time from Adafruit IO...")
        response = requests.get(TIME_URL)
        time_str = response.text.strip()  # Remove any leading/trailing whitespace
        print("Current time:", time_str)

        # Parse the current time from the time string
        time_parts = time_str.split()
        current_time = time_parts[1].split(':')
        current_hour = int(current_time[0])
        current_minute = int(current_time[1])

        # Get opening and closing hours and minutes
        opening_hour, opening_minute = parse_time(OPENING_TIME)
        closing_hour, closing_minute = parse_time(CLOSING_TIME)

        # Convert all times to minutes for easier comparison
        current_minutes = current_hour * 60 + current_minute
        opening_minutes = opening_hour * 60 + opening_minute
        closing_minutes = closing_hour * 60 + closing_minute

        # Check if we're within operating hours
        if opening_minutes <= current_minutes < closing_minutes:
            print(f"Within operating hours ({OPENING_TIME} to {CLOSING_TIME}), proceeding with measurement")

            # Explicitly pump the message loop
            io.loop()

            # Send the distance data
            print(f"Publishing {avg_distance:.1f} to espresso water level feed")
            io.publish("espresso-water-tank-level", f"{avg_distance:.1f}")

            # Send the battery data
            print(f"Publishing {battery_percent:.1f} to battery level feed")
            io.publish("espresso-water-sensor-battery", f"{battery_percent:.1f}")


            # Make sure the message gets sent
            io.loop()

            print("Water level sent successfully")

            # Keep NeoPixel lit for DISPLAY_DURATION seconds
            time.sleep(DISPLAY_DURATION)

            # Use normal check interval during operating hours
            # # pylint: disable=invalid-name
            sleep_seconds = SLEEP_DURATION
            print(f"Next check in {NORMAL_CHECK_MINUTES} minutes")
        else:
            print(f"Outside operating hours ({OPENING_TIME} to {CLOSING_TIME}), going back to sleep")
            # Calculate time until next opening
            if current_minutes >= closing_minutes:
                # After closing, calculate time until opening tomorrow
                minutes_until_open = (24 * 60 - current_minutes) + opening_minutes
            else:
                # Before opening, calculate time until opening today
                minutes_until_open = opening_minutes - current_minutes

            # Convert minutes to seconds for sleep duration
            sleep_seconds = minutes_until_open * 60
            hours_until_open = minutes_until_open // 60
            minutes_remaining = minutes_until_open % 60
            if minutes_remaining:
                print(f"Sleeping until {OPENING_TIME} ({hours_until_open} hours, {minutes_remaining} minutes)")
            else:
                print(f"Sleeping until {OPENING_TIME} ({hours_until_open} hours)")

        response.close()


    except Exception as e:
        print("Failed to get or send data, or connect. Error:", e,
              "\nBoard will hard reset in 30 seconds.")
        pixel.fill(OFF)
        time.sleep(30)
        microcontroller.reset()

else:
    print("Failed to get valid distance readings")
    pixel.fill(OFF)
    # pylint: disable=invalid-name
    sleep_seconds = SLEEP_DURATION  # Use normal interval if we couldn't get readings

# Prepare for deep sleep
pixel.brightness = 0  # Turn off NeoPixel

# Flush the serial output before sleep
# pylint: disable=pointless-statement
supervisor.runtime.serial_bytes_available
time.sleep(0.05)

# Create time alarm
time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + sleep_seconds)

# Enter deep sleep
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
