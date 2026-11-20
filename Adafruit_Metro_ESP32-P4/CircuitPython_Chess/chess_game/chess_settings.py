# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: GPL-3.0-or-later
# pylint: disable=import-outside-toplevel
"""Game settings (player colour, level, last game mode) saved in microcontroller.nvm.

Six bytes at NVM_OFFSET: b"TC", version 1, human_white (0/1), level (0-20) and
mode (1 player, 2 players or 3 online; anything else reads as 1). They are only
written when a new game changes them. nvm[8:35] holds the resistive shield's
touch calibration (see chess_touch_tsc).
"""

NVM_OFFSET = 0
MAGIC = b"TC\x01"


class Settings:
    def __init__(self, default_level=10):
        self.human_white = True
        self.level = default_level
        self.mode = 1
        try:
            import microcontroller

            self._nvm = microcontroller.nvm
        except (ImportError, AttributeError):
            self._nvm = None
        if self._nvm is not None:
            raw = self._nvm[NVM_OFFSET : NVM_OFFSET + 6]
            if raw[0:3] == MAGIC and raw[3] in (0, 1) and raw[4] <= 20:
                self.human_white = raw[3] == 1
                self.level = raw[4]
                self.mode = raw[5] if raw[5] in (1, 2, 3) else 1

    def save(self):
        if self._nvm is not None:
            self._nvm[NVM_OFFSET : NVM_OFFSET + 6] = MAGIC + bytes(
                (1 if self.human_white else 0, self.level, self.mode)
            )
