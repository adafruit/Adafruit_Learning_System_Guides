# SPDX-FileCopyrightText: 2019 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Remote Control code for Circuit Playground Bluefruit NeoPixel Animation and Color Remote Control.
To be used with another Circuit Playground Bluefruit running the NeoPixel Animator code.
"""

import time

from adafruit_circuitplayground.bluefruit import cpb

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService
from adafruit_bluefruit_connect.color_packet import ColorPacket
from adafruit_bluefruit_connect.button_packet import ButtonPacket


def scale(value):
    """Scale a value from acceleration value range to 0-255 (RGB range)"""
    value = abs(value)
    value = max(min(19.6, value), 0)
    return int(value / 19.6 * 255)


def send_packet(uart_connection_name, packet):
    """Returns False if no longer connected."""
    try:
        uart_connection_name[UARTService].write(packet.to_bytes())
    except:  # pylint: disable=bare-except
        try:
            uart_connection_name.disconnect()
        except:  # pylint: disable=bare-except
            pass
        return False
    return True


ble = BLERadio()

# Setup for preventing repeated button presses and tracking switch state
button_a_pressed = False
button_b_pressed = False
last_switch_state = None

uart_connection = None
# See if any existing connections are providing UARTService.
if ble.connected:
    for connection in ble.connections:
        if UARTService in connection:
            uart_connection = connection
        break

while True:
    last_switch_state = None
    if not uart_connection or not uart_connection.connected:  # If not connected...
        print("Scanning...")
        for adv in ble.start_scan(ProvideServicesAdvertisement, timeout=5):  # Scan...
            if UARTService in adv.services:  # If UARTService found...
                print("Found a UARTService advertisement.")
                uart_connection = ble.connect(adv)  # Create a UART connection...
                break
        # Stop scanning whether or not we are connected.
        ble.stop_scan()  # And stop scanning.
    while uart_connection and uart_connection.connected:  # If connected...
        if cpb.button_a and not button_a_pressed:  # If button A pressed...
            print("Button A pressed.")
            # Send a LEFT button packet.
            if not send_packet(uart_connection,
                               ButtonPacket(ButtonPacket.LEFT, pressed=True)):
                uart_connection = None
                continue
            button_a_pressed = True  # Set to True.
            time.sleep(0.05)  # Debounce.
        if not cpb.button_a and button_a_pressed:  # On button release...
            button_a_pressed = False  # Set to False.
            time.sleep(0.05)  # Debounce.
        if cpb.button_b and not button_b_pressed:  # If button B pressed...
            print("Button B pressed.")
            # Send a RIGHT button packet.
            if not send_packet(uart_connection,
                               ButtonPacket(ButtonPacket.RIGHT, pressed=True)):
                uart_connection = None
                continue
            button_b_pressed = True  # Set to True.
            time.sleep(0.05)  # Debounce.
        if not cpb.button_b and button_b_pressed:  # On button release...
            button_b_pressed = False  # Set to False.
            time.sleep(0.05)  # Debounce.
        if cpb.switch is not last_switch_state:  # If the switch state is changed...
            last_switch_state = cpb.switch  # Set state to current switch state.
            if cpb.switch:
                print("Switch is to the left: LEDs off!")
            else:
                print("Switch is to the right: LEDs on!")
            # Send a BUTTON_1 button packet.
            if not send_packet(uart_connection,
                               ButtonPacket(ButtonPacket.BUTTON_1, pressed=cpb.switch)):
                uart_connection = None
                continue
        if cpb.switch:  # If switch is to the left...
            cpb.pixels.fill((0, 0, 0))  # Turn off the LEDs.
        else:  # Otherwise...
            r, g, b = map(scale, cpb.acceleration)  # Map acceleration values to RGB values...
            color = (r, g, b)  # Set color to current mapped RGB value...
            print("Color:", color)
            cpb.pixels.fill(color)  # Fill Remote Control LEDs with current color...
            if not send_packet(uart_connection, ColorPacket(color)):  # And send a color packet.
                uart_connection = None
                continue
        time.sleep(0.1)  # Delay to prevent sending packets too quickly.
