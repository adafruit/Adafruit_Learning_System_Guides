"""
Dragon Drop: a simple game for Adafruit MACROPAD. Uses OLED display in
portrait (vertical) orientation. Tap one of four keys across a row to
catch falling eggs before they hit the ground.
"""

# pylint: disable=import-error, unused-import
import random
import time
import displayio
import adafruit_imageload
from adafruit_macropad import MacroPad
#from adafruit_display_shapes.rect import Rect
#from adafruit_display_text import label


# CONFIGURABLES ------------------------

MAX_EGGS = 20


# UTILITY FUNCTIONS AND CLASSES --------

class Sprite:
    def __init__(self, tile):
        self.column = 0
        self.is_fire = 0
        self.state = 0
        self.y = 0.0
        self.v = 0.0
        self.tile = tile
        self.start_time = 0.0

# ONE-TIME INITIALIZATION --------------

MACROPAD = MacroPad(rotation=90)
MACROPAD.display.auto_refresh = False
MACROPAD.pixels.auto_write = False

GROUP = displayio.Group(max_size=MAX_EGGS + 10)

# Bitmap containing five shadow tiles (no shadow through max shadow)
bitmap, palette = adafruit_imageload.load(
    'shadow.bmp', bitmap=displayio.Bitmap, palette=displayio.Palette)
# Tilegrid containing four shadows; one per column
shadow = displayio.TileGrid(bitmap, pixel_shader=palette, width=4, height=1,
           tile_width=16, tile_height=bitmap.height, default_tile=0, x=0,
           y=MACROPAD.display.height - bitmap.height)
GROUP.append(shadow)

# Bitmap containing eggs, hatchling and fireballs
bitmap, palette = adafruit_imageload.load(
    'sprites.bmp', bitmap=displayio.Bitmap, palette=displayio.Palette)
palette.make_transparent(0)

ACTIVE_SPRITES = 0
SPRITE = []
for i in range(MAX_EGGS):
    GROUP.append(displayio.TileGrid(bitmap, pixel_shader=palette, width=1,
                                    height=1, tile_width=16,
                                    tile_height=bitmap.height, default_tile=4,
                                    x=MACROPAD.display.width,
                                    y=MACROPAD.display.height))
    SPRITE.append(Sprite(GROUP[len(GROUP) - 1]))


MACROPAD.display.show(GROUP)
MACROPAD.display.refresh()


# MAIN LOOP ----------------------------

COLUMN_PRESSED = [False] * 4
COLUMN_MIN = [0] * 4
COLUMN_MAX = [0] * 4

while True:
    NOW = time.monotonic()

    # Find the min/max vertical bounds of sprites per-column
    for i in range(4):
        COLUMN_MIN[i], COLUMN_MAX[i] = MACROPAD.display.height, 0
    for i in range(ACTIVE_SPRITES):
        column = SPRITE[i].column
        COLUMN_MIN[column] = min(COLUMN_MIN[column], SPRITE[i].y)
        COLUMN_MAX[column] = max(COLUMN_MAX[column], SPRITE[i].y)
    # Select shadow bitmaps based on each column's lowest sprite
    for i in range(4):
        shadow[i] = int(5 * COLUMN_MAX[i] / MACROPAD.display.height)
        
    # Time to introduce a new sprite?
    if ACTIVE_SPRITES < MAX_EGGS and random.random() < 0.01:
        if max(COLUMN_MIN) > 16: # At least one column has space
            while True:
                column = random.randint(0, 3)
                if COLUMN_MIN[column] <= 16:
                    continue
                # Found a spot. Add sprite and break loop
                SPRITE[ACTIVE_SPRITES].column = column
                SPRITE[ACTIVE_SPRITES].is_fire = (random.random() < 0.25)
                SPRITE[i].tile[0] = 0 # Egg
                SPRITE[ACTIVE_SPRITES].y = 0.0
                SPRITE[ACTIVE_SPRITES].v = 0.0
                SPRITE[ACTIVE_SPRITES].start_time = NOW
                ACTIVE_SPRITES += 1
                break

    # Coalese any/all queued-up keypress events per column
    for x in range(4):
        COLUMN_PRESSED[x] = False
    while True:
        EVENT = MACROPAD.keys.events.get()
        if not EVENT:
            break
        if EVENT.pressed:
            COLUMN_PRESSED[EVENT.key_number % 4] = True
    if True in COLUMN_PRESSED:
        print(COLUMN_PRESSED)

    for i in range(ACTIVE_SPRITES):
        if SPRITE[i].is_fire:
            SPRITE[i].tile[0] = 3 + int((NOW * 4) % 2.0)
        SPRITE[i].y += SPRITE[i].v
# Ugh, this isn't right, need to reorder group too
        if SPRITE[i].y >= MACROPAD.display.height:
            SPRITE[i].tile[0] = 0
            SPRITE[i].x = MACROPAD.display.width # Move offscreen
            SPRITE[ACTIVE_SPRITES - 1], SPRITE[i] = SPRITE[i], SPRITE[ACTIVE_SPRITES - 1]
            ACTIVE_SPRITES -= 1
        SPRITE[i].v += 0.1
        SPRITE[i].tile.x = SPRITE[i].column * 16
        SPRITE[i].tile.y = int(SPRITE[i].y)

    MACROPAD.display.refresh()
