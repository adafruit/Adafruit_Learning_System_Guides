# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams
#
# SPDX-License-Identifier: MIT
# SPDX-License-Identifier: GPL-1.0-or-later
# Based on Pocket Chip's Challenge (https://github.com/makermelissa/PocketChipsChallenge)
# and Tile World 1.3.2 (https://www.muppetlabs.com/~breadbox/software/tworld/)
#
# pylint: disable=too-many-lines, wildcard-import, unused-wildcard-import
import random
from definitions import *
from creature import Creature
from element import Element
from level import Level, Tile
from point import Point
from slip import Slip
from audio import Audio

SOUND_EFFECTS = {
    "BUTTON_PUSHED": "/sounds/pop2.wav",
    "DOOR_OPENED": "/sounds/door.wav",
    "ITEM_COLLECTED": "/sounds/blip2.wav",
    "BOOTS_STOLEN": "/sounds/strike.wav",
    "WATER_SPLASH": "/sounds/water2.wav",
    "TELEPORT": "/sounds/teleport.wav",
    "CANT_MOVE": "/sounds/oof3.wav",
    "CHIP_LOSES": "/sounds/bummer.wav",
    "LEVEL_COMPLETE": "/sounds/ditty1.wav",
    "IC_COLLECTED": "/sounds/click3.wav",
    "BOMB_EXPLOSION": "/sounds/hit3.wav",
    "SOCKET_SOUND": "/sounds/chimes.wav",
    "TIME_LOW_TICK": "/sounds/click1.wav",
    "TIME_UP": "/sounds/bell.wav"
}

class GameLogic:
    """
    A class to represent the state of the game as well as
    control all the game movements and actions.
    """
    def __init__(self, data_file, **kwargs):
        self._tileset = [Element() for _ in range(0x70)]
        self._chip = Creature()
        self._create_tileset()
        self._game_mode = [GM_NEWGAME]
        self.last_level = 149
        self._chip.type = 0
        self._sliplist = []
        self._creature_pool = []
        self._block_pool = []
        self.current_level = Level(data_file)
        self._current_input = NONE
        self._chips_needed = 0
        self._moving = False
        self.dead_creatures = 0
        self.dead_blocks = 0
        self.keys = [0] * 4
        self.boots = [False] * 4
        self.status = SF_CHIPOKAY
        self.current_level_number = 2
        self._current_time = 0
        self._last_slip_dir = NONE
        self._controller_dir = NONE
        self._audio = Audio(**kwargs)
        self._time_limit = 0
        for sound_name, file in SOUND_EFFECTS.items():
            self._audio.add_sound(sound_name, file)

    def dec_level(self):
        if self.current_level_number > 1:
            self.set_level(self.current_level_number - 1)

    def inc_level(self):
        if self.current_level_number < self.last_level:
            self.set_level(self.current_level_number + 1)

    def set_level(self, level):
        self.set_game_mode(GM_LOADING)
        if not 1 <= level <= self.last_level:
            level = 1
        self.reset()
        self.current_level_number = level
        self.current_level.load(level)
        self.last_level = self.current_level.last_level
        self._time_limit = int(self.current_level.time_limit *
                               TICKS_PER_SECOND * (1000 / SECOND_LENGTH))
        self._chips_needed = self.current_level.chips_required
        self._extract_creatures()
        self.set_game_mode(GM_NORMAL)

    def _possesion(self, key):
        return {
            TYPE_KEY_BLUE: self.keys[BLUE_KEY],
            TYPE_KEY_RED: self.keys[RED_KEY],
            TYPE_KEY_YELLOW: self.keys[YELLOW_KEY],
            TYPE_KEY_GREEN: self.keys[GREEN_KEY],
            TYPE_DOOR_BLUE: self.keys[BLUE_KEY],
            TYPE_DOOR_RED: self.keys[RED_KEY],
            TYPE_DOOR_YELLOW: self.keys[YELLOW_KEY],
            TYPE_DOOR_GREEN: self.keys[GREEN_KEY],
            TYPE_BOOTS_WATER: self.boots[WATER_BOOTS],
            TYPE_BOOTS_FIRE: self.boots[FIRE_BOOTS],
            TYPE_BOOTS_ICE: self.boots[ICE_BOOTS],
            TYPE_BOOTS_SLIDE: self.boots[SUCTION_BOOTS],
            TYPE_ICE: self.boots[ICE_BOOTS],
            TYPE_ICEWALL_NORTHWEST: self.boots[ICE_BOOTS],
            TYPE_ICEWALL_NORTHEAST: self.boots[ICE_BOOTS],
            TYPE_ICEWALL_SOUTHWEST: self.boots[ICE_BOOTS],
            TYPE_ICEWALL_SOUTHEAST: self.boots[ICE_BOOTS],
            TYPE_SLIDE_NORTH: self.boots[SUCTION_BOOTS],
            TYPE_SLIDE_WEST: self.boots[SUCTION_BOOTS],
            TYPE_SLIDE_SOUTH: self.boots[SUCTION_BOOTS],
            TYPE_SLIDE_EAST: self.boots[SUCTION_BOOTS],
            TYPE_SLIDE_RANDOM: self.boots[SUCTION_BOOTS],
            TYPE_FIRE: self.boots[FIRE_BOOTS],
            TYPE_WATER: self.boots[WATER_BOOTS]
        }.get(key, False)

    def _collect(self, key):
        def add_key(key):
            self.keys[key] += 1

        def set_boots(boot):
            self.boots[boot] = True

        functions = {
            TYPE_KEY_BLUE: lambda: add_key(BLUE_KEY),
            TYPE_KEY_RED: lambda: add_key(RED_KEY),
            TYPE_KEY_YELLOW: lambda: add_key(YELLOW_KEY),
            TYPE_KEY_GREEN: lambda: add_key(GREEN_KEY),
            TYPE_DOOR_BLUE: lambda: add_key(BLUE_KEY),
            TYPE_DOOR_RED: lambda: add_key(RED_KEY),
            TYPE_DOOR_YELLOW: lambda: add_key(YELLOW_KEY),
            TYPE_DOOR_GREEN: lambda: add_key(GREEN_KEY),
            TYPE_BOOTS_WATER: lambda: set_boots(WATER_BOOTS),
            TYPE_BOOTS_FIRE: lambda: set_boots(FIRE_BOOTS),
            TYPE_BOOTS_ICE: lambda: set_boots(ICE_BOOTS),
            TYPE_BOOTS_SLIDE: lambda: set_boots(SUCTION_BOOTS),
            TYPE_ICE: lambda: set_boots(ICE_BOOTS),
            TYPE_ICEWALL_NORTHWEST: lambda: set_boots(ICE_BOOTS),
            TYPE_ICEWALL_NORTHEAST: lambda: set_boots(ICE_BOOTS),
            TYPE_ICEWALL_SOUTHWEST: lambda: set_boots(ICE_BOOTS),
            TYPE_ICEWALL_SOUTHEAST: lambda: set_boots(ICE_BOOTS),
            TYPE_SLIDE_NORTH: lambda: set_boots(SUCTION_BOOTS),
            TYPE_SLIDE_WEST: lambda: set_boots(SUCTION_BOOTS),
            TYPE_SLIDE_SOUTH: lambda: set_boots(SUCTION_BOOTS),
            TYPE_SLIDE_EAST: lambda: set_boots(SUCTION_BOOTS),
            TYPE_SLIDE_RANDOM: lambda: set_boots(SUCTION_BOOTS),
            TYPE_FIRE: lambda: set_boots(FIRE_BOOTS),
            TYPE_WATER: lambda: set_boots(WATER_BOOTS)
        }
        if key in functions:
            functions[key]()

    def _discard(self, key):
        def rem_key(key):
            self.keys[key] -= 1

        def unset_boots(boot):
            self.boots[boot] = False

        functions = {
            TYPE_KEY_BLUE: lambda: rem_key(BLUE_KEY),
            TYPE_KEY_RED: lambda: rem_key(RED_KEY),
            TYPE_KEY_YELLOW: lambda: rem_key(YELLOW_KEY),
            TYPE_DOOR_BLUE: lambda: rem_key(BLUE_KEY),
            TYPE_DOOR_RED: lambda: rem_key(RED_KEY),
            TYPE_DOOR_YELLOW: lambda: rem_key(YELLOW_KEY),
            TYPE_BOOTS_WATER: lambda: unset_boots(WATER_BOOTS),
            TYPE_BOOTS_FIRE: lambda: unset_boots(FIRE_BOOTS),
            TYPE_BOOTS_ICE: lambda: unset_boots(ICE_BOOTS),
            TYPE_BOOTS_SLIDE: lambda: unset_boots(SUCTION_BOOTS),
            TYPE_ICE: lambda: unset_boots(ICE_BOOTS),
            TYPE_ICEWALL_NORTHWEST: lambda: unset_boots(ICE_BOOTS),
            TYPE_ICEWALL_NORTHEAST: lambda: unset_boots(ICE_BOOTS),
            TYPE_ICEWALL_SOUTHWEST: lambda: unset_boots(ICE_BOOTS),
            TYPE_ICEWALL_SOUTHEAST: lambda: unset_boots(ICE_BOOTS),
            TYPE_SLIDE_NORTH: lambda: unset_boots(SUCTION_BOOTS),
            TYPE_SLIDE_WEST: lambda: unset_boots(SUCTION_BOOTS),
            TYPE_SLIDE_SOUTH: lambda: unset_boots(SUCTION_BOOTS),
            TYPE_SLIDE_EAST: lambda: unset_boots(SUCTION_BOOTS),
            TYPE_SLIDE_RANDOM: lambda: unset_boots(SUCTION_BOOTS),
            TYPE_FIRE: lambda: unset_boots(FIRE_BOOTS),
            TYPE_WATER: lambda: unset_boots(WATER_BOOTS)
        }
        if key in functions:
            functions[key]()

    def _get_slide_dir(self, floor):
        if floor == TYPE_SLIDE_NORTH:
            return NORTH
        elif floor == TYPE_SLIDE_WEST:
            return WEST
        elif floor == TYPE_SLIDE_SOUTH:
            return SOUTH
        elif floor == TYPE_SLIDE_EAST:
            return EAST
        elif floor == TYPE_SLIDE_RANDOM:
            return 1 << random.randint(0, 3)
        return NONE

    def _ice_wall_turn(self, floor, direction):
        if floor == TYPE_ICEWALL_NORTHEAST:
            return EAST if direction == SOUTH else NORTH if direction == WEST else direction
        elif floor == TYPE_ICEWALL_SOUTHWEST:
            return WEST if direction == NORTH else SOUTH if direction == EAST else direction
        elif floor == TYPE_ICEWALL_NORTHWEST:
            return WEST if direction == SOUTH else NORTH if direction == EAST else direction
        elif floor == TYPE_ICEWALL_SOUTHEAST:
            return EAST if direction == NORTH else SOUTH if direction == WEST else direction
        return direction

    def get_view_port(self):
        """
        This function lines up the edge of the map to the edge of the screen
        """
        ptTile = Point(self._chip.cur_pos.x, self._chip.cur_pos.y)
        if ptTile.x <= 4:
            ptTile.x = 4
        elif ptTile.x >= 27:
            ptTile.x = 27
        if ptTile.y <= 4:
            ptTile.y = 4
        elif ptTile.y >= 27:
            ptTile.y = 27
        return ptTile

    def get_chip_coords_in_viewport(self):
        chip = Point(self._chip.cur_pos.x, self._chip.cur_pos.y)
        viewport = self.get_view_port()
        x_pos = 4
        y_pos = 4
        if chip.x < viewport.x:
            x_pos = chip.x
        elif chip.x > viewport.x:
            x_pos = chip.x - viewport.x + 4
        if chip.y < viewport.y:
            y_pos = chip.y
        elif chip.y > viewport.y:
            y_pos = chip.y - viewport.y + 4
        return Point(x_pos, y_pos)

    def _can_make_move(self, creature, direction, flags):
        #pylint: disable=too-many-branches, too-many-return-statements
        ptTo = creature.get_tile_in_dir(direction)
        if not (0 <= ptTo.x < 32 and 0 <= ptTo.y < 32):
            return False

        if not flags & CMM_NOLEAVECHECK:
            nBottomTile = self.current_level.get_cell(creature.cur_pos).bottom.id
            if nBottomTile == TYPE_WALL_NORTH and direction == NORTH:
                return False
            elif nBottomTile == TYPE_WALL_WEST and direction == WEST:
                return False
            elif nBottomTile == TYPE_WALL_SOUTH and direction == SOUTH:
                return False
            elif nBottomTile == TYPE_WALL_EAST and direction == EAST:
                return False
            elif nBottomTile == TYPE_WALL_SOUTHEAST and direction in (SOUTH, EAST):
                return False
            elif nBottomTile == TYPE_BEARTRAP and not creature.state & CS_RELEASED:
                return False

        if creature.type == TYPE_CHIP:
            floor = self._floor_at(ptTo)
            if not self._tileset[floor].chip_walk & direction:
                return False
            if (floor == TYPE_SOCKET and self._chips_needed > 0):
                return False
            if (is_door(floor) and not self._possesion(floor)):
                return False
            if is_creature(self.current_level.get_cell(ptTo).top.id):
                tile_id = creature_id(self.current_level.get_cell(ptTo).top.id)
                if tile_id in (TYPE_CHIP, TYPE_CHIP_SWIMMING, TYPE_BLOCK):
                    return False
            if floor in (TYPE_HIDDENWALL_TEMP, TYPE_BLUEWALL_REAL):
                if not flags & CMM_NOEXPOSEWALLS:
                    self._set_floor_at(ptTo, TYPE_WALL)
                return False
            if floor == TYPE_BLOCK_STATIC:
                if not self._push_block(ptTo, direction, flags):
                    return False
                elif flags & CMM_NOPUSHING:
                    return False
                if ((flags & CMM_TELEPORTPUSH) and self._floor_at(ptTo) == TYPE_BLOCK_STATIC and
                    self.current_level.get_cell(ptTo).bottom.id == TYPE_EMPTY):
                    return True
                return self._can_make_move(creature, direction, flags | CMM_NOPUSHING)
        elif creature.type == TYPE_BLOCK:
            floor = self.current_level.get_cell(ptTo).top.id
            if is_creature(floor):
                tile_id = creature_id(floor)
                return tile_id in (TYPE_CHIP, TYPE_CHIP_SWIMMING)
            if not self._tileset[floor].block_move & direction:
                return False
        else:
            floor = self.current_level.get_cell(ptTo).top.id
            if is_creature(floor):
                tile_id = creature_id(floor)
                if tile_id in (TYPE_CHIP, TYPE_CHIP_SWIMMING):
                    floor = self.current_level.get_cell(ptTo).bottom.id
                    if is_creature(floor):
                        tile_id = creature_id(floor)
                        return tile_id in (TYPE_CHIP, TYPE_CHIP_SWIMMING)
            if is_creature(floor):
                if ((flags & CMM_CLONECANTBLOCK) and
                    floor == cr_tile(creature.type, creature.direction)):
                    return True
                return False
            if not self._tileset[floor].creature_walk & direction:
                return False
            if floor == TYPE_FIRE and (type in (TYPE_BUG, TYPE_WALKER)):
                if not flags & CMM_NOFIRECHECK:
                    return False

        if self.current_level.get_cell(ptTo).bottom.id == TYPE_CLONEMACHINE:
            return False

        return True

    def _push_block(self, ptPos, direction, flags):
        creature = self._get_block(ptPos)
        if creature is None:
            return False
        if creature.state & (CS_SLIP | CS_SLIDE):
            slip_dir = self._get_slip_dir(creature)
            if direction == slip_dir or direction == back(slip_dir):
                if not flags & CMM_TELEPORTPUSH:
                    return False
                return False
        if (not (flags & CMM_TELEPORTPUSH) and
            self.current_level.get_cell(ptPos).bottom.id == TYPE_BLOCK_STATIC):
            self.current_level.get_cell(ptPos).bottom.id = TYPE_EMPTY
        if not flags & CMM_NODEFERBUTTONS:
            creature.state |= CS_DEFERPUSH
            result = self._advance_creature(creature, direction)
        if not flags & CMM_NODEFERBUTTONS:
            creature.state &= ~CS_DEFERPUSH
        if not result:
            creature.state &= ~(CS_SLIP | CS_SLIDE)
        return result

    def _make_tile(self, tile_id, state):
        tile = Tile()
        tile.id = tile_id
        tile.state = state
        return tile

    def _update_creature(self, creature):
        if creature.hidden:
            return
        tile = self.current_level.get_cell(creature.cur_pos).top
        creature_type = creature.type
        if creature_type == TYPE_BLOCK:
            tile.id = TYPE_BLOCK_STATIC
            return
        elif creature_type == TYPE_CHIP:
            if self._get_chip_status():
                if self._get_chip_status() == SF_CHIPBURNED:
                    tile.id = TYPE_CHIP_BURNED
                    return
                elif self._get_chip_status() == SF_CHIPDROWNED:
                    tile.id = TYPE_CHIP_DROWNED
                    return
                elif self._get_chip_status() == SF_CHIPBOMBED:
                    tile.id = TYPE_CHIP_BOMBED
                    return
            elif self.current_level.get_cell(creature.cur_pos).bottom.id == TYPE_WATER:
                creature_type = TYPE_CHIP_SWIMMING

        direction = creature.direction
        if creature.state & CS_TURNING:
            direction = right(direction)
        tile.id = cr_tile(creature_type, direction)
        tile.state = 0

    def re_set_buttons(self):
        for x in range(32):
            for y in range(32):
                self.current_level.get_cell(Point(x, y)).top.state &= ~FS_BUTTONDOWN
                self.current_level.get_cell(Point(x, y)).bottom.state &= ~FS_BUTTONDOWN

    def handle_buttons(self):
        for x in range(32):
            for y in range(32):
                top = self.current_level.get_cell(Point(x, y)).top
                bottom = self.current_level.get_cell(Point(x, y)).bottom
                if top.state & FS_BUTTONDOWN:
                    top.state &= ~FS_BUTTONDOWN
                    tile_id = top.id
                elif bottom.state & FS_BUTTONDOWN:
                    bottom.state &= ~FS_BUTTONDOWN
                    tile_id = bottom.id
                else:
                    continue
                if tile_id == TYPE_BUTTON_BLUE:
                    self._toggle_tanks(None)
                    self._audio.play("BUTTON_PUSHED")
                elif tile_id == TYPE_BUTTON_GREEN:
                    self.current_level.toggle_blocks()
                elif tile_id == TYPE_BUTTON_RED:
                    self._activate_cloner(Point(x, y))
                    self._audio.play("BUTTON_PUSHED")
                elif tile_id == TYPE_BUTTON_BROWN:
                    self._spring_trap(Point(x, y))
                    self._audio.play("BUTTON_PUSHED")

    def _is_ice(self, tile):
        return (tile == TYPE_ICE or TYPE_ICEWALL_SOUTHEAST <= tile <= TYPE_ICEWALL_NORTHEAST)

    def _is_slide(self, tile):
        return (tile in (TYPE_SLIDE_SOUTH, TYPE_SLIDE_RANDOM) or
                TYPE_SLIDE_NORTH <= tile <= TYPE_SLIDE_WEST)

    def _start_floor_movement(self, creature, floor):
        creature.state &= ~(CS_SLIP | CS_SLIDE)

        if self._is_ice(floor):
            direction = self._ice_wall_turn(floor, creature.direction)
        elif self._is_slide(floor):
            direction = self._get_slide_dir(floor)
        elif floor == TYPE_TELEPORT:
            direction = creature.direction
        elif floor == TYPE_BEARTRAP and creature.type == TYPE_BLOCK:
            direction = creature.direction
        else:
            return

        if creature.type == TYPE_CHIP:
            creature.state |= (CS_SLIDE if self._is_slide(floor) else CS_SLIP)
            self._prepend_to_slip_list(creature, direction)
            creature.direction = direction
            self._update_creature(creature)
        else:
            creature.state |= CS_SLIP
            self._append_to_slip_list(creature, direction)

    def _end_floor_movement(self, creature):
        creature.state &= ~(CS_SLIP | CS_SLIDE)
        self._remove_from_slip_list(creature)

    def _update_slip_list(self):
        for slip in reversed(self._sliplist):
            if not slip.creature.state & (CS_SLIP | CS_SLIDE):
                self._end_floor_movement(slip.creature)

    def _floor_movements(self):
        #pylint: disable=too-many-branches
        slip_count = len(self._sliplist)
        for n in range(slip_count):
            saved_count = len(self._sliplist)
            slip = self._sliplist[n]
            creature = slip.creature
            if not creature.state & (CS_SLIP | CS_SLIDE):
                continue
            slip_direction = slip.dir
            if slip_direction == NONE:
                continue
            if creature.type == TYPE_CHIP:
                self._last_slip_dir = slip_direction
            if self._advance_creature(creature, slip_direction):
                if creature.type == TYPE_CHIP:
                    creature.state &= ~CS_HASMOVED
            else:
                floor = self.current_level.get_cell(creature.cur_pos).bottom.id
                if self._is_slide(floor):
                    if creature.type == TYPE_CHIP:
                        creature.state &= ~CS_HASMOVED
                elif self._is_ice(floor):
                    # Go back
                    slip_direction = self._ice_wall_turn(floor, back(slip_direction))
                    if creature.type == TYPE_CHIP:
                        self._last_slip_dir = slip_direction
                    if self._advance_creature(creature, slip_direction):
                        if creature.type == TYPE_CHIP:
                            creature.state &= ~CS_HASMOVED
                elif creature.type == TYPE_CHIP:
                    if floor in (TYPE_TELEPORT, TYPE_BLOCK_STATIC):
                        self._last_slip_dir = slip_direction = back(slip_direction)
                        if self._advance_creature(creature, slip_direction):
                            creature.state &= ~CS_HASMOVED
                if creature.state & (CS_SLIP | CS_SLIDE):
                    self._end_floor_movement(creature)
                    self._start_floor_movement(
                        creature,
                        self.current_level.get_cell(creature.cur_pos).bottom.id
                    )
            if self._check_for_ending():
                return
            # If creature is not slipping or sliding and the creature is not
            # chip and the slip list is one less than the saved count
            if (not (creature.state & (CS_SLIP | CS_SLIDE)) and
                creature.type != TYPE_CHIP and len(self._sliplist) == saved_count + 1):
                n += 1

    def get_death_message(self):
        # To be shown after dying
        for status, message in death_messages.items():
            if self._get_chip_status() == status:
                return message
        return None

    def get_decade_message(self):
        # To be shown after beating a level
        if self.current_level_number in decade_messages:
            return decade_messages[self.current_level_number]
        return None

    def _advance_creature(self, creature, direction):
        if direction == NONE:
            return True
        if creature.type == TYPE_CHIP:
            self._reset_chip_wait()
        if not self._start_movement(creature, direction):
            if creature.type == TYPE_CHIP:
                self._audio.play("CANT_MOVE")
                self.re_set_buttons()
            return False
        self._end_movement(creature)
        if creature.type == TYPE_CHIP:
            self.handle_buttons()

        return True

    def _start_movement(self, creature, direction):
        floor = self.current_level.get_cell(creature.cur_pos).bottom.id
        if not self._can_make_move(creature, direction, 0):
            if (creature.type == TYPE_CHIP or
                (floor != TYPE_BEARTRAP and floor != TYPE_CLONEMACHINE
                 and not creature.state & CS_SLIP)):
                creature.direction = direction
                self._update_creature(creature)
            return False

        creature.state &= ~CS_RELEASED
        creature.direction = direction
        return True

    def _end_movement(self, creature):
        #pylint: disable=too-many-branches, too-many-statements
        dead = False
        old_pos = creature.cur_pos
        new_pos = creature.front()
        cell = self.current_level.get_cell(new_pos)
        tile = cell.top
        floor = tile.id

        if creature.type == TYPE_CHIP:
            if floor in (TYPE_EMPTY, TYPE_DIRT, TYPE_BLUEWALL_FAKE):
                self.current_level.pop_tile(new_pos)
            elif floor == TYPE_WATER:
                if not self._possesion(TYPE_BOOTS_WATER):
                    self._set_chip_status(SF_CHIPDROWNED)
            elif floor == TYPE_FIRE:
                if not self._possesion(TYPE_BOOTS_FIRE):
                    self._set_chip_status(SF_CHIPBURNED)
            elif floor == TYPE_POPUPWALL:
                tile.id = TYPE_WALL
            elif floor in (TYPE_DOOR_RED, TYPE_DOOR_BLUE, TYPE_DOOR_YELLOW, TYPE_DOOR_GREEN):
                self._discard(floor)
                self.current_level.pop_tile(new_pos)
                self._audio.play("DOOR_OPENED")
            elif floor in (TYPE_KEY_RED, TYPE_KEY_BLUE, TYPE_KEY_YELLOW, TYPE_KEY_GREEN,
                           TYPE_BOOTS_ICE, TYPE_BOOTS_SLIDE, TYPE_BOOTS_FIRE, TYPE_BOOTS_WATER):
                if is_creature(cell.bottom.id):
                    self._set_chip_status(SF_CHIPHIT)
                self._collect(floor)
                self.current_level.pop_tile(new_pos)
                self._audio.play("ITEM_COLLECTED")
            elif floor == TYPE_THIEF:
                for item in range(4):
                    self.boots[item] = False
                self._audio.play("BOOTS_STOLEN")
            elif floor == TYPE_ICCHIP:
                self._chips_needed -= 1
                self.current_level.pop_tile(new_pos)
                self._audio.play("IC_COLLECTED")
            elif floor == TYPE_SOCKET:
                if self._chips_needed == 0:
                    self.current_level.pop_tile(new_pos)
            elif floor == TYPE_BOMB:
                self._set_chip_status(SF_CHIPBOMBED)
                self._audio.play("BOMB_EXPLOSION")
            else:
                if is_creature(floor):
                    self._set_chip_status(SF_CHIPHIT)
        elif creature.type == TYPE_BLOCK:
            if floor == TYPE_EMPTY:
                self.current_level.pop_tile(new_pos)
            elif floor == TYPE_WATER:
                tile.id = TYPE_DIRT
                dead = True
                self._audio.play("WATER_SPLASH")
            elif floor == TYPE_BOMB:
                tile.id = TYPE_EMPTY
                dead = True
                self._audio.play("BOMB_EXPLOSION")
            elif floor == TYPE_TELEPORT:
                if not tile.state & FS_BROKEN:
                    new_pos = self._teleport_creature(creature, new_pos)
        else:
            if is_creature(floor):
                tile = cell.bottom
                floor = tile.id
            if floor == TYPE_WATER:
                if creature.type != TYPE_GLIDER:
                    dead = True
            elif floor == TYPE_FIRE:
                if creature.type != TYPE_FIREBALL:
                    dead = True
            elif floor == TYPE_BOMB:
                tile.id = TYPE_EMPTY
                dead = True
                self._audio.play("BOMB_EXPLOSION")
            elif floor == TYPE_TELEPORT:
                if not tile.state & FS_BROKEN:
                    new_pos = self._teleport_creature(creature, new_pos)

        if (self.current_level.get_cell(old_pos).bottom.id != TYPE_CLONEMACHINE or
            creature.type == TYPE_CHIP):
            self.current_level.pop_tile(old_pos)

        if dead:
            self._remove_creature(creature)
            if self.current_level.get_cell(old_pos).bottom.id == TYPE_CLONEMACHINE:
                self.current_level.get_cell(old_pos).bottom.state &= ~FS_CLONING
            return

        if creature.type == TYPE_CHIP and floor == TYPE_TELEPORT and not tile.state & FS_BROKEN:
            pos = new_pos
            new_pos = self._teleport_creature(creature, new_pos)
            if pos != new_pos:
                self._audio.play("TELEPORT")
                if self._floor_at(new_pos) == TYPE_BLOCK_STATIC:
                    if self._last_slip_dir == NONE:
                        creature.direction = NORTH
                        self.current_level.get_cell(new_pos).top.id = cr_tile(TYPE_CHIP, NORTH)
                        floor = TYPE_EMPTY
                    else:
                        creature.direction = self._last_slip_dir


        creature.cur_pos = new_pos
        self._add_creature_to_map(creature)
        creature.cur_pos = old_pos

        tile = cell.bottom
        if floor == TYPE_BUTTON_BLUE:
            if creature.state & CS_DEFERPUSH:
                tile.state |= FS_BUTTONDOWN
            else:
                self._toggle_tanks(creature)
            self._audio.play("BUTTON_PUSHED")
        elif floor == TYPE_BUTTON_GREEN:
            if creature.state & CS_DEFERPUSH:
                tile.state |= FS_BUTTONDOWN
            else:
                self.current_level.toggle_blocks()
        elif floor == TYPE_BUTTON_RED:
            if creature.state & CS_DEFERPUSH:
                tile.state |= FS_BUTTONDOWN
            else:
                self._activate_cloner(new_pos)
            self._audio.play("BUTTON_PUSHED")
        elif floor == TYPE_BUTTON_BROWN:
            if creature.state & CS_DEFERPUSH:
                tile.state |= FS_BUTTONDOWN
            else:
                self._spring_trap(new_pos)
            self._audio.play("BUTTON_PUSHED")

        creature.cur_pos = new_pos

        if self.current_level.get_cell(old_pos).bottom.id == TYPE_CLONEMACHINE:
            self.current_level.get_cell(old_pos).bottom.state &= ~FS_CLONING

        if floor == TYPE_BEARTRAP:
            if self._is_trap_openr(new_pos, old_pos):
                tile.state |= CS_RELEASED
        elif self.current_level.get_cell(new_pos).bottom.id == TYPE_BEARTRAP:
            for trap in self.current_level.traps:
                if trap.device == new_pos:
                    creature.state |= CS_RELEASED
                    break

        if creature.type == TYPE_CHIP:
            if self._get_chip_status() != SF_CHIPOKAY:
                return
            if cell.bottom.id == TYPE_EXIT:
                self.status |= SF_COMPLETED
                return
        else:
            if is_creature(cell.bottom.id):
                if (creature_id(cell.bottom.id) == TYPE_CHIP or
                    creature_id(cell.bottom.id) == TYPE_CHIP_SWIMMING):
                    self._set_chip_status(SF_CHIPHIT)
                return

        was_slipping = creature.state & (CS_SLIP | CS_SLIDE)

        if floor == TYPE_TELEPORT:
            self._start_floor_movement(creature, floor)
        elif (self._is_ice(floor) and
              (creature.type != TYPE_CHIP or not self._possesion(TYPE_BOOTS_ICE))):
            self._start_floor_movement(creature, floor)
        elif (self._is_slide(floor) and
              (creature.type != TYPE_CHIP or not self._possesion(TYPE_BOOTS_SLIDE))):
            self._start_floor_movement(creature, floor)
        elif floor == TYPE_BEARTRAP and creature.type == TYPE_BLOCK and was_slipping:
            self._start_floor_movement(creature, floor)
        else:
            creature.state &= ~(CS_SLIP | CS_SLIDE)

        if (not was_slipping and (creature.state & (CS_SLIP | CS_SLIDE)) and
            creature.type != TYPE_CHIP):
            self._controller_dir = self._get_slip_dir(creature)

    def _add_creature_to_map(self, creature):
        if creature.hidden:
            return
        self.current_level.push_tile(creature.cur_pos, self._make_tile(TYPE_EMPTY, 0))
        self._update_creature(creature)

    def _cloner_from_button(self, pos):
        for cloner in self.current_level.cloners:
            if cloner.button == pos:
                return cloner.device
        return Point(-1, -1)

    def _is_trap_openr(self, pos, skip_pos):
        for trap in self.current_level.traps:
            if (trap.device == pos and trap.button != skip_pos and
                self._is_trap_button_down(trap.button)):
                return True
        return False

    def _trap_from_button(self, pos):
        for trap in self.current_level.traps:
            if trap.button == pos:
                return trap.device
        return Point(-1, -1)

    def _activate_cloner(self, button_pos):
        cloner_position = self._cloner_from_button(button_pos)
        if not 0 <= cloner_position.x < 32 or not 0 <= cloner_position.y < 32:
            return
        tile_to_clone = self.current_level.get_cell(cloner_position).top.id
        if not is_creature(tile_to_clone) or creature_id(tile_to_clone) == TYPE_CHIP:
            return
        if creature_id(tile_to_clone) == TYPE_BLOCK:
            creature = self._get_block(cloner_position)
            if creature.direction != NONE:
                self._advance_creature(creature, creature.direction)
        else:
            if self.current_level.get_cell(cloner_position).bottom.state & FS_CLONING:
                return
            dummy_creature = Creature(
                position=cloner_position,
                direction=creature_dir_id(tile_to_clone),
                type=creature_id(tile_to_clone)
            )
            if not self._can_make_move(
                dummy_creature, dummy_creature.direction, CMM_CLONECANTBLOCK):
                return
            creature = self._awaken_creature(cloner_position)
            if not creature:
                return
            creature.state |= CS_CLONING
            if self.current_level.get_cell(cloner_position).bottom.id == TYPE_CLONEMACHINE:
                self.current_level.get_cell(cloner_position).bottom.state |= FS_CLONING

    def _awaken_creature(self, pos):
        tile = self.current_level.get_cell(pos).top.id
        if not is_creature(tile) or creature_id(tile) == TYPE_CHIP:
            return None
        add_function = self._add_block if creature_id(tile) == TYPE_BLOCK else self._add_creature
        return add_function(pos, creature_dir_id(tile), creature_id(tile))

    def _spring_trap(self, button_position):
        trap_position = self._trap_from_button(button_position)
        if not 0 <= trap_position.x < 32 or not 0 <= trap_position.y < 32:
            return
        tile = self.current_level.get_cell(trap_position).top.id
        if (tile == TYPE_BLOCK_STATIC or
            self.current_level.get_cell(trap_position).bottom.state & FS_HASMUTANT):
            creature = self._get_block(trap_position)
            if creature:
                creature.state |= CS_RELEASED
        elif is_creature(tile):
            creature = self._get_creature(trap_position, True)
            if creature:
                creature.state |= CS_RELEASED

    def _teleport_creature(self, creature, start_position):
        orig_pos = creature.cur_pos
        dest = Point(start_position.x, start_position.y)
        while True:
            dest.x -= 1
            if dest.x < 0:
                dest.y -= 1
                dest.x = 31
            if dest.y < 0:
                dest.y = 31
            if dest == start_position:
                break
            tile = self.current_level.get_cell(dest).top
            if tile.id != TYPE_TELEPORT or (tile.state & FS_BROKEN):
                continue
            creature.cur_pos = dest
            can_move = self._can_make_move(
                creature,
                creature.direction,
                CMM_NOLEAVECHECK | CMM_NOEXPOSEWALLS | CMM_NODEFERBUTTONS |
                CMM_NOFIRECHECK | CMM_TELEPORTPUSH)
            creature.cur_pos = orig_pos
            if can_move:
                break
        return dest

    # We may remove this as I believe it has to do with path finding based on mouse clicks
    def _get_chip_walk_cmd(self):
        choices = [0, 0]
        pt_tile = self._chip.destination
        x = pt_tile.x - self._chip.cur_pos.x
        y = pt_tile.y - self._chip.cur_pos.y
        n = NORTH if y < 0 else SOUTH if y > 0 else NONE
        if y < 0:
            y = -y
        m = WEST if x < 0 else EAST if x > 0 else NONE
        if x < 0:
            x = -x
        if x > y:
            choices[0] = m
            choices[1] = n
        else:
            choices[0] = n
            choices[1] = m
        index = 0
        while index < 2:
            if choices[index] != NONE and self._can_make_move(self._chip, choices[index], 0):
                return dir_idx(choices[index])
            index += 1
        self._chip.walking = False
        return NONE

    def reset(self):
        self.set_game_mode(GM_NORMAL)
        self._moving = False
        self._current_time = 0
        self.keys = [0] * 4
        self.boots = [False] * 4
        self.status = SF_CHIPOKAY
        self._chip.walking = False
        self._chip.state = 0
        self._creature_pool = []
        self._block_pool = []
        self._set_button(NONE)
        self.dead_creatures = 0
        self.dead_blocks = 0

    def _extract_creatures(self):
        for creature_position in self.current_level.creatures:
            tile = self.current_level.get_cell(creature_position).top.id
            if is_creature(tile):
                self._add_creature(creature_position, creature_dir_id(tile), creature_id(tile))
        for x in range(32):
            for y in range(32):
                tile2 = self.current_level.get_cell(Point(x, y)).top.id
                if creature_id(tile2) == TYPE_CHIP:
                    self._chip.cur_pos = Point(x, y)
                    self._chip.type = TYPE_CHIP
                    self._chip.direction = creature_dir_id(tile2)

    def _append_to_slip_list(self, creature, direction):
        # Append the given creature to the end of the slip list
        for slip in self._sliplist:
            if slip.creature == creature:
                slip.dir = direction
                return creature

        slip = Slip()
        slip.creature = creature
        slip.dir = direction
        self._sliplist.append(slip)
        return creature

    def _prepend_to_slip_list(self, creature, direction):
        # Prepend the given creature to the start of the slip list
        if len(self._sliplist) > 0 and self._sliplist[0].creature == creature:
            self._sliplist[0].dir = direction
            return creature

        slip = Slip()
        slip.creature = creature
        slip.dir = direction
        self._sliplist.insert(0, slip)
        return creature

    def _remove_from_slip_list(self, creature):
        if len(self._sliplist) == 0:
            return

        for slip in self._sliplist:
            if slip.creature == creature:
                self._sliplist.remove(slip)
                break

    def _get_slip_dir(self, creature):
        for slip in self._sliplist:
            if slip.creature == creature:
                return slip.dir
        return NONE

    def _add_creature(self, tile_pos, direction, creature_type):
        new_creature = Creature(
            position=tile_pos,
            direction=direction,
            creature_type=creature_type
        )
        self._creature_pool.append(new_creature)
        return new_creature

    def _remove_creature(self, creature):
        if creature.type == TYPE_BLOCK:
            self.dead_blocks += 1
        else:
            self.dead_creatures += 1
        creature.state &= ~(CS_SLIP | CS_SLIDE)
        if creature.type == TYPE_CHIP:
            if self.status == SF_CHIPOKAY:
                self.status = SF_CHIPNOTOKAY
        creature.hidden = True

    def _remove_dead_creatures(self):
        for creature in self._creature_pool:
            if creature.hidden and not creature.on_slip_list:
                self._remove_creature(creature)
                self.dead_creatures -= 1

    def _get_creature(self, pos, include_chip):
        for creature in self._creature_pool:
            if creature.cur_pos == pos:
                return creature
        if include_chip and self._chip.cur_pos == pos:
            return self._chip
        return None

    def _add_block(self, tile_pos, direction, creature_type):
        new_block = Creature()
        new_block.cur_pos = tile_pos
        new_block.direction = direction
        new_block.type = creature_type
        self._block_pool.append(new_block)
        return new_block

    def _remove_dead_blocks(self):
        for block in self._block_pool:
            if block.hidden and not block.on_slip_list:
                self._block_pool.remove(block)
                self.dead_blocks -= 1

    def _get_block(self, pos):
        for block in self._block_pool:
            if block.cur_pos == pos and not block.hidden:
                return block
        tile = self.current_level.get_cell(pos).top.id
        if creature_id(tile) == TYPE_BLOCK:
            creature_dir = creature_dir_id(tile)
        elif tile == TYPE_BLOCK_STATIC:
            creature_dir = NONE
        else:
            return None

        new_block = self._add_block(pos, creature_dir, TYPE_BLOCK)
        if self.current_level.get_cell(pos).bottom.id == TYPE_BEARTRAP:
            for trap in self.current_level.traps:
                if trap.device == new_block.cur_pos:
                    new_block.state |= CS_RELEASED
                    break
        return new_block

    def _random_p(self, array, level):
        for index in range(5 - level, level + 1):
            number = random.randint(0, index - 1)
            array[number], array[index - 1] = array[index - 1], array[number]

    def _toggle_tanks(self, mid_move):
        for creature in self._creature_pool:
            if creature.hidden or creature.type != TYPE_TANK:
                continue
            creature.direction = back(creature.direction)
            if not creature.state & CS_TURNING:
                creature.state |= CS_TURNING | CS_HASMOVED
            if creature != mid_move:
                if creature_id(self.current_level.get_cell(creature.cur_pos).top.id) == TYPE_TANK:
                    self._update_creature(creature)
                else:
                    if creature.state & CS_TURNING:
                        creature.state &= ~CS_TURNING
                        self._update_creature(creature)
                        creature.state |= CS_TURNING
                    creature.direction = back(creature.direction)

    def set_game_mode(self, mode, push=True):
        game_mode = self.get_game_mode()
        if game_mode != mode:
            if not push and len(self._game_mode) > 0:
                self._game_mode.pop()
            self._game_mode.append(mode)
            # Housekeeping
            while len(self._game_mode) > 4:
                self._game_mode.pop(0)

    def revert_game_mode(self):
        self._game_mode.pop()

    def get_game_mode(self):
        last = len(self._game_mode) - 1
        if last < 0:
            return None
        return self._game_mode[last]

    def _choose_chip_move(self, creature, _discard):
        creature.to_direction = NONE
        if creature.hidden:
            return
        if not self.get_tick() & 3:
            creature.state &= ~CS_HASMOVED
        if creature.state & CS_HASMOVED:
            return
        direction = self._current_input
        self._set_button(NONE)

        if not NORTH <= direction <= EAST:
            direction = NONE
        if _discard or ((creature.state & CS_SLIDE) and direction == creature.direction):
            return
        creature.to_direction = direction

    def _choose_move(self, creature):
        if creature.type == TYPE_CHIP:
            self._choose_chip_move(creature, creature.state & CS_SLIP)
        else:
            if creature.state & CS_SLIP:
                creature.to_dir = NONE
            else:
                self._choose_creature_move(creature)

    def _choose_creature_move(self, creature):
        #pylint: disable=too-many-branches, too-many-statements, too-many-return-statements
        choices = [NONE, NONE, NONE, NONE]
        creature.to_direction = NONE
        creature_type = creature.type
        if creature.hidden:
            return
        if creature_type == TYPE_BLOCK:
            return
        if self.get_tick() & 2:
            return
        if creature_type in (TYPE_TEETH, TYPE_BLOB):
            if self.get_tick() & 4:
                return
        if creature.state & CS_TURNING:
            creature.state &= ~(CS_TURNING | CS_HASMOVED)
            self._update_creature(creature)
        if creature.state & CS_HASMOVED:
            self._controller_dir = NONE
            return
        if creature.state & (CS_SLIP | CS_SLIDE):
            return
        floor = self._floor_at(creature.cur_pos)
        next_direction = current_direction = creature.direction
        if floor in (TYPE_CLONEMACHINE, TYPE_BEARTRAP):
            if creature_type in (TYPE_TANK, TYPE_BALL, TYPE_GLIDER, TYPE_FIREBALL, TYPE_WALKER):
                choices[0] = current_direction
            elif creature_type == TYPE_BLOB:
                choices[0] = current_direction
                choices[1] = left(current_direction)
                choices[2] = back(current_direction)
                choices[3] = right(current_direction)
                self._random_p(choices, 4)
            elif creature_type in (TYPE_BUG, TYPE_PARAMECIUM, TYPE_TEETH):
                choices[0] = self._controller_dir
                creature.to_direction = self._controller_dir
                return
            else:
                raise ValueError("Invalid creature type")
        else:
            if creature_type == TYPE_TANK:
                choices[0] = current_direction
            elif creature_type == TYPE_BALL:
                choices[0] = current_direction
                choices[1] = back(current_direction)
            elif creature_type == TYPE_GLIDER:
                choices[0] = current_direction
                choices[1] = left(current_direction)
                choices[2] = right(current_direction)
                choices[3] = back(current_direction)
            elif creature_type == TYPE_FIREBALL:
                choices[0] = current_direction
                choices[1] = right(current_direction)
                choices[2] = left(current_direction)
                choices[3] = back(current_direction)
            elif creature_type == TYPE_WALKER:
                choices[0] = current_direction
                choices[1] = left(current_direction)
                choices[2] = back(current_direction)
                choices[3] = right(current_direction)
                self._random_p(choices[1:], 3)
            elif creature_type == TYPE_BLOB:
                choices[0] = current_direction
                choices[1] = left(current_direction)
                choices[2] = back(current_direction)
                choices[3] = right(current_direction)
                self._random_p(choices, 4)
            elif creature_type == TYPE_BUG:
                choices[0] = left(current_direction)
                choices[1] = current_direction
                choices[2] = right(current_direction)
                choices[3] = back(current_direction)
            elif creature_type == TYPE_PARAMECIUM:
                choices[0] = right(current_direction)
                choices[1] = current_direction
                choices[2] = left(current_direction)
                choices[3] = back(current_direction)
            elif creature_type == TYPE_TEETH:
                x = self._chip.cur_pos.x - creature.cur_pos.x
                y = self._chip.cur_pos.y - creature.cur_pos.y
                n = NORTH if y < 0 else SOUTH if y > 0 else NONE
                if y < 0:
                    y = -y
                m = WEST if x < 0 else EAST if x > 0 else NONE
                if x < 0:
                    x = -x
                if x > y:
                    choices[0] = m
                    choices[1] = n
                else:
                    choices[0] = n
                    choices[1] = m
                next_direction = choices[0]
            else:
                raise ValueError("Invalid creature type")
        for n in range(4):
            creature.to_direction = choices[n]
            self._controller_dir = creature.to_direction
            if self._can_make_move(creature, choices[n], 0):
                return
        if creature_type == TYPE_TANK:
            if ((creature.state & CS_RELEASED) or floor not in (TYPE_BEARTRAP, TYPE_CLONEMACHINE)):
                creature.state |= CS_HASMOVED
        creature.to_direction = next_direction

    def _prepare(self):
        if not self.get_tick() & 3:
            for creature in self._creature_pool:
                if creature.state & CS_TURNING:
                    creature.state &= ~(CS_TURNING | CS_HASMOVED)
                    self._update_creature(creature)
            self.status = (self.status & ~SF_CHIPWAITMASK) | ((self.status & SF_CHIPWAITMASK) + 1)
            if self.status & SF_CHIPWAITMASK > 3:
                self._reset_chip_wait()
                self._chip.direction = SOUTH
                self._update_creature(self._chip)

    def advance_game(self, input_command):
        #pylint: disable=too-many-branches
        dir_cmd = NONE
        if input_command == NONE:
            # Check if chip is autopathing
            if self._chip.walking:
                dir_cmd = self._get_chip_walk_cmd()
                if dir_cmd != NONE:
                    input_command = dir_cmd
        else:
            self._chip.walking = False

        # Don't start level until we have movement
        if self.get_tick() or (UP <= input_command <= RIGHT):
            self._current_time += 1

        if UP <= input_command <= RIGHT:
            self._set_button(idx_dir(input_command))
        else:
            self._set_button(NONE)

        self._prepare()

        if self.get_tick() and not self.get_tick() & 1:
            self._controller_dir = NONE
            for creature in self._creature_pool:
                if creature.hidden or (creature.state & CS_CLONING) or creature.type == TYPE_CHIP:
                    continue
                self._choose_move(creature)
                if creature.to_direction != NONE:
                    self._advance_creature(creature, creature.to_direction)
            if self._check_for_ending():
                self._finalize()
                return
        if self.get_tick() and not self.get_tick() & 1:
            self._floor_movements()
            if self._check_for_ending():
                self._finalize()
                return

        self._update_slip_list()

        if self._time_limit:
            if self.get_tick() >= self._time_limit:
                if self.status == SF_CHIPOKAY:
                    self.status = SF_CHIPNOTOKAY
                    self._set_chip_status(SF_CHIPTIMEUP)
                    self.set_game_mode(GM_CHIPDEAD)
                    self._audio.play("TIME_UP")
                return
            elif (self._time_limit - self.get_tick() <= 15 * TICKS_PER_SECOND and
                  self.get_tick() % TICKS_PER_SECOND == 0):
                self._audio.play("TIME_LOW_TICK")
        self._choose_move(self._chip)
        if self._chip.to_direction != NONE:
            if self._advance_creature(self._chip, self._chip.to_direction):
                if self._check_for_ending():
                    self._finalize()
                    return
            self._chip.state |= CS_HASMOVED
        self._update_slip_list()
        self._create_clones()
        self._finalize()

    def _create_clones(self):
        for creature in self._creature_pool:
            if creature.state & CS_CLONING:
                creature.state &= ~CS_CLONING

    def _finalize(self):
        if self.dead_creatures:
            self._remove_dead_creatures()
        if self.dead_blocks:
            self._remove_dead_blocks()
        if self.current_level.get_cell(self._chip.cur_pos).bottom.id == TYPE_HINTBUTTON:
            self.status |= SF_SHOWHINT
        else:
            self.status &= ~SF_SHOWHINT

    def _check_for_ending(self):
        if self.status & SF_COMPLETED:
            self._audio.play("CHIP_WINS")
            self.set_game_mode(GM_LEVELWON)
            return True
        if self.status & SF_CHIPNOTOKAY:
            self._audio.play("CHIP_LOSES")
            self.set_game_mode(GM_CHIPDEAD)
            return True
        return False

    def _create_tileset(self):
        #pylint: disable=too-many-statements
        # Chip, Block, Creature
        self._tileset[TYPE_EMPTY].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_WALL].set_walk(0, 0, 0)
        self._tileset[TYPE_ICCHIP].set_walk(NWSE, 0, 0)
        self._tileset[TYPE_WATER].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_FIRE].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_WALL_NORTH].set_walk(
            WEST | NORTH | EAST,
            WEST | NORTH | EAST,
            WEST | NORTH | EAST
        )
        self._tileset[TYPE_WALL_WEST].set_walk(
            NORTH | SOUTH | WEST,
            NORTH | SOUTH | WEST,
            NORTH | SOUTH | WEST
        )
        self._tileset[TYPE_WALL_SOUTH].set_walk(
            SOUTH | WEST | EAST,
            SOUTH | WEST | EAST,
            SOUTH | WEST | EAST
        )
        self._tileset[TYPE_WALL_EAST].set_walk(
            NORTH | EAST | SOUTH,
            NORTH | EAST | SOUTH,
            NORTH | EAST | SOUTH
        )
        self._tileset[TYPE_WALL_SOUTHEAST].set_walk(SOUTH | EAST, SOUTH | EAST, SOUTH | EAST)
        self._tileset[TYPE_BLOCK_STATIC].set_walk(NWSE, 0, 0)
        self._tileset[TYPE_DIRT].set_walk(NWSE, 0, 0)
        self._tileset[TYPE_ICE].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_SLIDE_SOUTH].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_SLIDE_NORTH].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_SLIDE_EAST].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_SLIDE_WEST].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_EXIT].set_walk(NWSE, NWSE, 0)
        self._tileset[TYPE_DOOR_BLUE].set_walk(NWSE, 0, 0)
        self._tileset[TYPE_DOOR_RED].set_walk(NWSE, 0, 0)
        self._tileset[TYPE_DOOR_GREEN].set_walk(NWSE, 0, 0)
        self._tileset[TYPE_DOOR_YELLOW].set_walk(NWSE, 0, 0)
        self._tileset[TYPE_ICEWALL_NORTHWEST].set_walk(SOUTH | EAST, SOUTH | EAST, SOUTH | EAST)
        self._tileset[TYPE_ICEWALL_NORTHEAST].set_walk(SOUTH | WEST, SOUTH | WEST, SOUTH | WEST)
        self._tileset[TYPE_ICEWALL_SOUTHWEST].set_walk(NORTH | EAST, NORTH | EAST, NORTH | EAST)
        self._tileset[TYPE_ICEWALL_SOUTHEAST].set_walk(NORTH | WEST, NORTH | WEST, NORTH | WEST)
        self._tileset[TYPE_BLUEWALL_FAKE].set_walk(NWSE, 0, 0)
        self._tileset[TYPE_BLUEWALL_REAL].set_walk(NWSE, 0, 0)
        self._tileset[TYPE_THIEF].set_walk(NWSE, 0, 0)
        self._tileset[TYPE_SOCKET].set_walk(NWSE, 0, 0)
        self._tileset[TYPE_BUTTON_GREEN].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_BUTTON_RED].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_SWITCHWALL_CLOSED].set_walk(0, 0, 0)
        self._tileset[TYPE_SWITCHWALL_OPEN].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_BUTTON_BROWN].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_BUTTON_BLUE].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_TELEPORT].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_BOMB].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_BEARTRAP].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_HIDDENWALL_PERM].set_walk(0, 0, 0)
        self._tileset[TYPE_HIDDENWALL_TEMP].set_walk(NWSE, 0, 0)
        self._tileset[TYPE_GRAVEL].set_walk(NWSE, NWSE, 0)
        self._tileset[TYPE_POPUPWALL].set_walk(NWSE, 0, 0)
        self._tileset[TYPE_HINTBUTTON].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_CLONEMACHINE].set_walk(0, 0, 0)
        self._tileset[TYPE_SLIDE_RANDOM].set_walk(NWSE, NWSE, 0)
        self._tileset[TYPE_KEY_BLUE].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_KEY_RED].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_KEY_GREEN].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_KEY_YELLOW].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_BOOTS_WATER].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_BOOTS_FIRE].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_BOOTS_ICE].set_walk(NWSE, NWSE, NWSE)
        self._tileset[TYPE_BOOTS_SLIDE].set_walk(NWSE, NWSE, NWSE)
        self._tileset[0x0E].set_walk(0, 0, 0)
        self._tileset[0x0F].set_walk(0, 0, 0)
        self._tileset[0x10].set_walk(0, 0, 0)
        self._tileset[0x11].set_walk(0, 0, 0)
        for index in range(0x40, 0x64):
            self._tileset[index].set_walk(NWSE, 0, 0)
        for index in range(0x64, 0x70):
            self._tileset[index].set_walk(0, NWSE, 0)

    def _set_floor_at(self, tile_coords, tile):
        test_tile = self.current_level.get_cell(tile_coords).top.id
        if not is_key(test_tile) and not is_boots(test_tile) and not is_creature(test_tile):
            self.current_level.get_cell(tile_coords).top.id = tile
            return
        else:
            self.current_level.get_cell(tile_coords).bottom.id = tile

    def _floor_at(self, tile_coords):
        tile = self.current_level.get_cell(tile_coords).top.id
        if not is_key(tile) and not is_boots(tile) and not is_creature(tile):
            return tile
        tile = self.current_level.get_cell(tile_coords).bottom.id
        if not is_key(tile) and not is_boots(tile) and not is_creature(tile):
            return tile
        return TYPE_EMPTY

    def _is_trap_button_down(self, coords):
        return (0 <= coords.x < 32 and 0 <= coords.y < 32 and
                self.current_level.get_cell(coords).top.id == TYPE_BUTTON_BROWN)

    def get_tick(self):
        return self._current_time

    def _set_chip_status(self, status):
        self.status = (self.status & ~SF_CHIPSTATUSMASK) | status

    def _get_chip_status(self):
        return self.status & SF_CHIPSTATUSMASK

    def _reset_chip_wait(self):
        self.status &= ~SF_CHIPWAITMASK

    def _set_button(self, button):
        self._current_input = button

    def get_chips_needed(self):
        if self._chips_needed < 0:
            return 0
        return self._chips_needed
