# SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# Written by Liz Clark (Adafruit Industries) with OpenAI ChatGPT v4 Feb 13, 2024 build
# https://help.openai.com/en/articles/6825453-chatgpt-release-notes

# https://chat.openai.com/share/430869c1-e28f-4203-9750-c6bbabe18be6

import os
import time
import csv
import serial

# Configuration
com_port = 'COM121'  # Adjust this to your COM port
baud_rate = 115200  # Adjust this to the baud rate of your sensor
base_csv_file_path = 'sensor_readings'

def find_next_file_name(base_path):
    """Finds the next available file name with an incremented suffix."""
    counter = 0
    while True:
        new_path = f"{base_path}_{counter}.csv" if counter else f"{base_path}.csv"
        if not os.path.isfile(new_path):
            return new_path
        counter += 1

def read_sensor_data(ser):
    line = ser.readline().decode('utf-8').strip()
    temperature, humidity = line.split(',')
    return float(temperature), float(humidity)

def save_to_csv(file_path, temperature, humidity):
    with open(file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        # Convert struct_time to a string for the CSV
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        writer.writerow([timestamp, temperature, humidity])

def main():
    csv_file_path = find_next_file_name(base_csv_file_path)
    # Write headers to the new file
    with open(csv_file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "Temperature", "Humidity"])

    with serial.Serial(com_port, baud_rate, timeout=1) as ser:
        print(f"Starting data logging to {csv_file_path}... Press Ctrl+C to stop.")
        try:
            while True:
                temperature, humidity = read_sensor_data(ser)
                save_to_csv(csv_file_path, temperature, humidity)
                print(f"Logged: Temperature={temperature}°C, Humidity={humidity}%")
                time.sleep(1)
        except KeyboardInterrupt:
            print("Data logging stopped.")

if __name__ == '__main__':
    main()
