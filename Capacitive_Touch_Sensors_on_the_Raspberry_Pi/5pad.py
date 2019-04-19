import time
import board
from digitalio import DigitalInOut, Direction

# set the GPIO input pins
pad0_pin = board.D22
pad1_pin = board.D21
pad2_pin = board.D17
pad3_pin = board.D24
pad4_pin = board.D23

pad0 = DigitalInOut(pad0_pin)
pad1 = DigitalInOut(pad1_pin)
pad2 = DigitalInOut(pad2_pin)
pad3 = DigitalInOut(pad3_pin)
pad4 = DigitalInOut(pad4_pin)

pad0.direction = Direction.INPUT
pad1.direction = Direction.INPUT
pad2.direction = Direction.INPUT
pad3.direction = Direction.INPUT
pad4.direction = Direction.INPUT

pad0_already_pressed = True
pad1_already_pressed = True
pad2_already_pressed = True
pad3_already_pressed = True
pad4_already_pressed = True

while True:

    if pad0.value and not pad0_already_pressed:
        print("Pad 0 pressed")
    pad0_already_pressed = pad0.value

    if pad1.value and not pad1_already_pressed:
        print("Pad 1 pressed")
    pad1_already_pressed = pad1.value

    if pad2.value and not pad2_already_pressed:
        print("Pad 2 pressed")
    pad2_already_pressed = pad2.value

    if pad3.value and not pad3_already_pressed:
        print("Pad 3 pressed")
    pad3_already_pressed = pad3.value

    if pad4.value and not pad4_already_pressed:
        print("Pad 4 pressed")
    pad4_already_pressed = pad4.value

    time.sleep(0.1)
