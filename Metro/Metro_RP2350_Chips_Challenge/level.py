# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams
#
# SPDX-License-Identifier: MIT
# SPDX-License-Identifier: GPL-1.0-or-later
# Based on Pocket Chip's Challenge (https://github.com/makermelissa/PocketChipsChallenge)
#
# pylint: disable=too-many-lines, wildcard-import, unused-wildcard-import

from point import Point
from device import Device
from definitions import TYPE_EMPTY, TYPE_SWITCHWALL_OPEN, TYPE_SWITCHWALL_CLOSED

COMPRESSED = 0
UNCOMPRESSED = 1

# These are the used optional field types
FIELD_TITLE = 3
FIELD_BEAR_TRAPS = 4
FIELD_CLONING_MACHINES = 5
FIELD_PASSWORD = 6
FIELD_HINT = 7
FIELD_MOVING_CREATURES = 10

class Tile:
    def __init__(self):
        self.id = 0
        self.state = 0

class Cell:
    def __init__(self):
        self.top = Tile()
        self.bottom = Tile()

    def __repr__(self):
        return f"Top: {hex(self.top.id)} Bottom: {hex(self.bottom.id)}"

class Level:
    def __init__(self, data_file):
        # Initialize any variables
        self._data_file = data_file
        self.level_number = 0
        self.last_level = 0
        self.time_limit = 0
        self.best_time = 0
        self.chips_required = 0
        self.password = ""
        self.hint = ""
        self.title = ""
        self.level_map = [Cell() for _ in range(1024)]
        self.traps = []
        self.cloners = []
        self.creatures = []
        self.passwords = {}

    def _reset_data(self):
        self.level_map = [Cell() for _ in range(1024)]
        self.traps = []
        self.cloners = []
        self.creatures = []

    def get_cell(self, coords):
        if isinstance(coords, int):
            coords = self.position_to_coords(coords)
        return self.level_map[self.coords_to_position(coords)]

    def coords_to_position(self, coords):
        return coords.y * 32 + coords.x

    def position_to_coords(self, position):
        return Point(position % 32, position // 32)

    def _read_int(self, file, byte_count):
        return int.from_bytes(file.read(byte_count), "little")

    def _update_cell_id(self, coords, tile_id, layer):
        getattr(self.get_cell(coords), layer).id = tile_id

    def _get_map_representation(self, layer):
        level_map = f"{layer} layer\n"
        for y in range(32):
            for x in range(32):
                level_map += f"{hex(getattr(self.get_cell(Point(x, y)), layer).id)} "
            level_map += "\n"
        return level_map


    def _process_map_data(self, map_data, layer):
        """
        Store RLE mapdata in uncompressed form
        """
        current_byte = 0
        current_position = 0
        while current_byte < len(map_data):
            if map_data[current_byte] == 0xFF:
                tile_id = map_data[current_byte + 2]
                if 0x0E <= tile_id <= 0x11:
                    tile_id += 0xC2
                for _ in range(map_data[current_byte + 1]):
                    coords = self.position_to_coords(current_position)
                    self._update_cell_id(coords, tile_id, layer)
                    current_position += 1
                current_byte += 3
            else:
                tile_id = map_data[current_byte]
                if 0x0E <= tile_id <= 0x11:
                    tile_id += 0xC2
                coords = self.position_to_coords(current_position)
                self._update_cell_id(coords, tile_id, layer)
                current_position += 1
                current_byte += 1

    def load(self, level_number):
        #pylint: disable=too-many-branches
        # Reset the data prior to loading
        self._reset_data()
        # Read the file and fill in the variables
        with open(self._data_file, "rb") as file:
            # Read the first 4 bytes in little endian format
            if self._read_int(file, 4) not in (0x0002AAAC, 0x0102AAAC):
                raise ValueError("Not a CHIP file")
            self.last_level = self._read_int(file, 2)
            if not 0 < level_number <= self.last_level:
                raise ValueError("Invalid level number")
            self.level_number = level_number
            # Seek to the start of the level data for the specified level
            while True:
                level_bytes = self._read_int(file, 2)
                if self._read_int(file, 2) == level_number:
                    break
                # Go to next level
                file.seek(level_bytes - 2, 1)

            # Read the level data
            self.time_limit = self._read_int(file, 2)
            self.chips_required = self._read_int(file, 2)
            compression = self._read_int(file, 2)
            if compression == COMPRESSED:
                raise ValueError("Compressed levels not supported")

            # Process the top map data
            layer_bytes = self._read_int(file, 2)
            map_data = file.read(layer_bytes)
            self._process_map_data(map_data, "top")

            # Process the bottom map data
            layer_bytes = self._read_int(file, 2)
            map_data = file.read(layer_bytes)
            self._process_map_data(map_data, "bottom")

            remaining_bytes = self._read_int(file, 2)
            while remaining_bytes > 0:
                field_type = self._read_int(file, 1)
                field_size = self._read_int(file, 1)
                remaining_bytes -= (2 + field_size)
                if field_type == FIELD_TITLE:
                    self.title = file.read(field_size).decode("utf-8").replace("\x00", "")
                elif field_type == FIELD_HINT:
                    self.hint = file.read(field_size).decode("utf-8").replace("\x00", "")
                elif field_type == FIELD_PASSWORD:
                    self.password = (
                        "".join([chr(c ^ 0x99) for c in file.read(field_size)]).replace("\x99", "")
                    )
                elif field_type == FIELD_BEAR_TRAPS:
                    trap_count = field_size // 10
                    for _ in range(trap_count):
                        button = Point(self._read_int(file, 2), self._read_int(file, 2))
                        device = Point(self._read_int(file, 2), self._read_int(file, 2))
                        self.traps.append(Device(button, device))
                        file.seek(2, 1)
                elif field_type == FIELD_CLONING_MACHINES:
                    cloner_count = field_size // 8
                    for _ in range(cloner_count):
                        button = Point(self._read_int(file, 2), self._read_int(file, 2))
                        device = Point(self._read_int(file, 2), self._read_int(file, 2))
                        self.cloners.append(Device(button, device))
                elif field_type == FIELD_MOVING_CREATURES:
                    creature_count = field_size // 2
                    for _ in range(creature_count):
                        self.creatures.append(Point(
                            self._read_int(file, 1),
                            self._read_int(file, 1)
                        ))

            # Load passwords if not already loaded
            if len(self.passwords) == 0:
                self._load_passwords(file)

    def _load_passwords(self, file):
        file.seek(6)    # Skip the file header
        while True:
            file.seek(2, 1)
            level_number = self._read_int(file, 2)
            file.seek(6, 1)
            layer_bytes = self._read_int(file, 2)   # Number of bytes in the top layer
            file.seek(layer_bytes, 1)   # Skip top layer
            layer_bytes = self._read_int(file, 2)   # Number of bytes in the top layer
            file.seek(layer_bytes, 1)   # Skip bottom layer
            remaining_bytes = self._read_int(file, 2)
            while remaining_bytes > 0:
                field_type = self._read_int(file, 1)
                field_size = self._read_int(file, 1)
                remaining_bytes -= (2 + field_size)
                if field_type == FIELD_PASSWORD:
                    password = file.read(field_size)
                    self.passwords[level_number] = (
                        "".join([chr(c ^ 0x99) for c in password]).replace("\x99", "")
                    )
                    file.seek(remaining_bytes, 1)
                    break
                file.seek(field_size, 1)
            if len(self.passwords) == self.last_level:
                break

    def toggle_blocks(self):
        for cell in self.level_map:
            if cell.top.id == TYPE_SWITCHWALL_OPEN:
                cell.top.id = TYPE_SWITCHWALL_CLOSED
            elif cell.top.id == TYPE_SWITCHWALL_CLOSED:
                cell.top.id = TYPE_SWITCHWALL_OPEN

            if cell.bottom.id == TYPE_SWITCHWALL_OPEN:
                cell.bottom.id = TYPE_SWITCHWALL_CLOSED
            elif cell.bottom.id == TYPE_SWITCHWALL_CLOSED:
                cell.bottom.id = TYPE_SWITCHWALL_OPEN

    def pop_tile(self, coords):
        tile = Tile()
        cell = self.get_cell(coords)
        tile.id = cell.top.id
        tile.state = cell.top.state
        cell.top.id = cell.bottom.id
        cell.top.state = cell.bottom.state
        cell.bottom.id = TYPE_EMPTY
        cell.bottom.state = 0

        return tile

    def push_tile(self, coords, tile):
        cell = self.get_cell(coords)
        cell.bottom.id = cell.top.id
        cell.bottom.state = cell.top.state
        cell.top.id = tile.id
        cell.top.state = tile.state

    def __str__(self):
        # print the map ids from the level
        return self._get_map_representation("top") + "\n" + self._get_map_representation("bottom")
