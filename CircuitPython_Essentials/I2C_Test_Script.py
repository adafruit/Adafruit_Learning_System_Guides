import board
import busio


def is_hardware_I2C(scl, sda):
    try:
        p = busio.I2C(scl, sda)
        p.deinit()
        return True
    except ValueError:
        return False


def get_unique_pins():
    pin_names = dir(board)
    if "NEOPIXEL" in pin_names:
        pin_names.remove("NEOPIXEL")
    if "APA102_MOSI" in pin_names:
        pin_names.remove("APA102_MOSI")
    if "APA102_SCK" in pin_names:
        pin_names.remove("APA102_SCK")
    pins = [getattr(board, p) for p in pin_names]
    unique = []
    for p in pins:
        if p not in unique:
            unique.append(p)
    return unique


for scl_pin in get_unique_pins():
    for sda_pin in get_unique_pins():
        if scl_pin is sda_pin:
            continue
        else:
            if is_hardware_I2C(scl_pin, sda_pin):
                print("SCL pin:", scl_pin, "\t SDA pin:", sda_pin)
            else:
                pass
