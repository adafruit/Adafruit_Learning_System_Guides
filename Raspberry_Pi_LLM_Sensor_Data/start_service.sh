#!/bin/bash
# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
cd /home/pi/RaspberryPi_LLM_Sensor_Data
source /home/pi/venvs/sensor_llm_venv/bin/activate
exec python /home/pi/RaspberryPi_LLM_Sensor_Data/take_sensor_readings.py
