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

# If the reason the board started up is due to a supervisor.reload()...
if supervisor.runtime.run_reason is supervisor.RunReason.SUPERVISOR_RELOAD:
    alarm.sleep_memory[3] += 1  # Increment reload number by 1.
    print(f"Reload number: {alarm.sleep_memory[3]}")  # Print current supervisor reload number.
    if alarm.sleep_memory[3] > 5:  # If supervisor reload number exceeds 5...
        # Print the following...
        print("Reload is not resolving the issue. \nBoard will hard reset in 20 seconds. ")
        time.sleep(20)  # ...wait 20 seconds...
        microcontroller.reset()  # ...and hard reset the board. This will clear alarm.sleep_memory.

# Initialise metadata.
if alarm.wake_alarm:
    print("Awake! Alarm type:", alarm.wake_alarm)
    # Increment wake count by 1.
    alarm.sleep_memory[0] += 1
else:
    print("Wakeup not caused by alarm.")
    # Set wake count to 0.
    alarm.sleep_memory[0] = 0
    # Set error count to 0.
    alarm.sleep_memory[2] = 0

# Print wake count to serial console.
print("Alarm wake count:", alarm.sleep_memory[0])

# No data has been sent yet, so the send-count is 0.
alarm.sleep_memory[1] = 0

# Set up battery monitoring.
voltage_pin = analogio.AnalogIn(board.VOLTAGE_MONITOR)
# Take the raw voltage pin value, and convert it to voltage.
voltage = (voltage_pin.value / 65536) * 2 * 3.3

# Set up red LED.
led = digitalio.DigitalInOut(board.LED)
led.switch_to_output()

# Set up the alarm pin.
switch_pin = digitalio.DigitalInOut(board.D27)
switch_pin.pull = digitalio.Pull.UP


# Send the data. Requires a feed name and a value to send.
def send_io_data(feed_name, value):
    """
    Send data to Adafruit IO.
    Provide an Adafruit IO feed name, and the value you wish to send.
    """
    feed = io.create_and_get_feed(feed_name)
    return io.send_data(feed["key"], value)


# Connect to WiFi
try:
    wifi.radio.connect(secrets["ssid"], secrets["password"])
    print("Connected to {}!".format(secrets["ssid"]))
    print("IP:", wifi.radio.ipv4_address)

    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl.create_default_context())
# WiFi connectivity fails with error messages, not specific errors, so this except is broad.
except Exception as error:  # pylint: disable=broad-except
    print("Failed to connect to WiFi. Error:", error, "\nBoard will reload in 15 seconds.")
    alarm.sleep_memory[2] += 1  # Increment error count by one.
    time.sleep(15)
    supervisor.reload()

# Pull your Adafruit IO username and key from secrets.py
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]
# Initialize an Adafruit IO HTTP API object
io = IO_HTTP(aio_username, aio_key, requests)

# Print battery voltage to the serial console and send it to Adafruit IO.
print(f"Current battery voltage: {voltage:.2f}V")
# Adafruit IO can run into issues if the network fails!
# This try/except ensures your code will continue to run.
try:
    led.value = True  # Turn on the LED to indicate data is being sent.
    send_io_data("battery-voltage", f"{voltage:.2f}V")
    led.value = False  # Turn off the LED to indicate data sending is complete.
# Adafruit IO can fail with multiple errors depending on the situation, so this except is broad.
except Exception as error:  # pylint: disable=broad-except
    print("Failed to send to Adafruit IO. Error:", error, "\nBoard will reload in 15 seconds.")
    alarm.sleep_memory[2] += 1  # Increment error count by one.
    time.sleep(15)
    supervisor.reload()

# While the door is open...
while not switch_pin.value:
    # Adafruit IO sending can run into various issues which cause errors.
    # This try/except ensures the code will continue to run.
    try:
        led.value = True  # Turn on the LED to indicate data is being sent.
        # Send data to Adafruit IO
        print("Sending new mail alert to Adafruit IO.")
        send_io_data("new-mail", "New mail!")
        print("Data sent!")
        # If METADATA = True at the beginning of the code, send more data.
        if METADATA:
            print("Sending metadata to Adafruit IO.")
            # The number of times the board has awakened by an alarm since the last reset.
            send_io_data("wake-count", alarm.sleep_memory[0])
            # The number of times the mailbox data has been sent.
            send_io_data("send-count", alarm.sleep_memory[1])
            # The number of WiFi or Adafruit IO errors that have occurred.
            send_io_data("error-count", alarm.sleep_memory[2])
            print("Metadata sent!")
        time.sleep(30)  # Delay included to avoid data limit throttling on Adafruit IO.
        alarm.sleep_memory[1] += 1  # Increment data send count by 1.
        led.value = False  # Turn off the LED to indicate data sending is complete.

    # Adafruit IO can fail with multiple errors depending on the situation, so this except is broad.
    except Exception as error:  # pylint: disable=broad-except
        print("Failed to send to Adafruit IO. Error:", error, "\nBoard will reload in 15 seconds.")
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

# Create a timer alarm to be triggered every 12 hours (43200 seconds).
time_alarm = alarm.time.TimeAlarm(monotonic_time=(time.monotonic() + 43200))

# Create a pin alarm on pin D27.
pin_alarm = alarm.pin.PinAlarm(pin=board.D27, value=False, pull=True)

print("Entering deep sleep.")

# Exit and set the alarm.
alarm.exit_and_deep_sleep_until_alarms(pin_alarm, time_alarm)
