# SPDX-FileCopyrightText: 2024 Tim Cocks
#
# SPDX-License-Identifier: MIT
import random
import time
import terminalio
import displayio
from adafruit_display_text.bitmap_label import Label
import adafruit_imageload
import foamyguy_nvm_helper as nvm_helper


class Entity:
    """
    Entity helper class holds a TileGrid and keeps track of direction and a set of current sprites.
    Includes functions for iterating through the sprites to make animations and
    for checking on collissions with other Entities. 
    """

    # Direction Constants
    DIRECTION_UP = 0
    DIRECTION_RIGHT = 1
    DIRECTION_LEFT = 2
    DIRECTION_DOWN = 3
    DIRECTION_NONE = 4

    def __init__(
            self,
            bitmap: displayio.Bitmap,
            pixel_shader: displayio.Palette,
            width: int = 1,
            height: int = 1,
            tile_width: int = 15,
            tile_height: int = 15,
            default_tile: int = 0
    ):
        # default direction is NONE subclasses can override it
        self._direction = self.DIRECTION_NONE

        # initialize the tilegrid for showing sprite(s)
        self._tilegrid = displayio.TileGrid(
            bitmap,
            pixel_shader=pixel_shader,
            width=width,
            height=height,
            tile_width=tile_width,
            tile_height=tile_height,
            default_tile=default_tile,
        )

        # keep property variables for size
        self.width = tile_width * width
        self.height = tile_height * height

        # sprites for the animation (None by default, subclasses or game activity can change them)
        self.current_sprites = []
        self.sprite_index = 0

    def next_sprite(self):
        """
        Advance to the next sprite in the sequence for animation.
        :return: None
        """
        self.sprite_index += 1
        if self.sprite_index >= len(self.current_sprites):
            self.sprite_index = 0
        self._tilegrid[0, 0] = self.current_sprites[self.sprite_index]

    @property
    def x(self):
        """
        X pixel position of the tilegrid on the display
        :return: int x location
        """
        return self._tilegrid.x

    @property
    def y(self):
        """
        Y pixel position of the tilegrid on the display
        :return: int y location
        """
        return self._tilegrid.y

    @x.setter
    def x(self, new_x):
        self._tilegrid.x = new_x

    @y.setter
    def y(self, new_y):
        # print("y setter")
        self._tilegrid.y = new_y

    @property
    def tilegrid(self):
        """
        The tilegrid used to show sprite(s)
        :return: TileGrid
        """
        return self._tilegrid

    def is_colliding(self, _other_entity):
        """
        Check if this entity is colliding with another entity.
        :param _other_entity: another entity to check ourself against
        :return: True if this instance is colidding with the _other_entity
        """
        _colliding_x = False
        _colliding_y = False
        length_x = abs(self.x - _other_entity.x)
        half_width_self = self.width / 2
        half_width_other = _other_entity.width / 2

        gap_between = length_x - half_width_self - half_width_other
        if (gap_between > 0):
            pass
        elif (gap_between == 0):
            pass
        elif (gap_between < 0):
            _colliding_x = True

        length_y = abs(self.y - _other_entity.y)
        half_height_self = self.height / 2
        half_height_other = _other_entity.height / 2

        gap_between = length_y - half_height_self - half_height_other
        if (gap_between > 0):
            pass
        elif (gap_between == 0):
            pass
        elif (gap_between < 0):
            _colliding_y = True

        # print("colliding x: {} - y: {}".format(_colliding_x, _colliding_y))

        return _colliding_x and _colliding_y

    def game_tick(self, game_obj):
        """
        Subclasses override this to add behavior to the entity.
        :return:
        """


class Ghost(Entity):
    """
    Ghost helper class manages behavior and graphics for the enemy ghost.
    """

    # Time based variables
    ANIMATION_DELAY = 100  # ms
    MOVE_DELAY = 8  # ms
    EDIBLE_DURATION = 2000  # ms
    EDIBLE_WARNING_DURATION = 1000  # ms

    # state machine state variables:

    # normal ghost eats pacman and results in gameover
    STATE_NORMAL = 0

    # edible ghost can be eaten by pacman for points
    STATE_EDIBLE = 1

    # edible warning state blinks the ghost to warn player
    STATE_EDIBLE_WARNING = 2

    # after the ghost is eaten by pacman its eyes fly off the screen
    STATE_DESPAWN_FLYOFF = 3

    def __init__(self, bitmap: displayio.Bitmap, pixel_shader: displayio.Palette, *args, **kwargs):
        """
        :param bitmap: sprite Bitmap object
        :param pixel_shader: sprite palette
        :param args: any other positional arguments to pass to parent class
        :param kwargs: any other keyword arguments to pass to parent class
        """
        super().__init__(bitmap, pixel_shader, *args, **kwargs)

        # last time we moved
        self.last_move_time = time.monotonic()

        # whether we are edible
        self._edible = False

        # when we turned edible
        self.turned_edible_at = None

        # when we need to start blinking
        self.edible_warn_time = None

        # last time we blinked
        self.last_animation_time = 0

        # state machine current state
        self.current_state = Ghost.STATE_NORMAL

    @property
    def edible(self):
        """
        Whether the ghost is edible
        :return: True if ghost is edible otherwise False
        """
        return self._edible

    @edible.setter
    def edible(self, new_val):
        # if ghost is becoming edible
        if new_val:
            # set the sprite to blue ghost
            self.tilegrid[0, 0] = 18

            # current timestamp
            # now = ticks_ms()
            now = time.monotonic_ns() // 1000000

            # save timestampe we turned edible
            self.turned_edible_at = now

            # set the time we need to start blinking
            self.edible_warn_time = now + (Ghost.EDIBLE_DURATION - Ghost.EDIBLE_WARNING_DURATION)

        # if ghost is becoming non-edible
        else:
            # set the sprite to normal red ghost
            self.tilegrid[0, 0] = 12

            # clear out the turned edible at timestamp
            self.turned_edible_at = None

        # update the _edible boolean
        self._edible = new_val

    def game_tick(self, game_obj):
        """
        Main behavior action function for the Ghost. Gets called by ChomperGame.game_tick().
        Checks the current state and acts accordingly.
        :param game_obj: The ChomperGame object to access variables and update things
        :return: True if the action resulted in display needing to be refreshed, otherwise False
        """
        # now = ticks_ms()
        now = time.monotonic_ns() // 1000000
        need_refresh = False

        # Top level if statements to check current state within the state machine

        # process movement for normal, edible, and blinking states
        if self.current_state in (Ghost.STATE_NORMAL, Ghost.STATE_EDIBLE, Ghost.STATE_EDIBLE_WARNING):

            # if it's been long enough since the last movement
            if now > self.last_move_time + Ghost.MOVE_DELAY:
                # update the last moved timestamp
                self.last_move_time = now

                # Check direction and prevent Ghost from moving thru the edges
                if self.x < (game_obj.display_size[0] // 3) - 16 and self.direction == Entity.DIRECTION_RIGHT:
                    # we're moving right, increase x position
                    self.x += 1
                if self.x > 0 and self.direction == Entity.DIRECTION_LEFT:
                    # we're moving left, decrease x position
                    self.x -= 1

                need_refresh = True

        # normal state ghost faces toward the player to chase them
        if self.current_state == Ghost.STATE_NORMAL:
            if self.x < game_obj.player_entity.x:
                self.direction = Entity.DIRECTION_RIGHT
            elif self.x > game_obj.player_entity.x:
                self.direction = Entity.DIRECTION_LEFT

        # edible and blinking faces away from the player to run away from them
        elif self.current_state in (Ghost.STATE_EDIBLE, Ghost.STATE_EDIBLE_WARNING):
            if self.x < game_obj.player_entity.x:
                self.direction = Entity.DIRECTION_LEFT
            else:
                self.direction = Entity.DIRECTION_RIGHT

        # edible state needs to determine when to blink
        if self.current_state == Ghost.STATE_EDIBLE:
            # if it's time to start warning blinks
            if self.edible_warn_time and now > self.edible_warn_time:
                # set sprites to blue and white ghosts for blinking
                self.current_sprites = (19, 18)
                # update the state machine current state variable
                self.current_state = Ghost.STATE_EDIBLE_WARNING

        # blinking state needs to animate sprites and determine
        # when to go back to normal state
        if self.current_state == Ghost.STATE_EDIBLE_WARNING:
            # if it's time to change sprites for the animation
            if now > self.last_animation_time + Ghost.ANIMATION_DELAY:
                # change to next sprite in the animation
                self.next_sprite()

            # if it's time to go back to normal
            if self.turned_edible_at and now > self.turned_edible_at + Ghost.EDIBLE_DURATION:
                # update the sprite to normal red ghost
                self.tilegrid[0, 0] = 12

                # set edible property and state machine variable
                self.edible = False
                self.current_state = Ghost.STATE_NORMAL

        # despawn flyoff state needs to fly the eyes off the screen
        # and determine when to respawn the new ghost
        if self.current_state == Ghost.STATE_DESPAWN_FLYOFF:
            # if it's time to move the eyes
            if now > self.last_move_time + Ghost.MOVE_DELAY:
                self.last_move_time = now

                # check direction and move. Stopping at the edge
                if self.x < game_obj.display_size[0] // 3 and self.direction == Entity.DIRECTION_RIGHT:
                    self.x += 2
                if self.x > 0 and self.direction == Entity.DIRECTION_LEFT:
                    self.x -= 2

                # if we hit the edge, it's time to respawn a new Ghost
                if self.x <= 0 or self.x >= game_obj.display_size[0] // 3:
                    # set the state to normal
                    self.current_state = Ghost.STATE_NORMAL

                    # clear out the warning timestamp
                    self.edible_warn_time = None

                    # set the sprite to normal red ghost
                    self.tilegrid[0, 0] = 12

                    # set edible property false for new ghost
                    self.edible = False

                    # spawn the new ghost at the edge furthest away from the player
                    spawn_left = game_obj.player_entity.x >= (game_obj.display_size[0] // 2) // 3
                    if spawn_left:
                        self.x = 0
                    else:
                        self.x = 21 * 15

        return need_refresh


class Player(Entity):
    """
    Player helper class manages behavior and graphics for the player character.
    """

    ANIMATION_DELAY = 200  # ms between chomp animation
    MOVE_DELAY = 6  # ms between movement steps

    RIGHT_SPRITES = (0, 5)
    LEFT_SPRITES = (2, 7)
    UP_SPRITES = (1, 6)
    DOWN_SPRITES = (3, 8)

    def __init__(self, bitmap: displayio.Bitmap, pixel_shader: displayio.Palette, *args, **kwargs):
        super().__init__(bitmap, pixel_shader, *args, **kwargs)
        # now = ticks_ms()
        now = time.monotonic_ns() // 1000000

        # initialize the movement and animation timestamps
        self.last_animation_time = now
        self.last_move_time = now

    def game_tick(self, game_obj):
        """
        Main behavior function for Player movement
        :param game_obj: ChomperGame object for accessing variables and changing things
        :return: True if the tick results in the display needing to be refreshed, otherwise False
        """

        # now = ticks_ms()
        now = time.monotonic_ns() // 1000000

        # if it's been long enough since the last movement
        if now > self.last_move_time + Player.MOVE_DELAY:
            # update the last moved timestamp
            self.last_move_time = now

            # if it's been long enough since the last aninmation sprite frame
            if self.last_animation_time + Player.ANIMATION_DELAY < now:
                # change sprites
                self.next_sprite()
                # update animation timestmp
                self.last_animation_time = now

            if self.direction == Entity.DIRECTION_RIGHT:
                # we're moving right, x location increases
                self.x += 1

            if self.direction == Entity.DIRECTION_LEFT:
                # we're moving left, x location decreases
                self.x -= 1

            # if we made it to an edge, teleport to the other side
            if self.x < 0 - self.width:
                self.x = game_obj.display_size[0] // 3
            elif self.x > game_obj.display_size[0] // 3:
                self.x = 0
            return True
        return False

    @property
    def direction(self):
        """
        whether the player is facing left or right
        :return: either Entity.DIRECTION_LEFT or Entity.DIRECTION_RIGHT
        """
        return self._direction

    @direction.setter
    def direction(self, new_direction):
        """
        Update the direction of the player
        :param new_direction: Entity.DIRECTION_LEFT or Entity.DIRECTION_Right
        :return: None
        """

        # update the sprites for chomp animation based on new direction
        if new_direction == self.DIRECTION_RIGHT:
            self.current_sprites = self.RIGHT_SPRITES
        if new_direction == self.DIRECTION_LEFT:
            self.current_sprites = self.LEFT_SPRITES

        # update direction variable
        self._direction = new_direction


class ChomperGame(displayio.Group):
    """
    Game helper class manages behavior and graphics for the entire game.
    Extends displayio.Group so it can be shown on a display directly, or
    added to another Group to be shown. Also supports Group scaling which
    is used by default at scale=3.
    """

    EMPTY_MAP_TILE = 17
    PLAYER_TILE = 0

    EASY_DIFFICULTY_THRESHOLD = 5
    MEDIUM_DIFFICULTY_THRESHOLD = 10
    HARD_DIFFICULTY_THRESHOLD = 20
    VERYHARD_DIFFICULTY_THRESHOLD = 40
    INSANE_DIFFICULTY_THRESHOLD = 80

    def __init__(
            self,
            display_size,
    ):
        super().__init__()

        # variables for score and multiplier
        self.score = 0
        self.multiplier = 1

        # display_size tuple referenced to know where the edges of the map are
        self.display_size = display_size

        # boolean for game over state
        self.game_over = False

        # Load the sprite sheet (bitmap)
        self._sprite_sheet, self._palette = adafruit_imageload.load("1d_chomper_spritesheet.bmp")

        # "green screen" transparent color
        self._palette.make_transparent(0)

        # sprites are 15px square
        self._tile_width = 15
        self._tile_height = 15

        # Create the background TileGrid. It will be flat black
        # with everything else drawn on top.
        self._background_tilegrid = displayio.TileGrid(self._sprite_sheet, pixel_shader=self._palette,
                                                       width=21,
                                                       height=3,
                                                       tile_width=self._tile_width,
                                                       tile_height=self._tile_height,
                                                       default_tile=ChomperGame.EMPTY_MAP_TILE)

        # Create the map TileGrid. It will contain the blue line walls, pellets, and empty tiles
        self._map_tilegrid = displayio.TileGrid(self._sprite_sheet, pixel_shader=self._palette,
                                                width=21,
                                                height=3,
                                                tile_width=self._tile_width,
                                                tile_height=self._tile_height,
                                                default_tile=ChomperGame.EMPTY_MAP_TILE)

        self._map_tilegrid.x = 2
        self._map_tilegrid.y = 12

        # spawn the top and bottom wall tiles
        for i in range(21):
            self._map_tilegrid[i, 0] = 13
            self._map_tilegrid[i, 2] = 13

        # create the pellets and keep a variable to count them
        self.spawn_pellets()
        self.pellets_in_play = 21

        # create player object
        self._player_entity = Player(
            self._sprite_sheet, pixel_shader=self._palette,
            width=1,
            height=1,
            tile_width=self._tile_width,
            tile_height=self._tile_height,
            default_tile=ChomperGame.PLAYER_TILE
        )
        self._player_entity.y = 12 + 15

        # add tilegrids to self Group instance
        self.append(self._background_tilegrid)
        self.append(self._map_tilegrid)
        self.append(self._player_entity.tilegrid)

        # create the ghost object
        ghost = Ghost(self._sprite_sheet, self._palette, default_tile=12)
        ghost.direction = Entity.DIRECTION_LEFT
        ghost.x = 21 * 15
        ghost.y = 12 + 15
        self.append(ghost.tilegrid)
        self.ghost = ghost

        # create labels for score, multiplier, highscore and gameover

        # Score label, top left
        self.score_lbl = Label(terminalio.FONT, text="Score:")
        self.score_lbl.anchor_point = (0, 0)
        self.score_lbl.anchored_position = (1, 1)
        self.append(self.score_lbl)

        # Score Value, top left
        self.score_value_lbl = Label(terminalio.FONT, text="0")
        self.score_value_lbl.anchor_point = (0, 0)
        self.score_value_lbl.anchored_position = (40, 1)
        self.append(self.score_value_lbl)

        # Multiplier label, top middle
        self.multiplier_lbl = Label(terminalio.FONT, text="x")
        self.multiplier_lbl.anchor_point = (0, 0)
        self.multiplier_lbl.anchored_position = (110, 1)
        self.append(self.multiplier_lbl)

        # Multiplier value, top middle
        self.multiplier_value_lbl = Label(terminalio.FONT, text="0")
        self.multiplier_value_lbl.anchor_point = (0, 0)
        self.multiplier_value_lbl.anchored_position = (118, 1)
        self.append(self.multiplier_value_lbl)

        # Gameover, bottom middle
        self.gameover_lbl = Label(terminalio.FONT, text="Game Over")
        self.gameover_lbl.anchor_point = (0.5, 1.0)
        self.gameover_lbl.anchored_position = ((self.display_size[0] // 2) // 3, self.display_size[1] // 3 - 5)

        # Highscore, top right.
        # Doesn't need separate label and value because it doesn't update during the game loop
        self.highscore_value_lbl = Label(terminalio.FONT, text="HI: 100")
        self.highscore_value_lbl.anchor_point = (1.0, 0)
        self.highscore_value_lbl.anchored_position = ((self.display_size[0] // 3) - 4, 1)
        self.append(self.highscore_value_lbl)
        self.highscore = 0

        try:
            # read data from NVM storage
            read_data = nvm_helper.read_data()

            # if we found data check if it's a highscore value
            if type(read_data) == list and read_data[0] == "1dc_hs":
                # it is a highscore so populate the label with its value
                self.highscore_value_lbl.text = f"HI: {read_data[1]}"
                self.highscore = read_data[1]

        except EOFError:
            # No saved Highscore
            pass

    def update_score(self):
        """
        Update the score and multiplier value labels with teir current values
        :return: None
        """
        self.score_value_lbl.text = str(self.score)
        self.multiplier_value_lbl.text = str(self.multiplier)

    def change_map_tile(self, tile_coords, new_tile_index):
        """
        Change a tile on the map to a different type
        :param tile_coords: Tuple (x, y) of coordinates in the map tilegrid to change
        :param new_tile_index: int new tile index value to set at the specified location
        :return: None
        """
        self._map_tilegrid[tile_coords[0], tile_coords[1]] = new_tile_index

    @property
    def player_entity(self):
        """
        The player entity helper object
        :return: Player object
        """
        return self._player_entity

    def spawn_pellets(self):
        """
        Fill the center row of the map with pellets. One is randomly
        chosen to be a big pellet instead of small.
        :return: None
        """
        # random choice for big pellet
        big_pellet_loc = random.randint(0, 20)

        # loop over tiles
        for i in range(21):
            if big_pellet_loc == i:
                # set the big pellet in its chosen location
                self._map_tilegrid[i, 1] = 9
            else:
                # set small pellets everywhere else
                self._map_tilegrid[i, 1] = 4

        # reset the pellet counter variable
        self.pellets_in_play = 21

    def game_tick(self):
        """
        Main "heartbeat" function of the game. This will get called over and over from the
        main code.py file. game_tick() is responsible for carrying out all game logic and
        updating visible components.
        :return: None
        """
        # if the game is over just return so nothing else happens.
        # game is effectively paused during game over, waiting on
        # the player to start a new game.
        if self.game_over:
            return
        # print(ticks_ms())
        # player takes action
        self.player_entity.game_tick(self)

        # player location in tile coordinate space
        if self.player_entity.direction == Entity.DIRECTION_LEFT:
            current_coords = (self.player_entity.x // 15, 1)
        elif self.player_entity.direction == Entity.DIRECTION_RIGHT:
            current_coords = ((self.player_entity.x + 1) // 15, 1)

        try:
            # check the tile type at the player's location
            current_tile_type = self._map_tilegrid[current_coords]
        except IndexError:
            # player is teleporting between sides right now
            current_tile_type = ChomperGame.EMPTY_MAP_TILE

        # if it's a pellet
        if current_tile_type in (4, 9):  # pellet, big pellet
            # remove the pellet, set the tile to empty
            self.change_map_tile(current_coords, ChomperGame.EMPTY_MAP_TILE)

            # add points to score
            self.score += 1 * self.multiplier

            # subtract a pellet from the count variable
            self.pellets_in_play -= 1

            # if the last pellet was eaten
            if self.pellets_in_play == 0:
                # make new pellets
                self.spawn_pellets()

                # add 1 to the multiplier
                self.multiplier += 1

                # increase difficulty if we reached a threshold
                if self.multiplier == ChomperGame.EASY_DIFFICULTY_THRESHOLD:
                    self.ghost.MOVE_DELAY -= 1
                if self.multiplier == ChomperGame.MEDIUM_DIFFICULTY_THRESHOLD:
                    self.ghost.MOVE_DELAY -= 1
                if self.multiplier == ChomperGame.HARD_DIFFICULTY_THRESHOLD:
                    self.ghost.MOVE_DELAY -= 1
                    self.player_entity.MOVE_DELAY -= 1
                if self.multiplier == ChomperGame.VERYHARD_DIFFICULTY_THRESHOLD:
                    self.ghost.MOVE_DELAY -= 1
                if self.multiplier == ChomperGame.INSANE_DIFFICULTY_THRESHOLD:
                    self.ghost.MOVE_DELAY -= 1

            # update the score labels in the UI
            self.update_score()

            # if it was a big pellet
            if current_tile_type == 9:
                # if the ghost is currently normal state, it becomes edible
                if self.ghost.current_state in (Ghost.STATE_NORMAL, Ghost.STATE_EDIBLE, Ghost.STATE_EDIBLE_WARNING):
                    # set the state and edible property
                    self.ghost.current_state = Ghost.STATE_EDIBLE
                    self.ghost.edible = True

        # ghost takes action
        self.ghost.game_tick(self)

        # if the player is touching the ghost and the ghost isn't currently flying off to despawn
        if self.player_entity.is_colliding(self.ghost) \
                and not self.ghost.current_state == Ghost.STATE_DESPAWN_FLYOFF:

            # if the ghost is in normal state, non-edible
            if not self.ghost.edible:
                # set the gameover boolean
                self.game_over = True

                # show the gameover text at bottom middle of display
                self.append(self.gameover_lbl)

                # if the score is greater than the previous highscore
                if self.score > self.highscore:
                    # save new high score value to NVM storage
                    nvm_helper.save_data(("1dc_hs", self.score), test_run=False)

                    # update the highscore variable for comparison after the next game
                    self.highscore = self.score

                    # update the highscore text in the UI
                    self.highscore_value_lbl.text = f"HI: {self.highscore}"

                # sleep a bit to ignore any btn presses that were intended for turning,
                # not starting next game.
                time.sleep(0.5)

            else:  # ghost is edible, nomnomnom

                # set the ghost state to despawn flyoff
                self.ghost.current_state = Ghost.STATE_DESPAWN_FLYOFF

                # change ghost's direction
                self.ghost.direction = Entity.DIRECTION_LEFT if self.ghost.direction == Entity.DIRECTION_RIGHT else Entity.DIRECTION_RIGHT

                # set the ghost sprite to eyes only
                self.ghost.tilegrid[0, 0] = 23

                # add points to player's score
                self.score += 2 * self.multiplier

                # if there are no big pellets on the map
                if not self.big_pellet_exists():
                    # convert one small pellet to a big one
                    self.convert_pellet_to_big()

    def convert_pellet_to_big(self):
        """
        Convert a random existing small pellet to a big one
        :return: None
        """

        # check which pellets are currently up
        pellet_locs = self.find_pellets()

        # choose a random one of them
        chosen_pellet = random.choice(pellet_locs)

        # update it's sprite to big pellet
        self._map_tilegrid[chosen_pellet, 1] = 9

    def big_pellet_exists(self):
        """
        Check if any big pellets exist
        :return: True if there is at least one big pellet on the map 
        """
        for i in range(21):
            if self._map_tilegrid[i, 1] == 9:
                return True

    def find_pellets(self):
        """
        Find all pellet locations
        :return: List of x location indexes containing small pellets
        """
        pellet_locs = []
        for i in range(21):
            if self._map_tilegrid[i, 1] == 4:
                pellet_locs.append(i)
        return pellet_locs

    def restart(self):
        """
        Reset everything and start a new game
        :return: None
        """
        # move player to the left side
        self.player_entity.x = 15

        # move ghost to the right side
        self.ghost.x = ((self.display_size[0] // 4) * 3) // 3

        # respawn pellets
        self.spawn_pellets()

        # set game_over to False
        self.game_over = False

        # reset score and multiplier
        self.score = 0
        self.multiplier = 1

        # update score and multiplier in the UI
        self.update_score()

        # remove the gameover text
        self.remove(self.gameover_lbl)
