# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT


import time
import board
import adafruit_sen6x
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_models import SensorReading


# How many seconds in between taking readings
INTERVAL = 60  # seconds

ROOM_NAME = "basement"

# Initialize I2C
i2c = board.I2C()

# Create SEN66 instance
sensor = adafruit_sen6x.SEN66(i2c)

# Read sensor info
print(f"Product: {sensor.product_name}")
print(f"Serial: {sensor.serial_number}")

# Check device status
status = sensor.device_status
print(f"Device {status}")

# Optional: Configure sensor before starting
# sensor.temperature_offset(offset=-2.0, slot=0)  # Apply -2°C offset
# sensor.voc_algorithm_tuning(index_offset=100)   # Adjust VOC baseline
# print(sensor.voc_algorithm) # Print VOC baseline

# CO2 configuration examples:
# sensor.co2_automatic_self_calibration = False  # Disable ASC for greenhouses
# sensor.ambient_pressure = 1020  # Set pressure in hPa
# sensor.sensor_altitude = 500    # Or set altitude in meters

# Start measurements
sensor.start_measurement()

# Wait for first measurement to be ready
print("Waiting for first measurement...")
time.sleep(2)
print("-" * 40)

# connect to database
engine = create_engine("sqlite:///sensor_data.db")
Session = sessionmaker(bind=engine)
session = Session()

# Read data continuously
while True:
    if sensor.data_ready:
        # Check for errors before reading
        sensor.check_sensor_errors()

        # Read all measurements
        data = sensor.all_measurements()

        # create data object instance
        reading = SensorReading(
            room_name=ROOM_NAME,
            temperature_c=data["temperature"],
            temperature_f=(data["temperature"] * 9 / 5) + 32,
            humidity=data["humidity"],
            pm25=data["pm2_5"],
            voc_index=data["voc_index"],
            nox_index=data["nox_index"],
            co2=data["co2"],
        )

        # Add and commit the reading to database
        session.add(reading)
        session.commit()
        print(reading)
        # Display values (None = sensor still initializing)
        print(
            f"Temperature: {data['temperature']:.1f}°C"
            if data["temperature"]
            else "Temperature: initializing..."
        )
        print(
            f"Humidity: {data['humidity']:.1f}%"
            if data["humidity"]
            else "Humidity: initializing..."
        )
        print(
            f"PM2.5: {data['pm2_5']:.1f} µg/m³"
            if data["pm2_5"]
            else "PM2.5: initializing..."
        )
        print(
            f"VOC Index: {data['voc_index']:.1f}"
            if data["voc_index"]
            else "VOC Index: initializing..."
        )
        print(
            f"NOx Index: {data['nox_index']:.1f}"
            if data["nox_index"]
            else "NOx Index: initializing..."
        )
        print(f"CO2: {data['co2']} ppm" if data["co2"] else "CO2: initializing...")
        print("-" * 40)
    time.sleep(INTERVAL)
