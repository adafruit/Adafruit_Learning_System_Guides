import board
import audiobusio
from microcontroller import Pin


def is_hardware_PDM(clock, data):
    try:
        p = audiobusio.PDMIn(clock, data)
        p.deinit()
        return True
    except ValueError:
        return False
    except RuntimeError:
        return True


def get_unique_pins():
    exclude = ["NEOPIXEL", "APA102_MOSI", "APA102_SCK"]
    pins = [
        pin
        for pin in [getattr(board, p) for p in dir(board) if p not in exclude]
        if isinstance(pin, Pin)
    ]
    unique = []
    for p in pins:
        if p not in unique:
            unique.append(p)
    return unique


for clock_pin in get_unique_pins():
    for data_pin in get_unique_pins():
        if clock_pin is data_pin:
            continue
        if is_hardware_PDM(clock_pin, data_pin):
            print("Clock pin:", clock_pin, "\t Data pin:", data_pin)
        else:
            pass
