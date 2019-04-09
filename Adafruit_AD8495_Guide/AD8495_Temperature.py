import time
import analogio
import board

ad8495 = analogio.AnalogIn(board.A1)


def get_voltage(pin):
    return (pin.value * 3.3) / 65536


while True:
    temperature = (get_voltage(ad8495) - 1.25) / 0.005
    print(temperature)
    print(get_voltage(ad8495))
    time.sleep(0.5)
