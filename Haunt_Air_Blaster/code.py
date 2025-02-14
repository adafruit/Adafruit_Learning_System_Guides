# SPDX-FileCopyrightText: 2024 John Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT
'''
Air Blaster
Feather RP2040 Prop-Maker with Power Relay FeatherWing and VL53L1X distance sensor
'''

import time
import board
import digitalio
import adafruit_vl53l1x

TRIGGER_DISTANCE = 50.0
triggered = False

i2c = board.STEMMA_I2C()
vl53 = adafruit_vl53l1x.VL53L1X(i2c)
vl53.distance_mode = 2
vl53.timing_budget = 100

print("VL53L1X Simple Test.")
print("--------------------")
model_id, module_type, mask_rev = vl53.model_info
print("Model ID: 0x{:0X}".format(model_id))
print("Module Type: 0x{:0X}".format(module_type))
print("Mask Revision: 0x{:0X}".format(mask_rev))
print("Distance Mode: ", end="")
if vl53.distance_mode == 1:
    print("SHORT")
elif vl53.distance_mode == 2:
    print("LONG")
else:
    print("UNKNOWN")
print("Timing Budget: {}".format(vl53.timing_budget))
print("--------------------")

vl53.start_ranging()

relay_pin = digitalio.DigitalInOut(board.D10)
relay_pin.direction = digitalio.Direction.OUTPUT
relay_pin.value = False

def blast(repeat, duration, rate):
    for _ in range(repeat):
        relay_pin.value = True
        print("bang")
        time.sleep(duration)
        relay_pin.value = False
        time.sleep(rate)

distance = None

while True:
    if vl53.data_ready:
        distance = vl53.distance
        print("Distance: {} cm".format(vl53.distance))
        vl53.clear_interrupt()
        time.sleep(0.1)

        if distance:
            if distance <= TRIGGER_DISTANCE:
                if not triggered :
                    blast(3, 0.01, 0.1)  # adjust repeat, duration, rate here
                    time.sleep(0.4)
                    blast(2, 0.01, 0.2)  # adjust repeat, duration, rate here
                    triggered = True

            else:
                triggered = False
