# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import board
import emmcio
import storage

user_in = input(
    "This will erase and format the eMMC storage as a FAT filesystem."
    + ' Everything on the eMMC will be lost. Enter "delete" to format: '
)

if user_in.lower() == "delete":
    e = emmcio.EMMC(
        clock=board.EMMC_CLK,
        command=board.EMMC_CMD,
        data=board.EMMC_DAT0,
        reset=board.EMMC_RESET,
        vccq=board.EMMC_VCCQ,
        high_speed=True,
        write_enabled=True,
    )
    b = bytearray(512)
    e.readblocks(0, b)
    print(bytes(b[:8]))
    storage.VfsFat.mkfs(e)  # DESTROYS that device's content
    e.deinit()  # then hard reset; automount should take it
else:
    print("Exiting with no action")
