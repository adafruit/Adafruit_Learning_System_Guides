# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Written by Liz Clark (Adafruit Industries) with OpenAI ChatGPT v4 Feb 13, 2024 build
# https://help.openai.com/en/articles/6825453-chatgpt-release-notes

# https://chat.openai.com/share/79f4ba33-c045-4fbb-b468-3625f5622b8b

import time
from threading import Thread, Lock
import serial
from Adafruit_IO import Client, Feed

# Configuration
com_port = 'COM123'  # Adjust this to your COM port
baud_rate = 115200
io_delay = 5

# Set to your Adafruit IO key.
# Remember, your key is a secret,
# so make sure not to publish it when you publish this code!
ADAFRUIT_IO_KEY = 'your-io-key-here'

# Set to your Adafruit IO username.
# (go to https://accounts.adafruit.com to find your username)
ADAFRUIT_IO_USERNAME = 'your-io-username-here'

# Shared buffer for sensor data
sensor_data = {'temperature': 0, 'humidity': 0}
data_lock = Lock()
stop_signal = False  # Shared stop signal

print("Connecting to Adafruit IO...")
# Create an instance of the REST client.
aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)
print("Connected!")

try:
    sht4x_temp = aio.feeds('temp-feed')
except: # pylint: disable = bare-except
    feed = Feed(name='temp-feed')
    sht4x_temp = aio.create_feed(feed)

try:
    sht4x_humid = aio.feeds('humid-feed')
except: # pylint: disable = bare-except
    feed = Feed(name='humid_feed')
    sht4x_humid = aio.create_feed(feed)

def read_sensor_data(ser):
    while not stop_signal:
        line = ser.readline().decode('utf-8').strip()
        temperature, humidity = line.split(',')
        with data_lock:
            sensor_data['temperature'] = temperature
            sensor_data['humidity'] = humidity
        time.sleep(1)

def send_data_to_io():
    while not stop_signal:
        time.sleep(io_delay)  # Adjust timing as needed
        with data_lock:
            temperature = sensor_data['temperature']
            humidity = sensor_data['humidity']
        aio.send_data(sht4x_temp.key, temperature)
        aio.send_data(sht4x_humid.key, humidity)
        print(f"Logged: Temperature={temperature}°C, Humidity={humidity}%")

def main():
    global stop_signal # pylint: disable = global-statement
    try:
        with serial.Serial(com_port, baud_rate, timeout=1) as ser:
            print("Starting data logging to Adafruit IO... Press Ctrl+C to stop.")
            sensor_thread = Thread(target=read_sensor_data, args=(ser,))
            io_thread = Thread(target=send_data_to_io)

            sensor_thread.start()
            io_thread.start()

            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        stop_signal = True
    finally:
        sensor_thread.join()
        io_thread.join()
        print("Data logging stopped.")

if __name__ == '__main__':
    main()
