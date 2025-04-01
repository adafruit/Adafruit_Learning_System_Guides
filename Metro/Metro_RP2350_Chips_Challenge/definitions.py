# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams
#
# SPDX-License-Identifier: MIT
from micropython import const

# Settings
PLAY_SOUNDS = False

# Timing Constants
TICKS_PER_SECOND = const(20)
SECOND_LENGTH = const(1000)

# Tile Constants
TYPE_NOTILE = const(-1)
TYPE_EMPTY = const(0x00)
TYPE_WALL = const(0x01)
TYPE_ICCHIP = const(0x02)
TYPE_WATER = const(0x03)
TYPE_FIRE = const(0x04)
TYPE_HIDDENWALL_PERM = const(0x05)
TYPE_WALL_NORTH = const(0x06)
TYPE_WALL_WEST = const(0x07)
TYPE_WALL_SOUTH = const(0x08)
TYPE_WALL_EAST = const(0x09)
TYPE_BLOCK_STATIC = const(0x0a)
TYPE_DIRT = const(0x0b)
TYPE_ICE = const(0x0c)
TYPE_SLIDE_SOUTH = const(0x0d)
TYPE_SLIDE_NORTH = const(0x12)
TYPE_SLIDE_EAST = const(0x13)
TYPE_SLIDE_WEST = const(0x14)
TYPE_EXIT = const(0x15)
TYPE_DOOR_BLUE = const(0x16)
TYPE_DOOR_RED = const(0x17)
TYPE_DOOR_GREEN = const(0x18)
TYPE_DOOR_YELLOW = const(0x19)
TYPE_ICEWALL_SOUTHEAST = const(0x1a)
TYPE_ICEWALL_SOUTHWEST = const(0x1b)
TYPE_ICEWALL_NORTHWEST = const(0x1c)
TYPE_ICEWALL_NORTHEAST = const(0x1d)
TYPE_BLUEWALL_FAKE = const(0x1e)
TYPE_BLUEWALL_REAL = const(0x1f)

TYPE_THIEF = const(0x21)
TYPE_SOCKET = const(0x22)
TYPE_BUTTON_GREEN = const(0x23)
TYPE_BUTTON_RED = const(0x24)
TYPE_SWITCHWALL_CLOSED = const(0x25)
TYPE_SWITCHWALL_OPEN = const(0x26)
TYPE_BUTTON_BROWN = const(0x27)
TYPE_BUTTON_BLUE = const(0x28)
TYPE_TELEPORT = const(0x29)
TYPE_BOMB = const(0x2a)
TYPE_BEARTRAP = const(0x2b)
TYPE_HIDDENWALL_TEMP = const(0x2c)
TYPE_GRAVEL = const(0x2d)
TYPE_POPUPWALL = const(0x2e)
TYPE_HINTBUTTON = const(0x2f)
TYPE_WALL_SOUTHEAST = const(0x30)
TYPE_CLONEMACHINE = const(0x31)
TYPE_SLIDE_RANDOM = const(0x32)

TYPE_CHIP_DROWNED = const(0x33)
TYPE_CHIP_BURNED = const(0x34)
TYPE_CHIP_BOMBED = const(0x35)

TYPE_EXITED_CHIP = const(0x39)
TYPE_EXIT_EXTRA_1 = const(0x3a)
TYPE_EXIT_EXTRA_2 = const(0x3b)

TYPE_BLOCK = const(0xd0)
TYPE_CHIP_SWIMMING = const(0x3c)
TYPE_BUG = const(0x40)
TYPE_FIREBALL = const(0x44)
TYPE_BALL = const(0x48)
TYPE_TANK = const(0x4c)
TYPE_GLIDER = const(0x50)
TYPE_TEETH = const(0x54)
TYPE_WALKER = const(0x58)
TYPE_BLOB = const(0x5c)
TYPE_PARAMECIUM = const(0x60)

TYPE_KEY_BLUE = const(0x64)
TYPE_KEY_RED = const(0x65)
TYPE_KEY_GREEN = const(0x66)
TYPE_KEY_YELLOW = const(0x67)

TYPE_BOOTS_WATER = const(0x68)
TYPE_BOOTS_FIRE = const(0x69)
TYPE_BOOTS_ICE = const(0x6a)
TYPE_BOOTS_SLIDE = const(0x6b)

TYPE_CHIP = const(0x6c)
TYPE_NOTHING = const(0xff)

# Map Directional Constants
NONE = const(-1)
NORTH = const(1)
WEST = const(2)
SOUTH = const(4)
EAST = const(8)
NWSE = const(NORTH | WEST | SOUTH | EAST)

# Command Constants
UP = const(0)
LEFT = const(1)
DOWN = const(2)
RIGHT = const(3)
NEXT_LEVEL = const(4)
PREVIOUS_LEVEL = const(5)
RESTART_LEVEL = const(6)
GOTO_LEVEL = const(7)
PAUSE = const(8)
QUIT = const(9)
OK = const(10)
CANCEL = const(11)
CHANGE_FIELDS = const(12)
DELCHAR = const(13)

# Keycode Constants
UP_ARROW = const("\x1b[A")
DOWN_ARROW = const("\x1b[B")
RIGHT_ARROW = const("\x1b[C")
LEFT_ARROW = const("\x1b[D")
SPACE = const(" ")
CTRL_G = const("\x07")  # Ctrl+G
CTRL_N = const("\x0E")  # Ctrl+N
CTRL_P = const("\x10")  # Ctrl+P
CTRL_Q = const("\x11")  # Ctrl+Q
CTRL_R = const("\x12")  # Ctrl+R
BACKSPACE = const("\x08")
TAB = const("\x09")
ENTER = const("\n")
ESC = const("\x1b")

# Mapping Buttons to Commands for different modes
GAMEPLAY_COMMANDS = {
    UP_ARROW: UP,
    LEFT_ARROW: LEFT,
    DOWN_ARROW: DOWN,
    RIGHT_ARROW: RIGHT,
    SPACE: PAUSE,
    CTRL_G: GOTO_LEVEL,
    CTRL_N: NEXT_LEVEL,
    CTRL_P: PREVIOUS_LEVEL,
    CTRL_Q: QUIT,
    CTRL_R: RESTART_LEVEL,
}

MESSAGE_COMMANDS = {
    ENTER: OK,
    SPACE: OK,
}

# Password commands include only letters, enter, tab, and backspace
PASSWORD_COMMANDS = {
     ESC: CANCEL,
     TAB: CHANGE_FIELDS,
     ENTER: OK,
     BACKSPACE: DELCHAR,
}

# The rest are input characters
for i in range(65, 91):
    PASSWORD_COMMANDS[chr(i)] = chr(i)
for i in range(97, 123):
    PASSWORD_COMMANDS[chr(i)] = chr(i)
for i in range(48, 58):
    PASSWORD_COMMANDS[chr(i)] = chr(i)

# Can Make Move Constants
CMM_NOLEAVECHECK = const(0x0001)
CMM_NOEXPOSEWALLS = const(0x0002)
CMM_CLONECANTBLOCK = const(0x0004)
CMM_NOPUSHING = const(0x0008)
CMM_TELEPORTPUSH = const(0x0010)
CMM_NOFIRECHECK = const(0x0020)
CMM_NODEFERBUTTONS = const(0x0040)

# Creature States
CS_RELEASED = const(0x01)
CS_CLONING = const(0x02)
CS_HASMOVED = const(0x04)
CS_TURNING = const(0x08)
CS_SLIP = const(0x10)
CS_SLIDE = const(0x20)
CS_DEFERPUSH = const(0x40)
CS_MUTANT = const(0x80)

#Floor State Constants
FS_BUTTONDOWN = const(0x01)
FS_CLONING = const(0x02)
FS_BROKEN = const(0x04)
FS_HASMUTANT = const(0x08)
FS_MARKER = const(0x10)

# Status Flag Constants
SF_CHIPWAITMASK = const(0x0007)
SF_CHIPOKAY = const(0x0000)
SF_CHIPBURNED = const(0x0010)
SF_CHIPBOMBED = const(0x0020)
SF_CHIPDROWNED = const(0x0030)
SF_CHIPHIT = const(0x0040)
SF_CHIPTIMEUP = const(0x0050)
SF_CHIPBLOCKHIT = const(0x0060)
SF_CHIPNOTOKAY = const(0x0070)
SF_CHIPSTATUSMASK = const(0x0070)
SF_DEFERBUTTONS = const(0x0080)
SF_COMPLETED = const(0x0100)
SF_SHOWHINT = const(0x10000000)

# Game Mode Constants
GM_NONE = const(0)          # No mode (not sure if this should be a mode)
GM_PAUSED = const(1)        # Paused
GM_CHIPDEAD = const(2)      # Chip is dead
GM_GAMEWON = const(3)       # Game is won
GM_LEVELWON = const(4)      # Level is won
GM_LOADING = const(5)       # Not sure
GM_MESSAGE = const(6)       # Message is displayed
GM_NEWGAME = const(7)       # Not sure
GM_NORMAL = const(8)        # Normal gameplay

# Key Constants
RED_KEY = const(0)
BLUE_KEY = const(1)
YELLOW_KEY = const(2)
GREEN_KEY = const(3)

# Boot Constants
ICE_BOOTS = const(0)
SUCTION_BOOTS = const(1)
FIRE_BOOTS = const(2)
WATER_BOOTS = const(3)

death_messages = {
    SF_CHIPHIT: "Ooops! Look out for creatures!",
    SF_CHIPDROWNED: "Ooops! Chip can't swim without flippers!",
    SF_CHIPBURNED: "Ooops! Don't step in the fire without fire boots!",
    SF_CHIPBOMBED: "Ooops! Don't touch the bombs!",
    SF_CHIPTIMEUP: "Ooops! Out of time!",
    SF_CHIPBLOCKHIT: "Ooops! Watch out for moving blocks!",
}

decade_messages = {
    10:	("After warming up on the first levels of the challenge, "
         "Chip is raring to go! 'This isn't so hard,' he thinks."),
    20:	("But the challenge turns out to be harder than Chip thought. "
         "The Bit Busters want it that way -- to keep out lobotomy heads."),
    30:	("Chip's thick-soled shoes and pop-bottle glasses speed him through "
         "the mazes while his calculator watch keeps track of time."),
    40:	"Chip reads the clues so he won't lose.",
    50:	("Picking up chips is what the challenge is all about. But on ice, "
         "Chip gets chapped and feels like a chump instead of a champ."),
    60:	("Chip hits the ice and decides to chill out. Then he runs into a "
         "fake wall and turns the maze into a thrash-a-thon!"),
    70:	("Chip is halfway through the world's hardest puzzle. If he suceeds, "
         "maybe the kids will stop calling him computer breath!"),
    80:	("Chip used to spend his time programming computer games and making "
         "models. But that was just practice for this brain-buster!"),
    90:	("'I can do it! I know I can!' Chip thinks as the going gets tougher. "
         "Besides, Melinda the Mental Marvel waits at the end."),
    100: ("Besides being an angel on earth, Melinda is the top scorer in the "
          "Challenge--and the president of the Bit Busters."),
    110: ("Chip can't wait to join the Bit Busters! The club's already figured "
          "out the school's password and accessed everyone's grades!"),
    120: ("If Chip's grades aren't as good as Melinda's, maybe she'll come "
          "over to his house and help him study!"),
    130: ("'I've made it this far,' Chip thinks. 'Totally fair, with my "
          "mega-brain.' Then he starts the next maze. 'Totally unfair!' he yelps."),
    140: "Groov-u-loids! Chip makes it almost to the end. He's stoked!",
    144: ("Melinda herself offers Chip membership in the exclusive Bit Busters "
          "computer club, and gives him access to the club's computer system. "
          "Chip is in heaven!"),
    149: ("Melinda herself offers Chip membership in the exclusive Bit Busters "
          "computer club, and gives him access to the club's computer system. "
          "Chip is in heaven!"),
}

victory_messages = {
    0: "Yowser! First Try!",
    2: "Go Bit Buster!",
    4: "Finished! Good Work!",
    5: "At last! You did it!",
}

winning_message = (
    "You completed {completed_levels} levels, and your total score for the "
    "challenge is {total_score} points.\n\n"
    "You can still improve your score, by completing levels that you skipped, "
    "and getting better times on each level. When you replay a level, if your "
    "new score is better than your old, your score will be adjusted by the "
    "difference. Select Best Times from the Game menu to see your scores for "
    "each level."
)

# This will show the game won sequence for any of these levels
# -1 represents the last level
final_levels = [144, -1]

def left(direction):
    return ((direction << 1) | (direction >> 3)) & 15

def back(direction):
    return ((direction << 2) | (direction >> 2)) & 15

def right(direction):
    return ((direction << 3) | (direction >> 1)) & 15

def creature_id(tile_id):
    return tile_id & ~3

def idx_dir(index):
    return 1 << (index & 3)

def dir_idx(direction):
    return (0x30210 >> (direction * 2)) & 3

def creature_dir_id(tile_id):
    return idx_dir(tile_id & 3)

def cr_tile(tile_id, direction):
    return tile_id | dir_idx(direction)

def is_key(tile):
    return TYPE_KEY_BLUE <= tile <= TYPE_KEY_YELLOW

def is_boots(tile):
    return TYPE_BOOTS_WATER <= tile <= TYPE_BOOTS_SLIDE

def is_creature(tile):
    return ((0x40 <= tile <= 0x63) or (TYPE_BLOCK <= tile <= TYPE_BLOCK + 3) or
    (TYPE_CHIP_SWIMMING <= tile <= TYPE_CHIP_SWIMMING + 3) or
    (TYPE_CHIP <= tile <= TYPE_CHIP + 3))

def is_door(tile):
    return TYPE_DOOR_BLUE <= tile <= TYPE_DOOR_YELLOW
