# SPDX-FileCopyrightText: 2021 Phillip Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT

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
    macropad._speaker_enable.value = True
    audio.play(audiocore.WaveFile(open(PATH + filename, 'rb')))

def show_screen(group):
    """ Activate a given displayio group, pause until keypress. """
    macropad.display.root_group = group
    macropad.display.refresh()
    # Purge any queued up key events...
    while macropad.keys.events.get():
        pass
    while True: # ...then wait for first new key press event
        key_event = macropad.keys.events.get()
        if key_event and key_event.pressed:
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

macropad = MacroPad(rotation=90)
macropad.display.auto_refresh = False
macropad.pixels.auto_write = False
macropad.pixels.brightness = 0.5
audio = audiopwmio.PWMAudioOut(board.SPEAKER) # For background audio

font = bitmap_font.load_font(PATH + 'cursive-smart.pcf')

# Create 3 displayio groups -- one each for the title, play and end screens.

title_group = displayio.Group()
title_bitmap, title_palette = adafruit_imageload.load(PATH + 'title.bmp',
                                                      bitmap=displayio.Bitmap,
                                                      palette=displayio.Palette)
title_group.append(displayio.TileGrid(title_bitmap, pixel_shader=title_palette,
                                      width=1, height=1,
                                      tile_width=title_bitmap.width,
                                      tile_height=title_bitmap.height))

# Bitmap containing eggs, hatchling and fireballs
sprite_bitmap, sprite_palette = adafruit_imageload.load(
    PATH + 'sprites.bmp', bitmap=displayio.Bitmap, palette=displayio.Palette)
sprite_palette.make_transparent(0)

play_group = displayio.Group()
# Bitmap containing five shadow tiles ('no shadow' through 'max shadow')
shadow_bitmap, shadow_palette = adafruit_imageload.load(
    PATH + 'shadow.bmp', bitmap=displayio.Bitmap, palette=displayio.Palette)
# Tilegrid with four shadow tiles; one per column
shadow = displayio.TileGrid(shadow_bitmap, pixel_shader=shadow_palette,
                            width=4, height=1, tile_width=16,
                            tile_height=shadow_bitmap.height, x=0,
                            y=macropad.display.height - shadow_bitmap.height)
play_group.append(shadow)
shadow_scale = 5 / (macropad.display.height - 20) # For picking shadow sprite
life_bar = HorizontalProgressBar((0, 0), (macropad.display.width, 7),
                                 value=100, min_value=0, max_value=100,
                                 bar_color=0xFFFFFF, outline_color=0xFFFFFF,
                                 fill_color=0, margin_size=1)
play_group.append(life_bar)
# Score is last object in play_group, can be indexed as -1
play_group.append(label.Label(font, text='0', color=0xFFFFFF,
                              anchor_point=(0.5, 0.0),
                              anchored_position=(macropad.display.width // 2,
                                                 10)))

end_group = displayio.Group()
end_bitmap, end_palette = adafruit_imageload.load(
    PATH + 'gameover.bmp', bitmap=displayio.Bitmap, palette=displayio.Palette)
end_group.append(displayio.TileGrid(end_bitmap, pixel_shader=end_palette,
                                    width=1, height=1,
                                    tile_width=end_bitmap.width,
                                    tile_height=end_bitmap.height))
end_group.append(label.Label(font, text='0', color=0xFFFFFF,
                             anchor_point=(0.5, 0.0),
                             anchored_position=(macropad.display.width // 2,
                                                90)))


# MAIN LOOP -- alternates play and end-game screens --------

show_screen(title_group) # Just do this once on startup

while True:

    # NEW GAME -------------------------

    sprites = []
    score = 0
    play_group[-1].text = '0' # Score text
    life_bar.value = 100
    audio.stop()
    macropad.display.root_group = play_group
    macropad.display.refresh()
    start = time.monotonic()

    # PLAY UNTIL LIFE BAR DEPLETED -----

    while life_bar.value > 0:
        now = time.monotonic()
        speed = 10 + (now - start) / 30   # Gradually speed up
        fire_sprite = 3 + int((now * 6) % 2.0) # For animating fire

        # Coalese any/all queued-up keypress events per column
        column_pressed = [False] * 4
        while True:
            event = macropad.keys.events.get()
            if not event:
                break
            if event.pressed:
                column_pressed[event.key_number % 4] = True

        # For determining upper/lower extents of active egg sprites per column
        column_min = [macropad.display.height] * 4
        column_max = [0] * 4

        # Traverse sprite list backwards so we can pop() without index problems
        for i in range(len(sprites) - 1, -1, -1):
            sprite = sprites[i]
            tile = play_group[i + 1] # Corresponding 1x1 TileGrid for sprite
            column = sprite.column
            elapsed = now - sprite.start_time # Time since add or pause event

            if sprite.is_fire:
                tile[0] = fire_sprite # Animate all flame sprites

            if sprite.paused:                # Sprite at bottom of screen
                if elapsed > 0.75:           # Hold position for 3/4 second,
                    for x in range(0, 9, 4): # then LEDs off,
                        macropad.pixels[x + sprite.column] = (0, 0, 0)
                    sprites.pop(i)           # and delete Sprite object and
                    play_group.pop(i + 1)    # element from displayio group
                    continue
                if not sprite.is_fire:
                    column_max[column] = max(column_max[column],
                                             macropad.display.height - 22)
            else: # Sprite in motion
                y = speed * elapsed * elapsed - 16
                # Track top of all sprites, bottom of eggs only
                column_min[column] = min(column_min[column], y)
                if not sprite.is_fire:
                    column_max[column] = max(column_max[column], y)
                tile.y = int(y) # Sprite's vertical pos. in play_group

                # Handle various catch or off-bottom actions...
                if sprite.is_fire:
                    if y >= macropad.display.height: # Off bottom of screen,
                        sprites.pop(i)               # remove fireball sprite
                        play_group.pop(i + 1)
                        continue
                    if y >= macropad.display.height - 40:
                        if column_pressed[column]:
                            # Fireball caught, ouch!
                            background_sound('sizzle.wav') # I smell bacon
                            sprite.paused = True
                            sprite.start_time = now
                            tile.y = macropad.display.height - 20
                            life_bar.value = max(0, life_bar.value - 5)
                            for x in range(0, 9, 4):
                                macropad.pixels[x + sprite.column] = (255, 0, 0)
                else: # Is egg...
                    if y >= macropad.display.height - 22:
                        # Egg hit ground
                        background_sound('splat.wav')
                        sprite.paused = True
                        sprite.start_time = now
                        tile.y = macropad.display.height - 22
                        tile[0] = 1 # Change sprite to broken egg
                        life_bar.value = max(0, life_bar.value - 5)
                        macropad.pixels[8 + sprite.column] = (255, 255, 0)
                    elif column_pressed[column]:
                        if y >= macropad.display.height - 40:
                            # Egg caught at right time
                            background_sound('rawr.wav')
                            sprite.paused = True
                            sprite.start_time = now
                            tile.y = macropad.display.height - 22
                            tile[0] = 2 # Hatchling
                            macropad.pixels[4 + sprite.column] = (0, 255, 0)
                            score += 10
                            play_group[-1].text = str(score)
                        elif y >= macropad.display.height - 58:
                            # Egg caught too early
                            background_sound('splat.wav')
                            sprite.paused = True
                            sprite.start_time = now
                            tile.y = macropad.display.height - 40
                            tile[0] = 1 # Broken egg
                            life_bar.value = max(0, life_bar.value - 5)
                            macropad.pixels[sprite.column] = (255, 255, 0)

        # Select shadow bitmaps based on each column's lowest egg
        for i in range(4):
            shadow[i] = min(4, int(column_max[i] * shadow_scale))

        # Time to introduce a new sprite? 1/20 chance each frame, if space
        if (len(sprites) < MAX_EGGS and random.random() < 0.05 and
                max(column_min) > 16):
            # Pick a column randomly...if it's occupied, keep trying...
            while True:
                column = random.randint(0, 3)
                if column_min[column] > 16:
                    # Found a clear spot. Add sprite and break loop
                    sprites.append(Sprite(column, now))
                    play_group.insert(-2, displayio.TileGrid(sprite_bitmap,
                                                             pixel_shader=sprite_palette,
                                                             width=1, height=1,
                                                             tile_width=16,
                                                             tile_height=sprite_bitmap.height,
                                                             x=column * 16,
                                                             y=-16))
                    break

        macropad.display.refresh()
        macropad.pixels.show()
        if not audio.playing:
            # pylint: disable=protected-access
            macropad._speaker_enable.value = False
        gc.collect()

        # Encoder button pauses/resumes game.
        macropad.encoder_switch_debounced.update()
        if macropad.encoder_switch_debounced.pressed:
            for n in (True, False, True): # Press, release, press
                while n == macropad.encoder_switch_debounced.pressed:
                    macropad.encoder_switch_debounced.update()
            # Sprite start times must be offset by pause duration
            # because time.monotonic() is used for drop physics.
            now = time.monotonic() - now # Pause duration
            for sprite in sprites:
                sprite.start_time += now

    # GAME OVER ------------------------

    time.sleep(1.5) # Pause display for a moment
    macropad.pixels.fill(0)
    macropad.pixels.show()
    # pylint: disable=protected-access
    macropad._speaker_enable.value = False
    # Pop any sprites from play_group (other elements remain, and sprites[]
    # list is cleared at start of next game).
    for _ in sprites:
        play_group.pop(1)
    end_group[-1].text = str(score)
    show_screen(end_group)
