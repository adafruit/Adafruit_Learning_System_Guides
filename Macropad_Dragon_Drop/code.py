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
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_progressbar.progressbar import HorizontalProgressBar



# CONFIGURABLES ------------------------

MAX_EGGS = 6


# UTILITY FUNCTIONS AND CLASSES --------

AUDIO = None

import audiocore
import audiopwmio
import board
AUDIO = audiopwmio.PWMAudioOut(board.SPEAKER)

def background_sound(filename):
    AUDIO.stop()
    MACROPAD._speaker_enable.value = True
    AUDIO.play(audiocore.WaveFile(open(filename, 'rb')))


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
# the PLAY_GROUP list (below), but they're not 1:1 -- latter has extra
# elements for background, score, etc.
SPRITES = []

# ONE-TIME INITIALIZATION --------------

MACROPAD = MacroPad(rotation=90)
MACROPAD.display.auto_refresh = False
MACROPAD.pixels.auto_write = False

TITLE_GROUP = displayio.Group(max_size=1)
# Bitmap containing title screen
TITLE_BITMAP, TITLE_PALETTE = adafruit_imageload.load(
    'dragondrop/title.bmp', bitmap=displayio.Bitmap, palette=displayio.Palette)
TITLE_GROUP.append(displayio.TileGrid(TITLE_BITMAP, pixel_shader=TITLE_PALETTE, width=1,
                                      height=1, tile_width=TITLE_BITMAP.width,
                                      tile_height=TITLE_BITMAP.height))

PLAY_GROUP = displayio.Group(max_size=MAX_EGGS + 10)

# Bitmap containing five shadow tiles (no shadow through max shadow)
SHADOW_BITMAP, SHADOW_PALETTE = adafruit_imageload.load(
    'dragondrop/shadow.bmp', bitmap=displayio.Bitmap, palette=displayio.Palette)
# Tilegrid containing four shadows; one per column
SHADOW = displayio.TileGrid(SHADOW_BITMAP, pixel_shader=SHADOW_PALETTE, width=4, height=1,
                            tile_width=16, tile_height=SHADOW_BITMAP.height,
                            x=0, y=MACROPAD.display.height - SHADOW_BITMAP.height)
PLAY_GROUP.append(SHADOW)

# Bitmap containing eggs, hatchling and fireballs
SPRITE_BITMAP, SPRITE_PALETTE = adafruit_imageload.load(
    'dragondrop/sprites.bmp', bitmap=displayio.Bitmap, palette=displayio.Palette)
SPRITE_PALETTE.make_transparent(0)

FONT = bitmap_font.load_font("/dragondrop/cursive-smart.pcf")
SCORE_LABEL = label.Label(FONT, text='0', max_glyphs=10, color=0xFFFFFF, anchor_point=(0.5, 0.0), anchored_position=(MACROPAD.display.width // 2, 10))
PLAY_GROUP.append(SCORE_LABEL)

LIFE_BAR = HorizontalProgressBar((0, 0), (MACROPAD.display.width, 7), value=100, min_value=0, max_value=100, bar_color=0xFFFFFF, outline_color=0xFFFFFF, fill_color=0, margin_size=1)
PLAY_GROUP.append(LIFE_BAR)



# Sprite states include falling, paused for catch and paused for breakage.
# Following pause, sprite is removed.


# MAIN LOOP ----------------------------

START_TIME = time.monotonic()

MACROPAD.display.show(TITLE_GROUP)
MACROPAD.display.refresh()
while not MACROPAD.keys.events.get():
    pass

MACROPAD.display.show(PLAY_GROUP)
MACROPAD.display.refresh()
SCORE = 0

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
        TILE = PLAY_GROUP[i + 1] # Corresponding TileGroup for sprite
        ELAPSED = NOW - sprite.start_time # Time since add or pause event

        if sprite.is_fire:
            # Animate fire sprites
            TILE[0] = 3 + int((NOW * 6) % 2.0)

        if sprite.paused:
            if ELAPSED > 0.75:  # Hold position for 3/4 second
                SPRITES.pop(i)
                PLAY_GROUP.pop(i + 1)
                continue
            if not sprite.is_fire:
                COLUMN_MAX[COLUMN] = max(COLUMN_MAX[COLUMN], MACROPAD.display.height - 22)
        else:
            y = SPEED * ELAPSED * ELAPSED - 16
            COLUMN_MIN[COLUMN] = min(COLUMN_MIN[COLUMN], y)
            if not sprite.is_fire:
                COLUMN_MAX[COLUMN] = max(COLUMN_MAX[COLUMN], y)
            TILE.y = int(y) # Sprite's vertical position in PLAY_GROUP list

            if sprite.is_fire:
                if y >= MACROPAD.display.height:
                    SPRITES.pop(i)
                    PLAY_GROUP.pop(i + 1)
                    continue
                else:
                    # Animate fire sprites
                    TILE[0] = 3 + int((NOW * 6) % 2.0)
                    # Fire catch logic
                    if y >= MACROPAD.display.height - 40 and COLUMN_PRESSED[COLUMN]:
                        background_sound('dragondrop/sizzle.wav')

                        sprite.paused = True
                        sprite.start_time = NOW
                        TILE.y = MACROPAD.display.height - 20
                        LIFE_BAR.value = max(0, LIFE_BAR.value - 4)
            else:
                if y >= MACROPAD.display.height - 22:
                    # Egg hit ground
                    background_sound('dragondrop/splat.wav')
                    TILE.y = MACROPAD.display.height - 22
                    TILE[0] = 1 # Broken egg
                    sprite.paused = True
                    sprite.start_time = NOW
                    LIFE_BAR.value = max(0, LIFE_BAR.value - 4)
                elif y >= MACROPAD.display.height - 40:
                    if COLUMN_PRESSED[COLUMN]:
                        # Egg caught at right time
                        background_sound('dragondrop/rawr.wav')
                        TILE.y = MACROPAD.display.height - 22
                        TILE[0] = 2 # Dragon hatchling
                        SCORE += 10
                        SCORE_LABEL.text = str(SCORE)
                        sprite.paused = True
                        sprite.start_time = NOW
                elif y >= MACROPAD.display.height - 58:
                    if COLUMN_PRESSED[COLUMN]:
                        # Egg caught too soon
                        background_sound('dragondrop/splat.wav')
                        TILE.y = MACROPAD.display.height - 40
                        TILE[0] = 1 # Broken egg
                        sprite.paused = True
                        sprite.start_time = NOW
                        LIFE_BAR.value = max(0, LIFE_BAR.value - 4)
    
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
                PLAY_GROUP.insert(-2, displayio.TileGrid(SPRITE_BITMAP,
                                                pixel_shader=SPRITE_PALETTE,
                                                width=1, height=1,
                                                tile_width=16,
                                                tile_height=SPRITE_BITMAP.height,
                                                x=COLUMN * 16,
                                                y=-16))
                break

    MACROPAD.display.refresh()
    if not AUDIO.playing:
        MACROPAD._speaker_enable.value = False
    gc.collect()
