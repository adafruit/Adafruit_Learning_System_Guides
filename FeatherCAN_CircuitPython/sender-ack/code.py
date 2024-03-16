# SPDX-FileCopyrightText: 2020 Jeff Epler for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import struct
import time

import board
import canio
import digitalio

# If the CAN transceiver has a standby pin, bring it out of standby mode
if hasattr(board, 'CAN_STANDBY'):
    standby = digitalio.DigitalInOut(board.CAN_STANDBY)
    standby.switch_to_output(False)

# If the CAN transceiver is powered by a boost converter, turn on its supply
if hasattr(board, 'BOOST_ENABLE'):
    boost_enable = digitalio.DigitalInOut(board.BOOST_ENABLE)
    boost_enable.switch_to_output(True)

# Use this line if your board has dedicated CAN pins. (Feather M4 CAN and Feather STM32F405)
can = canio.CAN(rx=board.CAN_RX, tx=board.CAN_TX, baudrate=250_000, auto_restart=True)
# On ESP32S2 most pins can be used for CAN.  Uncomment the following line to use IO5 and IO6
#can = canio.CAN(rx=board.IO6, tx=board.IO5, baudrate=250_000, auto_restart=True)
listener = can.listen(matches=[canio.Match(0x409)], timeout=.1)

old_bus_state = None
count = 0

while True:
    bus_state = can.state
    if bus_state != old_bus_state:
        print(f"Bus state changed to {bus_state}")
        old_bus_state = bus_state

    now_ms = (time.monotonic_ns() // 1_000_000) & 0xffffffff
    print(f"Sending message: count={count} now_ms={now_ms}")

    message = canio.Message(id=0x408, data=struct.pack("<II", count, now_ms))

    # Keep trying to send the same message until confirmed.
    while True:
        received_ack_confirmed = False
        can.send(message)

        # Read in all messages.
        for message_in in listener:
            data = message_in.data
            if len(data) != 4:
                print(f"Unusual message length {len(data)}")
                continue

            ack_count = struct.unpack("<I", data)[0]
            if ack_count == count:
                print(f"Received ACK: {ack_count}")
                received_ack_confirmed = True
                break
            else:
                print(f"Received incorrect ACK: {ack_count} should be {count}")

        if received_ack_confirmed:
            break

        print(f"No ACK received within receive timeout, sending {count} again")

    time.sleep(.5)
    count += 1
