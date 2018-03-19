import board
import busio


def is_hardware_SPI(clock_pin, data_pin):
    try:
        p = busio.SPI(clock_pin, data_pin)
        p.deinit()
        return True
    except ValueError:
        return False


if is_hardware_SPI(board.A1, board.A2):  # Provide the two pins you want to use.
    print("This pin combination is hardware SPI!")
else:
    print("This pin combination isn't hardware SPI.")
