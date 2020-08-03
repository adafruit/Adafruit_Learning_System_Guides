import time
import random
import gc
import board
import displayio
import adafruit_imageload
import ugame
import terminalio
from adafruit_display_text import label
from tilegame_assets.tiles import TILES
from tilegame_assets.states import (
    STATE_PLAYING,
    STATE_MAPWIN,
    STATE_WAITING,
    STATE_LOST_SPARKY,
    STATE_MINERVA,
)
from tilegame_assets.fun_facts import FACTS
from tilegame_assets.text_helper import wrap_nicely

# pylint: disable=bad-continuation

# Direction constants for comparison
UP = 0
DOWN = 1
RIGHT = 2
LEFT = 3

# how long to wait between rendering frames
FPS_DELAY = 1 / 60

# how many tiles can fit on thes screen. Tiles are 16x16 pixels
SCREEN_HEIGHT_TILES = 8
SCREEN_WIDTH_TILES = 10

# list of maps in order they should be played
MAPS = ["map0.csv", "map1.csv"]

GAME_STATE = {
    # hold the map state as it came out of the csv. Only holds non-entities.
    "ORIGINAL_MAP": {},
    # hold the current map state as it changes. Only holds non-entities.
    "CURRENT_MAP": {},
    # Dictionary with touple keys that map to lists of entity objects.
    # Each one has the index of the sprite in the ENTITY_SPRITES list
    # and the tile type string
    "ENTITY_SPRITES_DICT": {},
    # hold the location of the player in tile coordinates
    "PLAYER_LOC": (0, 0),
    # list of items the player has in inventory
    "INVENTORY": [],
    # how many hearts there are in this map level
    "TOTAL_HEARTS": 0,
    # sprite object to draw for the player
    "PLAYER_SPRITE": None,
    # size of the map
    "MAP_WIDTH": 0,
    "MAP_HEIGHT": 0,
    # which map level within MAPS we are currently playing
    "MAP_INDEX": 0,
    # current state of the state machine
    "STATE": STATE_PLAYING,
}

# dictionary with tuple keys that map to tile type values
# e.x. {(0,0): "left_wall", (1,1): "floor"}
CAMERA_VIEW = {}

# how far offset the camera is from the GAME_STATE['CURRENT_MAP']
# used to determine where things are at in the camera view vs. the MAP
CAMERA_OFFSET_X = 0
CAMERA_OFFSET_Y = 0

# list of sprite objects, one for each entity
ENTITY_SPRITES = []

# list of entities that need to be on the screen currently based on the camera view
NEED_TO_DRAW_ENTITIES = []


def get_tile(coords):
    """
    :param coords: (x, y) tuple
    :return: tile name of the tile at the given coords from GAME_STATE['CURRENT_MAP']
    """
    return GAME_STATE["CURRENT_MAP"][coords[0], coords[1]]


def get_tile_obj(coords):
    """
    :param coords: (x, y) tuple
    :return: tile object with stats and behavior for the tile at the given coords.
    """
    return TILES[GAME_STATE["CURRENT_MAP"][coords[0], coords[1]]]


#
def is_tile_moveable(tile_coords):
    """
    Check the can_walk property of the tile at the given coordinates
    :param tile_coords: (x, y) tuple
    :return: True if the player can walk on this tile. False otherwise.
    """
    return TILES[GAME_STATE["CURRENT_MAP"][tile_coords[0], tile_coords[1]]]["can_walk"]


print("after funcs {}".format(gc.mem_free()))

# display object variable
display = board.DISPLAY

# Load the sprite sheet (bitmap)
sprite_sheet, palette = adafruit_imageload.load(
    "tilegame_assets/sprite_sheet.bmp",
    bitmap=displayio.Bitmap,
    palette=displayio.Palette,
)

# make green be transparent so entities can be drawn on top of map tiles
palette.make_transparent(0)

# Create the castle TileGrid
castle = displayio.TileGrid(
    sprite_sheet,
    pixel_shader=palette,
    width=10,
    height=8,
    tile_width=16,
    tile_height=16,
)

# Create a Group to hold the sprite and castle
group = displayio.Group(max_size=33)

# Add castle to the group
group.append(castle)


def load_map(file_name):
    # pylint: disable=global-statement,too-many-statements,too-many-nested-blocks,too-many-branches
    global ENTITY_SPRITES, CAMERA_VIEW

    # empty the sprites from the group
    for cur_s in ENTITY_SPRITES:
        group.remove(cur_s)
    # remove player sprite
    try:
        group.remove(GAME_STATE["PLAYER_SPRITE"])
    except ValueError:
        pass

    # reset map and other game state objects
    GAME_STATE["ORIGINAL_MAP"] = {}
    GAME_STATE["CURRENT_MAP"] = {}
    ENTITY_SPRITES = []
    GAME_STATE["ENTITY_SPRITES_DICT"] = {}
    CAMERA_VIEW = {}
    GAME_STATE["INVENTORY"] = []
    GAME_STATE["TOTAL_HEARTS"] = 0

    # Open and read raw string from the map csv file
    f = open("tilegame_assets/{}".format(file_name), "r")
    map_csv_str = f.read()
    f.close()

    # split the raw string into lines
    map_csv_lines = map_csv_str.replace("\r", "").split("\n")

    # set the WIDTH and HEIGHT variables.
    # this assumes the map is rectangular.
    GAME_STATE["MAP_HEIGHT"] = len(map_csv_lines)
    GAME_STATE["MAP_WIDTH"] = len(map_csv_lines[0].split(","))

    # loop over each line storing index in y variable
    for y, line in enumerate(map_csv_lines):
        # ignore empty line
        if line != "":
            # loop over each tile type separated by commas, storing index in x variable
            for x, tile_name in enumerate(line.split(",")):
                print("%s '%s'" % (len(tile_name), str(tile_name)))

                # if the tile exists in our main dictionary
                if tile_name in TILES.keys():

                    # if the tile is an entity
                    if (
                        "entity" in TILES[tile_name].keys()
                        and TILES[tile_name]["entity"]
                    ):
                        # set the map tiles to floor
                        GAME_STATE["ORIGINAL_MAP"][x, y] = "floor"
                        GAME_STATE["CURRENT_MAP"][x, y] = "floor"

                        if tile_name == "heart":
                            GAME_STATE["TOTAL_HEARTS"] += 1

                        # if it's the player
                        if tile_name == "player":
                            # Create the sprite TileGrid
                            GAME_STATE["PLAYER_SPRITE"] = displayio.TileGrid(
                                sprite_sheet,
                                pixel_shader=palette,
                                width=1,
                                height=1,
                                tile_width=16,
                                tile_height=16,
                                default_tile=TILES[tile_name]["sprite_index"],
                            )

                            # set the position of sprite on screen
                            GAME_STATE["PLAYER_SPRITE"].x = x * 16
                            GAME_STATE["PLAYER_SPRITE"].y = y * 16

                            # set position in x,y tile coords for reference later
                            GAME_STATE["PLAYER_LOC"] = (x, y)

                            # add sprite to the group
                            group.append(GAME_STATE["PLAYER_SPRITE"])
                        else:  # not the player
                            # Create the sprite TileGrid
                            entity_srite = displayio.TileGrid(
                                sprite_sheet,
                                pixel_shader=palette,
                                width=1,
                                height=1,
                                tile_width=16,
                                tile_height=16,
                                default_tile=TILES[tile_name]["sprite_index"],
                            )
                            # set the position of sprite on screen
                            # default to off the edge
                            entity_srite.x = -16
                            entity_srite.y = -16

                            # add the sprite object to ENTITY_SPRITES list
                            ENTITY_SPRITES.append(entity_srite)
                            # print("setting GAME_STATE['ENTITY_SPRITES_DICT'][%s,%s]" % (x,y))

                            # create an entity obj
                            _entity_obj = {
                                "entity_sprite_index": len(ENTITY_SPRITES) - 1,
                                "map_tile_name": tile_name,
                            }

                            # if there are no entities at this location yet
                            if (x, y) not in GAME_STATE["ENTITY_SPRITES_DICT"]:
                                # create a list and add it to the dictionary at the x,y location
                                GAME_STATE["ENTITY_SPRITES_DICT"][x, y] = [_entity_obj]
                            else:
                                # append the entity to the existing list in the dictionary
                                GAME_STATE["ENTITY_SPRITES_DICT"][x, y].append(
                                    _entity_obj
                                )

                    else:  # tile is not entity
                        # set the tile_name into MAP dictionaries
                        GAME_STATE["ORIGINAL_MAP"][x, y] = tile_name
                        GAME_STATE["CURRENT_MAP"][x, y] = tile_name

                else:  # tile type wasn't found in dict
                    print("tile: %s not found in TILES dict" % tile_name)
    # add all entity sprites to the group
    print("appending {} sprites".format(len(ENTITY_SPRITES)))
    for entity in ENTITY_SPRITES:
        group.append(entity)


print("loading map")
load_map(MAPS[GAME_STATE["MAP_INDEX"]])

# Add the Group to the Display
display.show(group)

# variables to store previous value of button state
prev_up = False
prev_down = False
prev_left = False
prev_right = False


# helper function returns true if player is allowed to move given direction
# based on can_walk property of the tiles next to the player
def can_player_move(direction):
    try:
        if direction == UP:
            tile_above_coords = (
                GAME_STATE["PLAYER_LOC"][0],
                GAME_STATE["PLAYER_LOC"][1] - 1,
            )

            return TILES[
                GAME_STATE["CURRENT_MAP"][tile_above_coords[0], tile_above_coords[1]]
            ]["can_walk"]

        if direction == DOWN:
            tile_below_coords = (
                GAME_STATE["PLAYER_LOC"][0],
                GAME_STATE["PLAYER_LOC"][1] + 1,
            )
            return TILES[
                GAME_STATE["CURRENT_MAP"][tile_below_coords[0], tile_below_coords[1]]
            ]["can_walk"]

        if direction == LEFT:
            tile_left_of_coords = (
                GAME_STATE["PLAYER_LOC"][0] - 1,
                GAME_STATE["PLAYER_LOC"][1],
            )
            return TILES[
                GAME_STATE["CURRENT_MAP"][
                    tile_left_of_coords[0], tile_left_of_coords[1]
                ]
            ]["can_walk"]

        if direction == RIGHT:
            tile_right_of_coords = (
                GAME_STATE["PLAYER_LOC"][0] + 1,
                GAME_STATE["PLAYER_LOC"][1],
            )
            return TILES[
                GAME_STATE["CURRENT_MAP"][
                    tile_right_of_coords[0], tile_right_of_coords[1]
                ]
            ]["can_walk"]
    except KeyError:
        return False

    return None


# set the appropriate tiles into the CAMERA_VIEW dictionary
# based on given starting coords and size
def set_camera_view(startX, startY, width, height):
    # pylint: disable=global-statement
    global CAMERA_OFFSET_X
    global CAMERA_OFFSET_Y
    # set the offset variables for use in other parts of the code
    CAMERA_OFFSET_X = startX
    CAMERA_OFFSET_Y = startY

    # loop over the rows and indexes in the desired size section
    for y_index, y in enumerate(range(startY, startY + height)):
        # loop over columns and indexes in the desired size section
        for x_index, x in enumerate(range(startX, startX + width)):
            # print("setting camera_view[%s,%s]" % (x_index,y_index))
            try:
                # set the tile at the current coordinate of the MAP into the CAMERA_VIEW
                CAMERA_VIEW[x_index, y_index] = GAME_STATE["CURRENT_MAP"][x, y]
            except KeyError:
                # if coordinate is out of bounds set it to floor by default
                CAMERA_VIEW[x_index, y_index] = "floor"


# draw the current CAMERA_VIEW dictionary and the GAME_STATE['ENTITY_SPRITES_DICT']
def draw_camera_view():
    # list that will hold all entities that have been drawn based on their MAP location
    # any entities not in this list should get moved off the screen
    drew_entities = []
    # print(CAMERA_VIEW)
    # pylint: disable=too-many-nested-blocks

    # loop over y tile coordinates
    for y in range(0, SCREEN_HEIGHT_TILES):
        # loop over x tile coordinates
        for x in range(0, SCREEN_WIDTH_TILES):
            # tile name at this location
            tile_name = CAMERA_VIEW[x, y]

            # if tile exists in the main dictionary
            if tile_name in TILES.keys():
                # if there are entity(s) at this location
                if (x + CAMERA_OFFSET_X, y + CAMERA_OFFSET_Y) in GAME_STATE[
                    "ENTITY_SPRITES_DICT"
                ]:
                    # default background for entities is floor
                    castle[x, y] = TILES["floor"]["sprite_index"]

                    # if it's not the player
                    if tile_name != "player":
                        # loop over all entities at this location
                        for entity_obj_at_tile in GAME_STATE["ENTITY_SPRITES_DICT"][
                            x + CAMERA_OFFSET_X, y + CAMERA_OFFSET_Y
                        ]:
                            # set appropriate x,y screen coordinates
                            # based on tile coordinates
                            ENTITY_SPRITES[
                                int(entity_obj_at_tile["entity_sprite_index"])
                            ].x = (x * 16)
                            ENTITY_SPRITES[
                                int(entity_obj_at_tile["entity_sprite_index"])
                            ].y = (y * 16)

                            # add the index of the entity sprite to the draw_entities
                            # list so we know not to hide it later.
                            drew_entities.append(
                                entity_obj_at_tile["entity_sprite_index"]
                            )

                else:  # no entities at this location
                    # set the sprite index of this tile into the CASTLE dictionary
                    castle[x, y] = TILES[tile_name]["sprite_index"]

            else:  # tile type not found in main dictionary
                # default to floor tile
                castle[x, y] = TILES["floor"]["sprite_index"]

            # if the player is at this x,y tile coordinate accounting for camera offset
            if GAME_STATE["PLAYER_LOC"] == ((x + CAMERA_OFFSET_X, y + CAMERA_OFFSET_Y)):
                # set player sprite screen coordinates
                GAME_STATE["PLAYER_SPRITE"].x = x * 16
                GAME_STATE["PLAYER_SPRITE"].y = y * 16

    # loop over all entity sprites
    for index in range(0, len(ENTITY_SPRITES)):
        # if the sprite wasn't drawn then it's outside the camera view
        if index not in drew_entities:
            # hide the sprite by moving it off screen
            ENTITY_SPRITES[index].x = int(-16)
            ENTITY_SPRITES[index].y = int(-16)


# variable to store timestamp of last drawn frame
last_update_time = 0

# variables to store movement offset values
x_offset = 0
y_offset = 0


def show_splash(new_text, color, vertical_offset=18):
    text_area.text = ""
    text_area.text = new_text
    text_area.y = round(text_area.text.count("\n") * vertical_offset / 2)
    text_area.color = color
    group.append(splash)


# game message background bmp file
with open(
    "tilegame_assets/game_message_background.bmp", "rb"
) as game_message_background:
    # Make the splash context
    splash = displayio.Group(max_size=4)

    odb = displayio.OnDiskBitmap(game_message_background)

    bg_grid = displayio.TileGrid(odb, pixel_shader=displayio.ColorConverter())

    splash.append(bg_grid)

    # Text for the message
    text_group = displayio.Group(max_size=8, scale=1, x=14, y=18)
    text_area = label.Label(terminalio.FONT, text=" " * 180, color=0xD39AE5)
    text_group.append(text_area)
    splash.append(text_group)

    # main loop
    while True:
        # set the current button values into variables
        cur_btn_vals = ugame.buttons.get_pressed()
        cur_up = cur_btn_vals & ugame.K_UP
        cur_down = cur_btn_vals & ugame.K_DOWN
        cur_right = cur_btn_vals & ugame.K_RIGHT
        cur_left = cur_btn_vals & ugame.K_LEFT
        cur_a = cur_btn_vals & ugame.K_O or cur_btn_vals & ugame.K_X

        if GAME_STATE["STATE"] == STATE_WAITING:
            print(cur_a)
            if cur_a:
                GAME_STATE["STATE"] = STATE_PLAYING
                group.remove(splash)

        if GAME_STATE["STATE"] == STATE_PLAYING:
            # check for up button press / release
            if not cur_up and prev_up:
                if can_player_move(UP):
                    x_offset = 0
                    y_offset = -1

            # check for down button press / release
            if not cur_down and prev_down:
                if can_player_move(DOWN):
                    x_offset = 0
                    y_offset = 1

            # check for right button press / release
            if not cur_right and prev_right:
                if can_player_move(RIGHT):
                    x_offset = 1
                    y_offset = 0

            # check for left button press / release
            if not cur_left and prev_left:
                if can_player_move(LEFT):
                    x_offset = -1
                    y_offset = 0

            # if any offset is not zero then we need to process player movement
            if x_offset != 0 or y_offset != 0:
                # variable to store if player is allowed to move
                can_move = False

                # coordinates the player is moving to
                moving_to_coords = (
                    GAME_STATE["PLAYER_LOC"][0] + x_offset,
                    GAME_STATE["PLAYER_LOC"][1] + y_offset,
                )

                # tile name of the spot player is moving to
                moving_to_tile_name = GAME_STATE["CURRENT_MAP"][
                    moving_to_coords[0], moving_to_coords[1]
                ]

                # if there are entity(s) at spot the player is moving to
                if moving_to_coords in GAME_STATE["ENTITY_SPRITES_DICT"]:
                    print("found entity(s) where we are moving to")

                    # loop over all entities at the location player is moving to
                    for entity_obj in GAME_STATE["ENTITY_SPRITES_DICT"][
                        moving_to_coords
                    ]:
                        print("checking entity %s" % entity_obj["map_tile_name"])
                        # if the entity has a before_move behavior function
                        if "before_move" in TILES[entity_obj["map_tile_name"]].keys():
                            print(
                                "calling before_move %s, %s, %s"
                                % (
                                    moving_to_coords,
                                    GAME_STATE["PLAYER_LOC"],
                                    entity_obj,
                                )
                            )
                            # call the before_move behavior function act upon it's result
                            if TILES[entity_obj["map_tile_name"]]["before_move"](
                                moving_to_coords,
                                GAME_STATE["PLAYER_LOC"],
                                entity_obj,
                                GAME_STATE,
                            ):
                                # all the movement if it returned true
                                can_move = True
                            else:
                                # break and don't allow movement if it returned false
                                break
                        else:  # entity does not have a before_move function
                            # allow movement
                            can_move = True
                    if can_move:
                        # set the player loc variable to the new coords
                        GAME_STATE["PLAYER_LOC"] = moving_to_coords

                else:  # no entities at the location player is moving to
                    # set player loc variable to new coords
                    GAME_STATE["PLAYER_LOC"] = moving_to_coords

            # reset movement offset variables
            y_offset = 0
            x_offset = 0

            # set previous button values for next iteration
            prev_up = cur_up
            prev_down = cur_down
            prev_right = cur_right
            prev_left = cur_left

            # current time
            now = time.monotonic()

            # if it has been long enough based on FPS delay
            if now > last_update_time + FPS_DELAY:
                # Set camera to 10x8 centered on the player
                # Clamped to (0, MAP_WIDTH) and (0, MAP_HEIGHT)
                set_camera_view(
                    max(
                        min(
                            GAME_STATE["PLAYER_LOC"][0] - 4,
                            GAME_STATE["MAP_WIDTH"] - SCREEN_WIDTH_TILES,
                        ),
                        0,
                    ),
                    max(
                        min(
                            GAME_STATE["PLAYER_LOC"][1] - 3,
                            GAME_STATE["MAP_HEIGHT"] - SCREEN_HEIGHT_TILES,
                        ),
                        0,
                    ),
                    10,
                    8,
                )
                # draw the camera
                draw_camera_view()
            # if player beat this map
            if GAME_STATE["STATE"] == STATE_MAPWIN:
                GAME_STATE["MAP_INDEX"] += 1
                # if player has beaten all maps
                if GAME_STATE["MAP_INDEX"] >= len(MAPS):
                    GAME_STATE["MAP_INDEX"] = 0
                    GAME_STATE["STATE"] = STATE_WAITING
                    load_map(MAPS[GAME_STATE["MAP_INDEX"]])
                    show_splash(
                        "You Win \n =D \nCongratulations. \nStart Over?", 0x29C1CF
                    )
                else:
                    # prompt to start next
                    GAME_STATE["STATE"] = STATE_WAITING
                    load_map(MAPS[GAME_STATE["MAP_INDEX"]])
                    show_splash(
                        "You beat this level\n =D \nCongratulations. \nStart Next?",
                        0x29C1CF,
                    )
            # game over from sparky
            elif GAME_STATE["STATE"] == STATE_LOST_SPARKY:
                GAME_STATE["MAP_INDEX"] = 0
                GAME_STATE["STATE"] = STATE_WAITING
                game_over_text = (
                    "Be careful not to \ntouch Sparky unless \n"
                    "you've collected \nenough Mho's.\nStarting Over"
                )
                load_map(MAPS[GAME_STATE["MAP_INDEX"]])
                show_splash(game_over_text, 0x25AFBB)

            # talking to minerva
            elif GAME_STATE["STATE"] == STATE_MINERVA:
                GAME_STATE["STATE"] = STATE_WAITING
                random_fact = random.choice(FACTS)
                minerva_txt = wrap_nicely("Minerva: {}".format(random_fact), 23)
                show_splash(minerva_txt, 0xD39AE5, 10)

            # store the last update time
            last_update_time = now
