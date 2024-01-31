# SPDX-FileCopyrightText: Copyright (c) 2024 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import time
import board
from rainbowio import colorwheel
from digitalio import DigitalInOut
from adafruit_mcp2515 import MCP2515 as CAN
from adafruit_mcp2515.canio import Message
from adafruit_seesaw import seesaw,  neopixel, rotaryio, digitalio

cs = DigitalInOut(board.CAN_CS)
cs.switch_to_output()
spi = board.SPI()

can_bus = CAN(
    spi, cs, loopback=False, silent=False
)  # use loopback to test without another device

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
seesaw = seesaw.Seesaw(i2c, addr=0x36)

seesaw_product = (seesaw.get_version() >> 16) & 0xFFFF
print("Found product {}".format(seesaw_product))
if seesaw_product != 4991:
    print("Wrong firmware loaded?  Expected 4991")

seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
button = digitalio.DigitalIO(seesaw, 24)
pixel = neopixel.NeoPixel(seesaw, 6, 1)
pixel.brightness = 0.3

button_held = False
color = 0

encoder = rotaryio.IncrementalEncoder(seesaw)
last_position = 0

while True:
    with can_bus.listen(timeout=5.0) as listener:
        position = -encoder.position

        if position != last_position:
            if position > last_position:
                color += 5
            else:
                color -= 5
            color = (color + 256) % 256  # wrap around to 0-256
            pixel.fill(colorwheel(color))
            last_position = position
            str_pos = str(position)
            byte_pos = str_pos.encode()
            message = Message(id=0x1234ABCD, data=byte_pos, extended=True)
            send_success = can_bus.send(message)
            print("Send success:", send_success)

        if not button.value and not button_held:
            button_held = True
            message = Message(id=0x1234ABCD, data=b"pressed", extended=True)
            send_success = can_bus.send(message)
            print("Send success:", send_success)

        if button.value and button_held:
            button_held = False
            message = Message(id=0x1234ABCD, data=b"released", extended=True)
            send_success = can_bus.send(message)
            print("Send success:", send_success)

    time.sleep(0.1)
