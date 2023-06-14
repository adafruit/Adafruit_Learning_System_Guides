# SPDX-FileCopyrightText: 2023 Eva Herrada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import random
import board
import usb_cdc
import digitalio

import adafruit_rfm9x

spi = board.SPI()

# radio setup
RADIO_FREQ_MHZ = 915.0

LED = digitalio.DigitalInOut(board.LED)
LED.direction = digitalio.Direction.OUTPUT

CS = digitalio.DigitalInOut(board.RFM_CS)
RESET = digitalio.DigitalInOut(board.RFM_RST)

rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)

rfm9x.tx_power = 23

# Wait to receive packets.  Note that this library can't receive data at a fast
# rate, in fact it can only receive and process one 252 byte packet at a time.
# This means you should only use this for low bandwidth scenarios, like sending
# and receiving a single message at a time.
print("Waiting for packets...")

MESSAGE = b""
ID = None
while True:
    char = usb_cdc.console.read(usb_cdc.console.in_waiting)
    if char:
        MESSAGE += char
        # print(char.decode('utf-8'), end="")
        if char[-1:] == b"\r":
            MESSAGE = MESSAGE[:-1]
            ID = random.randint(0, 1000)
            rfm9x.send(bytes(f"{ID}|", "utf-8") + MESSAGE)
            print(f"{ID}|{MESSAGE.decode()}")
            timestamp = time.monotonic()
            sent = MESSAGE
            MESSAGE = b""
            continue

    packet = rfm9x.receive()

    if packet is None:
        # Packet has not been received
        LED.value = False
    else:
        # Received a packet!
        LED.value = True

        try:
            PACKET_TEXT = str(packet, "ascii")
        except UnicodeError:
            print("error")
            continue

        print(PACKET_TEXT)
        mess_id, text = PACKET_TEXT.split("|")
        if mess_id != "-1":
            rfm9x.send(bytes(f"-1|{mess_id}", "utf-8"))
            print(f"Received: {PACKET_TEXT}")
        else:
            print(f"Delivered: {text}")
            ID = None

        rssi = rfm9x.last_rssi
        print(f"RSSI: {rssi} dB")
