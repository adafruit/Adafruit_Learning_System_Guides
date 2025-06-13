# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import usb_cdc

# Enable USB CDC (serial) communication
usb_cdc.enable(console=True, data=True)