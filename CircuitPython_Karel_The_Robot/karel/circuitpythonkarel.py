# SPDX-FileCopyrightText: 2024 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Karel the Robot helper class
"""

import json
import time

import terminalio
from adafruit_display_text.bitmap_label import Label
import adafruit_imageload
import board
from displayio import Group, Bitmap, Palette, TileGrid

EAST = 0
NORTH = 1
WEST = 2
SOUTH = 3

DIRECTION_WORDS = ["east", "north", "west", "south"]

DELAY = 0.2

TILE_SIZE = 24

COLOR_NAMES = [
    "white",
    "black",
    "red",
    "orange",
    "yellow",
    "green",
    "blue",
    "purple",
    "pink",
    "light_gray",
    "gray",
    "brown",
    "dark_green",
    "turquoise",
    "dark_blue",
    "dark_red",
]
COLOR_VALUES = [
    0xFFFFFF,
    0x000000,
    0xFF0000,
    0xFFA500,
    0xFFEE00,
    0x00C000,
    0x0000FF,
    0x8040C0,
    0xFF40C0,
    0xAAAAAA,
    0x444444,
    0xCA801D,
    0x008700,
    0x00C0C0,
    0x0000AA,
    0x800000,
]


class FrontIsBlocked(Exception):
    pass


class BeeperNotPresent(Exception):
    pass


class NoBeepersInBag(Exception):
    pass


class Karel:
    def __init__(self, spritesheet_bmp, spritesheet_palette):

        self.tilegrid = TileGrid(
            spritesheet_bmp,
            pixel_shader=spritesheet_palette,
            default_tile=0,
            tile_width=TILE_SIZE,
            tile_height=TILE_SIZE,
        )
        self._direction = EAST
        self.beeper_count = 0

    @property
    def direction(self):
        return self._direction

    @direction.setter
    def direction(self, new_value):
        self._direction = new_value
        if new_value == NORTH:
            self.tilegrid[0, 0] = 1
        if new_value == EAST:
            self.tilegrid[0, 0] = 0
        if new_value == SOUTH:
            self.tilegrid[0, 0] = 3
        if new_value == WEST:
            self.tilegrid[0, 0] = 2

    @property
    def x(self):
        return self.tilegrid.x // TILE_SIZE

    @x.setter
    def x(self, new_value):
        self.tilegrid.x = new_value * TILE_SIZE

    @property
    def y(self):
        return self.tilegrid.y // TILE_SIZE

    @y.setter
    def y(self, new_value):
        self.tilegrid.y = new_value * TILE_SIZE


class World:
    def __init__(self, display, world_width=10, world_height=10, beeper_limit=False):
        self.world_width = world_width
        self.world_height = world_height
        color_count = len(COLOR_NAMES)
        self.background_bmp = Bitmap(world_width, world_height, color_count)
        self.background_palette = Palette(color_count)
        for i, color_val in enumerate(COLOR_VALUES):
            self.background_palette[i] = color_val
        self.background_tilegrid = TileGrid(
            bitmap=self.background_bmp, pixel_shader=self.background_palette
        )
        self.background_group = Group(scale=TILE_SIZE)
        self.background_group.append(self.background_tilegrid)
        self.display = display

        self.world_group = Group()
        self.world_group.append(self.background_group)

        lib_dir = "/".join(__file__.split("/")[0:3])
        self.spritesheet_bmp, self.spritesheet_palette = adafruit_imageload.load(
            f"{lib_dir}/spritesheet.png"
        )
        self.spritesheet_palette.make_transparent(0)

        self.world_tilegrid = TileGrid(
            self.spritesheet_bmp,
            pixel_shader=self.spritesheet_palette,
            tile_width=TILE_SIZE,
            tile_height=TILE_SIZE,
            width=20,
            height=15,
            default_tile=7,
        )

        self.beeper_limit = beeper_limit

        self.beeper_count_labels = None
        self._init_beeper_counts()
        self.world_group.append(self.world_tilegrid)

        self.karel = Karel(self.spritesheet_bmp, self.spritesheet_palette)
        self.world_group.append(self.karel.tilegrid)

        display.root_group = self.world_group
        time.sleep(DELAY)

    def _init_beeper_counts(self):
        if self.beeper_count_labels is not None:
            for lbl in self.beeper_count_labels:
                self.world_group.remove(lbl)

        self.beeper_count_labels = {}
        self.beeper_counts = []
        for _ in range(self.world_height):
            self.beeper_counts.append([0 for x in range(self.world_width)])

    def load_state(self, state_obj):
        self._init_beeper_counts()
        if "beeper_counts" in state_obj["input"]:
            for beeper_count_loc_str in state_obj["input"]["beeper_counts"].keys():
                beeper_count_loc = [int(_) for _ in beeper_count_loc_str.split(",")]
                self.beeper_counts[world.world_height - 1 - beeper_count_loc[1]][
                    beeper_count_loc[0]
                ] = state_obj["input"]["beeper_counts"][beeper_count_loc_str]
            update_beeper_count_labels()

        self.karel.x = state_obj["input"]["karel"]["x"]
        self.karel.y = self.world_height - 1 - state_obj["input"]["karel"]["y"]
        self.karel.direction = DIRECTION_WORDS.index(
            state_obj["input"]["karel"]["direction"]
        )

        for y, row in enumerate(state_obj["input"]["world"]):
            for x, cell in enumerate(row):
                self.world_tilegrid[x, y] = cell

    def check_goal_state(self, state_obj):

        if (self.world_height - 1 - self.karel.y) != state_obj["goal"]["karel"]["y"]:
            print("karel y incorrect")
            return False
        if self.karel.x != state_obj["goal"]["karel"]["x"]:
            print("karel x incorrect")
            return False
        if self.karel.direction != DIRECTION_WORDS.index(
            state_obj["goal"]["karel"]["direction"]
        ):
            print("karel dir incorrect")
            return False

        if "beeper_counts" in state_obj["goal"]:
            for beeper_count_loc_str in state_obj["goal"]["beeper_counts"].keys():
                beeper_count_loc = [int(_) for _ in beeper_count_loc_str.split(",")]
                if (
                    self.beeper_counts[world.world_height - 1 - beeper_count_loc[1]][
                        beeper_count_loc[0]
                    ]
                    != state_obj["goal"]["beeper_counts"][beeper_count_loc_str]
                ):
                    print(f"beeper count incorrect {beeper_count_loc}")
                    return False

        for y in range(self.world_height):
            for x in range(self.world_width):

                goal_cell_index = state_obj["goal"]["world"][y][x]
                if self.world_tilegrid[x, y] != goal_cell_index:
                    print(
                        f"world mismatch: {(x, world.world_height - 1 - y)}: "
                        + f"{self.world_tilegrid[x, y]} != {goal_cell_index}"
                    )
                    return False
        return True


world = World(board.DISPLAY)


def move():
    if front_is_blocked():
        raise FrontIsBlocked("Karel can't move there")

    if world.karel.direction == EAST:
        world.karel.x += 1
    if world.karel.direction == WEST:
        world.karel.x -= 1

    if world.karel.direction == NORTH:
        world.karel.y -= 1
    if world.karel.direction == SOUTH:
        world.karel.y += 1

    time.sleep(DELAY)


def turn_left():
    if world.karel.direction == EAST:
        world.karel.direction = NORTH
    elif world.karel.direction == NORTH:
        world.karel.direction = WEST
    elif world.karel.direction == WEST:
        world.karel.direction = SOUTH
    elif world.karel.direction == SOUTH:
        world.karel.direction = EAST
    time.sleep(DELAY)


def corner_is_blocked(corner_x, corner_y):
    corner_loc = [corner_x, corner_y]
    if corner_loc[0] < 0 or corner_loc[1] < 0:
        return True

    if corner_loc[0] >= world.world_width or corner_loc[1] >= world.world_height:
        return True
    tile_index = world.world_tilegrid[corner_loc[0], corner_loc[1]]
    if tile_index in (6, 7):
        return True

    return False


def front_is_blocked():
    front_loc = [world.karel.x, world.karel.y]
    if world.karel.direction == EAST:
        front_loc[0] += 1
    if world.karel.direction == WEST:
        front_loc[0] -= 1
    if world.karel.direction == NORTH:
        front_loc[1] -= 1
    if world.karel.direction == SOUTH:
        front_loc[1] += 1
    return corner_is_blocked(front_loc[0], front_loc[1])


def right_is_blocked():
    right_loc = [world.karel.x, world.karel.y]
    if world.karel.direction == EAST:
        right_loc[1] += 1
    if world.karel.direction == WEST:
        right_loc[1] -= 1
    if world.karel.direction == NORTH:
        right_loc[0] += 1
    if world.karel.direction == SOUTH:
        right_loc[0] -= 1
    return corner_is_blocked(right_loc[0], right_loc[1])


def left_is_blocked():
    left_loc = [world.karel.x, world.karel.y]
    if world.karel.direction == EAST:
        left_loc[1] -= 1
    if world.karel.direction == WEST:
        left_loc[1] += 1
    if world.karel.direction == NORTH:
        left_loc[0] -= 1
    if world.karel.direction == SOUTH:
        left_loc[0] += 1
    return corner_is_blocked(left_loc[0], left_loc[1])


def paint_corner(color):
    if color not in COLOR_NAMES:
        raise ValueError(
            f"Color {color} is not valid. Supported colors are {COLOR_NAMES}"
        )
    world.background_bmp[world.karel.x, world.karel.y] = COLOR_NAMES.index(color)


def update_beeper_count_labels():
    for y, row in enumerate(world.beeper_counts):
        for x, count in enumerate(row):
            if count <= 1:
                if (x, y) in world.beeper_count_labels:
                    world.world_group.remove(world.beeper_count_labels[(x, y)])
                    world.beeper_count_labels.pop((x, y))

            else:
                if (x, y) in world.beeper_count_labels:
                    world.beeper_count_labels[(x, y)].text = str(count)
                else:
                    world.beeper_count_labels[(x, y)] = Label(
                        terminalio.FONT,
                        text=str(count),
                        color=0x000000,
                        anchor_point=(0.5, 0.5),
                        anchored_position=(
                            x * TILE_SIZE + TILE_SIZE // 2,
                            y * TILE_SIZE + TILE_SIZE // 2,
                        ),
                    )
                    world.world_group.append(world.beeper_count_labels[(x, y)])


def pick_beeper():
    if not beepers_present():
        raise BeeperNotPresent("There is no beeper here")

    world.karel.beeper_count += 1

    world.beeper_counts[world.karel.y][world.karel.x] = max(
        0, world.beeper_counts[world.karel.y][world.karel.x] - 1
    )
    update_beeper_count_labels()
    if world.beeper_counts[world.karel.y][world.karel.x] == 0:
        world.world_tilegrid[world.karel.x, world.karel.y] = 5
    time.sleep(DELAY)


def beepers_in_bag():
    return world.karel.beeper_count


def put_beeper():
    if beepers_in_bag() == 0 and world.beeper_limit:
        raise NoBeepersInBag("There are no beepers in Karel's bag")

    world.karel.beeper_count -= 1
    world.beeper_counts[world.karel.y][world.karel.x] += 1
    update_beeper_count_labels()
    world.world_tilegrid[world.karel.x, world.karel.y] = 4
    time.sleep(DELAY)


def beepers_present():
    tile_index = world.world_tilegrid[world.karel.x, world.karel.y]
    if tile_index == 4:
        return True
    return False


def no_beepers_in_bag():
    return world.karel.beeper_count == 0


def no_beepers_present():
    return not beepers_present()


def facing_north():
    return world.karel.direction == NORTH


def facing_east():
    return world.karel.direction == EAST


def facing_west():
    return world.karel.direction == WEST


def facing_south():
    return world.karel.direction == SOUTH


def not_facing_north():
    return not facing_north()


def not_facing_east():
    return not facing_east()


def not_facing_west():
    return not facing_west()


def not_facing_south():
    return not facing_south()


def left_is_clear():
    return not left_is_blocked()


def right_is_clear():
    return not right_is_blocked()


def front_is_clear():
    return not front_is_blocked()


def load_state_file(state_filepath):
    with open(state_filepath, "r") as f:
        ch_obj = json.load(f)
    world.load_state(ch_obj)

    time.sleep(DELAY)
    return ch_obj
