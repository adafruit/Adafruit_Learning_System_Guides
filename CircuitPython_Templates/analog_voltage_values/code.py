"""CircuitPython analog voltage value example"""
import time
import board
import analogio

analog_pin = analogio.AnalogIn(board.A0)


def get_voltage(pin):
    return (pin.value * 3.3) / 65535


while True:
    print(get_voltage(analog_pin))
    time.sleep(0.1)
