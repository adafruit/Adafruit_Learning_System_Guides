# SPDX-FileCopyrightText: 2023 Jeff Epler for Adafruit Industries
# SPDX-License-Identifier: MIT
import time
import board
import digitalio
from adafruit_hid.mouse import Mouse
from usb_hid import devices

SCALE = 3

def delta(value): # Convert 8 bit value to signed number of distance steps
    value = ~value # All value is inverted on the bus
    if value & 0x80:  # and is in sign-magnitude format
        return -(value & 0x7f)
    else:
        return value & 0x7f

mouse = Mouse(devices)

spi = board.SPI()
strobe = digitalio.DigitalInOut(board.RX)
strobe.switch_to_output(False)

if not spi.try_lock():
    raise SystemExit("could not lock SPI bus")

spi.configure(baudrate=100_000, polarity=1)

# Wait for the mouse to be ready at power-on
time.sleep(2)

# A buffer to fetch mouse data into
data = bytearray(4)

print("Mouse is ready!")
while True:
    # Request fresh data
    strobe.value = True
    strobe.value = False

    # Must do read in 2 pieces with delay in between
    spi.readinto(data, end=2)
    spi.readinto(data, start=2)
    lmb = bool(~data[1] & 0x40)  # data is inverted on the bus
    rmb = bool(~data[1] & 0x80)
    dy = delta(data[2])
    dx = delta(data[3])


    # Pressing both buttons together emulates the wheel
    wheel = lmb and rmb

    # Compute the new button state
    old_buttons = mouse.report[0]
    mouse.report[0] = (
        0 if wheel else
        mouse.LEFT_BUTTON if lmb else
        mouse.RIGHT_BUTTON if rmb else
        0)

    # If there's any movement, send a move event
    if dx or dy:
        if wheel:
            mouse.move(dx * SCALE, 0, wheel=-dy)
        else:
            mouse.move(dx * SCALE, dy * SCALE)
    elif old_buttons != mouse.report[0]:
        mouse.press(0) # Send buttons previously set via report[0]
