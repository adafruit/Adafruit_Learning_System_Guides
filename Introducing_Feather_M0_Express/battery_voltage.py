import board
import analogio

vbat_voltage = analogio.AnalogIn(board.D9)


def get_voltage(pin):
    return (pin.value * 3.3) / 65536 * 2


battery_voltage = get_voltage(vbat_voltage)
print("VBat voltage: {:.2f}".format(battery_voltage))
