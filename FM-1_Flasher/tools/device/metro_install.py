# SPDX-FileCopyrightText: 2026 John Park for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-only
"""v2 spike 2: installs on the Metro ESP32-P4, from the REPL.

    import metro_install                       # mounts /sd, starts the host
    metro_install.run("/sd/firmware/sloop")    # dry run: identity only
    metro_install.run("/sd/firmware/sloop", go=True)

Needs the 512-byte enumeration buffer build with the TinyUSB DWC2 abort fix
(docs/PLAN-v2.md), and fm1_install.py, fm1proto, fm1update, fm1usb and
adafruit_usb_host_descriptors in lib/.
"""
import board
import digitalio
import sdioio
import storage
import usb_host

import fm1_install

power = digitalio.DigitalInOut(board.USB_HOST_POWER)
power.switch_to_output(value=True)
port = usb_host.Port(board.USB_HOST_DP, board.USB_HOST_DM)

try:
    storage.getmount("/sd")
except OSError:
    sd = sdioio.SDCard(clock=board.SD_CLK, command=board.SD_CMD,
                       data=[board.SD_DATA0, board.SD_DATA1, board.SD_DATA2, board.SD_DATA3],
                       frequency=40_000_000)
    storage.mount(storage.VfsFat(sd), "/sd")


def run(folder, go=False, **kw):
    return fm1_install.run(folder, go=go, **kw)
