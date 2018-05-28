import time

import analogio
import board

potentiometer = analogio.AnalogIn(board.A1)


def get_voltage(pin):
    return (pin.value * 3.3) / 65536


while True:
    print((get_voltage(potentiometer),))
    time.sleep(0.1)
