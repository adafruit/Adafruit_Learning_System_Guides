# SPDX-FileCopyrightText: Copyright (c) 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""AS5600 Encoder"""
import usb_hid
import board
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
import adafruit_as5600

i2c = board.STEMMA_I2C()
sensor = adafruit_as5600.AS5600(i2c)
enc_inc = ConsumerControlCode.VOLUME_INCREMENT
enc_dec = ConsumerControlCode.VOLUME_DECREMENT
cc = ConsumerControl(usb_hid.devices)

last_val = sensor.angle

THRESHOLD = sensor.max_angle // 2 # default max_angle is 4095
# you can change the max_angle. ex: sensor.max_angle = 1000

MIN_CHANGE = 25  # minimum change to register as movement
# increase to make less sensitive, decrease to make more sensitive

while True:
    enc_val = sensor.angle
    if abs(enc_val - last_val) >= MIN_CHANGE or abs(enc_val - last_val) > THRESHOLD:
        # Calculate the difference
        diff = enc_val - last_val
        # Check for wraparound
        if diff > THRESHOLD:
            # Wrapped from ~4095 to ~0 (actually turning backwards)
            cc.send(enc_dec)
        elif diff < -THRESHOLD:
            # Wrapped from ~0 to ~4095 (actually turning forwards)
            cc.send(enc_inc)
        elif diff > 0:
            # Normal forward rotation
            cc.send(enc_inc)
        else:
            # Normal backward rotation (diff < 0)
            cc.send(enc_dec)
        last_val = enc_val
