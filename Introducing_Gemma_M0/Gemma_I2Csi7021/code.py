# I2C sensor demo

import time

import adafruit_si7021
import board
import busio

i2c = busio.I2C(board.SCL, board.SDA)

# lock the I2C device before we try to scan
while not i2c.try_lock():
    pass
print("I2C addresses found:", [hex(i) for i in i2c.scan()])

# unlock I2C now that we're done scanning.
i2c.unlock()

# Create library object on our I2C port
si7021 = adafruit_si7021.SI7021(i2c)

# Use library to read the data!
while True:
    print("Temp: %0.2F *C   Humidity: %0.1F %%" %
          (si7021.temperature, si7021.relative_humidity))
    time.sleep(1)
