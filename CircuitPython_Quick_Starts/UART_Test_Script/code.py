import board
import busio


def is_hardware_UART(tx, rx):
    try:
        p = busio.UART(tx, rx)
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


for tx_pin in get_unique_pins():
    for rx_pin in get_unique_pins():
        if rx_pin is tx_pin:
            continue
        else:
            if is_hardware_UART(tx_pin, rx_pin):
                print("RX pin:", rx_pin, "\t TX pin:", tx_pin)
            else:
                pass
