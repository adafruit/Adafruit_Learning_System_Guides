# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`fruitjam_ble`
================================================================================

Bluetooth LE through the Fruit Jam's ESP32-C6, with central role support
(scanning and connecting to peripherals), for use with ``adafruit_ble``.

The firmware's built-in ``_bleio`` can talk to the ESP32-C6 too, but it can
only advertise and accept connections. This package replaces it with a Python
``_bleio`` that can also scan, connect and use a peripheral's services.
Importing it registers `fruitjam_ble.bleio` as the ``_bleio`` module, so import
it before ``adafruit_ble``::

    import fruitjam_ble  # isort: skip
    from adafruit_ble import BLERadio

    ble = BLERadio(fruitjam_ble.start_bluetooth())

* Author(s): Tim Cocks
"""

import sys
import time

import board
import busio
import digitalio

from . import bleio
from .bleio import Adapter
from .uart_hci import HCIError, HCITimeoutError, UARTHCI

# pylint: disable=global-statement, unpacking-non-sequence

if "adafruit_ble" in sys.modules and sys.modules.get("_bleio") is not bleio:
    raise ImportError("Import fruitjam_ble before adafruit_ble")
sys.modules["_bleio"] = bleio

_pins = None


def start_bluetooth(*, name=None, debug=False):
    """Reset the ESP32-C6 into Bluetooth mode and return an `Adapter` for it, to
    pass to ``adafruit_ble.BLERadio``. Calling it again resets the ESP32-C6 and
    returns a new Adapter.

    The ESP32-C6 must be running the AirLift (NINA) firmware. WiFi can't be used
    at the same time. Resetting the ESP32-C6 also resets the headphone DAC,
    because they share a reset line.

    :param str name: the name to advertise, if advertising
    :param bool debug: print the ESP32-C6's startup messages
    """
    global _pins
    stop_bluetooth()
    reset = digitalio.DigitalInOut(board.ESP_RESET)
    reset.switch_to_output(False)
    # ESP_IRQ is the ESP32-C6's boot mode pin during reset (high to run its
    # firmware) and its RTS input afterwards.
    rts = digitalio.DigitalInOut(board.ESP_IRQ)
    rts.switch_to_output(True)
    # Chip select low during reset picks Bluetooth mode instead of WiFi.
    chip_select = digitalio.DigitalInOut(board.ESP_CS)
    chip_select.switch_to_output(False)
    cts = digitalio.DigitalInOut(board.ESP_BUSY)
    cts.switch_to_input()
    uart = busio.UART(
        board.ESP_TX,
        board.ESP_RX,
        baudrate=115200,
        timeout=0,
        receiver_buffer_size=4096,
    )
    _pins = (uart, reset, rts, chip_select, cts)

    time.sleep(0.1)
    reset.value = True
    time.sleep(1.0)
    startup = b""
    while uart.in_waiting:
        startup += uart.read(uart.in_waiting)
    if debug:
        print(startup.decode("utf-8", "replace"))
    if not startup:
        raise RuntimeError("ESP32-C6 did not start")

    hci = UARTHCI(uart, rts=rts, cts=cts)
    return Adapter(hci, name=name)


def stop_bluetooth():
    """Hold the ESP32-C6 in reset and release the pins `start_bluetooth` took."""
    global _pins
    if _pins is None:
        return
    uart, reset, rts, chip_select, cts = _pins
    _pins = None
    reset.value = False
    for pin in (uart, rts, chip_select, cts, reset):
        pin.deinit()
