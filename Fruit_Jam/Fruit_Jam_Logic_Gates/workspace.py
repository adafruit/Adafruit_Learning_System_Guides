# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import json
import time

import adafruit_imageload
from displayio import TileGrid, OnDiskBitmap, Palette, Group, Bitmap
from tilepalettemapper import TilePaletteMapper
from terminalio import FONT

from adafruit_anchored_group import AnchoredGroup
from adafruit_display_text.text_box import TextBox
from adafruit_display_text.bitmap_label import Label
from adafruit_displayio_layout.layouts.grid_layout import GridLayout

from entity import (
    TwoInputOneOutputGate,
    AndGate,
    OrGate,
    NandGate,
    NorGate,
    NotGate,
    XorGate,
    XnorGate,
    VirtualPushButton,
    OutputPanel,
    NeoPixelOutput,
    PhysicalButton,
    Wire,
    ConnectorIn,
    ConnectorOut,
)

# pylint: disable=too-many-branches, too-many-statements

VALID_SAVE_SLOTS = tuple("0123456789")

DEFAULT_HOTKEYS = {
    b"\x1b[A": "scroll_up",  # up arrow
    b"\x1b[B": "scroll_down",  # down arrow
    b"\x1b[C": "scroll_right",  # right arrow
    b"\x1b[D": "scroll_left",  # left arrow
    b"q": "eyedropper",
    b"s": "save",
    b"o": "open",
    b"a": "add",
    b"\x08": "remove",  # backspace
    b"\x1b[3~": "remove",  # delete
}

# index of empty tile in the spritesheet
EMPTY = 8

# map class names to constructor functions
ENTITY_CLASS_CONSTRUCTOR_MAP = {
    "AndGate": AndGate,
    "OrGate": OrGate,
    "NandGate": NandGate,
    "NorGate": NorGate,
    "XorGate": XorGate,
    "XnorGate": XnorGate,
    "NotGate": NotGate,
    "Wire": Wire,
    "ConnectorIn": ConnectorIn,
    "ConnectorOut": ConnectorOut,
    "OutputPanel": OutputPanel,
    "VirtualPushButton": VirtualPushButton,
    "PhysicalButton": PhysicalButton,
    "NeoPixelOutput": NeoPixelOutput,
}

# maximum number of connectors allowed on workspace
MAX_CONNECTORS = 5

class Workspace:
    """
    A scrollable area to place logic gates and other Entities. Handles interactions with the user
    via mouse and keyboard event functions. Contains a Toolbox for selecting new parts to be
    added to the workspace.

    :param neopixels: NeoPixel object used with NeoPixelOutput entities
    :param buttons: Tuple containing DigitalInOut instances connected to the 3
      physical buttons on the Fruit Jam.
    :param hotkeys: Optional hotkeys dictionary to override the defaults.
    """

    def __init__(self, neopixels, buttons, hotkeys=None):
        # store hardware peripheral references
        self.neopixels = neopixels
        self.buttons = buttons

        # load default hotkeys if user has not supplied custom ones.
        self.hotkeys = DEFAULT_HOTKEYS if hotkeys is None else hotkeys

        # load the spritesheet bitmap
        self.spritesheet, palette = adafruit_imageload.load(
            "logic_gates_assets/sprites.bmp"
        )
        self.spritesheet_pixel_shader = palette

        # setup TilePaletteMapper
        self.tile_palette_mapper = TilePaletteMapper(
            self.spritesheet_pixel_shader,  # input pixel_shader
            len(self.spritesheet_pixel_shader),  # input color count
        )

        # setup main workspace TileGrid
        self.tilegrid = TileGrid(
            bitmap=self.spritesheet,
            pixel_shader=self.tile_palette_mapper,
            default_tile=EMPTY,
            width=26,
            height=18,
            tile_width=24,
            tile_height=24,
        )

        # setup group to hold all visual elements
        self.group = Group()
        self.group.append(self.tilegrid)

        # setup overlay elements that float on top of the workspace
        self.overlay_palette = Palette(18)
        for i, color in enumerate(self.spritesheet_pixel_shader):
            self.overlay_palette[i] = color
        self.overlay_palette.make_transparent(0)

        # setup Overlay TilePaletteMapper
        self.overlay_palette_mapper = TilePaletteMapper(
            self.overlay_palette,  # input pixel_shader
            len(self.overlay_palette),  # input color count
        )

        # setup overlay TileGrid
        self.overlay_tilegrid = TileGrid(
            bitmap=self.spritesheet,
            pixel_shader=self.overlay_palette_mapper,
            default_tile=EMPTY,
            width=26,
            height=18,
            tile_width=24,
            tile_height=24)

        self.group.append(self.overlay_tilegrid)

        # setup add entity button bitmap and TileGrid
        self.add_btn_bmp = OnDiskBitmap("logic_gates_assets/add_btn.bmp")
        self.add_btn_tg = TileGrid(
            bitmap=self.add_btn_bmp, pixel_shader=self.add_btn_bmp.pixel_shader
        )
        self.group.append(self.add_btn_tg)

        # setup message label, empty for now, used to get input or give feedback to user
        self.message_lbl = Label(FONT, text="")
        self.message_lbl.anchor_point = (0, 0)
        self.message_lbl.anchored_position = (
            self.add_btn_tg.x + self.add_btn_tg.tile_width + 2,
            2,
        )
        self.group.append(self.message_lbl)

        # Setup moving entity graphics used when an entity is following the mouse
        # waiting to be placed on the workspace
        self.mouse_moving_palette = Palette(len(self.spritesheet_pixel_shader))
        for i, color in enumerate(self.spritesheet_pixel_shader):
            self.mouse_moving_palette[i] = color
        self.mouse_moving_palette.make_transparent(0)
        self.mouse_moving_palette[3] = 0x000000
        self.mouse_moving_palette[4] = 0x000000
        self.mouse_moving_palette[5] = 0x000000
        self.mouse_moving_tg = TileGrid(
            bitmap=self.spritesheet,
            pixel_shader=self.mouse_moving_palette,
            width=2,
            height=3,
            default_tile=EMPTY,
            tile_width=24,
            tile_height=24,
        )
        self.mouse_moving_tg.hidden = True

        # list to hold all Entities on the workspace
        self.entities = []

        # list to hold available connectors
        self.available_connectors = list(range(MAX_CONNECTORS))

        # variable to hold an Entity that is moving with the mouse
        self.moving_entity = None

        # workspace scroll offsets
        self._scroll_x = 0
        self._scroll_y = 0

        # setup ToolBox for selecting entities to add
        self.toolbox = ToolBox(self.spritesheet, self)
        self.group.append(self.toolbox.group)

        # variables for message control
        self.waiting_for_save_slot_input = False
        self.waiting_for_open_slot_input = False
        self.hide_message_at = None

    def add_entity(self, entity):
        """
        Add the given entity to the workspace at the location specified by entity.location.
        Setting the appropriate tile sprites.
        """
        self.entities.append(entity)
        for i in range(len(entity.tiles)):
            self.tilegrid[entity.tile_locations[i]] = entity.tiles[i]
        entity.apply_state_palette_mapping()

    def remove_entity(self, entity):
        """
        Remove the given entity from the workspace.
        """
        self.entities.remove(entity)
        for i in range(len(entity.tiles)):
            self.tilegrid[entity.tile_locations[i]] = EMPTY
            self.overlay_tilegrid[entity.tile_locations[i]] = EMPTY

        # Special case for ConnectorOut to clear its input wire tap overlay
        if isinstance(entity, ConnectorOut):
            if isinstance(entity.input_entity,Wire):
                self.overlay_tilegrid[entity.input_entity_location] = EMPTY

    def _set_mouse_moving_tiles(self, entity):
        """
        Set the sprite tiles on the mouse moving TileGrid based on the given entity.
        """
        for i in range(self.mouse_moving_tg.width * self.mouse_moving_tg.height):
            self.mouse_moving_tg[i] = EMPTY

        midpoint_offset = 1 if entity.size[1] == 1 else 0

        for i, loc in enumerate(entity.tile_locations):
            self.mouse_moving_tg[
                loc[0] - entity.location[0],
                loc[1] - entity.location[1] + midpoint_offset,
            ] = entity.tiles[i]

    def handle_mouse_click(self, screen_x, screen_y, pressed_btns):
        """
        Handle mouse click events sent from code.py
        """

        # hand add button click & Toolbox outside of scroll logic
        # since it floats on top and is unaffected by scroll.
        if "left" in pressed_btns:
            # if the toolbox is visible let it handle the click event.
            if not self.toolbox.hidden:
                self.toolbox.handle_mouse_click((screen_x, screen_y))
                return

            # if the click is on the add button
            if self.add_btn_tg.contains((screen_x, screen_y, 0)):
                # if there is no entity on the mouse, open the ToolBox
                if self.moving_entity is None:
                    self.toolbox.hidden = False

                # if there is an entity on the mouse, remove it
                else:
                    self.moving_entity = None
                    self.mouse_moving_tg.hidden = True
                return

        # apply offset value based on scroll position
        screen_x -= self._scroll_x * self.tilegrid.tile_width * 1
        screen_y -= self._scroll_y * self.tilegrid.tile_height * 1

        # calculate tile coordinates
        tile_x = screen_x // self.tilegrid.tile_width
        tile_y = screen_y // self.tilegrid.tile_height

        # get the entity at the coordinates if there is one
        clicked_entity = self.entity_at((tile_x, tile_y))

        # handle left click
        if "left" in pressed_btns:
            # if there is an entity moving with the mouse
            if self.moving_entity is not None:

                # set the entities location to the clicked coordinates
                if isinstance(
                    self.moving_entity, (TwoInputOneOutputGate, NeoPixelOutput)
                ):
                    self.moving_entity.location = (tile_x, tile_y - 1)
                else:
                    self.moving_entity.location = (tile_x, tile_y)

                # Ignore the click if the landing space is occupied
                if self.landing_zone_clear(self.moving_entity):
                    # for Wires, guess the appropriate state if the flag to keep state is not set
                    if (
                        isinstance(self.moving_entity, Wire)
                        and not self.moving_entity.keep_state_after_drop
                    ):
                        self.moving_entity.state = (
                            self.moving_entity.guess_appropriate_state(
                                self.moving_entity.location
                            )
                        )

                    # add the entity at the clicked coordinates
                    self.add_entity(self.moving_entity)
                    # run the logic simulation with the new entity in it
                    self.update()
                    # remove the moving entity from the mouse
                    self.moving_entity = None
                    self.mouse_moving_tg.hidden = True
                return

            # ignore left click on empty space
            if clicked_entity is None:
                return

            # if the entity has a handle_click() function call
            # it to allow entity to handle the click event
            if hasattr(clicked_entity, "handle_click"):
                clicked_entity.handle_click()
                # update the logic simulation after click has been handled
                self.update()

        # handle right click event
        elif "right" in pressed_btns:
            # if there is not a moving entity following the mouse
            if self.moving_entity is None:
                # if the click was on empty space do nothing
                if clicked_entity is None:
                    return

                # remove the entity from the workspace and set it
                # as the moving entity following the mouse
                self.moving_entity = clicked_entity
                self._set_mouse_moving_tiles(self.moving_entity)
                self.mouse_moving_tg.hidden = False
                self.remove_entity(self.moving_entity)

                # for Wires keep the existing state when they're dropped
                if isinstance(self.moving_entity, Wire):
                    self.moving_entity.keep_state_after_drop = True

    def handle_key_press(self, key_bytes, mouse_x, mouse_y):
        """
        Handle keyboard key press events sent from code.py.
        Also receives the current mouse location.
        """

        # if we're waiting for user to input the save slot number
        if self.waiting_for_save_slot_input:
            # convert keypress to string
            key_str = key_bytes.decode("utf-8")
            # if the entered value is a valid save slot 0-9
            if key_str in VALID_SAVE_SLOTS:
                # update the message to the user with the value they typed
                self.message_lbl.text += key_str
                # get the JSON data to save
                save_data = self.json()
                # write JSON data to the save file with slot number in filename
                with open(f"/saves/logic_gates_{key_str}.json", "w") as f:
                    f.write(save_data)
                    # update the message to user with save success
                    self.message_lbl.text = f"Saved in slot: {key_str}"
                    # set the time to hide the message to user
                    self.hide_message_at = time.monotonic() + 2.0
                # set flag back to not waiting for save slot input
                self.waiting_for_save_slot_input = False
            return

        # if we're waiting for user to input the open slot number
        if self.waiting_for_open_slot_input:
            # convert keypress to string
            key_str = key_bytes.decode("utf-8")
            # if the entered value is a valid save slot 0-9
            if key_str in VALID_SAVE_SLOTS:
                # try to open and read JSON data from the specified save slot file
                try:
                    with open(f"/saves/logic_gates_{key_str}.json", "r") as f:
                        save_data = json.loads(f.read())

                        # load the workspace state from the JSON data
                        self.load_from_json(save_data)
                        # update message to user with opened save slot success
                        self.message_lbl.text = f"Opened from slot: {key_str}"
                        # set the time to hide the user message
                        self.hide_message_at = time.monotonic() + 2.0
                except OSError:
                    # inform user no file was found at the entered save slot
                    self.message_lbl.text = f"No save in slot: {key_str}"
                    self.hide_message_at = time.monotonic() + 2.0
                self.waiting_for_open_slot_input = False
            return

        # lookup the pressed key int he hotkey map
        action = self.hotkeys.get(key_bytes, None)
        # if the pressed key doesn't map to any actions
        # just print its bytes for debugging.
        if action is None:
            print(key_bytes)
            return

        # scroll up
        if action == "scroll_up":
            self._scroll_y += 1
            self.apply_scroll()

        # scroll down
        elif action == "scroll_down":
            self._scroll_y -= 1
            self.apply_scroll()

        # scroll right
        elif action == "scroll_right":
            self._scroll_x -= 1
            self.apply_scroll()

        # scroll left
        elif action == "scroll_left":
            self._scroll_x += 1
            self.apply_scroll()

        # save action, ask user for the slot to save in
        elif action == "save":
            self.waiting_for_save_slot_input = True
            self.message_lbl.text = "Save Slot: "
            # keep message showing until user responds
            self.hide_message_at = None

        # open action, ask user for slot to open from
        elif action == "open":
            self.waiting_for_open_slot_input = True
            self.message_lbl.text = "Open Slot: "
            # keep message showing until user responds
            self.hide_message_at = None

        # add action, show the ToolBox to select a new entity to add
        elif action == "add":
            if self.moving_entity is None:
                self.toolbox.hidden = False

        # remove action, clear out the entity moving with the mouse
        elif action == "remove":
            if self.moving_entity is not None:
                # Speical ConnectorOut case, add connection_number back into available list
                if isinstance(self.moving_entity, ConnectorOut):
                    self.available_connectors.append(self.moving_entity.connector_number)
                    self.available_connectors.sort()
                    # Remove connections from all ConnectorIn entities pointing to this ConnectorOut
                    for entity in self.entities:
                        if isinstance(entity, ConnectorIn) and \
                            entity.connector_number == self.moving_entity.connector_number:

                            entity.connector_number = None
                            entity.input_one = None

                self.moving_entity = None
                self.mouse_moving_tg.hidden = True
                self.update()

        # eyedropper or pipette action
        elif action == "eyedropper":
            # if there is already an entity moving with the mouse
            if self.moving_entity is not None:
                # clear out the entity moving with the mouse
                # This was a "back door" delete of the object, better to just ignore
                # otherwise we need to add the ConnectorOut special case here as well
                #self.moving_entity = None
                #self.mouse_moving_tg.hidden = True
                return

            # adjust mouse coordinates for the scroll position
            mouse_x -= self._scroll_x * self.tilegrid.tile_width * 1
            mouse_y -= self._scroll_y * self.tilegrid.tile_height * 1

            # get the tile coordinates of mouse location
            tile_x = mouse_x // self.tilegrid.tile_width
            tile_y = mouse_y // self.tilegrid.tile_height

            # try to get the entity at the tile coordinates
            target_entity = self.entity_at((tile_x, tile_y))

            # special case only limited number of ConnectorOuts
            if target_entity is not None and isinstance(target_entity, ConnectorOut):
                num_ConnectorOuts = 0
                for entity in self.entities:
                    if isinstance(entity, ConnectorOut):
                        num_ConnectorOuts += 1
                if num_ConnectorOuts >= MAX_CONNECTORS:
                    # Can't create additional ConnectorOut
                    target_entity = None

            # if there was an entity at the coordinates
            if target_entity is not None:
                # set up an object to clone the entity at the coordinates
                clone_json = {
                    "class": target_entity.__class__.__name__,
                    "location": (0, 0),
                }
                # apply any possible attributes to the clone object
                if hasattr(target_entity, "state"):
                    clone_json["state"] = target_entity.state
                if hasattr(target_entity, "pressed_state"):
                    clone_json["pressed_state"] = target_entity.pressed_state
                if hasattr(target_entity, "index"):
                    clone_json["index"] = target_entity.index
                if hasattr(target_entity, "inputs_left"):
                    clone_json["inputs_left"] = target_entity.inputs_left

                # create an Entity from the clone object
                cloned_entity = self.create_entity_from_json(
                    clone_json, add_to_workspace=False
                )

                # set the newly created entity as the entity moving with mouse
                self.moving_entity = cloned_entity
                self._set_mouse_moving_tiles(cloned_entity)
                self.mouse_moving_tg.x = mouse_x - 12
                self.mouse_moving_tg.y = mouse_y - 24 - 12
                self.mouse_moving_tg.hidden = False

                # for Wires keep the existing state when they're dropped
                if isinstance(self.moving_entity, Wire):
                    self.moving_entity.keep_state_after_drop = True

    def landing_zone_clear(self, entity):
        """True if there are no entities in the space that would be occupied by the given entity"""
        for loc in entity.tile_locations:
            if self.entity_at(loc) is not None:
                return False
        return True

    def read_input(self):
        """
        Read input from the user stripping the prompt message
        """
        return self.message_lbl.text.replace("Save Slot: ", "").replace(
            "Open Slot: ", ""
        )

    def json(self):
        """
        Build and return a JSON object representing the current workspace state.
        """
        # loop over all entities and create serialized objects with their state
        save_obj = {"entities": []}
        for entity in self.entities:
            entity_obj = {
                "class": entity.__class__.__name__,
                "location": entity.location,
            }
            if hasattr(entity, "state"):
                entity_obj["state"] = entity.state
            if hasattr(entity, "pressed_state"):
                entity_obj["pressed_state"] = entity.pressed_state
            if hasattr(entity, "index"):
                entity_obj["index"] = entity.index
            if hasattr(entity, "inputs_left"):
                entity_obj["inputs_left"] = entity.inputs_left
            if hasattr(entity, "connector_number"):
                entity_obj["connector_number"] = entity.connector_number
            save_obj["entities"].append(entity_obj)
        return json.dumps(save_obj)

    def create_entity_from_json(self, entity_json, add_to_workspace=True):
        """
        Create an entity from a JSON object representing an entity state.
        """
        location = tuple(entity_json["location"])
        # special case NeoPixelOutput needs the NeoPixel object
        if entity_json["class"] == "NeoPixelOutput":
            new_entity = ENTITY_CLASS_CONSTRUCTOR_MAP[entity_json["class"]](
                location, self, self.neopixels, add_to_workspace=add_to_workspace
            )
        # special case PhysicalButton needs the button index
        elif entity_json["class"] == "PhysicalButton":
            new_entity = ENTITY_CLASS_CONSTRUCTOR_MAP[entity_json["class"]](
                location, self, entity_json["index"], add_to_workspace=add_to_workspace
            )
        # special case Wire needs the wire state number
        elif entity_json["class"] == "Wire":
            new_entity = ENTITY_CLASS_CONSTRUCTOR_MAP[entity_json["class"]](
                location, self, entity_json["state"], add_to_workspace=add_to_workspace
            )
        # special case Connectors need the connector number
        elif entity_json["class"] == "ConnectorIn" or entity_json["class"] == "ConnectorOut":
            if entity_json.get("connector_number") is not None:
                new_entity = ENTITY_CLASS_CONSTRUCTOR_MAP[entity_json["class"]](
                    location, self, entity_json["connector_number"],
                    add_to_workspace=add_to_workspace
                )
            else:
                new_entity = ENTITY_CLASS_CONSTRUCTOR_MAP[entity_json["class"]](
                    location, self, add_to_workspace=add_to_workspace
                )
        # default case all other entity types
        else:
            new_entity = ENTITY_CLASS_CONSTRUCTOR_MAP[entity_json["class"]](
                location, self, add_to_workspace=add_to_workspace
            )

        # if the entity has the inputs_left property then set it according to object
        if "inputs_left" in entity_json:
            new_entity.inputs_left = entity_json["inputs_left"]

        return new_entity

    def load_from_json(self, json_data):
        """
        Load the workspace state from a JSON object.
        """
        # reset list of available ConnectorOuts
        self.available_connectors = list(range(MAX_CONNECTORS))
        self.neopixels.fill(0)
        # clear out all sprites in the tilegrid
        for i in range(self.tilegrid.width * self.tilegrid.height):
            self.tilegrid[i] = EMPTY
            self.overlay_tilegrid[i] = EMPTY

        # clear out entities list
        self.entities.clear()

        # loop over entities in JSON object
        for entity_json in json_data["entities"]:
            # create current entity
            self.create_entity_from_json(entity_json)

        # Connect any connectors
        for entity in self.entities:
            if isinstance(entity,ConnectorOut):
                if entity.connector_number in self.available_connectors:
                    self.available_connectors.remove(entity.connector_number)
                for entity_in in self.entities:
                    if isinstance(entity_in,ConnectorIn) and \
                        entity_in.connector_number is not None and \
                        entity.connector_number == entity_in.connector_number:

                        entity_in.input_one = entity

        # update the logic simulation with all new entities
        self.update()

    def apply_scroll(self):
        """
        Move the main workspace TileGrid based on the current scroll position
        """
        self.tilegrid.x = self._scroll_x * self.tilegrid.tile_width * 1
        self.tilegrid.y = self._scroll_y * self.tilegrid.tile_height * 1

    def entity_at(self, location):
        """
        Get the Entity at the given location or None if there isn't one.
        """
        for entity in self.entities:
            if location in entity.tile_locations:
                return entity
        return None

    def update(self):
        """
        Run the logic simulation based on everything's current state.
        """

        # hide the message label if it's time to
        now = time.monotonic()
        if self.hide_message_at is not None and self.hide_message_at < now:
            self.hide_message_at = None
            self.message_lbl.text = ""

        # loop over all entities and update each one
        # with update() function or value property.
        for entity in self.entities:
            if hasattr(entity, "update"):
                entity.update()
            else:
                _ = entity.value


class ToolBox:
    """
    A grid of all possible Entities for the user to choose from to
    add new entities to the workspace.
    """

    # basic objects representing each item in the Grid
    # will be looped over to set up Grid dynamically
    GRID_ITEMS = [
        {
            "label": "And Gate",
            "tiles": (10, 11),
            "constructor": AndGate,
            "size": (2, 1),
        },
        {
            "label": "Nand Gate",
            "tiles": (14, 15),
            "constructor": NandGate,
            "size": (2, 1),
        },
        {"label": "Or Gate", "tiles": (12, 13), "constructor": OrGate, "size": (2, 1)},
        {"label": "Nor Gate", "tiles": (6, 7), "constructor": NorGate, "size": (2, 1)},
        {"label": "Not Gate", "tiles": (22,), "constructor": NotGate, "size": (1, 1)},
        {"label": "Xor Gate", "tiles": (4, 5), "constructor": XorGate, "size": (2, 1)},
        {
            "label": "Xnor Gate",
            "tiles": (24, 25),
            "constructor": XnorGate,
            "size": (2, 1),
        },
        {
            "label": "Virtual PushButton",
            "tiles": (21,),
            "constructor": VirtualPushButton,
            "size": (1, 1),
        },
        {
            "label": "Output Panel",
            "tiles": (2, 3),
            "constructor": OutputPanel,
            "size": (2, 1),
        },
        {
            "label": "NeoPixel Output",
            "tiles": (16,),
            "constructor": NeoPixelOutput,
            "size": (1, 1),
        },
        {
            "label": "Physical Button",
            "tiles": (23,),
            "constructor": PhysicalButton,
            "index": 0,
            "size": (1, 1),
        },
        {
            "label": "Physical Button",
            "tiles": (26,),
            "constructor": PhysicalButton,
            "index": 1,
            "size": (1, 1),
        },
        {
            "label": "Physical Button",
            "tiles": (27,),
            "constructor": PhysicalButton,
            "index": 2,
            "size": (1, 1),
        },
        {
            "label": "Output Connector",
            "tiles": (31,),
            "constructor": ConnectorOut,
            "size": (1, 1),
        },
        {
            "label": "Input Connector",
            "tiles": (30,),
            "constructor": ConnectorIn,
            "size": (1, 1),
        },
        {
            "label": "Wire",
            "tiles": (19,),
            "constructor": Wire,
            "size": (1, 1),
        },
    ]

    def __init__(self, spritesheet_bmp, workspace):
        self._workspace = workspace

        # main group to hold all visual elements
        self.group = Group()

        # setup solid background to hide the workspace underneath the ToolBox
        bg_group = Group(scale=20)
        bg_bitmap = Bitmap(320 // 20, 240 // 20, 1)
        bg_palette = Palette(1)
        bg_palette[0] = 0x888888
        bg_tg = TileGrid(bitmap=bg_bitmap, pixel_shader=bg_palette)
        bg_group.append(bg_tg)
        self.group.append(bg_group)

        # setup GridLayout to hold entities to choose from
        self.grid = GridLayout(
            0, 0, 320, 240, (5, 4), divider_lines=True, divider_line_color=0x666666
        )
        self.group.append(self.grid)

        # store spritesheet and palette for use later
        self.spritesheet = spritesheet_bmp
        self.spritesheet_pixel_shader = workspace.spritesheet_pixel_shader

        # initialize all Entities in the grid
        self._init_grid()

        # ToolBox is hidden by default when created
        self.hidden = True

    def _init_grid(self):
        """
        Setup all Entities in the Grid
        """
        # loop over objects in GRID_ITEMS
        for i, item in enumerate(self.GRID_ITEMS):
            # calculate x,y position in the grid
            grid_pos = (i % self.grid.grid_size[0], i // self.grid.grid_size[0])

            # setup a label for the entity
            item_lbl = TextBox(
                FONT,
                text=item["label"],
                width=320 // self.grid.grid_size[0],
                height=TextBox.DYNAMIC_HEIGHT,
                align=TextBox.ALIGN_CENTER,
                y=8,
            )
            x_pos = 6 if item["size"][0] == 2 else 18

            # setup an icon TileGrid for the entity
            item_icon = TileGrid(
                bitmap=self.spritesheet,
                pixel_shader=self.spritesheet_pixel_shader,
                tile_width=24,
                tile_height=24,
                width=item["size"][0],
                height=item["size"][1],
                default_tile=EMPTY,
                y=item_lbl.bounding_box[3] + 4,
                x=x_pos,
            )
            for tile_index in range(len(item["tiles"])):
                item_icon[tile_index] = item["tiles"][tile_index]
                item_icon[tile_index] = item["tiles"][tile_index]

            # put the entity label and icon in an AnchoredGroup
            item_group = AnchoredGroup()
            item_group.append(item_lbl)
            item_group.append(item_icon)

            # Add the AnchoredGroup to the Grid.
            self.grid.add_content(item_group, grid_position=grid_pos, cell_size=(1, 1))

    @property
    def hidden(self):
        """
        True if the ToolBox is hidden, False if it is visible.
        """
        return self._hidden

    @hidden.setter
    def hidden(self, value):
        self._hidden = value
        self.group.hidden = value

    def handle_mouse_click(self, screen_coords):
        """
        Handle mouse click event sent by code.py
        """
        # get the grid cell location that was clicked
        clicked_cell_coords = self.grid.which_cell_contains(screen_coords)

        # calculate the 0 based index of the clicked cell
        clicked_cell_index = (
            clicked_cell_coords[0] + clicked_cell_coords[1] * self.grid.grid_size[0]
        )

        # if the click was on an empty cell close the ToolBox
        if clicked_cell_index > len(self.GRID_ITEMS) - 1:
            self.hidden = True
            return

        # get the object representing the item at the clicked cell
        clicked_item = self.GRID_ITEMS[clicked_cell_index]

        # special case NeoPixelOutout needs the NeoPixel object
        if clicked_item["label"] == "NeoPixel Output":
            new_entity = clicked_item["constructor"](
                (0, 0),
                self._workspace,
                self._workspace.neopixels,
                add_to_workspace=False,
            )

        # special case PhysicalButton needs the button index
        elif clicked_item["label"] == "Physical Button":
            new_entity = clicked_item["constructor"](
                (0, 0), self._workspace, clicked_item["index"], add_to_workspace=False
            )

        # special case only limited number of ConnectorOuts
        elif clicked_item["label"] == "Output Connector":
            num_ConnectorOuts = 0
            for entity in self._workspace.entities:
                if isinstance(entity, ConnectorOut):
                    num_ConnectorOuts += 1
            if num_ConnectorOuts >= MAX_CONNECTORS:
                # close the ToolBox
                self.hidden = True
                return

            new_entity = clicked_item["constructor"](
                (0, 0), self._workspace, add_to_workspace=False
            )

        # default behavior all other entity types
        else:
            new_entity = clicked_item["constructor"](
                (0, 0), self._workspace, add_to_workspace=False
            )

        # set the created entity as the entity moving with mouse
        self._workspace.moving_entity = new_entity
        self._workspace._set_mouse_moving_tiles(  # pylint: disable=protected-access
            new_entity
        )
        self._workspace.mouse_moving_tg.hidden = False

        # close the ToolBox
        self.hidden = True
