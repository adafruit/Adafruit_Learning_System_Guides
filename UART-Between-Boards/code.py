# SPDX-FileCopyrightText: Copyright (c) 2021 Dylan Herrada for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2021 Dan Halbert for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
Code for communicating between two CircuitPlayground Express boards using UART.
Sends value from the onboard light sensor to the other board and the other board sets its
NeoPixels accordingly.
"""

import time
import board
import busio
import digitalio
import neopixel
import analogio

pixels = neopixel.NeoPixel(board.NEOPIXEL, 10, brightness=0.1, auto_write=False)

light_sensor = analogio.AnalogIn(board.LIGHT)

btn_A = digitalio.DigitalInOut(board.BUTTON_A)
btn_A.switch_to_input(pull=digitalio.Pull.DOWN)

btn_B = digitalio.DigitalInOut(board.BUTTON_B)
btn_B.switch_to_input(pull=digitalio.Pull.DOWN)

# Use a timeout of zero so we don't delay while waiting for a message.
uart = busio.UART(board.TX, board.RX, baudrate=9600, timeout=0)

# Messages are of the form:
# "<TYPE,value,value,value,...>"
# We send and receive two types of messages:
#
# Message contains a light sensor value (float):
# <L,light>
#
# Message contains statuses of two buttons. Increment NeoPixel brightness by 0.1 if the second
# button is pressed, and reduce brightness by 0.1 if the first button is pressed.
# <B,btn_A,btn_B>

UPDATE_INTERVAL = 3.0
last_time_sent = 0

# Wait for the beginning of a message.
message_started = False

while True:
    # Send light sensor value only every UPDATE_INTERVAL seconds.
    now = time.monotonic()
    if now - last_time_sent >= UPDATE_INTERVAL:
        light = light_sensor.value
        uart.write(bytes(f"<L,{light}>", "ascii"))
        print("sending light value", light)
        last_time_sent = now

    if any((btn_A.value, btn_B.value)):
        # Send values of built-in buttons if any are pressed
        uart.write(bytes(f"<B,{btn_A.value},{btn_B.value}>", "ascii"))
        print(f"Sent ({btn_A.value}, {btn_B.value})")

        # Don't do anything else until both buttons are released
        time.sleep(0.1)
        while any((btn_A.value, btn_B.value)):
            pass

    byte_read = uart.read(1)  # Read one byte over UART lines
    if byte_read is None:
        # Nothing read.
        continue

    if byte_read == b"<":
        # Start of message. Start accumulating bytes, but don't record the "<".
        message = []
        message_started = True
        continue

    if message_started:
        if byte_read == b">":
            # End of message. Don't record the ">".
            # Now we have a complete message. Convert it to a string, and split it up.
            message_parts = "".join(message).split(",")
            message_type = message_parts[0]
            message_started = False

            if message_parts[0] == "L":
                # Received a message telling us a light sensor value
                peak = int(((int(message_parts[1]) - 2000) / 62000) * 10)
                for i in range(0, 10):
                    if i <= peak:
                        pixels[i] = (0, 255, 0)
                    else:
                        pixels[i] = (0, 0, 0)
                pixels.show()
                print(f"Received light value of {message_parts[1]}")
                print(f"Lighting up {peak + 1} NeoPixels")

            elif message_parts[0] == "B":
                # Received a message asking us to change our brightness.
                if message_parts[1] == "True":
                    pixels.brightness = max(0.0, pixels.brightness - 0.1)
                    print(f"Brightness set to: {pixels.brightness}")
                if message_parts[2] == "True":
                    pixels.brightness = min(1.0, pixels.brightness + 0.1)
                    print(f"Brightness set to: {pixels.brightness}")

        else:
            # Accumulate message byte.
            message.append(chr(byte_read[0]))
