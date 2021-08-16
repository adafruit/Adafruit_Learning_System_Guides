import time
from random import randint
from micropython import const
import board
import terminalio
import displayio
import adafruit_imageload
import digitalio
import simpleio
from gamepadshift import GamePadShift
from adafruit_display_text import label

#  setup for PyBadge buttons
BUTTON_LEFT = const(128)
BUTTON_UP = const(64)
BUTTON_DOWN = const(32)
BUTTON_RIGHT = const(16)
BUTTON_SEL = const(8)
BUTTON_START = const(4)
BUTTON_A = const(2)
BUTTON_B = const(1)

pad = GamePadShift(digitalio.DigitalInOut(board.BUTTON_CLOCK),
                   digitalio.DigitalInOut(board.BUTTON_OUT),
                   digitalio.DigitalInOut(board.BUTTON_LATCH))

current_buttons = pad.get_pressed()
last_read = 0

#  enables speaker
speakerEnable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
speakerEnable.switch_to_output(value=True)

# Sprite cell values
EMPTY = 0
BLINKA_1 = 1
BLINKA_2 = 2
SPARKY = 3
HEART = 4
JUMP_1 = 5
JUMP_2 = 6

#  creates display
display = board.DISPLAY
#  scale=2 allows the sprites to be bigger
group = displayio.Group(scale=2)

#  Blinka sprite setup
blinka, blinka_pal = adafruit_imageload.load("/spritesNew.bmp",
                                             bitmap=displayio.Bitmap,
                                             palette=displayio.Palette)

#  creates a transparent background for Blinka
blinka_pal.make_transparent(7)
blinka_grid = displayio.TileGrid(blinka, pixel_shader=blinka_pal,
                                 width=2, height=1,
                                 tile_height=16, tile_width=16,
                                 default_tile=EMPTY)
blinka_grid.x = 0
blinka_grid.y = 32

blinka_group = displayio.Group()
blinka_group.append(blinka_grid)

#  first Sparky sprite
sparky0, sparky0_pal = adafruit_imageload.load("/spritesNew.bmp",
                                               bitmap=displayio.Bitmap,
                                               palette=displayio.Palette)
sparky0_pal.make_transparent(7)
sparky0_grid = displayio.TileGrid(sparky0, pixel_shader=sparky0_pal,
                                  width=1, height=1,
                                  tile_height=16, tile_width=16,
                                  default_tile=SPARKY)
#  all Sparky sprites begin off screen
sparky0_grid.x = 100
sparky0_grid.y = 32

sparky0_group = displayio.Group()
sparky0_group.append(sparky0_grid)

#  2nd Sparky sprite
sparky1, sparky1_pal = adafruit_imageload.load("/spritesNew.bmp",
                                               bitmap=displayio.Bitmap,
                                               palette=displayio.Palette)
sparky1_pal.make_transparent(7)
sparky1_grid = displayio.TileGrid(sparky1, pixel_shader=sparky1_pal,
                                  width=1, height=1,
                                  tile_height=16, tile_width=16,
                                  default_tile=SPARKY)
sparky1_grid.x = 100
sparky1_grid.y = 32

sparky1_group = displayio.Group()
sparky1_group.append(sparky1_grid)

#  3rd Sparky sprite
sparky2, sparky2_pal = adafruit_imageload.load("/spritesNew.bmp",
                                               bitmap=displayio.Bitmap,
                                               palette=displayio.Palette)
sparky2_pal.make_transparent(7)
sparky2_grid = displayio.TileGrid(sparky2, pixel_shader=sparky2_pal,
                                  width=1, height=1,
                                  tile_height=16, tile_width=16,
                                  default_tile=SPARKY)
sparky2_grid.x = 100
sparky2_grid.y = 32

sparky2_group = displayio.Group()
sparky2_group.append(sparky2_grid)

#  heart sprite group
life_bit, life_pal = adafruit_imageload.load("/spritesNew.bmp",
                                             bitmap=displayio.Bitmap,
                                             palette=displayio.Palette)
life_grid = displayio.TileGrid(life_bit, pixel_shader=life_pal,
                               width=3, height=1,
                               tile_height=16, tile_width=16,
                               default_tile=HEART)

life_group = displayio.Group()
life_group.append(life_grid)

#  adding all graphics groups to the main display group
group.append(blinka_group)
group.append(sparky0_group)
group.append(sparky1_group)
group.append(sparky2_group)
group.append(life_group)

#  text area for the running score
score_text = "      "
font = terminalio.FONT
score_color = 0x0000FF

#  text for "game over" graphic
game_over_text = label.Label(font, text = "         ", color = 0xFF00FF)
# score text
score_area = label.Label(font, text=score_text, color=score_color)
#  text for "new game" graphic
new_game_text = label.Label(font, text = "           ", color = 0xFF00FF)

# coordinants for text areas
score_area.x = 57
score_area.y = 6
game_over_text.x = 13
game_over_text.y = 30
new_game_text.x = 8
new_game_text.y = 30
# creating a text display group
text_group = displayio.Group()
text_group.append(score_area)
text_group.append(game_over_text)
text_group.append(new_game_text)
#  adding text group to main display group
group.append(text_group)

#  displaying main display group
display.show(group)

#  state for hit detection
crash = False
#  states to see if a Sparky is on screen
sparky0 = False
sparky1 = False
sparky2 = False

#  array of Sparky states
sparky_states = [sparky0, sparky1, sparky2]
#  array of x location for Sparky's
sparky_x = [sparky0_grid.x, sparky1_grid.x, sparky2_grid.x]

#  function to display the heart sprites for lives
def life():
    for _ in range(0, 3):
        life_grid[_, 0] = EMPTY
        for hearts in range(life_count):
            life_grid[hearts, 0] = HEART

#  lives at beginning of the game
life_count = 3

#  variables for scoring
jump_score = 0
total_score = 0
bonus = 0
#  state for Blinka being in default 'slither' mode
snake = True
#  state to check if Blinka has jumped over Sparky
cleared = False
#  state for the end of a game
end = False
#  state for a new game beginning
new_game = True
#  state for detecting game over
game_over = False
#  variable to change between Blinka's two slither sprites
b = 1
#  variable to hold time.monotonic() count for Blinka slither animation
slither = 0
#  variables to hold time.monotonic() count to delay Sparky spawning
blue = 0
smoke = 0
monster = 0

while True:

    #  checks if button has been pressed
    if (last_read + 0.01) < time.monotonic():
        buttons = pad.get_pressed()
        last_read = time.monotonic()
    #  new game
    if new_game and not game_over:
        #  graphics for new game splash screen
        blinka_grid.y = 16
        blinka_grid[0] = JUMP_1
        blinka_grid[1] = JUMP_2
        sparky0_grid.x = 5
        sparky1_grid.x = 40
        sparky2_grid.x = 65
        score_area.text = 300
        new_game_text.text = "BLINKA JUMP"
        life()
        #  if start is pressed...
        if current_buttons != buttons:
            if buttons & BUTTON_START:
                #  prepares display for gameplay
                print("start game")
                new_game_text.text = "        "
                life_count = 3
                start = time.monotonic()
                new_game = False
                end = False
                sparky0_grid.x = 100
                sparky1_grid.x = 100
                sparky2_grid.x = 100
    #  if game has started...
    if not game_over and not new_game:
        #  gets time.monotonic() to have a running score
        mono = time.monotonic()
        score = mono - start
        #  adds 10 points every time a Sparky is cleared
        total_score = score + jump_score
        #  displays score as text
        score_area.text = int(total_score)

        #  puts Sparky states and x location into callable arrays
        for s in range(3):
            sparky_state = sparky_states[s]
            sparky_location = sparky_x[s]

        #  Sparkys are generated using a staggered delay
        #  and matching an int to a random int
        #  1st Sparky
        if (blue + 0.03) < time.monotonic():
            if randint(1, 15) == 3:
                sparky_states[0] = True
            blue = time.monotonic()
        #  2nd Sparky
        if (smoke + 0.07) < time.monotonic():
            if randint(1, 15) == 7:
                sparky_states[1] = True
            smoke = time.monotonic()
        #  3rd Sparky
        if (monster + 0.12) < time.monotonic():
            if randint(1, 15) == 12:
                sparky_states[2] = True
            monster = time.monotonic()
        #  if a Sparky is generated, it scrolls across the screen 1 pixel at a time
        #  1st Sparky
        if sparky_states[0] is True:
            sparky0_grid.x -= 1
            sparky_x[0] = sparky0_grid.x
            display.refresh(target_frames_per_second=120)
            #  when a Sparky is 16 pixels off the display,
            #  it goes back to its starting position
            if sparky0_grid.x is -16:
                sparky_states[0] = False
                sparky0_grid.x = 100
                sparky_x[0] = sparky0_grid.x
        #  2nd Sparky
        if sparky_states[1] is True:
            sparky1_grid.x -= 1
            sparky_x[1] = sparky1_grid.x
            display.refresh(target_frames_per_second=120)
            if sparky1_grid.x is -16:
                sparky_states[1] = False
                sparky1_grid.x = 100
                sparky_x[1] = sparky1_grid.x
        #  3rd Sparky
        if sparky_states[2] is True:
            sparky2_grid.x -= 1
            sparky_x[2] = sparky2_grid.x
            display.refresh(target_frames_per_second=120)
            if sparky2_grid.x is -16:
                sparky_states[2] = False
                sparky2_grid.x = 100
                sparky_x[2] = sparky2_grid.x

        #  if no lives are left then the game ends
        if life_count is 0:
            game_over = True

        #  if the A button is pressed then Blinka is no longer in the default
        #  slither animation aka she jumps
        if current_buttons != buttons:
            if buttons & BUTTON_A:
                snake = False

        #  heart sprites are displayed to show life count
        life()

        #  if Blinka is slithering...
        if snake:
            #  Blinka default location
            blinka_grid.y = 32
            #  empty 2nd tile so that the jump sprite can be shown using
            #  the same tilegrid
            blinka_grid[1] = EMPTY
            #  every .15 seconds Blinka's slither sprite changes
            #  so that her slithering is animated
            #  b holds tilegrid position to display correct sprite
            if (slither + 0.15) < time.monotonic():
                blinka_grid[0] = b
                b += 1
                slither = time.monotonic()
            if b > 2:
                b = 1
            #  if a Sparky collides with Blinka while she is slithering...
            for s in range(3):
                if sparky_x[s] == 8 and blinka_grid.y == 32:
                    #  tone is played
                    simpleio.tone(board.SPEAKER, 493.88, 0.05)
                    simpleio.tone(board.SPEAKER, 349.23, 0.05)
                    #  lose a life
                    life_count = life_count - 1
        #  if the A button is pressed then...
        else:
            #  Blinka JUMPS
            #  y location changes one row up and both jump sprites are shown
            blinka_grid.y = 16
            blinka_grid[0] = JUMP_1
            blinka_grid[1] = JUMP_2
            #  if Blinka jumps over a Sparky...
            for j in range(3):
                if sparky_x[j] == 8 and not cleared:
                    #  10 points to the player
                    bonus += 1
                    jump_score = bonus * 10
                    cleared = True
                    #  special victory tone is played
                    simpleio.tone(board.SPEAKER, 523.25, 0.005)
                    simpleio.tone(board.SPEAKER, 783.99, 0.005)
        #  resets back to Blinka animation
        snake = True
        #  resets that Blinka has not jumped over a Sparky
        cleared = False

    #  if there are no more lives, the game is over
    if game_over and not new_game:
        #  game over text is displayed
        game_over_text.text = "GAME OVER"
        score_area.text = "    "
        #  end game tone is played
        #  and then the screen holds with the last
        #  sprites on screen and game over text
        if not end:
            simpleio.tone(board.SPEAKER, 220, 0.05)
            simpleio.tone(board.SPEAKER, 207.65, 0.05)
            simpleio.tone(board.SPEAKER, 196, 0.5)
            end = True

        #  if the start button is pressed...
        if (current_buttons != buttons) and game_over:
            if buttons & BUTTON_START:
                #  display, states and score are reset for gameplay
                game_over_text.text = "        "
                life_count = 3
                start = time.monotonic()
                game_over = False
                end = False
                total_score = 0
                jump_score = 0
                bonus = 0
                score = 0
                blue = 0
                smoke = 0
                monster = 0
                sparky0_grid.x = 100
                sparky1_grid.x = 100
                sparky2_grid.x = 100
                #  game begins again with all Sparky's off screen
