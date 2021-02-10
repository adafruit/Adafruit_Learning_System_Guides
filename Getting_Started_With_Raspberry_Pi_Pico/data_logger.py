"""
Data logging example for Pico. Logs the temperature to a file on the Pico.
"""
import time
import board
import digitalio
import microcontroller

led = digitalio.DigitalInOut(board.LED)
led.switch_to_output()

try:
    with open("/temperature.txt", "a") as datalog:
        while True:
            temp = microcontroller.cpu[0].temperature
            datalog.write('{0:f}\n'.format(temp))
            datalog.flush()
            led.value = not led.value
            time.sleep(1)
except OSError as e:  # Typically when the filesystem isn't writeable...
    delay = 0.5  # ...blink the LED every half second.
    if e.args[0] == 28:  # If the filesystem is full...
        delay = 0.25  # ...blink the LED faster!
    while True:
        led.value = not led.value
        time.sleep(delay)
