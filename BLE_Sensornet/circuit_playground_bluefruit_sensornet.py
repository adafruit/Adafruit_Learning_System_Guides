"""This uses the Circuit Playground Bluefruit as a Bluetooth LE sensor node."""

import time
from adafruit_circuitplayground import cp
import adafruit_ble_broadcastnet

print("This is BroadcastNet Circuit Playground Bluefruit sensor:", adafruit_ble_broadcastnet.device_address)

while True:
    measurement = adafruit_ble_broadcastnet.AdafruitSensorMeasurement()
    measurement.light = cp.light
    measurement.temperature = cp.temperature
    measurement.acceleration = cp.acceleration

    print(measurement)
    adafruit_ble_broadcastnet.broadcast(measurement)
    time.sleep(60)
