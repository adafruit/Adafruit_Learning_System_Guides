# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams
#
# SPDX-License-Identifier: MIT
from point import Point

class Device:
    def __init__(self, button=None, device=None):
        self.button = button if button else Point(0, 0)
        self.device = device if device else Point(0, 0)
