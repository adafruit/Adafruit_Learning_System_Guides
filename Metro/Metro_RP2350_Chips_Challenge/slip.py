# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams
#
# SPDX-License-Identifier: MIT
class Slip:
    def __init__(self):
        self.creature = None
        self.dir = None

    def __repr__(self):
        return f"Creature: {self.creature} | Slip Direction: {self.dir}"
