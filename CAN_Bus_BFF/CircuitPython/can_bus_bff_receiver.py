# SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import time
import board
import terminalio
import displayio
import i2cdisplaybus
from digitalio import DigitalInOut
from adafruit_mcp2515.canio import Message, RemoteTransmissionRequest
from adafruit_mcp2515 import MCP2515 as CAN
import adafruit_displayio_ssd1306
from adafruit_display_text import label

displayio.release_displays()

i2c = board.STEMMA_I2C()
# STEMMA OLED setup
display_bus = i2cdisplaybus.I2CDisplayBus(i2c, device_address=0x3D, reset=None)
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=128, height=64)

cs = DigitalInOut(board.A3)
cs.switch_to_output()
spi = board.SPI()

can_bus = CAN(
    spi, cs, loopback=False, silent=False
)  # use loopback to test without another device

splash = displayio.Group()
display.root_group = splash

font = terminalio.FONT
main_area = label.Label(
    font, text="CAN Receiver", color=0xFFFFFF)
main_area.anchor_point = (0.5, 0.0)
main_area.anchored_position = (display.width / 2, 0)

msg_area = label.Label(
    font, text="ID: ", color=0xFFFFFF)
msg_area.anchor_point = (0.0, 0.5)
msg_area.anchored_position = (0, display.height / 2)

val_area = label.Label(
    font, text="Val: ", color=0xFFFFFF)
val_area.anchor_point = (0.0, 1.0)
val_area.anchored_position = (0, display.height)

splash.append(main_area)
splash.append(msg_area)
splash.append(val_area)

while True:
    with can_bus.listen(timeout=1.0) as listener:

        message_count = listener.in_waiting()
        for i in range(message_count):
            print(message_count, "messages available")
            msg = listener.receive()
            print("Message from ", hex(msg.id))
            msg_area.text = f"ID: {hex(msg.id)}"
            if isinstance(msg, Message):
                print("message data:", msg.data)
                val_area.text = f"Val: {msg.data}"
            if isinstance(msg, RemoteTransmissionRequest):
                print("RTR length:", msg.length)
    time.sleep(0.1)
