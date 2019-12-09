"""
Control code for Circuit Playground Bluefruit NeoPixel Animation and Color controller. To be used
with receiver code.
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
    except (OSError, KeyError):
        try:
            uart_connection_name.disconnect()
        except:  # pylint: disable=bare-except
            pass
        return False
    return True


ble = BLERadio()

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
    if not uart_connection or not uart_connection.connected:
        print("Scanning...")
        for adv in ble.start_scan(ProvideServicesAdvertisement, timeout=5):
            if UARTService in adv.services:
                print("Found a UARTService advertisement.")
                uart_connection = ble.connect(adv)
                break
        # Stop scanning whether or not we are connected.
        ble.stop_scan()
    while uart_connection and uart_connection.connected:
        if cpb.button_a and not button_a_pressed:
            print("Button A pressed.")
            if not send_packet(uart_connection,
                               ButtonPacket(ButtonPacket.LEFT, pressed=True)):
                uart_connection = None
                continue
            button_a_pressed = True
            time.sleep(0.05)
        if not cpb.button_a and button_a_pressed:
            button_a_pressed = False
            time.sleep(0.05)
        if cpb.button_b and not button_b_pressed:
            print("Button B pressed.")
            if not send_packet(uart_connection,
                               ButtonPacket(ButtonPacket.RIGHT, pressed=True)):
                uart_connection = None
                continue
            button_b_pressed = True
            time.sleep(0.05)
        if not cpb.button_b and button_b_pressed:
            button_b_pressed = False
            time.sleep(0.05)
        if cpb.switch is not last_switch_state:
            last_switch_state = cpb.switch
            print("Switch is to the", "left: LEDs off!" if cpb.switch else "right: LEDs on!")
            if not send_packet(uart_connection,
                               ButtonPacket(ButtonPacket.BUTTON_1, pressed=cpb.switch)):
                uart_connection = None
                continue
        if cpb.switch:
            cpb.pixels.fill(0)
        else:
            r, g, b = map(scale, cpb.acceleration)
            color = (r, g, b)
            print(color)
            cpb.pixels.fill(color)
            if not send_packet(uart_connection, ColorPacket(color)):
                uart_connection = None
                continue
        time.sleep(0.1)
