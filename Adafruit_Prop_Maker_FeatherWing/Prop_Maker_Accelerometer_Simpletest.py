"""Simple example to print acceleration data to console"""
import time
import digitalio
import board
import busio
import adafruit_lis3dh

# Set up accelerometer on I2C bus, 4G range:
i2c = busio.I2C(board.SCL, board.SDA)
int1 = digitalio.DigitalInOut(board.D6)
accel = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)
accel.range = adafruit_lis3dh.RANGE_4_G
accel.set_tap(1, 100)

while True:
    x, y, z = accel.acceleration
    print(x, y, z)
    time.sleep(0.1)
    if accel.tapped:
        print("Tapped!")
