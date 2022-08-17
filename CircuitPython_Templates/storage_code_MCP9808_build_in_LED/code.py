# SPDX-FileCopyrightText: 2022 Kattni Rembor for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
CircuitPython Essentials Storage CP Filesystem code.py file

For use with boards with a built-in red LED.

Logs temperature using MCP9808 temperature sensor.
"""
import time
import board
import digitalio
import adafruit_mcp9808

led = digitalio.DigitalInOut(board.LED)
led.switch_to_output()

# For connecting MCP9808 via STEMMA QT
mcp9808 = adafruit_mcp9808.MCP9808(board.STEMMA_I2C())

# For connecting MCP9808 via pins and breadboard
# mcp9808 = adafruit_mcp9808.MCP9808(board.I2C())

try:
    with open("/temperature.txt", "a") as temp_log:
        while True:
            # The temperature in Celsius. Include the
            # math to do the C to F conversion here, if desired.
            temperature = mcp9808.temperature

            # Write the temperature to the temperature.txt file every 10 seconds.
            temp_log.write('{0:.2f}\n'.format(temperature))
            temp_log.flush()

            # Blink the LED on every write...
            led.value = True
            time.sleep(1)  # ...for one second.
            led.value = False  # Then turn it off...
            time.sleep(9)  # ...for the other 9 seconds.

except OSError as e:  # When the filesystem is NOT writable by CircuitPython...
    delay = 0.5  # ...blink the LED every half second.
    if e.args[0] == 28:  # If the file system is full...
        delay = 0.15  # ...blink the LED every 0.15 seconds!
    while True:
        led.value = not led.value
        time.sleep(delay)
