import time
import random
import board
import displayio
import adafruit_imageload

# display background color
BACKGROUND_COLOR = 0x00AEF0

# how long to wait between animation frames in seconds
ANIMATION_TIME = 0.3


class NekoAnimatedSprite(displayio.TileGrid):
    # how many pixels the cat will move for each step
    CONFIG_STEP_SIZE = 10

    # how likely the cat is to stop moving to clean or sleep.
    # lower number means more likely to happen
    CONFIG_STOP_CHANCE_FACTOR = 30

    # how likely the cat is to start moving after scratching a wall.
    # lower number means mroe likely to heppen
    CONFIG_START_CHANCE_FACTOR = 10

    # Minimum time to stop and scratch in seconds. larger time means scratch for longer
    CONFIG_MIN_SCRATCH_TIME = 2

    # State object indexes
    _ID = 0
    _ANIMATION_LIST = 1
    _MOVEMENT_STEP = 2

    # last time an animation occurred
    LAST_ANIMATION_TIME = -1

    # index of the sprite within the current animation that is currently showing
    CURRENT_ANIMATION_INDEX = 0

    # last time the cat changed states
    # used to enforce minimum scratch time
    LAST_STATE_CHANGE_TIME = -1

    # State objects
    # (ID, (Animation List), (Step Sizes))
    STATE_SITTING = (0, (0,), (0, 0))

    STATE_MOVING_LEFT = (1, (20, 21), (-CONFIG_STEP_SIZE, 0))
    STATE_MOVING_UP = (2, (16, 17), (0, -CONFIG_STEP_SIZE))
    STATE_MOVING_RIGHT = (3, (12, 13), (CONFIG_STEP_SIZE, 0))
    STATE_MOVING_DOWN = (4, (8, 9), (0, CONFIG_STEP_SIZE))
    STATE_MOVING_UP_RIGHT = (
        5,
        (14, 15),
        (CONFIG_STEP_SIZE // 2, -CONFIG_STEP_SIZE // 2),
    )
    STATE_MOVING_UP_LEFT = (
        6,
        (18, 19),
        (-CONFIG_STEP_SIZE // 2, -CONFIG_STEP_SIZE // 2),
    )
    STATE_MOVING_DOWN_LEFT = (
        7,
        (22, 23),
        (-CONFIG_STEP_SIZE // 2, CONFIG_STEP_SIZE // 2),
    )
    STATE_MOVING_DOWN_RIGHT = (
        8,
        (10, 11),
        (CONFIG_STEP_SIZE // 2, CONFIG_STEP_SIZE // 2),
    )

    STATE_SCRATCHING_LEFT = (9, (30, 31), (0, 0))
    STATE_SCRATCHING_RIGHT = (10, (26, 27), (0, 0))
    STATE_SCRATCHING_DOWN = (11, (24, 25), (0, 0))
    STATE_SCRATCHING_UP = (12, (28, 29), (0, 0))

    STATE_CLEANING = (13, (0, 0, 1, 1, 2, 3, 2, 3, 1, 1, 2, 3, 2, 3, 0, 0, 0), (0, 0))
    STATE_SLEEPING = (
        14,
        (
            0,
            0,
            4,
            4,
            4,
            0,
            0,
            4,
            4,
            4,
            0,
            0,
            5,
            6,
            5,
            6,
            5,
            6,
            5,
            6,
            5,
            6,
            7,
            7,
            0,
            0,
            0,
        ),
        (0, 0),
    )

    # these states count as "moving"
    MOVING_STATES = (
        STATE_MOVING_UP,
        STATE_MOVING_DOWN,
        STATE_MOVING_LEFT,
        STATE_MOVING_RIGHT,
        STATE_MOVING_UP_LEFT,
        STATE_MOVING_UP_RIGHT,
        STATE_MOVING_DOWN_LEFT,
        STATE_MOVING_DOWN_RIGHT,
    )

    # current state private field
    _CURRENT_STATE = STATE_SITTING

    # current animation list
    CURRENT_ANIMATION = _CURRENT_STATE[_ANIMATION_LIST]

    """
    Neko Animated Cat Sprite. Extends displayio.TileGrid manages changing the visible
    sprite image to animate the cat in it's various states.

    :param float animation_time: How long to wait in-between animation frames. Unit is seconds.
     default is 0.3 seconds
    :param tuple display_size: Tuple containing width and height of display.
     Defaults to values from board.DISPLAY. Used to determine with we are at the edge
     so we know to start scratching.
    """

    def __init__(self, animation_time=0.3, display_size=None):
        if not display_size:
            # if display_size was not passed, try to use defaults from board
            if "DISPLAY" in dir(board):
                self._display_size = (board.DISPLAY.width, board.DISPLAY.height)
            else:
                raise RuntimeError(
                    "Must pass display_size argument if not using built-in display."
                )
        else:
            # use the display_size that was passed in
            self._display_size = display_size

        # Load the sprite sheet bitmap and palette
        sprite_sheet, palette = adafruit_imageload.load(
            "/neko_cat_spritesheet.bmp",
            bitmap=displayio.Bitmap,
            palette=displayio.Palette,
        )

        # make the first color transparent
        palette.make_transparent(0)

        # Create a sprite tilegrid as self
        super().__init__(
            sprite_sheet,
            pixel_shader=palette,
            width=1,
            height=1,
            tile_width=32,
            tile_height=32,
        )

        self.x = 0
        self.y = 0

        # set the animation time into a private field
        self._animation_time = animation_time

    def _advance_animation_index(self):
        """
        Helper function to increment the animation index, and wrap it back around to
        0 after it reaches the final animation in the list.
        :return: None
        """
        self.CURRENT_ANIMATION_INDEX += 1
        if self.CURRENT_ANIMATION_INDEX >= len(self.CURRENT_ANIMATION):
            self.CURRENT_ANIMATION_INDEX = 0

    @property
    def animation_time(self):
        """
        How long to wait in-between animation frames. Unit is seconds.

        :return: animation_time
        """
        return self._animation_time

    @animation_time.setter
    def animation_time(self, new_time):
        self._animation_time = new_time

    @property
    def current_state(self):
        """
        The current state object.
        (ID, (Animation List), (Step Sizes))

        :return tuple: current state object
        """
        return self._CURRENT_STATE

    @current_state.setter
    def current_state(self, new_state):
        # update the current state object
        self._CURRENT_STATE = new_state
        # update the current animation list
        self.CURRENT_ANIMATION = new_state[self._ANIMATION_LIST]
        # reset current animation index to 0
        self.CURRENT_ANIMATION_INDEX = 0
        # show the first sprite in the animation
        self[0] = self.CURRENT_ANIMATION[self.CURRENT_ANIMATION_INDEX]
        # update the last state change time
        self.LAST_STATE_CHANGE_TIME = time.monotonic()

    def animate(self):
        """
        If enough time has passed since the previous animation then
        execute the next animation step by changing the currently visible sprite and
        advancing the animation index.

        :return bool: True if an animation frame occured. False if it's not time yet
         for an animation frame.
        """
        _now = time.monotonic()
        # is it time to do an animation step?
        if _now > self.LAST_ANIMATION_TIME + self.animation_time:
            # update the visible sprite
            self[0] = self.CURRENT_ANIMATION[self.CURRENT_ANIMATION_INDEX]
            # advance the animation index
            self._advance_animation_index()
            # update the last animation time
            self.LAST_ANIMATION_TIME = _now
            return True

        # Not time for animation step yet
        return False

    @property
    def is_moving(self):
        """
        Is the cat currently moving or not.

        :return bool: True if cat is in a moving state. False otherwise.
        """
        return self.current_state in self.MOVING_STATES

    def update(self):
        # pylint: disable=too-many-branches
        """
        Attempt to do animation step. Move if in a moving state. Change states if needed.

        :return: None
        """
        _now = time.monotonic()
        # attempt animation
        did_animate = self.animate()

        # if we did do an animation step
        if did_animate:
            # if cat is in a moving state
            if self.is_moving:
                # random chance to start sleeping or cleaning
                _roll = random.randint(0, self.CONFIG_STOP_CHANCE_FACTOR - 1)
                if _roll == 0:
                    # change to new state: sleeping or cleaning
                    _chosen_state = random.choice(
                        (self.STATE_CLEANING, self.STATE_SLEEPING)
                    )
                    self.current_state = _chosen_state
            else:  # cat is not moving

                # if we are currently in a scratching state
                if len(self.current_state[self._ANIMATION_LIST]) <= 2:

                    # check if we have scratched the minimum time
                    if (
                        _now
                        >= self.LAST_STATE_CHANGE_TIME + self.CONFIG_MIN_SCRATCH_TIME
                    ):
                        # minimum scratch time has elapsed

                        # random chance to start moving
                        _roll = random.randint(0, self.CONFIG_START_CHANCE_FACTOR - 1)
                        if _roll == 0:
                            # start moving in a random direction
                            _chosen_state = random.choice(self.MOVING_STATES)
                            self.current_state = _chosen_state

                else:  # if we are sleeping or cleaning or another complex animation state

                    # if we have done every step of the animation
                    if self.CURRENT_ANIMATION_INDEX == 0:
                        # change to a random moving state
                        _chosen_state = random.choice(self.MOVING_STATES)
                        self.current_state = _chosen_state

            # If we are far enough away from side walls to step in the current moving direction
            if (
                0
                <= (self.x + self.current_state[self._MOVEMENT_STEP][0])
                < (self._display_size[0] - self.tile_width)
            ):

                # move the cat horizontally by current state step size x
                self.x += self.current_state[self._MOVEMENT_STEP][0]

            else:  # we ran into a side wall
                if self.x > self.CONFIG_STEP_SIZE:
                    # ran into right wall
                    self.x = self._display_size[0] - self.tile_width - 1
                    # change state to scratching right
                    self.current_state = self.STATE_SCRATCHING_RIGHT
                else:
                    # ran into left wall
                    self.x = 1
                    # change state to scratching left
                    self.current_state = self.STATE_SCRATCHING_LEFT

            # If we are far enough away from top and bottom walls
            # to step in the current moving direction
            if (
                0
                <= (self.y + self.current_state[self._MOVEMENT_STEP][1])
                < (self._display_size[1] - self.tile_height)
            ):

                # move the cat vertically by current state step size y
                self.y += self.current_state[self._MOVEMENT_STEP][1]

            else:  # ran into top or bottom wall
                if self.y > self.CONFIG_STEP_SIZE:
                    # ran into bottom wall
                    self.y = self._display_size[1] - self.tile_height - 1
                    # change state to scratching down
                    self.current_state = self.STATE_SCRATCHING_DOWN
                else:
                    # ran into top wall
                    self.y = 1
                    # change state to scratching up
                    self.current_state = self.STATE_SCRATCHING_UP


# default to built-in display
display = board.DISPLAY

# create displayio Group
main_group = displayio.Group()

# create background group
background_group = displayio.Group(scale=16)
background_bitmap = displayio.Bitmap(20, 15, 1)
background_palette = displayio.Palette(1)
background_palette[0] = BACKGROUND_COLOR
background_tilegrid = displayio.TileGrid(
    background_bitmap, pixel_shader=background_palette
)
background_group.append(background_tilegrid)

# add background to main_group
main_group.append(background_group)

# create Neko
neko = NekoAnimatedSprite(animation_time=ANIMATION_TIME)

# put Neko in center of display
neko.x = display.width // 2 - neko.tile_width // 2
neko.y = display.height // 2 - neko.tile_height // 2

# add neko to main_group
main_group.append(neko)

# show main_group on the display
display.show(main_group)

while True:
    # update Neko to do animations and movements
    neko.update()
