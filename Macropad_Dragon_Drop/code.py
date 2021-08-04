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
import board      # These three can be removed
import audiocore  # if/when MacroPad library
import audiopwmio # adds background audio


# CONFIGURABLES ------------------------

MAX_EGGS = 7          # Max count of all projectiles; some are fireballs
PATH = '/dragondrop/' # Location of graphics, fonts, WAVs, etc.


# UTILITY FUNCTIONS AND CLASSES --------

def background_sound(filename):
    """ Start a WAV file playing in the background (non-blocking). This
        func can be removed if/when MacroPad lib gets background audio. """
    # pylint: disable=protected-access
    MACROPAD._speaker_enable.value = True
    AUDIO.play(audiocore.WaveFile(open(PATH + filename, 'rb')))

def show_screen(group):
    """ Activate a given displayio group, pause until keypress. """
    MACROPAD.display.show(group)
    MACROPAD.display.refresh()
    # Purge any queued up key events...
    while MACROPAD.keys.events.get():
        pass
    while True: # ...then wait for first new key press event
        event = MACROPAD.keys.events.get()
        if event and event.pressed:
            return

# pylint: disable=too-few-public-methods
class Sprite:
    """ Class holds sprite (eggs, fireballs) state information. """
    def __init__(self, col, start_time):
        self.column = col                       # 0-3
        self.is_fire = (random.random() < 0.25) # 1/4 chance of fireballs
        self.start_time = start_time            # For drop physics
        self.paused = False


# ONE-TIME INITIALIZATION --------------

MACROPAD = MacroPad(rotation=90)
MACROPAD.display.auto_refresh = False
MACROPAD.pixels.auto_write = False
MACROPAD.pixels.brightness = 0.5
AUDIO = audiopwmio.PWMAudioOut(board.SPEAKER) # For background audio

FONT = bitmap_font.load_font(PATH + 'cursive-smart.pcf')

# Create 3 displayio groups -- one each for the title, play and end screens.

TITLE_GROUP = displayio.Group()
TITLE_BITMAP, TITLE_PALETTE = adafruit_imageload.load(PATH + 'title.bmp',
                                                      bitmap=displayio.Bitmap,
                                                      palette=displayio.Palette)
TITLE_GROUP.append(displayio.TileGrid(TITLE_BITMAP, pixel_shader=TITLE_PALETTE,
                                      width=1, height=1,
                                      tile_width=TITLE_BITMAP.width,
                                      tile_height=TITLE_BITMAP.height))

# Bitmap containing eggs, hatchling and fireballs
SPRITE_BITMAP, SPRITE_PALETTE = adafruit_imageload.load(
    PATH + 'sprites.bmp', bitmap=displayio.Bitmap, palette=displayio.Palette)
SPRITE_PALETTE.make_transparent(0)

PLAY_GROUP = displayio.Group()
# Bitmap containing five shadow tiles ('no shadow' through 'max shadow')
SHADOW_BITMAP, SHADOW_PALETTE = adafruit_imageload.load(
    PATH + 'shadow.bmp', bitmap=displayio.Bitmap, palette=displayio.Palette)
# Tilegrid with four shadow tiles; one per column
SHADOW = displayio.TileGrid(SHADOW_BITMAP, pixel_shader=SHADOW_PALETTE,
                            width=4, height=1, tile_width=16,
                            tile_height=SHADOW_BITMAP.height, x=0,
                            y=MACROPAD.display.height - SHADOW_BITMAP.height)
PLAY_GROUP.append(SHADOW)
SHADOW_SCALE = 5 / (MACROPAD.display.height - 20) # For picking shadow sprite
LIFE_BAR = HorizontalProgressBar((0, 0), (MACROPAD.display.width, 7),
                                 value=100, min_value=0, max_value=100,
                                 bar_color=0xFFFFFF, outline_color=0xFFFFFF,
                                 fill_color=0, margin_size=1)
PLAY_GROUP.append(LIFE_BAR)
# Score is last object in PLAY_GROUP, can be indexed as -1
PLAY_GROUP.append(label.Label(FONT, text='0', color=0xFFFFFF,
                              anchor_point=(0.5, 0.0),
                              anchored_position=(MACROPAD.display.width // 2,
                                                 10)))

END_GROUP = displayio.Group()
END_BITMAP, END_PALETTE = adafruit_imageload.load(
    PATH + 'gameover.bmp', bitmap=displayio.Bitmap, palette=displayio.Palette)
END_GROUP.append(displayio.TileGrid(END_BITMAP, pixel_shader=END_PALETTE,
                                    width=1, height=1,
                                    tile_width=END_BITMAP.width,
                                    tile_height=END_BITMAP.height))
END_GROUP.append(label.Label(FONT, text='0', color=0xFFFFFF,
                             anchor_point=(0.5, 0.0),
                             anchored_position=(MACROPAD.display.width // 2,
                                                90)))


# MAIN LOOP -- alternates play and end-game screens --------

show_screen(TITLE_GROUP) # Just do this once on startup

while True:

    # NEW GAME -------------------------

    SPRITES = []
    SCORE = 0
    PLAY_GROUP[-1].text = '0' # Score text
    LIFE_BAR.value = 100
    AUDIO.stop()
    MACROPAD.display.show(PLAY_GROUP)
    MACROPAD.display.refresh()
    START_TIME = time.monotonic()

    # PLAY UNTIL LIFE BAR DEPLETED -----

    while LIFE_BAR.value > 0:
        NOW = time.monotonic()
        SPEED = 10 + (NOW - START_TIME) / 30   # Gradually speed up
        FIRE_SPRITE = 3 + int((NOW * 6) % 2.0) # For animating fire

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

        # Traverse sprite list backwards so we can pop() without index problems
        for i in range(len(SPRITES) - 1, -1, -1):
            sprite = SPRITES[i]
            tile = PLAY_GROUP[i + 1] # Corresponding 1x1 TileGrid for sprite
            column = sprite.column
            elapsed = NOW - sprite.start_time # Time since add or pause event

            if sprite.is_fire:
                tile[0] = FIRE_SPRITE # Animate all flame sprites

            if sprite.paused:                # Sprite at bottom of screen
                if elapsed > 0.75:           # Hold position for 3/4 second,
                    for x in range(0, 9, 4): # then LEDs off,
                        MACROPAD.pixels[x + sprite.column] = (0, 0, 0)
                    SPRITES.pop(i)           # and delete Sprite object and
                    PLAY_GROUP.pop(i + 1)    # element from displayio group
                    continue
                if not sprite.is_fire:
                    COLUMN_MAX[column] = max(COLUMN_MAX[column],
                                             MACROPAD.display.height - 22)
            else: # Sprite in motion
                y = SPEED * elapsed * elapsed - 16
                # Track top of all sprites, bottom of eggs only
                COLUMN_MIN[column] = min(COLUMN_MIN[column], y)
                if not sprite.is_fire:
                    COLUMN_MAX[column] = max(COLUMN_MAX[column], y)
                tile.y = int(y) # Sprite's vertical pos. in PLAY_GROUP

                # Handle various catch or off-bottom actions...
                if sprite.is_fire:
                    if y >= MACROPAD.display.height: # Off bottom of screen,
                        SPRITES.pop(i)               # remove fireball sprite
                        PLAY_GROUP.pop(i + 1)
                        continue
                    elif y >= MACROPAD.display.height - 40:
                        if COLUMN_PRESSED[column]:
                            # Fireball caught, ouch!
                            background_sound('sizzle.wav') # I smell bacon
                            sprite.paused = True
                            sprite.start_time = NOW
                            tile.y = MACROPAD.display.height - 20
                            LIFE_BAR.value = max(0, LIFE_BAR.value - 5)
                            for x in range(0, 9, 4):
                                MACROPAD.pixels[x + sprite.column] = (255, 0, 0)
                else: # Is egg...
                    if y >= MACROPAD.display.height - 22:
                        # Egg hit ground
                        background_sound('splat.wav')
                        sprite.paused = True
                        sprite.start_time = NOW
                        tile.y = MACROPAD.display.height - 22
                        tile[0] = 1 # Change sprite to broken egg
                        LIFE_BAR.value = max(0, LIFE_BAR.value - 5)
                        MACROPAD.pixels[8 + sprite.column] = (255, 255, 0)
                    elif COLUMN_PRESSED[column]:
                        if y >= MACROPAD.display.height - 40:
                            # Egg caught at right time
                            background_sound('rawr.wav')
                            sprite.paused = True
                            sprite.start_time = NOW
                            tile.y = MACROPAD.display.height - 22
                            tile[0] = 2 # Hatchling
                            MACROPAD.pixels[4 + sprite.column] = (0, 255, 0)
                            SCORE += 10
                            PLAY_GROUP[-1].text = str(SCORE)
                        elif y >= MACROPAD.display.height - 58:
                            # Egg caught too early
                            background_sound('splat.wav')
                            sprite.paused = True
                            sprite.start_time = NOW
                            tile.y = MACROPAD.display.height - 40
                            tile[0] = 1 # Broken egg
                            LIFE_BAR.value = max(0, LIFE_BAR.value - 5)
                            MACROPAD.pixels[sprite.column] = (255, 255, 0)

        # Select shadow bitmaps based on each column's lowest egg
        for i in range(4):
            SHADOW[i] = min(4, int(COLUMN_MAX[i] * SHADOW_SCALE))

        # Time to introduce a new sprite? 1/20 chance each frame, if space
        if (len(SPRITES) < MAX_EGGS and random.random() < 0.05 and
                max(COLUMN_MIN) > 16):
            # Pick a column randomly...if it's occupied, keep trying...
            while True:
                COLUMN = random.randint(0, 3)
                if COLUMN_MIN[COLUMN] > 16:
                    # Found a clear spot. Add sprite and break loop
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
        MACROPAD.pixels.show()
        if not AUDIO.playing:
            # pylint: disable=protected-access
            MACROPAD._speaker_enable.value = False
        gc.collect()

        # Encoder button pauses/resumes game.
        MACROPAD.encoder_switch_debounced.update()
        if MACROPAD.encoder_switch_debounced.pressed:
            for n in (True, False, True): # Press, release, press
                while n == MACROPAD.encoder_switch_debounced.pressed:
                    MACROPAD.encoder_switch_debounced.update()
            # Sprite start times must be offset by pause duration
            # because time.monotonic() is used for drop physics.
            NOW = time.monotonic() - NOW # Pause duration
            for sprite in SPRITES:
                sprite.start_time += NOW

    # GAME OVER ------------------------

    time.sleep(1.5) # Pause display for a moment
    MACROPAD.pixels.fill(0)
    MACROPAD.pixels.show()
    # pylint: disable=protected-access
    MACROPAD._speaker_enable.value = False
    # Pop any sprites from PLAY_GROUP (other elements remain, and SPRITES[]
    # list is cleared at start of next game).
    for _ in SPRITES:
        PLAY_GROUP.pop(1)
    END_GROUP[-1].text = str(SCORE)
    show_screen(END_GROUP)
