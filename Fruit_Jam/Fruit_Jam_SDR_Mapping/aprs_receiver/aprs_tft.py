# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""The 2.8" TFT Touch Shield (Adafruit 1651) as the receiver's screen and
SD card, on boards without picodvi (the Metro ESP32-P4).

The ILI9341 (320x240, the same size as the Fruit Jam's DVI framebuffer)
and the SD card share the board's SPI bus (the ICSP header): display CS
D10, DC D9; card CS D4. The touch controller (STMPE610, CS D8) is not used.
Needs adafruit_ili9341 in lib/.
"""
import board
import displayio
import fourwire

# pylint: disable=import-outside-toplevel

TFT_CS = board.D10
TFT_DC = board.D9
SD_CS = board.D4
BAUDRATE = 40000000        # the ILI9341's write clock
ROTATION = 0               # 0: landscape as the driver sets it; 180: upside down


def open_display(width, height):
    """The display, which only refreshes when told to (as the DVI one)."""
    import adafruit_ili9341
    displayio.release_displays()
    bus = fourwire.FourWire(board.SPI(), command=TFT_DC, chip_select=TFT_CS, baudrate=BAUDRATE)
    return adafruit_ili9341.ILI9341(bus, width=width, height=height, rotation=ROTATION,
                                    auto_refresh=False)


def sd_card():
    """The shield's SD card (an sdcardio.SDCard) on the board's SPI bus."""
    import sdcardio
    return sdcardio.SDCard(board.SPI(), SD_CS)
