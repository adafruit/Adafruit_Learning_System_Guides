# SPDX-FileCopyrightText: 2022 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
CPU load blinkenlights for Little Connection Machine. Random bits flicker
in response to overall processor load across all cores. This relies on the
'psutil' Python module, which should already be present in Raspbian OS,
but if not, install with: pip install psutil

psutil can provide all sorts of system information -- per-core load, network
use, temperature and more -- but this example is meant to be minimal,
understandable and work across different Pi models (even single-core).
Consider it a stepping off point for your own customizations. See psutil
documentation for ideas: https://pypi.org/project/psutil/

Since this program itself comprises part of the overall CPU load, the LEDs
some amount of LEDs will always be blinking. This is normal and by design.
"""

import random
import psutil
from cm1 import CM1


class CPULoad(CM1):
    """Simple CPU load blinkenlights for Little Connection Machine."""

    def run(self):
        """Main loop for Little Connection Machine CPU load blinkies."""

        while True:
            self.clear()  # Clear PIL self.image, part of the CM1 base class
            blinkyness = 100 - int(psutil.cpu_percent() + 0.5)
            for row in range(self.image.height):
                for col in range(self.image.width):
                    if random.randint(1, 100) > blinkyness:
                        # self.draw is PIL draw object in CM1 base class
                        self.draw.point([col, row], fill=self.brightness)
            self.redraw()
            # No delay in this example, just run full-tilt!


if __name__ == "__main__":
    MY_APP = CPULoad()  # Instantiate class, calls __init__() above
    MY_APP.process()
