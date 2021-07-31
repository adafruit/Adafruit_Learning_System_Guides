"""
Dragon Drop: a simple game for Adafruit MACROPAD. Uses OLED display in
portrait (vertical) orientation. Tap one of four keys across a row to
catch falling eggs before they hit the ground. Avoid fireballs.
"""

# pylint: disable=import-error, unused-import
import gc
import random
import time
import displayio
import adafruit_imageload
from adafruit_macropad import MacroPad
#from adafruit_display_shapes.rect import Rect
#from adafruit_display_text import label


# CONFIGURABLES ------------------------

MAX_EGGS = 6


# UTILITY FUNCTIONS AND CLASSES --------

# pylint: disable=too-few-public-methods
class Sprite:
    """ Class for sprite (eggs, fireballs) state information """
    def __init__(self, column, start_time):
        self.column = column                    # 0-3
        self.is_fire = (random.random() < 0.25) # 1/4 chance of fireballs
        self.start_time = start_time            # For drop physics
        self.paused = False
        self.prev_pos = 0

# List of Sprite objects, appended and popped as needed. Same is done with
# the GROUP list (below), but they're not 1:1 -- latter has extra elements
# for background, score, etc.
SPRITES = []

# ONE-TIME INITIALIZATION --------------

MACROPAD = MacroPad(rotation=90)
MACROPAD.display.auto_refresh = False
MACROPAD.pixels.auto_write = False

GROUP = displayio.Group(max_size=MAX_EGGS + 10)

# Bitmap containing five shadow tiles (no shadow through max shadow)
BITMAP, PALETTE = adafruit_imageload.load(
    'shadow.bmp', bitmap=displayio.Bitmap, palette=displayio.Palette)
# Tilegrid containing four shadows; one per column
SHADOW = displayio.TileGrid(BITMAP, pixel_shader=PALETTE, width=4, height=1,
                            tile_width=16, tile_height=BITMAP.height,
                            x=0, y=MACROPAD.display.height - BITMAP.height)
GROUP.append(SHADOW)

# Bitmap containing eggs, hatchling and fireballs
SPRITE_BITMAP, SPRITE_PALETTE = adafruit_imageload.load(
    'sprites.bmp', bitmap=displayio.Bitmap, palette=displayio.Palette)
SPRITE_PALETTE.make_transparent(0)

MACROPAD.display.show(GROUP)
MACROPAD.display.refresh()

# Sprite states include falling, paused for catch and paused for breakage.
# Following pause, sprite is removed.


# MAIN LOOP ----------------------------

START_TIME = time.monotonic()

while True:
    NOW = time.monotonic()
    SPEED = 10 + (NOW - START_TIME) / 30

    # Coalese any/all queued-up keypress events per column
    COLUMN_PRESSED = [False] * 4
    while True:
        EVENT = MACROPAD.keys.events.get()
        if not EVENT:
            break
        if EVENT.pressed:
            COLUMN_PRESSED[EVENT.key_number % 4] = True

    # For determining upper/lower extents of active egg sprites per column
    COLUMN_MIN = [MACROPAD.display.height] * 4
    COLUMN_MAX = [0] * 4

#    for i, sprite in enumerate(SPRITES):
    # Traverse sprite list backwards so we can pop() without index problems
    for i in range(len(SPRITES) - 1, -1, -1):
        sprite = SPRITES[i]
        COLUMN = sprite.column
        TILE = GROUP[i + 1]               # Corresponding TileGroup for sprite
        ELAPSED = NOW - sprite.start_time # Time since add or pause event

        if sprite.paused:
            if ELAPSED > 0.75:  # Hold position for 3/4 second
                SPRITES.pop(i)
                GROUP.pop(i + 1)
                continue
            if not sprite.is_fire:
                COLUMN_MAX[COLUMN] = max(COLUMN_MAX[COLUMN], MACROPAD.display.height - 22)
        else:
            y = SPEED * ELAPSED * ELAPSED - 16
            COLUMN_MIN[COLUMN] = min(COLUMN_MIN[COLUMN], y)
            if not sprite.is_fire:
                COLUMN_MAX[COLUMN] = max(COLUMN_MAX[COLUMN], y)
            TILE.y = int(y) # Sprite's vertical position in GROUP list

        if sprite.is_fire:
            if y >= MACROPAD.display.height:
                SPRITES.pop(i)
                GROUP.pop(i + 1)
                continue
            else:
                # Animate fire sprites
                TILE[0] = 3 + int((NOW * 6) % 2.0)
                # Fire catch logic
                if y >= MACROPAD.display.height - 40 and COLUMN_PRESSED[COLUMN]:
                    sprite.paused = True
                    sprite.start_time = NOW
                    TILE.y = MACROPAD.display.height - 20
        else:
            if y >= MACROPAD.display.height - 22:
                # Egg hit ground
                TILE.y = MACROPAD.display.height - 22
                TILE[0] = 1 # Broken egg
                sprite.paused = True
                sprite.start_time = NOW
            elif y >= MACROPAD.display.height - 40:
                if COLUMN_PRESSED[COLUMN]:
                    # Egg caught at right time
                    TILE.y = MACROPAD.display.height - 22
                    TILE[0] = 2 # Dragon hatchling
                    sprite.paused = True
                    sprite.start_time = NOW
            elif y >= MACROPAD.display.height - 58:
                if COLUMN_PRESSED[COLUMN]:
                    # Egg caught too soon
                    TILE.y = MACROPAD.display.height - 40
                    TILE[0] = 1 # Broken egg
                    sprite.paused = True
                    sprite.start_time = NOW

        sprite.prev_pos = y

    # Select shadow bitmaps based on each column's lowest sprite
    for i in range(4):
        SHADOW[i] = min(4, int(5 * COLUMN_MAX[i] / MACROPAD.display.height))

    # Time to introduce a new sprite?
    if len(SPRITES) < MAX_EGGS and random.random() < 0.05:
        if max(COLUMN_MIN) > 16: # At least one column has space
            while True:
                COLUMN = random.randint(0, 3)
                if COLUMN_MIN[COLUMN] <= 16:
                    continue
                # Found a spot. Add sprite and break loop
                SPRITES.append(Sprite(COLUMN, NOW))
                GROUP.append(displayio.TileGrid(SPRITE_BITMAP,
                                                pixel_shader=SPRITE_PALETTE,
                                                width=1, height=1,
                                                tile_width=16,
                                                tile_height=SPRITE_BITMAP.height,
                                                x=COLUMN * 16,
                                                y=-16))
                break

    MACROPAD.display.refresh()
    gc.collect()
