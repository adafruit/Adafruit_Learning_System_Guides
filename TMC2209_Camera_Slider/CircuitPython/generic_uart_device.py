# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# pylint: disable=too-few-public-methods

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_BusDevice.git"

class GenericUARTDevice:
    """Class for communicating with a device via generic UART read/write functions"""

    def __init__(self, uart, read_func=None, write_func=None,
                 readreg_func=None, writereg_func=None):
        self._uart = uart
        self._read_func = read_func
        self._write_func = write_func
        self._readreg_func = readreg_func
        self._writereg_func = writereg_func

    def read(self, buffer: bytearray, length: int) -> int:
        """Read raw data from device into buffer"""
        if self._read_func is None:
            return 0
        while self._uart.in_waiting:
            self._uart.read()
        return self._read_func(buffer, length)

    def write(self, buffer: bytes, length: int) -> int:
        """Write raw data from buffer to device"""
        if self._write_func is None:
            return 0
        return self._write_func(buffer, length)

    def read_register(self, addr_buf: bytes, addr_len: int,
                      data_buf: bytearray, data_len: int) -> int:
        """Read from device register"""
        if self._readreg_func is None:
            return 0
        return self._readreg_func(addr_buf, addr_len, data_buf, data_len)

    def write_register(self, addr_buf: bytes, addr_len: int, data_buf: bytes, data_len: int) -> int:
        """Write to device register"""
        if self._writereg_func is None:
            return 0
        return self._writereg_func(addr_buf, addr_len, data_buf, data_len)
