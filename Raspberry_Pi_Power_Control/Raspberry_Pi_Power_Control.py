import time
import board
from digitalio import DigitalInOut, Direction

pir_pin = board.D24
power_pin = board.D23

pir = DigitalInOut(pir_pin)
pir.direction = Direction.INPUT

power = DigitalInOut(power_pin)
power.direction = Direction.OUTPUT
power.value = False

while True:
    if pir.value:
        print("POWER ON")
        power.value = True
        time.sleep(20)
        print("POWER OFF")
        power.value = False
        time.sleep(5)
    time.sleep(1)
