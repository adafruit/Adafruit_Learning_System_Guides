# SPDX-FileCopyrightText: 2018 Dave Astels for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import board
import busio
from uart_handler import UartHandler
import adafruit_logging as logging

uart = busio.UART(board.TX, board.RX, baudrate=115200)
logger = logging.getLogger("test")
logger.addHandler(UartHandler(uart))
logger.setLevel(logging.INFO)
logger.info("testing")
