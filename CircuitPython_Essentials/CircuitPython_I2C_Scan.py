# CircuitPython demo - I2C scan

import board
import busio
import time

# can also use board.SDA and board.SCL for neater looking code!
i2c = busio.I2C(board.SCL, board.SDA)

while not i2c.try_lock():
    pass

while True:
    print("I2C addresses found:", [hex(device_address) for device_address in i2c.scan()])
    time.sleep(2)
