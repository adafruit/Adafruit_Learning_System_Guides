import board
import time

from adafruit_onewire.bus import OneWireBus
from adafruit_ds18x20 import DS18X20

# Initialize one-wire bus on board pin D5.
ow_bus = OneWireBus(board.D4)

# Scan for sensors and grab the first one found.
ds18 = DS18X20(ow_bus, ow_bus.scan()[0])

# Main loop to print the temperature every second.
while True:
    print('Temperature: {0:0.3f}C'.format(ds18.temperature))
    time.sleep(1.0)
