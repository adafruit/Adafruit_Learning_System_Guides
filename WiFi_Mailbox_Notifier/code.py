# SPDX-FileCopyrightText: 2022 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""CircuitPython WiFi Mailbox Notifier"""

import time
import ssl
import alarm
import board
import digitalio
import analogio
import wifi
import socketpool
import supervisor
import microcontroller
import adafruit_requests
from adafruit_io.adafruit_io import IO_HTTP

# Get WiFi/Adafruit IO details from secrets.py
try:
    from secrets import secrets
except ImportError:
    print("Please create secrets.py and add your WiFi and AIO credentials there!")
    raise

# Update to True if you want metadata sent to Adafruit IO. Defaults to False.
METADATA = False

# If the reason the board started up is not the standard CircuitPython reset-type start up...
if supervisor.runtime.run_reason is not supervisor.RunReason.STARTUP:
    alarm.sleep_memory[3] += 1  # Increment reload number by 1.
    print(f"Reload number {alarm.sleep_memory[3]}")  # Print current reload number.
    if alarm.sleep_memory[3] > 5:  # If reload number exceeds 5...
        # Print the following...
        print("Reload not resolving the issue. \nBoard will hard reset in 20 seconds. ")
        time.sleep(20)  # ...wait 20 seconds...
        microcontroller.reset()  # ...and hard reset the board. This will clear alarm.sleep_memory.

# Initialise metadata.
if alarm.wake_alarm:
    print("Awake", alarm.wake_alarm)
    # Increment wake count by 1.
    alarm.sleep_memory[0] += 1
else:
    print("No wake up alarm")
    # Set wake count to 0.
    alarm.sleep_memory[0] = 0
    # Set error count to 0.
    alarm.sleep_memory[2] = 0

# Set up battery monitoring.
voltage_pin = analogio.AnalogIn(board.VOLTAGE_MONITOR)
# Take the raw voltage pin value, and convert it to voltage.
voltage = ((voltage_pin.value * 2) * 3.3) / 65536

# Set up red LED.
led = digitalio.DigitalInOut(board.LED)
led.switch_to_output()

# Set up the alarm pin.
switch_pin = digitalio.DigitalInOut(board.D27)
switch_pin.pull = digitalio.Pull.UP


# Send the data. Requires a feed name and a value to send.
def send_io_data(feed, value):
    """
    Send data to Adafruit IO.

    Provide an Adafruit IO feed name, and the value you wish to send.
    """
    return io.send_data(feed["key"], value)


# Print wake count to serial console.
print("Wake count:", alarm.sleep_memory[0])

# Connect to WiFi
try:
    wifi.radio.connect(secrets["ssid"], secrets["password"])
    print("Connected to {}!".format(secrets["ssid"]))
    print("IP:", wifi.radio.ipv4_address)

    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl.create_default_context())
# WiFi connectivity fails with error messages, not specific errors, so this except is broad.
except Exception as e:  # pylint: disable=broad-except
    print("Failed to connect to WiFi. Error:", e, "\nBoard will reload in 15 seconds.")
    alarm.sleep_memory[2] += 1  # Increment error count by one.
    time.sleep(15)
    supervisor.reload()

# Set your Adafruit IO Username and Key in secrets.py
# (visit io.adafruit.com if you need to create an account,
# or if you need your Adafruit IO key.)
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]

# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_username, aio_key, requests)

# Print battery voltage to the serial console. Not necessary for Adafruit IO.
print(f"Current battery voltage: {voltage:.2f}")

# No data has been sent yet, so the send-count is 0.
alarm.sleep_memory[1] = 0

# Turn on the LED to indicate data is being sent.
led.value = True

# While the switch is open...
while not switch_pin.value:
    # Adafruit IO sending can run into issues if the network fails!
    # This ensures the code will continue to run.
    try:
        # Send data to Adafruit IO
        print("Sending new mail alert and battery voltage to Adafruit IO.")
        send_io_data(io.create_and_get_feed("new-mail"), "New mail!")
        send_io_data(io.create_and_get_feed("battery-voltage"), f"{voltage:.2f}V")
        print("Data sent!")
        if METADATA:
            print("Sending metadata to AdafruitIO.")
            # The number of times the board has awakened in the current cycle.
            send_io_data(io.create_and_get_feed("wake-count"), alarm.sleep_memory[0])
            # The number of times the mailbox/battery data has been sent.
            send_io_data(io.create_and_get_feed("send-count"), alarm.sleep_memory[1])
            # The number of Adafruit IO errors that has occurred.
            send_io_data(io.create_and_get_feed("error-count"), alarm.sleep_memory[2])
            print("Metadata sent!")
        time.sleep(30)  # Delay included to avoid data limit throttling on Adafruit IO.
        alarm.sleep_memory[1] += 1  # Increment data send count by 1.
        led.value = False  # Turn off the LED to indicate data sending is complete.

    # Adafruit IO can fail with multiple errors depending on the situation, so this except is broad.
    except Exception as e:  # pylint: disable=broad-except
        print("Failed to send to Adafruit IO. Error:", e, "\nBoard will reload in 15 seconds.")
        alarm.sleep_memory[2] += 1  # Increment error count by one.
        time.sleep(15)
        supervisor.reload()

# Deinitialise the alarm pin.
switch_pin.deinit()

# Turn off the NeoPixel/I2C power for deep sleep.
power_pin = digitalio.DigitalInOut(board.NEOPIXEL_I2C_POWER)
power_pin.switch_to_output(False)

# Turn off LED for deep sleep.
led.value = False

# Create an alarm on pin D27.
pin_alarm = alarm.pin.PinAlarm(pin=board.D27, value=False, pull=True)

print("Entering deep sleep.")

# Exit and set the alarm.
alarm.exit_and_deep_sleep_until_alarms(pin_alarm)
