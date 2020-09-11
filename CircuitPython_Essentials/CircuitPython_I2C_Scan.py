# CircuitPython demo - I2C scan

import time

import board

i2c = board.I2C()

while not i2c.try_lock():
    pass

while True:
    print("I2C addresses found:", [hex(device_address)
                                   for device_address in i2c.scan()])
    time.sleep(2)
