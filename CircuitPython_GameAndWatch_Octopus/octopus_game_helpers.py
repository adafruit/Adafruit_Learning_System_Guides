import math
import time

import adafruit_imageload
import terminalio
from displayio import TileGrid, Group, OnDiskBitmap
from adafruit_display_text.bitmap_label import Label


class OctopusGame(Group):
    """
    This class will orchestrate and manage the entire game. High level functions are provided for
    hardware input events to come in via. It extends `displayio.Group` so it can be added to
    other Groups or shown directly on the display.
    """

    # Seconds between flailing diver animation frames
    CAUGHT_DIVER_ANIMATION_DELAY = 0.3

    # Seconds between treasure pulling animation frames
    DEPOSIT_TREASURE_ANIMATION_DELAY = 0.3

    # How many frames to run the treasure pulling animation for
    DEPOSIT_TREASURE_ANIMATION_FRAMES = 3

    # Game mode state variables
    GAME_MODE_A = 0
    GAME_MODE_B = 0

    # Vertical position of game mode labels (near bottom left)
    GAME_MODE_A_LBL_Y = 128 - 14
    GAME_MODE_B_LBL_Y = 128 - 4

    # State machine constant variables:

    STATE_WAITING_TO_PLAY = -1  # Before game begins

    STATE_NORMAL_GAMEPLAY = 0  # Standard game behavior

    STATE_CAUGHT_ANIMATION = 1  # Diver has been caught

    STATE_DEPOSIT_TREASURE_ANIMATION = 2  # Depositing treasure at the boat

    STATE_GAME_OVER = 3  # Diver has been caught and no lives remain

    # -- End of State machine constants --

    # Seconds to play the caught diver flailing animations
    CAUGHT_DIVER_LENGTH = 4.0

    # "Cheat" variable to make diver invincible for testing / development
    INVINCIBLE = False

    # Seconds between game Octopus movements, will get faster as score increases
    SCORE_SPEED_FACTOR = 0.5

    def __init__(self):
        super().__init__()

        # current score variable
        self._score = 0

        # timestamp when the diver was caught
        self._diver_caught_time = 0

        # main state machine current state
        self.current_state = OctopusGame.STATE_WAITING_TO_PLAY

        # current extra lives available
        self.extra_lives = 2

        # speed of the octopus movements, goes faster as score increases
        self.score_speed_factor = OctopusGame.SCORE_SPEED_FACTOR

        # current frame index for depositing treasure animation
        self.current_deposit_treasure_animation_frame = 0

        # game mode variable
        self.current_game_mode = OctopusGame.GAME_MODE_A

        # Set up Background
        self.bg_bmp = OnDiskBitmap("sprites/bg_with_shadow.bmp")
        self.bg_tilegrid = TileGrid(self.bg_bmp, pixel_shader=self.bg_bmp.pixel_shader)
        self.append(self.bg_tilegrid)

        # Set up Extra Life indicator images
        self.extra_life_bmp = OnDiskBitmap("sprites/diver_extra_life.bmp")
        self.extra_life_bmp.pixel_shader.make_transparent(0)
        self.extra_life_tilegrid_1 = TileGrid(self.extra_life_bmp,
                                              pixel_shader=self.extra_life_bmp.pixel_shader)
        self.extra_life_tilegrid_2 = TileGrid(self.extra_life_bmp,
                                              pixel_shader=self.extra_life_bmp.pixel_shader)

        self.extra_life_tilegrid_1.x = 33
        self.extra_life_tilegrid_2.x = 46
        self.extra_life_tilegrid_1.y = 4
        self.extra_life_tilegrid_2.y = 4

        self.append(self.extra_life_tilegrid_1)
        self.append(self.extra_life_tilegrid_2)

        # Set up Player Character
        self.player = DiverPlayer()
        self.player.hidden = True
        self.append(self.player)

        # Set up Octopus object
        self.octopus = Octopus()
        self.append(self.octopus)

        # Set up caught flailing diver
        self.caught_diver_bmp, self.caught_diver_palette = adafruit_imageload.load(
            "sprites/diver_caught_small.bmp")
        self.caught_diver_tilegrid = TileGrid(self.caught_diver_bmp,
                                              pixel_shader=self.caught_diver_palette,
                                              height=1, width=1, tile_width=31, tile_height=40)
        self.caught_diver_palette.make_transparent(0)

        self.caught_diver_tilegrid.y = 46
        self.caught_diver_tilegrid.x = 82
        self.append(self.caught_diver_tilegrid)
        self.caught_diver_tilegrid.hidden = True
        self.caught_diver_last_anim_time = 0

        # Set up treasure depositing boat diver sprite
        self.boat_diver_bmp, self.boat_diver_palette = adafruit_imageload.load(
            "sprites/diver_boat_small.bmp"
        )
        self.boat_diver_tilegrid = TileGrid(self.boat_diver_bmp,
                                            pixel_shader=self.boat_diver_palette,
                                            width=1, height=1, tile_width=21, tile_height=16,
                                            default_tile=1)
        self.boat_diver_palette.make_transparent(0)
        self.boat_diver_tilegrid.x = 11
        self.boat_diver_tilegrid.y = 5
        self.boat_diver_last_anim_time = 0
        self.append(self.boat_diver_tilegrid)

        # hide the caught diver to begin
        self.hide_caught_diver()

        # Set up label to show the current score
        self.score_lbl = Label(font=terminalio.FONT, text="0000", color=0x0)
        self.score_lbl.x = 90
        self.score_lbl.y = 5
        self.append(self.score_lbl)

        # Set up game mode label
        self.mode_lbl = Label(font=terminalio.FONT, text="", color=0x0)
        self.mode_lbl.x = 1
        self.mode_lbl.y = OctopusGame.GAME_MODE_A_LBL_Y
        self.append(self.mode_lbl)

        # Treasure that the diver had before moving
        self._before_move_treasure_count = 0

    @property
    def score(self):
        """
        Current game score
        :return: The current score
        """
        return self._score

    @score.setter
    def score(self, new_score):
        """
        Set the score variable and update the visual score label
        :param new_score: new score value
        :return: None
        """
        self._score = new_score
        self.score_speed_factor = self._score / 500
        self.score_lbl.text = str(self.score)

    def update_extra_lives(self):
        """
        Hide / Show the appropriate extra live indicator images
        :return: None
        """
        if self.extra_lives == 2:
            self.extra_life_tilegrid_1.hidden = False
            self.extra_life_tilegrid_2.hidden = False
        if self.extra_lives == 1:
            self.extra_life_tilegrid_2.hidden = True
        if self.extra_lives == 0:
            self.extra_life_tilegrid_1.hidden = True

    def show_caught_diver(self):
        """
        Show the caught diver and begin the flailing animation
        :return: None
        """

        # player loses currently held treasure
        self.player.treasure_count = 0

        # set the player state
        self.player.CUR_STATE = DiverPlayer.STATE_NO_TREASURE

        # current timestamp
        now = time.monotonic()

        # save the timestamp so we can compare to know when we're done
        self._diver_caught_time = now

        # hide the player character
        self.player.hidden = True

        # Show the appropriate tentacle segments
        self.octopus.t1as2_tilegrid.hidden = True
        self.octopus.t1as3_tilegrid.hidden = True
        self.octopus.t1as4_tilegrid.hidden = True

        # self.octopus.t2s3_tilegrid.hidden = True
        # self.octopus.t2s0_tilegrid.hidden = True
        # self.octopus.t2s1_tilegrid.hidden = True

        # set the appropriate tentacle index segment for tentacle 1
        self.octopus.tentacle_cur_indexes[1] = 1

        # Hide the appropriate tentacle segments.
        self.octopus.t1bs2_tilegrid.hidden = False
        self.octopus.t1s1_tilegrid.hidden = False
        self.octopus.t1s0_tilegrid.hidden = False
        self.caught_diver_tilegrid.hidden = False

    def hide_caught_diver(self):
        """
        Hide the caught diver and stop the flailing animation
        :return: None
        """

        self.caught_diver_tilegrid.hidden = True
        self.octopus.t1bs2_tilegrid.hidden = True
        self.boat_diver_tilegrid.hidden = False
        self.player.CUR_LOCATION_INDEX = 0
        self.player.CUR_SPRITE_INDEX = 0
        self.player.update_location_and_sprite()

    def left_button_press(self):
        """
        Left movement button action function. code.py will poll the hardware and call this.
        :return: None
        """

        # check which state we're in to determine appropriate action(s)
        if self.current_state != OctopusGame.STATE_GAME_OVER and self.current_state != OctopusGame.STATE_WAITING_TO_PLAY:

            # if player just moved from the last spot in the water to the boat
            if self.player.CUR_LOCATION_INDEX == 0:

                # empty treasure from the player
                if self.player.treasure_count > 0:
                    # hide the player character
                    self.player.hidden = True

                    # set the boat diver sprite
                    self.boat_diver_tilegrid[0, 0] = 1

                    # store a timestamp for animation
                    self.boat_diver_last_anim_time = time.monotonic()

                    # show the boat diver
                    self.boat_diver_tilegrid.hidden = False

                    # Start the depositing treasure animation
                    self.deposit_treasure()

            else:  # player did not just move out of the water into the boat

                if not self.player.hidden:

                    # tell the player object to move and let it handle the specific details
                    self.player.move_backward()

    def right_button_press(self):
        """
        Right movement button action function. code.py will poll the hardware and call this.
        :return: None
        """
        # check which state we're in to determin the appropriate action(s)
        if self.current_state not in (
                OctopusGame.STATE_GAME_OVER, OctopusGame.STATE_WAITING_TO_PLAY):

            # if the boat diver is currently showing
            if not self.boat_diver_tilegrid.hidden:
                # hide the boat diver
                self.boat_diver_tilegrid.hidden = True

                # show the player character
                self.player.hidden = False


            else:  # boat diver isn't currently showing
                if not self.player.hidden:
                    # store treasure count before moving
                    self._before_move_treasure_count = self.player.treasure_count

                    # tell player to move forward and let it handle the details
                    self.player.move_forward()

                    # if treasure count changed then we know that we got one
                    if self.player.treasure_count != self._before_move_treasure_count:
                        # increment the score
                        self.score += 1

    def reset(self):
        """
        Reset the game back to beginning state.
        :return: None
        """
        self.score = 0
        self.extra_lives = 2
        self.update_extra_lives()

    def a_button_press(self):
        """
        (A) Button action function. code.py will poll hardware and call this as needed
        :return: None
        """

        # if we're in game over, or waiting to play state
        if self.current_state in (OctopusGame.STATE_GAME_OVER, OctopusGame.STATE_WAITING_TO_PLAY):
            # reset the game
            self.reset()
            # set the mode to A
            self.current_game_mode = OctopusGame.GAME_MODE_A
            # update the mode label
            self.mode_lbl.text = "GAMEA"
            self.mode_lbl.y = OctopusGame.GAME_MODE_A_LBL_Y
            # set the current state to playing for the state machine
            self.current_state = OctopusGame.STATE_NORMAL_GAMEPLAY

    def b_button_press(self):
        """
       (B) Button action function. code.py will poll hardware and call this as needed
       :return: None
       """
        # if we're in game over or waiting to play state
        if self.current_state in (OctopusGame.STATE_GAME_OVER, OctopusGame.STATE_WAITING_TO_PLAY):
            # reset the game
            self.reset()
            # set the mode to B
            self.current_game_mode = OctopusGame.GAME_MODE_B
            # update the mode label
            self.mode_lbl.text = "GAMEB"
            self.mode_lbl.y = OctopusGame.GAME_MODE_B_LBL_Y
            # set the current state to playing for the state machine.
            self.current_state = OctopusGame.STATE_NORMAL_GAMEPLAY

    def deposit_treasure(self):
        """
       Show the deposit treasure animation
       :return: None
       """

        # set the current state for the game state machine
        self.current_state = OctopusGame.STATE_DEPOSIT_TREASURE_ANIMATION

        # set the state for the player state machine
        self.player.CUR_STATE = DiverPlayer.STATE_NO_TREASURE

        # loop for animation frames
        for i in range(3):
            # increment score
            self.score += 1
            # wait until next animation frame
            time.sleep(0.15)

        # empty player treasure
        self.player.treasure_count = 0

        # show the correct location and sprite for player character
        self.player.update_location_and_sprite()

    def lose_life(self):
        """
        Process a lost life for the player. Called when octopus catches diver
        :return: None
        """
        # decrement lives
        self.extra_lives -= 1

        # check for game over
        if self.extra_lives <= -1:
            # set current state to game over
            self.current_state = OctopusGame.STATE_GAME_OVER

        # update the extra lives indicators
        self.update_extra_lives()

        # show the caught diver and start the flailing animation
        self.show_caught_diver()

    def tick(self):
        """
        Main game.tick() function, will be called once per iteration in the main loop.

        Will process behaviors based on current state. Will call tick() on Player and Octopus
        as needed.
        :return: None
        """

        # store a timestamp to reference
        now = time.monotonic()
        # if current state is normal game playing
        if self.current_state == OctopusGame.STATE_NORMAL_GAMEPLAY:
            # if the caught diver / flail animation is not showing
            if self.caught_diver_tilegrid.hidden:
                # call tick on the octopus, it will decide it's time to hide or show a tentacle segment
                self.octopus.tick(self)

            # only check for player being caught if the invincibility cheat is off.
            if not self.INVINCIBLE:
                # check if the player is within reach of the last tentacle segments
                # call lose_life() if so to process it
                if self.player.CUR_LOCATION_INDEX == 0 and not self.player.hidden:
                    if not self.octopus.t0as2_tilegrid.hidden:
                        self.lose_life()
                if self.player.CUR_LOCATION_INDEX == 1 and not self.player.hidden:
                    if not self.octopus.t0bs3_tilegrid.hidden:
                        self.lose_life()
                if self.player.CUR_LOCATION_INDEX == 2 and not self.player.hidden:
                    if not self.octopus.t1as4_tilegrid.hidden:
                        self.lose_life()
                if self.player.CUR_LOCATION_INDEX == 3 and not self.player.hidden:
                    if not self.octopus.t2s3_tilegrid.hidden:
                        self.lose_life()
                if self.player.CUR_LOCATION_INDEX == 4 and not self.player.hidden:
                    if not self.octopus.t3s2_tilegrid.hidden:
                        self.lose_life()

            # if the caught diver / flail animation is showing
            if not self.caught_diver_tilegrid.hidden:
                # if the total duration has not elapsed yet
                if now <= self._diver_caught_time + OctopusGame.CAUGHT_DIVER_LENGTH:

                    # if it's been long enough since the previously shown frame
                    if now >= OctopusGame.CAUGHT_DIVER_ANIMATION_DELAY + self.caught_diver_last_anim_time:

                        # show the next animation frame by swaping indexes in the spritesheet
                        self.caught_diver_tilegrid[0, 0] = 0 if self.caught_diver_tilegrid[
                                                                    0, 0] == 1 else 1

                        # store the timestamp to compare with next time
                        self.caught_diver_last_anim_time = now

                else:  # the total duration has elapsed
                    # stop the animation and hide the caught diver
                    self.hide_caught_diver()

            # call player tick, it will manage the taking treasure animation as needed
            self.player.tick()

        # if current state is depositing treasure animation
        elif self.current_state == OctopusGame.STATE_DEPOSIT_TREASURE_ANIMATION:

            # if enough time has passed since the last animation frame shown
            if now >= OctopusGame.DEPOSIT_TREASURE_ANIMATION_DELAY + self.boat_diver_last_anim_time:

                # if we haven't shown all of the frames yet
                if self.current_deposit_treasure_animation_frame < OctopusGame.DEPOSIT_TREASURE_ANIMATION_FRAMES:
                    # increment the frame count
                    self.current_deposit_treasure_animation_frame += 1

                    # swap the sprite index to change to the other tile in the spritesheet
                    self.boat_diver_tilegrid[0, 0] = 1 if self.boat_diver_tilegrid[0, 0] == 0 else 0

                    # store the timestamp to comapre with next time
                    self.boat_diver_last_anim_time = now

                else:  # We have shown all of the frames
                    # set the sprite index to the one without the treasure bag
                    self.boat_diver_tilegrid[0, 0] = 1
                    # set the current state to normal game playing
                    self.current_state = OctopusGame.STATE_NORMAL_GAMEPLAY
                    # set the frame count to zero for next time we need to show it
                    self.current_deposit_treasure_animation_frame = 0

        # if current state is game over
        elif self.current_state == OctopusGame.STATE_GAME_OVER:
            # if enough time has passed since the previous flailing diver animation frame
            if now >= OctopusGame.CAUGHT_DIVER_ANIMATION_DELAY + self.caught_diver_last_anim_time:
                # swap the sprite index to show the other tile in the flailing animation spritesheet
                self.caught_diver_tilegrid[0, 0] = 0 if self.caught_diver_tilegrid[
                                                            0, 0] == 1 else 1
                # store the timestamp to comapre with next time
                self.caught_diver_last_anim_time = now


class Octopus(Group):
    """
    This class will contain all of the graphics and behavior for the Octopus
    tentacle segments. A tick() method will be called during the game.tick() and
    it will hide and show segments as needed to make the tentacles appear to extend
    and retract.

    It extends Group so it can be added to other Group's and shown on the display.
    """

    # direction constant variables
    TENTACLE_DIRECTION_EXTENDING = 0
    TENTACLE_DIRECTION_RETRACTING = 1

    # tentacle 0 path option variables
    TENTACLE_0_PATH_A = 0
    TENTACLE_0_PATH_B = 1

    # action speed starting point, will be modified by score
    BASE_TICK_DELAY = 0.75

    # maximum action speed delay value
    MAX_TICK_SPEED = BASE_TICK_DELAY - 0.1  # seconds

    # order that the tentacles will take actions
    TENTACLE_ORDER = [0, 2, 1, 3]

    def __init__(self):
        super().__init__()

        # timestamp of most recent action
        self.last_action_time = 0

        # index of the tentacle currently moving
        self.current_tentacle_index = 0

        # --- Set up tentacle segment images ---
        self.t0s0_bmp, self.t0s0_palette = adafruit_imageload.load("sprites/tentacle_0_seg_0.bmp")
        self.t0s0_tilegrid = TileGrid(self.t0s0_bmp, pixel_shader=self.t0s0_palette)
        self.t0s0_palette.make_transparent(0)
        self.t0s0_tilegrid.x = 57
        self.t0s0_tilegrid.y = 40

        self.t0as1_bmp, self.t0as1_palette = adafruit_imageload.load("sprites/tentacle_0a_seg_1.bmp")
        self.t0as1_tilegrid = TileGrid(self.t0as1_bmp, pixel_shader=self.t0as1_palette)
        self.t0as1_palette.make_transparent(0)
        self.t0as1_tilegrid.x = 47
        self.t0as1_tilegrid.y = 43

        self.t0as2_bmp, self.t0as2_palette = adafruit_imageload.load("sprites/tentacle_0a_seg_2.bmp")
        self.t0as2_tilegrid = TileGrid(self.t0as2_bmp, pixel_shader=self.t0as2_palette)
        self.t0as2_palette.make_transparent(0)
        self.t0as2_tilegrid.x = 33
        self.t0as2_tilegrid.y = 36

        self.t0bs1_bmp, self.t0bs1_palette = adafruit_imageload.load("sprites/tentacle_0b_seg_1.bmp")
        self.t0bs1_tilegrid = TileGrid(self.t0bs1_bmp, pixel_shader=self.t0bs1_palette)
        self.t0bs1_palette.make_transparent(0)
        self.t0bs1_tilegrid.x = 53
        self.t0bs1_tilegrid.y = 50

        self.t0bs2_bmp, self.t0bs2_palette = adafruit_imageload.load("sprites/tentacle_0b_seg_2.bmp")
        self.t0bs2_tilegrid = TileGrid(self.t0bs2_bmp, pixel_shader=self.t0bs2_palette)
        self.t0bs2_palette.make_transparent(0)
        self.t0bs2_tilegrid.x = 49
        self.t0bs2_tilegrid.y = 56

        self.t0bs3_bmp, self.t0bs3_palette = adafruit_imageload.load("sprites/tentacle_0b_seg_3.bmp")
        self.t0bs3_tilegrid = TileGrid(self.t0bs3_bmp, pixel_shader=self.t0bs3_palette)
        self.t0bs3_palette.make_transparent(0)
        self.t0bs3_tilegrid.x = 36
        self.t0bs3_tilegrid.y = 69

        self.t1s0_bmp, self.t1s0_palette = adafruit_imageload.load("sprites/tentacle_1_seg_0.bmp")
        self.t1s0_tilegrid = TileGrid(self.t1s0_bmp, pixel_shader=self.t1s0_palette)
        self.t1s0_palette.make_transparent(0)
        self.t1s0_tilegrid.x = 72
        self.t1s0_tilegrid.y = 51

        self.t1s1_bmp, self.t1s1_palette = adafruit_imageload.load("sprites/tentacle_1_seg_1.bmp")
        self.t1s1_tilegrid = TileGrid(self.t1s1_bmp, pixel_shader=self.t1s1_palette)
        self.t1s1_palette.make_transparent(0)
        self.t1s1_tilegrid.x = 71
        self.t1s1_tilegrid.y = 61

        self.t1as2_bmp, self.t1as2_palette = adafruit_imageload.load("sprites/tentacle_1a_seg_2.bmp")
        self.t1as2_tilegrid = TileGrid(self.t1as2_bmp, pixel_shader=self.t1as2_palette)
        self.t1as2_palette.make_transparent(0)
        self.t1as2_tilegrid.x = 70
        self.t1as2_tilegrid.y = 69

        self.t1as3_bmp, self.t1as3_palette = adafruit_imageload.load("sprites/tentacle_1a_seg_3.bmp")
        self.t1as3_tilegrid = TileGrid(self.t1as3_bmp, pixel_shader=self.t1as3_palette)
        self.t1as3_palette.make_transparent(0)
        self.t1as3_tilegrid.x = 70
        self.t1as3_tilegrid.y = 78

        self.t1as4_bmp, self.t1as4_palette = adafruit_imageload.load("sprites/tentacle_1a_seg_4.bmp")
        self.t1as4_tilegrid = TileGrid(self.t1as4_bmp, pixel_shader=self.t1as4_palette)
        self.t1as4_palette.make_transparent(0)
        self.t1as4_tilegrid.x = 65
        self.t1as4_tilegrid.y = 87

        self.t1bs2_bmp, self.t1bs2_palette = adafruit_imageload.load("sprites/tentacle_1b_seg_2.bmp")
        self.t1bs2_tilegrid = TileGrid(self.t1bs2_bmp, pixel_shader=self.t1bs2_palette)
        self.t1bs2_palette.make_transparent(0)
        self.t1bs2_tilegrid.x = 79
        self.t1bs2_tilegrid.y = 71

        self.t2s0_bmp, self.t2s0_palette = adafruit_imageload.load("sprites/tentacle_2_seg_0.bmp")
        self.t2s0_tilegrid = TileGrid(self.t2s0_bmp, pixel_shader=self.t2s0_palette)
        self.t2s0_palette.make_transparent(0)
        self.t2s0_tilegrid.x = 94
        self.t2s0_tilegrid.y = 66

        self.t2s1_bmp, self.t2s1_palette = adafruit_imageload.load("sprites/tentacle_2_seg_1.bmp")
        self.t2s1_tilegrid = TileGrid(self.t2s1_bmp, pixel_shader=self.t2s1_palette)
        self.t2s1_palette.make_transparent(0)
        self.t2s1_tilegrid.x = 95
        self.t2s1_tilegrid.y = 75

        self.t2s2_bmp, self.t2s2_palette = adafruit_imageload.load("sprites/tentacle_2_seg_2.bmp")
        self.t2s2_tilegrid = TileGrid(self.t2s2_bmp, pixel_shader=self.t2s2_palette)
        self.t2s2_palette.make_transparent(0)
        self.t2s2_tilegrid.x = 98
        self.t2s2_tilegrid.y = 80

        self.t2s3_bmp, self.t2s3_palette = adafruit_imageload.load("sprites/tentacle_2_seg_3.bmp")
        self.t2s3_tilegrid = TileGrid(self.t2s3_bmp, pixel_shader=self.t2s3_palette)
        self.t2s3_palette.make_transparent(0)
        self.t2s3_tilegrid.x = 99
        self.t2s3_tilegrid.y = 88

        self.t3s0_bmp, self.t3s0_palette = adafruit_imageload.load("sprites/tentacle_3_seg_0.bmp")
        self.t3s0_tilegrid = TileGrid(self.t3s0_bmp, pixel_shader=self.t3s0_palette)
        self.t3s0_palette.make_transparent(0)
        self.t3s0_tilegrid.x = 119
        self.t3s0_tilegrid.y = 72

        self.t3s1_bmp, self.t3s1_palette = adafruit_imageload.load("sprites/tentacle_3_seg_1.bmp")
        self.t3s1_tilegrid = TileGrid(self.t3s1_bmp, pixel_shader=self.t3s1_palette)
        self.t3s1_palette.make_transparent(0)
        self.t3s1_tilegrid.x = 119
        self.t3s1_tilegrid.y = 80

        self.t3s2_bmp, self.t3s2_palette = adafruit_imageload.load("sprites/tentacle_3_seg_2.bmp")
        self.t3s2_tilegrid = TileGrid(self.t3s2_bmp, pixel_shader=self.t3s2_palette)
        self.t3s2_palette.make_transparent(0)
        self.t3s2_tilegrid.x = 120
        self.t3s2_tilegrid.y = 87

        self.append(self.t0s0_tilegrid)
        self.append(self.t0as1_tilegrid)
        self.append(self.t0as2_tilegrid)
        self.append(self.t0bs1_tilegrid)
        self.append(self.t0bs2_tilegrid)
        self.append(self.t0bs3_tilegrid)
        self.append(self.t1s0_tilegrid)
        self.append(self.t1s1_tilegrid)
        self.append(self.t1as2_tilegrid)
        self.append(self.t1as3_tilegrid)
        self.append(self.t1as4_tilegrid)
        self.append(self.t1bs2_tilegrid)
        self.append(self.t2s0_tilegrid)
        self.append(self.t2s1_tilegrid)
        self.append(self.t2s2_tilegrid)
        self.append(self.t2s3_tilegrid)
        self.append(self.t3s0_tilegrid)
        self.append(self.t3s1_tilegrid)
        self.append(self.t3s2_tilegrid)
        # --- End of tentacle segment initializations ---

        # Lists of segments for each tentacle
        self.tentacle_0a_list = [self.t0s0_tilegrid, self.t0as1_tilegrid, self.t0as2_tilegrid]
        self.tentacle_0b_list = [self.t0s0_tilegrid, self.t0bs1_tilegrid, self.t0bs2_tilegrid,
                                 self.t0bs3_tilegrid]
        self.tentacle_1_list = [self.t1s0_tilegrid, self.t1s1_tilegrid, self.t1as2_tilegrid,
                                self.t1as3_tilegrid, self.t1as4_tilegrid]
        self.tentacle_2_list = [self.t2s0_tilegrid, self.t2s1_tilegrid, self.t2s2_tilegrid,
                                self.t2s3_tilegrid]
        self.tentacle_3_list = [self.t3s0_tilegrid, self.t3s1_tilegrid, self.t3s2_tilegrid]

        # list of the tentacles
        self.tentacles = [self.tentacle_0a_list, self.tentacle_1_list, self.tentacle_2_list,
                          self.tentacle_3_list]

        # list of directions for each tentacle
        self.tentacle_directions = []

        # initialize all of the directions to extending
        self.tentacle_directions[:] = [Octopus.TENTACLE_DIRECTION_EXTENDING] * 4

        # tentacle 0 path variable
        self.tentacle_0_path = Octopus.TENTACLE_0_PATH_A

        # list of current segment indexes for each tentacle
        self.tentacle_cur_indexes = []

        # initialize segment indexes to -1
        self.tentacle_cur_indexes[:] = [-1] * 4

        # hide all of the segments to start with
        self.hide_all_segments()

    @property
    def current_tentacle(self):
        """
        The tentacle that will move next

        :return: index of the current tentacle to move
        """
        return Octopus.TENTACLE_ORDER[self.current_tentacle_index]

    def hide_all_segments(self):
        """
        Hide all of the tentacle segments
        :return: None
        """

        # loop over all segments in every tentacle
        for segment in self.tentacle_0a_list + self.tentacle_0b_list + self.tentacle_1_list + \
                       self.tentacle_2_list + self.tentacle_3_list:

            # hide the current segment
            segment.hidden = True

        # reset all tentacle current indexes to -1
        self.tentacle_cur_indexes[:] = [-1] * 4

        # reset all tentacle directions to extending
        self.tentacle_directions[:] = [Octopus.TENTACLE_DIRECTION_EXTENDING] * 4


    def tick(self, game_obj):
        """
        Octopus tick() function called during game.tick(). Take turns extending and
        retracting each tentacle in the sequence dictated by ORDER.

        :param game_obj: The game object with context data and variables
        :return: None
        """

        # timestamp to determine if it's time for an action to occur
        now = time.monotonic()

        # Check if it's time for an acction
        if self.last_action_time + (
                Octopus.BASE_TICK_DELAY - min(game_obj.score_speed_factor,
                                              Octopus.MAX_TICK_SPEED)) <= now:

            # store the timestamp to compare against next iteration
            self.last_action_time = now

            # if we're moving tentacle 0
            if self.current_tentacle == 0:

                # if tentacle 0 is extending
                if self.tentacle_directions[0] == Octopus.TENTACLE_DIRECTION_EXTENDING:
                    # increment segment index
                    self.tentacle_cur_indexes[0] += 1

                    # if we're on path A
                    if self.tentacle_0_path == Octopus.TENTACLE_0_PATH_A:
                        # if we're on the last segment
                        if self.tentacle_cur_indexes[0] >= len(self.tentacle_0a_list) - 1:
                            # change directions to retracting
                            self.tentacle_directions[0] = Octopus.TENTACLE_DIRECTION_RETRACTING

                        # show the current segment
                        self.tentacle_0a_list[self.tentacle_cur_indexes[0]].hidden = False

                    # if we're on path B
                    elif self.tentacle_0_path == Octopus.TENTACLE_0_PATH_B:
                        # if we're on the last segment
                        if self.tentacle_cur_indexes[0] >= len(self.tentacle_0b_list) - 1:
                            # change direction to retracting
                            self.tentacle_directions[0] = Octopus.TENTACLE_DIRECTION_RETRACTING

                        # show the current segment
                        self.tentacle_0b_list[self.tentacle_cur_indexes[0]].hidden = False

                # if tentacle 0 is retracting
                elif self.tentacle_directions[0] == Octopus.TENTACLE_DIRECTION_RETRACTING:
                    # decrement the current segment index
                    self.tentacle_cur_indexes[0] -= 1

                    # if the we're done with the first segment
                    if self.tentacle_cur_indexes[0] < -1:
                        # reset the index to the first segment
                        self.tentacle_cur_indexes[0] += 1

                        # set the direction to extending
                        self.tentacle_directions[0] = Octopus.TENTACLE_DIRECTION_EXTENDING
                        # if we are currently on path A
                        if self.tentacle_0_path == Octopus.TENTACLE_0_PATH_A:
                            # change to path B
                            self.tentacle_0_path = Octopus.TENTACLE_0_PATH_B

                        else:  # we are currently on path B
                            # change to path A
                            self.tentacle_0_path = Octopus.TENTACLE_0_PATH_A

                    # if we're on path A
                    if self.tentacle_0_path == Octopus.TENTACLE_0_PATH_A:
                        # hide the current segment
                        self.tentacle_0a_list[self.tentacle_cur_indexes[0] + 1].hidden = True

                    # if we're on path B
                    elif self.tentacle_0_path == Octopus.TENTACLE_0_PATH_B:
                        # hide the current segment
                        self.tentacle_0b_list[self.tentacle_cur_indexes[0] + 1].hidden = True

            else:  # we're moving tentacle 1, 2, or 3 not tentacle 0

                #  current tentacle list that we're processing action for
                _cur_tentacle_list = self.tentacles[self.current_tentacle]

                #  index of current tentacle
                _cur_tentacle_index = self.tentacle_cur_indexes[self.current_tentacle]

                #  direction of this tentacle
                _cur_tentacle_direction = self.tentacle_directions[self.current_tentacle]

                # if the tentacle is extending
                if _cur_tentacle_direction == Octopus.TENTACLE_DIRECTION_EXTENDING:

                    # increment the index of current segment
                    self.tentacle_cur_indexes[self.current_tentacle] += 1

                    # if it's the last segment in the tentacle
                    if self.tentacle_cur_indexes[self.current_tentacle] >= len(
                            _cur_tentacle_list) - 1:

                        # change the direction to retracting
                        self.tentacle_directions[
                            self.current_tentacle] = Octopus.TENTACLE_DIRECTION_RETRACTING

                    # show the  current segment
                    _cur_tentacle_list[
                        self.tentacle_cur_indexes[self.current_tentacle]].hidden = False

                # if the tentacle is retracting
                elif _cur_tentacle_direction == Octopus.TENTACLE_DIRECTION_RETRACTING:

                    # decrement the segment index
                    self.tentacle_cur_indexes[self.current_tentacle] -= 1

                    # if all segments have been retracted
                    if self.tentacle_cur_indexes[self.current_tentacle] <= -1:

                        # change direction to extending
                        self.tentacle_directions[
                            self.current_tentacle] = Octopus.TENTACLE_DIRECTION_EXTENDING

                    # hide the current segment
                    _cur_tentacle_list[
                        self.tentacle_cur_indexes[self.current_tentacle] + 1].hidden = True

            # increment tentacle index so we process the next segment next time
            self.current_tentacle_index += 1

            # if this was the final tentacle
            if self.current_tentacle_index > 3:
                # reset the index back to the beginning
                self.current_tentacle_index = 0


class DiverPlayer(TileGrid):
    """
    This class will contain the sprites and behavior for the player character.
    A spritesheet contains sprites for each state of the diver. The states change
    when for each location and based on whether

    It extends TileGrid so it can be added to a Group and shown on the display.
    """

    # list of X,Y coordinate locations that the diver can move to on the map.
    DIVER_LOCATIONS = [(9, 29), (9, 73), (44, 91), (72, 90), (102, 94)]

    # Sprite indexes within the sprite sheet for non-treasure divers
    SPRITE_INDEXES_NO_TREASURE = [0, 2, 4, 6, 8]

    # Sprite indexes within the sprite sheet for divers with treasure
    SPRITE_INDEXES_WITH_TREASURE = [1, 3, 5, 7, 10]

    # Sprite indexes within the sprite sheet for the diver taking treasure
    SPRITE_INDEXES_TAKING_TREASURE = [10, 9, 11]

    # State machine index variables
    STATE_NO_TREASURE = 0
    STATE_HAVE_TREASURE = 1
    STATE_TAKING_TREASURE = 2

    # Taking treasure animation delay
    TREASURE_ANIMATION_DELAY = 0.3  # seconds

    def __init__(self):
        # set up diver sprite sheet
        self._sprite_sheet_bmp, self._sprite_sheet_palette = adafruit_imageload.load(
            "sprites/diver_sprite_sheet_v2.bmp")

        # initialize super instance of TileGrid
        super().__init__(self._sprite_sheet_bmp, pixel_shader=self._sprite_sheet_palette,
                         height=1, width=1, tile_width=29, tile_height=28)

        # set the transparent color index
        self._sprite_sheet_palette.make_transparent(0)

        # index of the sprite currently showing
        self.CUR_SPRITE_INDEX = 0

        # index of the current location coordinate point
        self.CUR_LOCATION_INDEX = 0

        # state machine current state variable
        self.CUR_STATE = DiverPlayer.STATE_NO_TREASURE

        # timestamp of last time the an animation sprite frame was shown
        self.last_treasure_animation_time = 0

        # how much treasure the player is holding
        self.treasure_count = 0

        # set the initial location and sprite
        self.update_location_and_sprite()

    def update_location_and_sprite(self):
        """
        Update the current location and sprite of the diver based on the current indexe values.

        :return: None
        """

        # set the x and y location of the diver.
        self.x = self.DIVER_LOCATIONS[self.CUR_LOCATION_INDEX][0]
        self.y = self.DIVER_LOCATIONS[self.CUR_LOCATION_INDEX][1]

        # check which state we're in currently
        if self.CUR_STATE == DiverPlayer.STATE_NO_TREASURE:
            # set the sprite index from the no treasure sprites
            self[0, 0] = DiverPlayer.SPRITE_INDEXES_NO_TREASURE[self.CUR_SPRITE_INDEX]
        elif self.CUR_STATE == DiverPlayer.STATE_HAVE_TREASURE:
            # set the sprite index from the sprites with treasure
            self[0, 0] = DiverPlayer.SPRITE_INDEXES_WITH_TREASURE[self.CUR_SPRITE_INDEX]
        elif self.CUR_STATE == DiverPlayer.STATE_TAKING_TREASURE:
            # set the sprite index for the start of the taking treasure animation
            print(f"CUR_SPRITE_INDEX: {self.CUR_SPRITE_INDEX}")
            print(
                f"TILE INDEX: {DiverPlayer.SPRITE_INDEXES_TAKING_TREASURE[self.CUR_SPRITE_INDEX]}")
            self[0, 0] = DiverPlayer.SPRITE_INDEXES_TAKING_TREASURE[self.CUR_SPRITE_INDEX]

    def move_forward(self):
        """
        Move the diver forward one location on the map. If they're at the treasure chest
        then take a treasure from it and play the animation.

        :return: None
        """

        # if we are note currently taking treasure
        if self.CUR_STATE != DiverPlayer.STATE_TAKING_TREASURE:
            # if we're not at the spot next to the treasure chest
            if self.CUR_LOCATION_INDEX <= 3:
                # increment location and sprite indexes
                self.CUR_SPRITE_INDEX += 1
                self.CUR_LOCATION_INDEX += 1

            # if we are at the spot next to the treasure
            elif self.CUR_LOCATION_INDEX == 4:
                # set the state machine current state variable
                self.CUR_STATE = DiverPlayer.STATE_TAKING_TREASURE

                # set the sprite index
                self.CUR_SPRITE_INDEX = 0

                # increment treasure
                self.treasure_count += 1

            # set the position and sprite based on the new indexes
            self.update_location_and_sprite()

    def move_backward(self):
        """
        Move the player backward one location on the map.
        :return: None
        """

        # if the current state is not taking treasure
        if self.CUR_STATE != DiverPlayer.STATE_TAKING_TREASURE:

            # if current location is next to the treasure chest
            if self.CUR_LOCATION_INDEX == 4:
                # decrement the location index
                self.CUR_LOCATION_INDEX -= 1
                # Set the state according to whether the diver has treasure or not
                self.CUR_STATE = DiverPlayer.STATE_HAVE_TREASURE if self.treasure_count >= 0 else DiverPlayer.STATE_NO_TREASUREm
                # set the sprite index
                self.CUR_SPRITE_INDEX = 3

            # if current location is not next to the boat
            elif self.CUR_LOCATION_INDEX > 0:
                # decrement location and sprite indexes
                self.CUR_LOCATION_INDEX -= 1
                self.CUR_SPRITE_INDEX -= 1

            # if current location is next to the boat
            else:
                pass
                # drop off treasure at boat
                print("drop off: {}".format(self.treasure_count))

                # set the state to no treasure
                self.CUR_STATE = DiverPlayer.STATE_NO_TREASURE

            # set the position and sprite based on the new indexes
            self.update_location_and_sprite()

    def tick(self):
        """
        Player tick function, called from game tick. Will process the taking treasure
        animation when needed.
        :return: None
        """
        # if we're in the taking treasure state
        if self.CUR_STATE == DiverPlayer.STATE_TAKING_TREASURE:
            # store a timestamp to compare with
            now = time.monotonic()

            # if it's been long enough since the last animation frame
            if now >= self.last_treasure_animation_time + DiverPlayer.TREASURE_ANIMATION_DELAY:
                # increment the sprite index
                self.CUR_SPRITE_INDEX += 1

                # if we've shown all of the animation sprites
                if self.CUR_SPRITE_INDEX == len(DiverPlayer.SPRITE_INDEXES_TAKING_TREASURE):
                    # set the state to have treasure
                    self.CUR_STATE = DiverPlayer.STATE_HAVE_TREASURE

                    # set the sprite index to the correct one for this location with treasure
                    self.CUR_SPRITE_INDEX = 4

                # set the position and sprite based on the new indexes
                self.update_location_and_sprite()

                # store the timestamp to compare with next time
                self.last_treasure_animation_time = now
