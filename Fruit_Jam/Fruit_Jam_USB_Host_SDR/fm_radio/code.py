# SPDX-FileCopyrightText: Copyright (c) 2026 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""Direct RTL-SDR AM/FM/weather reception on Fruit Jam, audio on the 3.5 mm jack."""

import time
import supervisor
from am_fm_radio import run
from radio_ui_am_fm import RadioUI

# pylint: disable=broad-except

supervisor.runtime.autoreload = False
while True:
    try:
        run()
    except Exception as error:
        print("RADIO_ERROR", type(error).__name__, str(error))
        try:
            RadioUI().draw(
                "RECONNECTING", 0, "receiver stopped; retrying shortly", str(error)[:48]
            )
        except Exception:
            pass
        time.sleep(3)
