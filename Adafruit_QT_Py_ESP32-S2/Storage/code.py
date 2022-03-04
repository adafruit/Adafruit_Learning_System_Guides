# SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Essentials Storage CP Filesystem code.py file
"""
import time
import board
import microcontroller
import neopixel

pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)

try:
    with open("/temperature.txt", "a") as temp_log:
        while True:
            # The microcontroller temperature in Celsius. Include the
            # math to do the C to F conversion here, if desired.
            temperature = microcontroller.cpu.temperature

            # Write the temperature to the temperature.txt file every 10 seconds.
            temp_log.write('{0:.2f}\n'.format(temperature))
            temp_log.flush()

            # Blink the NeoPixel on every write...
            pixel.fill((255, 0, 0))
            time.sleep(1)  # ...for one second.
            pixel.fill((0, 0, 0))  # Then turn it off...
            time.sleep(9)  # ...for the other 9 seconds.

except OSError as e:  # When the filesystem is NOT writable by CircuitPython...
    delay = 0.5  # ...blink the NeoPixel every half second.
    if e.args[0] == 28:  # If the file system is full...
        delay = 0.15  # ...blink the NeoPixel every 0.15 seconds!
    while True:
        pixel.fill((255, 0, 0))
        time.sleep(delay)
        pixel.fill((0, 0, 0))
        time.sleep(delay)
