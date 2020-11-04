import struct

import board
import canio
import digitalio

# If the CAN transceiver has a standby pin, bring it out of standby mode
if hasattr(board, 'CAN_STANDBY'):
    standby = digitalio.DigitalInOut(board.CAN_STANDBY)
    standby.switch_to_output(False)

# If the CAN transceiver is powered by a boost converter, turn on its supply
if hasattr(board, 'BOOST_ENABLE'):
    standby = digitalio.DigitalInOut(board.BOOST_ENABLE)
    standby.switch_to_output(True)

can = canio.CAN(rx=board.CAN_RX, tx=board.CAN_TX, baudrate=250_000, auto_restart=True)
listener = can.listen(matches=[canio.Match(0x408)], timeout=.9)

old_bus_state = None
old_count = -1

while True:
    bus_state = can.state
    if bus_state != old_bus_state:
        print(f"Bus state changed to {bus_state}")
        old_bus_state = bus_state

    message = listener.receive()
    if message is None:
        print("No messsage received within timeout")
        continue

    data = message.data
    if len(data) != 8:
        print(f"Unusual message length {len(data)}")
        continue

    count, now_ms = struct.unpack("<II", data)
    gap = count - old_count
    old_count = count
    print(f"received message: count={count} now_ms={now_ms}")
    if gap != 1:
        print(f"gap: {gap}")
