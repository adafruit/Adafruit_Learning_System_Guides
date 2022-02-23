# SPDX-FileCopyrightText: 2018 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
The MIT License (MIT)

Copyright (c) 2018 Dave Astels

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

--------------------------------------------------------------------------------
Manage the emulator hardware.
"""

import adafruit_mcp230xx
import digitalio

# control pin values

PROGRAMMER_USE = False
EMULATE_USE = True

WRITE_ENABLED = False
WRITE_DISABLED = True

CHIP_ENABLED = False
CHIP_DISABLED = True

CLOCK_ACTIVE = False
CLOCK_INACTIVE = True

RESET_INACTIVE = False
RESET_ACTIVE = True

LED_OFF = False
LED_ON = True

ENABLE_HOST_ACCESS = False
DISABLE_HOST_ACCESS = True


class Emulator:
    """Handle all interaction with the emulator circuit."""

    def __init__(self, i2c):
        self.mcp = adafruit_mcp230xx.MCP23017(i2c)
        self.mcp.iodir = 0x0000  # Make all pins outputs

        # Configure the individual control pins

        self.mode_pin = self.mcp.get_pin(8)
        self.mode_pin.direction = digitalio.Direction.OUTPUT
        self.mode_pin.value = PROGRAMMER_USE

        self.write_pin = self.mcp.get_pin(9)
        self.write_pin.direction = digitalio.Direction.OUTPUT
        self.write_pin.value = WRITE_DISABLED

        self.chip_select_pin = self.mcp.get_pin(10)
        self.chip_select_pin.direction = digitalio.Direction.OUTPUT
        self.chip_select_pin.value = CHIP_DISABLED

        self.address_clock_pin = self.mcp.get_pin(11)
        self.address_clock_pin.direction = digitalio.Direction.OUTPUT
        self.address_clock_pin.value = CLOCK_INACTIVE

        self.clock_reset_pin = self.mcp.get_pin(12)
        self.clock_reset_pin.direction = digitalio.Direction.OUTPUT
        self.clock_reset_pin.value = RESET_INACTIVE

        self.led_pin = self.mcp.get_pin(13)
        self.led_pin.direction = digitalio.Direction.OUTPUT
        self.led_pin.value = False

    def __pulse_write(self):
        self.write_pin.value = WRITE_ENABLED
        self.write_pin.value = WRITE_DISABLED

    def __deactivate_ram(self):
        self.chip_select_pin.value = CHIP_DISABLED

    def __activate_ram(self):
        self.chip_select_pin.value = CHIP_ENABLED

    def __reset_address_counter(self):
        self.clock_reset_pin.value = RESET_ACTIVE
        self.clock_reset_pin.value = RESET_INACTIVE

    def __advance_address_counter(self):
        self.address_clock_pin.value = CLOCK_ACTIVE
        self.address_clock_pin.value = CLOCK_INACTIVE

    def __output_on_port_a(self, data_byte):
        """A hack to get around the limitation of the 23017
        library to use 8-bit ports"""
        self.mcp.gpio = (self.mcp.gpio & 0xFF00) | (data_byte & 0x00FF)

    def enter_program_mode(self):
        """Enter program mode, allowing loading of the emulator RAM."""
        self.mode_pin.value = PROGRAMMER_USE
        self.led_pin.value = LED_OFF

    def enter_emulate_mode(self):
        """Enter emulate mode, giving control of the emulator
        ram to the host."""
        self.mode_pin.value = EMULATE_USE
        self.led_pin.value = LED_ON

    def load_ram(self, code):
        """Load the emulator RAM. Automatically switched to program mode.
           :param [byte] code: the list of bytes to load into the emulator RAM
        """
        self.enter_program_mode()
        self.__reset_address_counter()
        for data_byte in code:
            self.__output_on_port_a(data_byte)
            self.__activate_ram()
            self.__pulse_write()
            self.__deactivate_ram()
            self.__advance_address_counter()
