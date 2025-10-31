# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# pylint: disable=abstract-method, attribute-defined-outside-init, unsubscriptable-object, useless-object-inheritance
# pylint: disable=unsupported-assignment-operation, line-too-long, too-many-lines, too-many-branches

try:
    from typing import Optional
except ImportError:
    pass

COLOR_COUNT = 8
EMPTY = 8
X = 0
Y = 1
WIDTH = 0
HEIGHT = 1


class Entity(object):
    """
    Class representing an entity that can be added to a workspace.
    All Gates and other objects that can be used in the simulation will extend this class.
    """

    size = (1, 1)
    """Size in tiles of the rectangle that contains the entity.
    Note that some tiles with this maybe unused."""

    _location = (0, 0)
    """The location of the top left tile of the entity within the workspace"""

    tile_locations = (_location,)
    """Locations of all tiles used by the entity"""

    tiles = (EMPTY,)
    """Tile indexes from the spritesheet used by the entity"""

    type = "None"
    """The entity type"""

    _workspace = None

    def apply_state_palette_mapping(self):
        """
        Apply the dynamic palette color mapping based on the
        current state of the entity.
        """
        raise NotImplementedError()

    @property
    def value(self):
        """
        The logic output value of the entity
        """
        raise NotImplementedError()

    def _init_tile_locations(self):
        """
        Initialize the tile locations and input entity tile locations.
        """

        raise NotImplementedError()

    @property
    def location(self):
        """Location of the top left tile of the entity within the workspace, in tile coordinates"""
        return self._location

    @location.setter
    def location(self, value):
        self._location = value
        # re-calculate tile locations
        self._init_tile_locations()


class OutputPanel(Entity):
    """
    Output panel that displays logic values as 1 or 0
    """

    def __init__(self, location, workspace, add_to_workspace=True):
        self.type = "output"
        self.size = (2, 1)
        self._workspace = workspace
        self.location = location
        self._init_tile_locations()
        self.tiles = [2, 3]
        self._input_one = False
        if add_to_workspace:
            self._workspace.add_entity(self)

    def _init_tile_locations(self):
        self.tile_locations = (self.location, (self.location[X] + 1, self.location[Y]))
        # Location of the entity connected to the input of the panel in x,y tile coords
        self.input_entity_location = (self.location[X] - 1, self.location[Y])

    @property
    def palette_mapping(self):
        """Dynamic palette mapping list of color indexes
        based on the current state of the entity"""
        pal = list(range(COLOR_COUNT))
        pal[3] = 7 if self._input_one else 1
        pal[4] = 1 if self._input_one else 2
        pal[5] = 1 if not self._input_one else 2
        return pal

    def apply_state_palette_mapping(self):
        cur_state_palette = self.palette_mapping
        for loc in self.tile_locations:
            self._workspace.tilegrid.pixel_shader[loc] = cur_state_palette

    @property
    def input_one(self):
        """Logic value of input one"""
        return self._input_one

    @input_one.setter
    def input_one(self, value):
        self._input_one = value
        self.apply_state_palette_mapping()

    @property
    def value(self):
        # Output panel does not have a logic output value
        return False

    def update(self):
        """
        Run logic simulation for this entity
        """
        input_entity = self.input_entity
        # if no input entity then set logic value False
        if input_entity is None:
            self.input_one = False
            self.apply_state_palette_mapping()
            return

        # update logic value based on entity value
        self.input_one = self.input_entity.value

    @property
    def input_entity(self):
        """Entity at the input location"""
        return self._workspace.entity_at(self.input_entity_location)


class VirtualPushButton(Entity):
    """
    Virtual push button that can be on or off, clicked by the mouse to change state
    """

    def __init__(
        self, location, workspace, initial_pressed_state=False, add_to_workspace=True
    ):
        self.type = "input"
        self.size = (1, 1)
        self._workspace = workspace
        self.location = location
        self._init_tile_locations()
        self.tiles = [21]

        self.pressed_state = initial_pressed_state

        if add_to_workspace:
            self._workspace.add_entity(self)

    def _init_tile_locations(self):
        self.tile_locations = (self.location,)

    @property
    def value(self):
        return self.pressed_state

    def apply_state_palette_mapping(self):
        pal = list(range(COLOR_COUNT))
        pal[5] = 7 if self.value else 1
        pal[2] = 7 if self.value else 6

        for loc in self.tile_locations:
            self._workspace.tilegrid.pixel_shader[loc] = pal

    def handle_click(self):
        self.pressed_state = not self.pressed_state
        self.apply_state_palette_mapping()
        self._workspace.update()


class PhysicalButton(Entity):
    """
    Physical button tied to one of the hardware buttons on the Fruit Jam
    """

    SPRITE_INDEXES = (23, 26, 27)

    def __init__(self, location, workspace, index, add_to_workspace=True):
        self.index = index
        self.type = "input"
        self.size = (1, 1)
        self._workspace = workspace
        self.location = location
        self._init_tile_locations()
        self.tiles = [self.SPRITE_INDEXES[index]]

        if add_to_workspace:
            self._workspace.add_entity(self)

    def _init_tile_locations(self):
        self.tile_locations = (self.location,)

    def update(self):
        self.apply_state_palette_mapping()

    @property
    def value(self):
        return not self._workspace.buttons[self.index].value

    def apply_state_palette_mapping(self):
        pal = list(range(COLOR_COUNT))
        pal[5] = 7 if self.value else 1
        pal[2] = 7 if self.value else 6

        for loc in self.tile_locations:
            self._workspace.tilegrid.pixel_shader[loc] = pal

class SignalReceiver(Entity):
    """
    Virtual Connector used to bring signals into an entity from a Signal Transmitter
    """

    def __init__(self, location, workspace, connector_number=None, add_to_workspace=True):
        self.type = "input"
        self.size = (1, 1)
        self._workspace = workspace
        self.location = location
        self._init_tile_locations()
        self.tiles = [30]
        self.connector_number = None
        self._overlay_tile = None
        self._input_one = None

        if connector_number is None:
            # Find the last SignalTransmitter entity added to the workspace to link to
            for entity in self._workspace.entities:
                if isinstance(entity, SignalTransmitter):
                    self.connector_number = entity.connector_number
                    self._input_one = entity
        else:
            self.connector_number = connector_number

        if add_to_workspace:
            self._workspace.add_entity(self)

        self.apply_state_palette_mapping()

    def _init_tile_locations(self):
        self.tile_locations = (self.location,)

    def update(self):
        """
        Run logic simulation for this entity
        """
        self.apply_state_palette_mapping()

    @property
    def input_one(self):
        """The input entity for this Wire."""
        return self._input_one

    @input_one.setter
    def input_one(self, input_entity):
        if isinstance(input_entity, SignalTransmitter):
            self._input_one = input_entity
            self.apply_state_palette_mapping()

    @property
    def value(self):
        if self.connector_number is None:
            return False
        elif self.input_one is None:
            return False
        elif self.input_one.input_one is None:
            return False
        elif self._input_one.input_one == self:
            return False

        return self.input_one.input_one.value

    def apply_state_palette_mapping(self):
        pal = list(range(COLOR_COUNT))
        pal[5] = 7 if self.value else 1
        pal[2] = 7 if self.value else 6

        for loc in self.tile_locations:
            self._workspace.tilegrid.pixel_shader[loc] = pal

        if self._overlay_tile is not None and self._overlay_tile != self.tile_locations[0]:
            self._workspace.overlay_tilegrid[self._overlay_tile] = EMPTY
        pal = list(range(COLOR_COUNT))
        pal[3] = 1
        pal[4] = 0
        if self.connector_number is not None:
            self._workspace.overlay_palette_mapper[self.tile_locations[0]] = pal
            self._workspace.overlay_tilegrid[self.tile_locations[0]] = 34 + self.connector_number
            self._overlay_tile = self.tile_locations[0]
        else:
            self._workspace.overlay_tilegrid[self.tile_locations[0]] = EMPTY
            self._overlay_tile = None

    def handle_click(self):
        """
        Cycle through available SignalTransmitter entities on the workspace
        """
        connector_outs = []
        inuse_connector_numbers = []
        for entity in self._workspace.entities:
            if isinstance(entity, SignalTransmitter):
                connector_outs.append(entity)
                inuse_connector_numbers.append(entity.connector_number)

        if len(inuse_connector_numbers) == 0:
            return

        inuse_connector_numbers.sort()
        if self.connector_number is None:
            self.connector_number = inuse_connector_numbers[0]
        else:
            if self.connector_number in inuse_connector_numbers:
                connector_index = inuse_connector_numbers.index(self.connector_number)
            else:
                connector_index = -1

            self.connector_number = \
                inuse_connector_numbers[(connector_index + 1) % max(len(connector_outs),1)]

        self.input_one = None
        for entity in connector_outs:
            if entity.connector_number == self.connector_number:
                self.input_one = entity

class SignalTransmitter(Entity):
    """
    Virtual Connector used to send signals from an entity to a Signal Receiver
    """

    def __init__(self, location, workspace, connector_number=None, add_to_workspace=True):
        self.type = "output"
        self.size = (1, 1)
        self._workspace = workspace
        self.location = location
        self._init_tile_locations()
        self.tiles = [31]
        self._input_one = None
        self._overlay_tile = None

        if connector_number is None:
            # Set the connection_number to the next value available
            if len(self._workspace.available_connectors) > 0:
                self.connector_number = self._workspace.available_connectors.pop(0)
            else:
                # Too many connectors, workspace shouldn't allow this to happen
                raise RuntimeError("Too many Signal Transmitters")
        else:
            self.connector_number = connector_number

        self._tap = None

        if add_to_workspace:
            self._workspace.add_entity(self)

    def _init_tile_locations(self):
        self.tile_locations = (self.location,)
        # Location of the entity connected to the left of the Signal Transmitter in x,y tile coords
        self.input_entity_location = (self.location[X] - 1, self.location[Y])

    def update(self):
        """
        Run logic simulation for this entity
        """
        # if no input entity
        if self.input_entity is None:
            self.input_one = None
            self.apply_state_palette_mapping()
            return

        # update logic value based on entity value
        self.input_one = self.input_entity
        self.apply_state_palette_mapping()

    @property
    def input_entity(self):
        """Entity at the input location"""
        # Only recieve input from output wire on larger gates
        if self._workspace.entity_at(self.input_entity_location) == \
            self._workspace.entity_at((self.location[X], self.location[Y] - 1)) or \
            self._workspace.entity_at(self.input_entity_location) == \
            self._workspace.entity_at((self.location[X], self.location[Y] + 1)):

            # If entity to left is also above or below us then we're not connected to it's output
            return None

        return self._workspace.entity_at(self.input_entity_location)

    @property
    def palette_mapping(self):
        """The palette mapping for the current state. Used for
        setting the appropriate color on the input and output lines."""
        pal = list(range(COLOR_COUNT))
        if self.input_one is not None:
            pal[2] = 7 if self.input_one.value else 6
            pal[5] = 7 if self.input_one.value else 1
        else:
            pal[2] = 6
            pal[5] = 1

        return pal

    def apply_state_palette_mapping(self):
        cur_state_palette = self.palette_mapping
        for loc in self.tile_locations:
            self._workspace.tilegrid.pixel_shader[loc] = cur_state_palette

        if self._tap is not None and self._tap != self.input_entity_location:
            self._workspace.overlay_tilegrid[self._tap] = EMPTY
        if self._overlay_tile is not None and self._overlay_tile != self.tile_locations[0]:
            self._workspace.overlay_tilegrid[self._overlay_tile] = EMPTY
        pal = list(range(COLOR_COUNT))

        if isinstance(self.input_entity,Wire):
            pal[3] = 7 if self.input_one.value else 1
            self._workspace.overlay_palette_mapper[self.input_entity_location] = pal
            self._workspace.overlay_tilegrid[self.input_entity_location] = 33
            self._tap = self.input_entity_location
        else:
            self._tap = None

        if self.connector_number is not None:
            pal[3] = 0
            pal[4] = 1
            self._workspace.overlay_palette_mapper[self.tile_locations[0]] = pal
            self._workspace.overlay_tilegrid[self.tile_locations[0]] = 34 + self.connector_number
            self._overlay_tile = self.tile_locations[0]
        else:
            self._overlay_tile = None

    @property
    def input_one(self):
        """Entity at input one"""
        self._input_one = self.input_entity
        return self._input_one

    @input_one.setter
    def input_one(self, value):
        self._input_one = value
        self.apply_state_palette_mapping()

    @property
    def value(self):
        # Output panel does not have a logic output value
        return False

class Wire(Entity):
    """
    Wire used to connect entities together
    """

    STATES = [
        "left_right",
        "up_down",
        "up_right",
        "down_left",
        "up_left",
        "down_right",
        # unused states
        # "left_up_right",
        # "left_down_right",
        # "left_up_down",
        # "right_up_down"
    ]

    # sprite sheet tile indexes matching states from STATES list
    TILE_INDEXES = [19, 9, 1, 0, 17, 32]

    def __init__(self, location, workspace, state=None, add_to_workspace=True):
        self._recursion_guard = False
        self.type = "wire"
        self.size = (1, 1)
        self._workspace = workspace
        self._state = None
        self.tiles = [19]
        if state is None:
            guessed_state = self.guess_appropriate_state(location)
            self.state = guessed_state
        else:
            self.state = state
        self.location = location

        self._output = False

        if add_to_workspace:
            self._workspace.add_entity(self)

        # whether to keep the existing state after
        # being placed on the workspace.
        self.keep_state_after_drop = False

    def update(self):
        _ = self.value
        self._recursion_guard = False

    @property
    def state(self):
        """The index of the current state of the Wire. Different states
        represent connections on different sides."""
        return self._state

    @state.setter
    def state(self, value):
        self._state = value
        self._init_tile_locations()
        self.tiles[0] = self.TILE_INDEXES[self.state]
        try:
            self._workspace.remove_entity(self)
            self._workspace.add_entity(self)
        except ValueError:
            # This Wire entity was not on the Workspace
            pass

    def guess_appropriate_state(self, location):
        """
        Try to guess the appropriate state to use for the Wire based
        on the surrounding entities.

        :param location: The location to check around
        :return int: the index of the guessed most appropriate state
        """
        entity_above = (
            self._workspace.entity_at((location[0], location[1] - 1)) is not None
        )
        entity_left = (
            self._workspace.entity_at((location[0] - 1, location[1])) is not None
        )
        entity_below = (
            self._workspace.entity_at((location[0], location[1] + 1)) is not None
        )
        entity_right = (
            self._workspace.entity_at((location[0] + 1, location[1])) is not None
        )

        ret_val = 0
        if entity_left and entity_right:
            ret_val = 0
        elif entity_above and entity_below:
            ret_val = 1
        elif entity_above and entity_right:
            ret_val = 2
        elif entity_below and entity_left:
            ret_val = 3
        elif entity_above and entity_left:
            ret_val = 4
        elif entity_below and entity_right:
            ret_val = 5

        return ret_val

    def handle_click(self):
        """
        Change the state of the Wire cycling between all possible states.
        """
        if self.state < 5:
            self.state += 1
        else:
            self.state = 0

    def _init_tile_locations(self):
        self.tile_locations = (self.location,)

    @property
    def palette_mapping(self):
        """
        Dynamic palette mapping list of colors based on the current state
        """
        pal = list(range(COLOR_COUNT))
        pal[3] = 7 if self._output else 1
        return pal

    def apply_state_palette_mapping(self):
        cur_state_palette = self.palette_mapping
        for loc in self.tile_locations:
            self._workspace.tilegrid.pixel_shader[loc] = cur_state_palette

    def find_neighboring_wire_end(self, direction, wire_segments=None):
        """
        Find the end of the wire segment in the given direction.

        :param direction: Direction to search in ("left", "right", "up", "down")
        :return: tuple of (end entity, list of wire segments in this direction)
        """
        if wire_segments is None:
            wire_segments = []

        # exit recursion if we have already visited this wire segment
        if self in wire_segments:
            return (None, wire_segments)

        wire_segments.append(self)
        current_location = self.location

        if direction == "left":
            opposite = "right"
            next_location = (current_location[X] - 1, current_location[Y])
        elif direction == "right":
            opposite = "left"
            next_location = (current_location[X] + 1, current_location[Y])
        elif direction == "up":
            opposite = "down"
            next_location = (current_location[X], current_location[Y] - 1)
        elif direction == "down":
            opposite = "up"
            next_location = (current_location[X], current_location[Y] + 1)

        neighbor_entity = self._workspace.entity_at(next_location)

        if neighbor_entity is not None:
            if neighbor_entity.type == "wire":
                if opposite in self.STATES[neighbor_entity.state]:
                    # wire is properly connected to another wire segment, follow it
                    neighbor_state = self.STATES[neighbor_entity.state].split('_')
                    neighbor_direction = neighbor_state[1-neighbor_state.index(opposite)]
                    return neighbor_entity.find_neighboring_wire_end(neighbor_direction, wire_segments)
            elif direction == "left" and neighbor_entity.type in ("input", "gate"):
                # Only recieve input from output wire on larger gates
                if self._workspace.entity_at(next_location) != \
                    self._workspace.entity_at((current_location[X], current_location[Y] - 1)) and \
                    self._workspace.entity_at(next_location) != \
                    self._workspace.entity_at((current_location[X], current_location[Y] + 1)):

                    # wire is properly connected to an entity that supplies a value
                    return(neighbor_entity, wire_segments)

        # no wire or input entity found, or not properly connected
        return (None, wire_segments)

    @property
    def output(self):
        return self._output

    @output.setter
    def output(self, value):
        self._output = value

    @property
    def recursion_guard(self):
        return self._recursion_guard

    @recursion_guard.setter
    def recursion_guard(self, value):
        self._recursion_guard = value

    @property
    def value(self):

        if self._recursion_guard:
            if self._output is None:
                self._output = False
            self.apply_state_palette_mapping()
            return self._output

        self._recursion_guard = True

        # traverse connected wire segments to find input entities and map entire wire
        wires = []
        wire_value = False
        # only check for entities connected to the two sides defined by the state
        for direction in self.STATES[self.state].split('_'):
            end_entity, wire_seg = self.find_neighboring_wire_end(direction,[])
            wires.append(wire_seg)

            # Set wire value to the value of the input entity found at the end of the wire segment
            if end_entity is not None and end_entity.type in ("input", "gate"):
                wire_value = end_entity.value

        # Set the output of all the line segments to the value of the input entity
        for seg in wires[0]+wires[1]:
            if seg is not self:
                seg.output = wire_value
                # _recursion_guard is now being used as a sort of "dirty" flag to improve performance
                seg.recursion_guard = True
                seg.apply_state_palette_mapping()

        self._output = wire_value
        self.apply_state_palette_mapping()
        return self._output

class TwoInputOneOutputGate(Entity):
    """
    Super class for all Gate objects that have two inputs and one output.
    Implements function and logics that are shared between the different types of Gates.
    """

    _input_one = None
    _input_two = None
    _output = None

    size = (2, 3)
    """Size in tiles of the rectangle that contains the entity.
    Note that some tiles with this maybe unused."""

    input_one_entity_location = None
    """location of input entity one in x,y tile coordinates"""

    input_two_entity_location = None
    """location of input entity two in x,y tile coordinates"""

    _inputs_left = True
    """Whether the inputs are to the left (True), or top/bottom (False)"""
    def __init__(self):
        self._recursion_guard = False
        self.type = "gate"

        self._input_one = False
        self._input_two = False
        self._output = False

    @property
    def output(self) -> bool:
        """Value of the output"""
        return self._output

    @property
    def input_one_entity(self) -> Optional[Entity]:
        """Entity connected to input one"""
        return self._workspace.entity_at(self.input_one_entity_location)

    @property
    def input_two_entity(self) -> Entity:
        """Entity connected to input two"""
        return self._workspace.entity_at(self.input_two_entity_location)

    @property
    def input_one(self) -> bool:
        """Logic value of input one"""
        return self._input_one

    @property
    def input_two(self):
        """Logic value of input one"""
        return self._input_two

    @input_one.setter
    def input_one(self, value):
        raise NotImplementedError()

    @input_two.setter
    def input_two(self, value):
        raise NotImplementedError()

    @property
    def value(self):
        """Calculate the output logic value of this gate. Will call
        value property on input entities."""
        if self._recursion_guard:
            self._recursion_guard = False
            return self.output

        self._recursion_guard = True
        input_one_entity = self.input_one_entity
        input_two_entity = self.input_two_entity

        # print(f"Gate.value input_one_entity: {input_one_entity}, input_two_entity: {input_two_entity}")

        if input_one_entity is None:
            self.input_one = False
        else:
            self.input_one = input_one_entity.value

        if input_two_entity is None:
            self.input_two = False
        else:
            self.input_two = input_two_entity.value

        self._recursion_guard = False
        return self.output

    def handle_click(self):
        """Toggle between inputs left and inputs above/below"""
        self.inputs_left = not self._inputs_left

    @property
    def inputs_left(self):
        """True if inputs are to the left, False if they are above and below"""
        return self._inputs_left

    @inputs_left.setter
    def inputs_left(self, value):
        self._inputs_left = value
        if self._inputs_left:
            self.input_one_entity_location = (self.location[X] - 1, self.location[Y])
            self.input_two_entity_location = (
                self.location[X] - 1,
                self.location[Y] + 2,
            )
            self.tiles[0] = 0
            self.tiles[3] = 20
        else:
            self.input_one_entity_location = (self.location[X], self.location[Y] - 1)
            self.input_two_entity_location = (self.location[X], self.location[Y] + 3)
            self.tiles[0] = 9
            self.tiles[3] = 28

        try:
            self._workspace.remove_entity(self)
            self._workspace.add_entity(self)
        except ValueError:
            # was not in entities list
            pass

    def _init_tile_locations(self):
        self.tile_locations = (
            self.location,
            (self.location[X], self.location[Y] + 1),
            (self.location[X] + 1, self.location[Y] + 1),
            (self.location[X], self.location[Y] + 2),
        )

        self.input_one_entity_location = (self.location[X] - 1, self.location[Y])
        self.input_two_entity_location = (self.location[X] - 1, self.location[Y] + 2)

    @property
    def palette_mapping(self):
        """The palette mapping for the current state. Used for
        setting the appropriate color on the input and output lines."""
        pal = list(range(COLOR_COUNT))
        pal[3] = 7 if self.input_one else 1
        pal[4] = 7 if self.input_two else 1
        pal[5] = 7 if self.output else 1
        return pal

    def apply_state_palette_mapping(self):
        """
        Apply the current palette mapping to all tiles used by this Gate.
        """
        cur_state_palette = self.palette_mapping

        for loc in self.tile_locations:
            self._workspace.tilegrid.pixel_shader[loc] = cur_state_palette


class AndGate(TwoInputOneOutputGate):
    """AndGate - When both inputs are True the output will be True, otherwise False."""

    def __init__(self, location, workspace, add_to_workspace=True):
        super().__init__()

        self._workspace = workspace
        self.location = location

        self._init_tile_locations()

        self.tiles = [0, 10, 11, 20]

        if add_to_workspace:
            self._workspace.add_entity(self)

    @TwoInputOneOutputGate.input_one.setter
    def input_one(self, value):
        self._input_one = value
        self._output = self._input_one and self._input_two
        self.apply_state_palette_mapping()

    @TwoInputOneOutputGate.input_two.setter
    def input_two(self, value):
        self._input_two = value
        self._output = self._input_one and self._input_two
        self.apply_state_palette_mapping()


class NandGate(TwoInputOneOutputGate):
    """NandGate - When at least one input is False the output will be True, otherwise False."""

    def __init__(self, location, workspace, add_to_workspace=True):
        super().__init__()

        self._workspace = workspace
        self.location = location

        self._init_tile_locations()

        self.tiles = [0, 14, 15, 20]

        if add_to_workspace:
            self._workspace.add_entity(self)

    @TwoInputOneOutputGate.input_one.setter
    def input_one(self, value):
        self._input_one = value
        self._output = not self._input_one or not self._input_two
        self.apply_state_palette_mapping()

    @TwoInputOneOutputGate.input_two.setter
    def input_two(self, value):
        self._input_two = value
        self._output = not self._input_one or not self._input_two
        self.apply_state_palette_mapping()


class OrGate(TwoInputOneOutputGate):
    """OrGate - When either input is True the output will be True, otherwise False."""

    def __init__(self, location, workspace, add_to_workspace=True):
        super().__init__()

        self._workspace = workspace
        self.location = location

        self._init_tile_locations()

        self.tiles = [0, 12, 13, 20]

        if add_to_workspace:
            self._workspace.add_entity(self)

    @TwoInputOneOutputGate.input_one.setter
    def input_one(self, value):
        self._input_one = value
        self._output = self._input_one or self._input_two
        self.apply_state_palette_mapping()

    @TwoInputOneOutputGate.input_two.setter
    def input_two(self, value):
        self._input_two = value
        self._output = self._input_one or self._input_two
        self.apply_state_palette_mapping()


class NorGate(TwoInputOneOutputGate):
    """NorGate - When both inputs are False the output will be True, otherwise False."""

    def __init__(self, location, workspace, add_to_workspace=True):
        super().__init__()

        self._workspace = workspace
        self.location = location

        self._init_tile_locations()

        self.tiles = [0, 6, 7, 20]

        if add_to_workspace:
            self._workspace.add_entity(self)

    @TwoInputOneOutputGate.input_one.setter
    def input_one(self, value):
        self._input_one = value
        self._output = not self._input_one and not self._input_two
        self.apply_state_palette_mapping()

    @TwoInputOneOutputGate.input_two.setter
    def input_two(self, value):
        self._input_two = value
        self._output = not self._input_one and not self._input_two
        self.apply_state_palette_mapping()


class XorGate(TwoInputOneOutputGate):
    """XorGate - When one input is True and the other input is False the output will be True, otherwise False."""

    def __init__(self, location, workspace, add_to_workspace=True):
        super().__init__()

        self._workspace = workspace
        self.location = location

        self._init_tile_locations()

        self.tiles = [0, 4, 5, 20]

        if add_to_workspace:
            self._workspace.add_entity(self)

    @TwoInputOneOutputGate.input_one.setter
    def input_one(self, value):
        self._input_one = value
        self._output = False
        if self._input_one and not self._input_two:
            self._output = True
        if not self._input_one and self._input_two:
            self._output = True
        self.apply_state_palette_mapping()

    @TwoInputOneOutputGate.input_two.setter
    def input_two(self, value):
        self._input_two = value
        self._output = False
        if self._input_one and not self._input_two:
            self._output = True
        if not self._input_one and self._input_two:
            self._output = True
        self.apply_state_palette_mapping()


class XnorGate(TwoInputOneOutputGate):
    """XNOR Gate - When both inputs are True, or both inputs are False the output will be True, otherwise False"""

    def __init__(self, location, workspace, add_to_workspace=True):
        super().__init__()

        self._workspace = workspace
        self.location = location

        self._init_tile_locations()

        self.tiles = [0, 24, 25, 20]

        if add_to_workspace:
            self._workspace.add_entity(self)

    @TwoInputOneOutputGate.input_one.setter
    def input_one(self, value):
        self._input_one = value
        self._output = False
        if self._input_one and self._input_two:
            self._output = True
        if not self._input_one and not self._input_two:
            self._output = True
        self.apply_state_palette_mapping()

    @TwoInputOneOutputGate.input_two.setter
    def input_two(self, value):
        self._input_two = value
        self._output = False
        if self._input_one and self._input_two:
            self._output = True
        if not self._input_one and not self._input_two:
            self._output = True
        self.apply_state_palette_mapping()


class NotGate(Entity):
    """NOT Gate - When the input is False the output will be True, otherwise False."""

    def __init__(self, location, workspace, add_to_workspace=True):
        self._recursion_guard = False

        self.type = "gate"

        self._workspace = workspace
        self.location = location

        self.tiles = [22]

        self._input_one = False
        self._output = True

        if add_to_workspace:
            self._workspace.add_entity(self)

    @property
    def input_one(self):
        return self._input_one

    @input_one.setter
    def input_one(self, value):
        self._input_one = value
        self._output = not self._input_one
        self.apply_state_palette_mapping()

    @property
    def output(self):
        return self._output

    def apply_state_palette_mapping(self):
        pal = list(range(COLOR_COUNT))
        pal[4] = 7 if self.input_one else 1
        pal[5] = 7 if self.output else 1

        for loc in self.tile_locations:
            self._workspace.tilegrid.pixel_shader[loc] = pal

    @property
    def input_one_entity(self):
        return self._workspace.entity_at(self.input_one_entity_location)

    @property
    def value(self):
        if self._recursion_guard:
            self._recursion_guard = False
            return self.output

        self._recursion_guard = True
        input_one_entity = self.input_one_entity

        if input_one_entity is not None:
            self.input_one = input_one_entity.value
        else:
            self.input_one = False

        self._recursion_guard = False
        return self.output

    def _init_tile_locations(self):
        self.tile_locations = (self.location,)
        self.input_one_entity_location = (self.location[X] - 1, self.location[Y])


class NeoPixelOutput(Entity):
    """
    NeoPixelOutput with 3 inputs that correspond to red, green, and blue.
    Connected to physical NeoPixels on the Fruit Jam.
    """

    _input_red = None
    _input_green = None
    _input_blue = None

    size = (1, 3)

    input_one_entity_location = None
    """location of input entity one in x,y tile coordinates"""

    input_two_entity_location = None
    """location of input entity two in x,y tile coordinates"""

    input_three_entity_location = None
    """location of input entity two in x,y tile coordinates"""

    def __init__(self, location, workspace, neopixel_obj, add_to_workspace=True):
        self.type = "output"
        self.neopixels = neopixel_obj
        self.tiles = [0, 16, 20]
        self._workspace = workspace
        self.location = location
        self._init_tile_locations()
        self._inputs_left = False

        if add_to_workspace:
            self._workspace.add_entity(self)

    @property
    def input_one_entity(self) -> Optional[Entity]:
        """Entity connected to input one"""
        return self._workspace.entity_at(self.input_one_entity_location)

    @property
    def input_two_entity(self) -> Entity:
        """Entity connected to input two"""
        return self._workspace.entity_at(self.input_two_entity_location)

    @property
    def input_three_entity(self) -> Entity:
        """Entity connected to input two"""
        return self._workspace.entity_at(self.input_three_entity_location)

    @property
    def input_one(self) -> bool:
        """Logic value of input one"""
        return self._input_red

    @property
    def input_two(self):
        """Logic value of input one"""
        return self._input_green

    @property
    def input_three(self):
        """Logic value of input one"""
        return self._input_blue

    @input_one.setter
    def input_one(self, value):
        self._input_red = value

    @input_two.setter
    def input_two(self, value):
        self._input_green = value

    @input_three.setter
    def input_three(self, value):
        self._input_blue = value

    def _init_tile_locations(self):
        self.tile_locations = (
            self.location,
            (self.location[X], self.location[Y] + 1),
            (self.location[X], self.location[Y] + 2),
        )

        self.input_one_entity_location = (self.location[X] - 1, self.location[Y])
        self.input_two_entity_location = (self.location[X] - 1, self.location[Y] + 1)
        self.input_three_entity_location = (self.location[X] - 1, self.location[Y] + 2)

    def handle_click(self):
        """Toggle between inputs left and inputs above/below"""
        self.inputs_left = not self._inputs_left

    @property
    def inputs_left(self):
        """True if the inputs are to the left, False if they are above and below"""
        return self._inputs_left

    @inputs_left.setter
    def inputs_left(self, value):
        self._inputs_left = value
        if self._inputs_left:
            self.input_one_entity_location = (self.location[X] - 1, self.location[Y])
            self.input_three_entity_location = (
                self.location[X] - 1,
                self.location[Y] + 2,
            )
            self.tiles[0] = 0
            self.tiles[2] = 20
        else:
            self.input_one_entity_location = (self.location[X], self.location[Y] - 1)
            self.input_three_entity_location = (self.location[X], self.location[Y] + 3)
            self.tiles[0] = 9
            self.tiles[2] = 28
        self._workspace.remove_entity(self)
        self._workspace.add_entity(self)

    @property
    def palette_mapping(self):
        """The palette mapping for the current state. Used for
        setting the appropriate color on the input and output lines."""
        pal = list(range(COLOR_COUNT))
        pal[3] = 7 if self.input_one else 1
        pal[4] = 7 if self.input_two else 1
        pal[5] = 7 if self.input_three else 1
        return pal

    @property
    def value(self):
        return False

    def apply_state_palette_mapping(self):
        """
        Apply the current palette mapping to all tiles used by this Gate.
        """
        cur_state_palette = self.palette_mapping

        # top and middle tile behave 'normally'
        for loc in self.tile_locations[:-1]:
            self._workspace.tilegrid.pixel_shader[loc] = cur_state_palette

        # bottom tile different behavior because extension wire
        # is using palette index that is typically for input two,
        # but on this object the same index is used for input two and
        # input three.
        pal = list(range(COLOR_COUNT))
        pal[4] = 7 if self.input_three else 1
        self._workspace.tilegrid.pixel_shader[self.tile_locations[-1]] = pal

    def update(self):
        """Run the logic simulation with the current state of the inputs.
        Update physical NeoPixels based on logic values of inputs."""
        input_one_entity = self.input_one_entity
        input_two_entity = self.input_two_entity
        input_three_entity = self.input_three_entity

        if input_one_entity is not None:
            self.input_one = input_one_entity.value
        else:
            self.input_one = False

        if input_two_entity is not None:
            self.input_two = input_two_entity.value
        else:
            self.input_two = False

        if input_three_entity is not None:
            self.input_three = input_three_entity.value
        else:
            self.input_three = False

        self.neopixels.fill(
            (
                255 if self.input_one else 0,
                255 if self.input_two else 0,
                255 if self.input_three else 0,
            )
        )
        self.apply_state_palette_mapping()
