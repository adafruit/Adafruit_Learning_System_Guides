# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams
#
# SPDX-License-Identifier: MIT
class Element:
    def __init__(self, walkable=(0, 0, 0)):
        self.chip_walk = walkable[0]
        self.block_move = walkable[1]
        self.creature_walk = walkable[2]

    def set_walk(self, chip_walk, block_move, creature_walk):
        self.chip_walk = chip_walk
        self.block_move = block_move
        self.creature_walk = creature_walk
