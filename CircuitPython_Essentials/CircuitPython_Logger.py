"""CircuitPython Essentials Storage logging example"""
import time
import board
import digitalio
import microcontroller

# For most CircuitPython boards:
led = digitalio.DigitalInOut(board.D13)
# For QT Py M0:
# led = digitalio.DigitalInOut(board.SCK)
led.switch_to_output()

try:
    with open("/temperature.txt", "a") as fp:
        while True:
            temp = microcontroller.cpu.temperature
            # do the C-to-F conversion here if you would like
            fp.write('{0:f}\n'.format(temp))
            fp.flush()
            led.value = not led.value
            time.sleep(1)
except OSError as e:
    delay = 0.5
    if e.args[0] == 28:
        delay = 0.25
    while True:
        led.value = not led.value
        time.sleep(delay)
