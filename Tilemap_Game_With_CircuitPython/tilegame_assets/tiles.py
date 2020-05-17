from tilegame_assets.states import *


# Minerva before_move. Set game state to STATE_MINERVA
def minerva_walk(to_coords, from_coords, entity_obj, GAME_STATE):
    GAME_STATE['STATE'] = STATE_MINERVA
    return False


# Sparky before_move. If user does not have a Mho in inventory they lose.
# If user does have Mho subtract one from inventory and consume Sparky.
def sparky_walk(to_coords, from_coords, entity_obj, GAME_STATE):
    if GAME_STATE['INVENTORY'].count("mho") > 0:
        GAME_STATE['INVENTORY'].remove("mho")
        GAME_STATE['ENTITY_SPRITES_DICT'][to_coords].remove(entity_obj)
        if len(GAME_STATE['ENTITY_SPRITES_DICT'][to_coords]) == 0:
            del GAME_STATE['ENTITY_SPRITES_DICT'][to_coords]
        if (-1, -1) in GAME_STATE['ENTITY_SPRITES_DICT']:
            GAME_STATE['ENTITY_SPRITES_DICT'][-1, -1].append(entity_obj)
        else:
            GAME_STATE['ENTITY_SPRITES_DICT'][-1, -1] = [entity_obj]
        return True
    else:
        GAME_STATE['STATE'] = STATE_LOST_SPARKY
        return True


# Robot before_move. If user has all Hearts they win the map.
def robot_walk(to_coords, from_coords, entity_obj, GAME_STATE):
    if GAME_STATE['INVENTORY'].count("heart") == GAME_STATE['TOTAL_HEARTS']:
        GAME_STATE["STATE"] = STATE_MAPWIN
        return True

    return False


# Remove the item from this location and add it to player inventory.
def take_item(to_coords, from_coords, entity_obj, GAME_STATE):
    print(entity_obj)
    GAME_STATE['INVENTORY'].append(entity_obj["map_tile_name"])
    GAME_STATE['ENTITY_SPRITES_DICT'][to_coords].remove(entity_obj)
    if len(GAME_STATE['ENTITY_SPRITES_DICT'][to_coords]) == 0:
        del GAME_STATE['ENTITY_SPRITES_DICT'][to_coords]

    if (-1, -1) in GAME_STATE['ENTITY_SPRITES_DICT']:
        GAME_STATE['ENTITY_SPRITES_DICT'][-1, -1].append(entity_obj)
    else:
        GAME_STATE['ENTITY_SPRITES_DICT'][-1, -1] = [entity_obj]

    return True


# main dictionary that maps tile type strings to objects.
# each one stores the sprite_sheet index and any necessary
# behavioral stats like can_walk or before_move
TILES = {
    # empty strings default to floor and no walk.
    "": {
        "sprite_index": 10,
        "can_walk": False
    },
    "floor": {
        "sprite_index": 10,
        "can_walk": True
    },
    "top_wall": {
        "sprite_index": 7,
        "can_walk": False
    },
    "top_right_wall": {
        "sprite_index": 8,
        "can_walk": False
    },
    "top_left_wall": {
        "sprite_index": 6,
        "can_walk": False
    },
    "bottom_right_wall": {
        "sprite_index": 14,
        "can_walk": False
    },
    "bottom_left_wall": {
        "sprite_index": 12,
        "can_walk": False
    },
    "right_wall": {
        "sprite_index": 11,
        "can_walk": False
    },
    "left_wall": {
        "sprite_index": 9,
        "can_walk": False
    },
    "bottom_wall": {
        "sprite_index": 13,
        "can_walk": False
    },
    "robot": {
        "sprite_index": 1,
        "can_walk": True,
        "entity": True,
        "before_move": robot_walk
    },
    "heart": {
        "sprite_index": 5,
        "can_walk": True,
        "entity": True,
        "before_move": take_item
    },
    "mho": {
        "sprite_index": 2,
        "can_walk": True,
        "entity": True,
        "before_move": take_item
    },
    "sparky": {
        "sprite_index": 4,
        "can_walk": True,
        "entity": True,
        "before_move": sparky_walk
    },
    "minerva": {
        "sprite_index": 3,
        "can_walk": True,
        "entity": True,
        "before_move": minerva_walk
    },
    "player": {
        "sprite_index": 0,
        "entity": True,
    }
}
