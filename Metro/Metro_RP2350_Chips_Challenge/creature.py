# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams
#
# SPDX-License-Identifier: MIT
from point import Point
from definitions import NONE, TYPE_BLOCK, TYPE_CHIP, NORTH, SOUTH, WEST, EAST

DIR_UP = 0
DIR_LEFT = 1
DIR_DOWN = 2
DIR_RIGHT = 3

# creatures should move based on chip, tiles near them, and their own AI
# creatures should be able to move in any direction assuming they are not blocked

# Abstract class
class Creature:
    def __init__(self, *, position=None, direction=NONE, creature_type=NONE):
        self.cur_pos = position or Point(0, 0)
        self.type = creature_type or TYPE_BLOCK
        self.direction = direction
        self.state = 0x00
        self.hidden = False
        self.on_slip_list = False
        self.to_direction = NONE

    def move(self, destination):
        if destination.y < self.cur_pos.y:
            self.direction = NORTH
        elif destination.x < self.cur_pos.x:
            self.direction = WEST
        elif destination.y > self.cur_pos.y:
            self.direction = SOUTH
        elif destination.x > self.cur_pos.x:
            self.direction = EAST
        else:
            self.direction = NONE
        self.cur_pos = destination

    def image_number(self):
        tile_index = 0
        if self.type == TYPE_CHIP:
            tile_index = 0x6C
        elif self.type == TYPE_BLOCK:
            tile_index = 0x0A
        else:
            tile_index = 0x40 + ((self.type - 1) * 4)

        if self.direction == WEST:
            tile_index += DIR_LEFT
        elif self.direction == EAST:
            tile_index += DIR_RIGHT
        elif self.direction == NORTH:
            tile_index += DIR_UP
        elif self.direction in (SOUTH, NONE):
            tile_index += DIR_DOWN
        return tile_index

    def get_tile_in_dir(self, direction):
        pt_dir = Point(self.cur_pos.x, self.cur_pos.y)
        if direction == WEST:
            pt_dir.x -= 1
        elif direction == EAST:
            pt_dir.x += 1
        elif direction == NORTH:
            pt_dir.y -= 1
        elif direction == SOUTH:
            pt_dir.y += 1
        return pt_dir

    def left(self):
        # return the point to the left of the creature
        pt_dest = Point(self.cur_pos.x, self.cur_pos.y)
        if self.direction == NORTH:
            pt_dest.x -= 1
        elif self.direction == WEST:
            pt_dest.y += 1
        elif self.direction == SOUTH:
            pt_dest.x += 1
        elif self.direction == EAST:
            pt_dest.y -= 1
        return pt_dest

    def right(self):
         # Return point to the right of the creature
        pt_dest = Point(self.cur_pos.x, self.cur_pos.y)
        if self.direction == NORTH:
            pt_dest.x += 1
        elif self.direction == WEST:
            pt_dest.y -= 1
        elif self.direction == SOUTH:
            pt_dest.x -= 1
        elif self.direction == EAST:
            pt_dest.y += 1
        return pt_dest

    def back(self):
        # Return point behind the creature
        pt_dest = Point(self.cur_pos.x, self.cur_pos.y)
        if self.direction == NORTH:
            pt_dest.y += 1
        elif self.direction == WEST:
            pt_dest.x += 1
        elif self.direction == SOUTH:
            pt_dest.y -= 1
        elif self.direction == EAST:
            pt_dest.x -= 1
        return pt_dest

    def front(self):
        # Return point in front of the creature
        pt_dest = Point(self.cur_pos.x, self.cur_pos.y)
        if self.direction == NORTH:
            pt_dest.y -= 1
        elif self.direction == WEST:
            pt_dest.x -= 1
        elif self.direction == SOUTH:
            pt_dest.y += 1
        elif self.direction == EAST:
            pt_dest.x += 1
        return pt_dest

    def reverse(self):
        if self.direction == NORTH:
            return SOUTH
        elif self.direction == SOUTH:
            return NORTH
        elif self.direction == WEST:
            return EAST
        elif self.direction == EAST:
            return WEST
        else:
            return self.direction
