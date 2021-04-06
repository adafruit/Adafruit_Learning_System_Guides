import time
import displayio
from adafruit_circuitplayground import cp
import adafruit_imageload
from adafruit_gizmo import tft_gizmo
from adafruit_display_shapes.circle import Circle

#  setup for the Gizmo TFT
display = tft_gizmo.TFT_Gizmo()

#  loading the background image
bg_bitmap, bg_palette = adafruit_imageload.load("/clouds_bg.bmp",
                                         bitmap=displayio.Bitmap,
                                         palette=displayio.Palette)
bg_grid = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette)

#  loading the crescent moon bitmap sequence
bitmap, palette = adafruit_imageload.load("/moon_anime.bmp",
                                         bitmap=displayio.Bitmap,
                                         palette=displayio.Palette)
#  makes the black background transparent so we only see the cresent moon
palette.make_transparent(0)

tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette, width = 1, height = 1,
                               tile_height = 120, tile_width = 120,
                               default_tile = 0)

#  two circles for the center "jewel"
jewel_outline = Circle(x0=120, y0=120, r=40, fill=0xfbf236)
jewel = Circle(x0=120, y0=120, r=35, fill=0xf70570)

#  adding the two jewel circle elements to a group
jewel_splash = displayio.Group(max_size=20)
jewel_splash.append(jewel_outline)
jewel_splash.append(jewel)

#  making a group for the crescent moon sequence
#  scale is 2 because at full 240x240 resolution image is too big
moon_group = displayio.Group(scale = 2)
#  group to hold all of the display elements
main_group = displayio.Group()

#  adding the crescent moon tile grid to the moon group
moon_group.append(tile_grid)
#  adding the background to the main group
main_group.append(bg_grid)
#  adding the moon group to the main group
main_group.append(moon_group)
#  adding the jewel circles to the main group
main_group.append(jewel_splash)

#  showing the main group on the display
display.show(main_group)

#  tracks the tilegrid index location for the crescent moon
moon = 0
#  holds time.monotonic()
crescent = 0
#  a button debouncing
a_pressed = False
#  b button debouncing
b_pressed = False
#  tracks if music is playing
music_playing = False
#  tracks if animation is paused
animation_pause = False

while True:
    #  button debouncing
    if not cp.button_a and a_pressed:
        a_pressed = False
    if not cp.button_b and b_pressed:
        b_pressed = False
    #  runs crescent moon animation
    if not music_playing and not animation_pause:
        #  every .8 seconds...
        if (crescent + .8) < time.monotonic():
            #  the moon animation cycles
            tile_grid[0] = moon
            #  moon is the tilegrid index location
            moon += 1
            #  resets timer
            crescent = time.monotonic()
            #  resets tilegrid index
            if moon > 35:
                moon = 0
    #  if music is NOT playing and you press the a button...
    if not music_playing and (cp.button_a and not a_pressed):
        #  music begins playing and will loop
        music_playing = True
        a_pressed = True
        print("music playing")
        #  song plays once
        cp.play_file("moonlight_densetsu.wav")
        #  music_playing state is updated
        music_playing = False
    #  if the animation IS playing and you press the b button...
    if not animation_pause and (cp.button_b and not b_pressed):
        #  the animation pauses by updating the animation_pause state
        animation_pause = True
        b_pressed = True
        #  debugging REPL message
        print("animation paused")
    #  if the animation is PAUSED and you press the b button...
    if animation_pause and (cp.button_b and not b_pressed):
        #  the animation begins again by updating the animation_pause state
        animation_pause = False
        b_pressed = True
        #  debugging REPL message
        print("animation running again")
