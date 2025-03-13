# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
import random
import adafruit_imageload
from displayio import TileGrid

X = 0
Y = 1


class Snake:
    """
    Snake helper class keeps track of the current direction of the snake
    and the x,y coordinates of all segments within the snake.
    """

    # direction constants
    DIRECTION_UP = 0
    DIRECTION_DOWN = 1
    DIRECTION_RIGHT = 2
    DIRECTION_LEFT = 3

    def __init__(self, starting_location=(10, 10)):

        # this list will hold locations of all segments
        # we have only 1 segment when first initialized
        self.locations = [list(starting_location)]

        # start in a random direction
        self.direction = random.randint(0, 3)

    def grow(self):
        """
        Grow the snake by 1 segment
        """
        # check which direction we're currently going
        if self.direction == self.DIRECTION_UP:
            # new segment below the tail
            new_segment = [self.tail[X], self.tail[Y] + 1]
        elif self.direction == self.DIRECTION_DOWN:
            # new segment above the tail
            new_segment = [self.tail[X], self.tail[Y] - 1]
        elif self.direction == self.DIRECTION_LEFT:
            # new segment to the right of the tail
            new_segment = [self.tail[X] + 1, self.tail[Y]]
        elif self.direction == self.DIRECTION_RIGHT:
            # new segment to the left of the tail
            new_segment = [self.tail[X] - 1, self.tail[Y]]
        else:
            raise RuntimeError("Invalid Direction")
        # add the new segment to our list
        self.locations.append(new_segment)

    @property
    def size(self):
        """
        Length of the snake in segments
        """
        return len(self.locations)

    def __len__(self):
        """
        Length of the snake in segments
        """
        return len(self.locations)

    @property
    def head(self):
        """
        The x,y coordinates of the head segment of the snake
        """
        return self.locations[0]

    @property
    def tail(self):
        """
        The x,y coordinates of the tail segment of the snake
        """
        return self.locations[-1]


class World(TileGrid):
    """
    World helper class draws the world as a TileGrid and plots
    apples and snakes within it.
    """

    # sprite tile indexes within the spritesheet
    EMPTY_SPRITE_INDEX = 0
    SNAKE_SPRITE_INDEX = 1
    APPLE_RED_SPRITE_INDEX = 2
    APPLE_GREEN_SPRITE_INDEX = 3

    def __init__(self, width=20, height=16):

        # load the spritesheet
        self.spritesheet_bmp, self.spritesheet_palette = adafruit_imageload.load(
            "snake_spritesheet.bmp"
        )

        # initialize the superclass TileGrid
        super().__init__(
            bitmap=self.spritesheet_bmp,
            pixel_shader=self.spritesheet_palette,
            width=width,
            height=height,
            tile_width=8,
            tile_height=8,
            default_tile=0,
        )

    def draw_snake(self, snake):
        """
        Set the snake segments into the TileGrid at their current locations.
        """
        # loop over all segment location x,y pairs
        for location in snake.locations:
            # update the TileGrid to show the snake sprite at this location
            self[location] = self.SNAKE_SPRITE_INDEX

    def move_snake(self, snake):
        # pylint: disable=too-many-branches
        """
        Move the snake one step in its current direction
        """
        # variable to hold what we will return
        return_val = None

        # store the previous head location
        prev_loc = tuple(snake.head)

        # variable for the next loc, starts on prev_loc and will be modified below
        next_loc = [prev_loc[X], prev_loc[Y]]

        # if the snake is going up
        if snake.direction == snake.DIRECTION_UP:
            # if the snake is not at the top edge
            if snake.head[Y] > 0:
                # move the next_loc Y value north by 1
                next_loc[Y] -= 1

            else:  # snake is at top edge
                raise GameOverException("Game Over - OOB Top")

        # if the snake is going down
        if snake.direction == snake.DIRECTION_DOWN:
            # if the snake is not at the bottom edge
            if snake.head[Y] < self.height - 1:
                # move the next_loc Y value south by 1
                next_loc[Y] += 1

            else:  # snake is at bottom edge
                raise GameOverException("Game Over - OOB Bottom")

        # if the snake is going left
        if snake.direction == snake.DIRECTION_LEFT:
            # if the snake is not at the left edge
            if snake.head[X] > 0:
                # move the next_loc Y value west by 1
                next_loc[X] -= 1

            else:  # snake is at left edge
                raise GameOverException("Game Over - OOB Left")

        # if snake is going right
        if snake.direction == snake.DIRECTION_RIGHT:
            # if snake is not at the right edge
            if snake.head[X] < self.width - 1:
                # move the next_loc Y value east by 1
                next_loc[X] += 1

            else:  # snake is at right edge
                raise GameOverException("Game Over - OOB Right")

        # Check if there is an apple at the next_loc
        if self[tuple(next_loc)] in (
            self.APPLE_RED_SPRITE_INDEX,
            self.APPLE_GREEN_SPRITE_INDEX,
        ):
            # add the next_loc as a new segment to the snake
            # it goes at the beginning of the list, making
            # it the new head segment
            snake.locations.insert(0, next_loc)

            # if it's a red apple
            if self[tuple(next_loc)] == self.APPLE_RED_SPRITE_INDEX:
                # add a new red apple to replace it
                self.add_apple(
                    snake=snake, apple_sprite_index=self.APPLE_RED_SPRITE_INDEX
                )
                # update the return_val to indicate red apple was eaten
                return_val = self.APPLE_RED_SPRITE_INDEX

            # if it's a green apple
            elif self[tuple(next_loc)] == self.APPLE_GREEN_SPRITE_INDEX:
                # add a new green apple to replace it
                self.add_apple(
                    snake=snake, apple_sprite_index=self.APPLE_GREEN_SPRITE_INDEX
                )
                # update the return_val to indicate green apple was eaten
                return_val = self.APPLE_GREEN_SPRITE_INDEX

        # check if a snake segment is at the next_loc
        elif self[tuple(next_loc)] == self.SNAKE_SPRITE_INDEX:
            # snake ran into itself
            raise GameOverException("Game Over - Ran Into Self")

        # there is nothing at the next_loc
        else:
            # change the head segment location to next_loc
            snake.locations[0] = next_loc

            # loop over all segments in the snake
            for i, location in enumerate(snake.locations):
                # skip the head segment, it's already been handled
                if i != 0:
                    # temp var with this segment location
                    _tmp = tuple(location)
                    # update the X value of this segment to the X from prev_loc
                    snake.locations[i][X] = prev_loc[X]
                    # update the Y value of this segment to the Y from prev_loc
                    snake.locations[i][Y] = prev_loc[Y]

                    # update prev_loc to the temp var
                    prev_loc = _tmp

                # if this is the tail segment
                if i == len(snake.locations) - 1:  # tail
                    # set this location to an empty tile
                    # it's now the empty tile behind the snake
                    self[prev_loc] = self.EMPTY_SPRITE_INDEX

        # draw the snake at the new location
        self.draw_snake(snake)

        # return the apple that was eaten or None
        return return_val

    def add_apple(
        self, location=None, snake=None, apple_sprite_index=APPLE_RED_SPRITE_INDEX
    ):
        """
        Add a new apple to the world
        """
        # check if snake was passed in
        if snake is None:
            # we need the snake so that we avoid putting an apple
            # in the same spot as any of its segments.
            raise AttributeError("Must pass snake")

        # loop until the location contains an empty tile
        while location is None or self[location] != self.EMPTY_SPRITE_INDEX:

            # select a random location in the world
            location = [
                random.randint(0, self.width - 1),
                random.randint(0, self.height - 1),
            ]

        # set the tile at the lcoation to the appropriate apple sprite tile index
        self[tuple(location)] = apple_sprite_index


class SpeedAdjuster:
    """
    SpeedAdjuster helper class keeps track of the speed of the snake
    and provides easy to use increase and decrease speed functions.

    Speed is controlled by altering the delay time between
    game steps.
    """

    # min and max delay values in seconds
    MIN = 0.05
    MAX = 0.4

    def __init__(self, speed):
        """
        :param speed: speed as a value 0-20, lower is faster.
        """
        # limit speed to the range 0-20
        if speed < 0 or speed > 20:
            raise ValueError("Speed must be between 0 and 20")

        # store speed value on self
        self.speed = speed

        # map the speed value to a delay value between the min and max
        self.delay = SpeedAdjuster.map_range(
            self.speed, 0, 20, SpeedAdjuster.MIN, SpeedAdjuster.MAX
        )

    def increase_speed(self):
        """
        Speed up by 1 speed value
        """

        # if we aren't at max speed already
        if self.speed > 0:
            # speed value goes down by one because lower is faster
            self.speed -= 1
            # update the delay with the new speed value mapped between min and max
            self.delay = SpeedAdjuster.map_range(
                self.speed, 0, 20, SpeedAdjuster.MIN, SpeedAdjuster.MAX
            )

    def decrease_speed(self):
        """
        Slow down by 1 speed value
        """
        # if we aren't at min speed already
        if self.speed < 20:
            # speed value goes up by one because higher is slower
            self.speed += 1
            # update the delay with the new speed value mapped between min and max
            self.delay = SpeedAdjuster.map_range(
                self.speed, 0, 20, SpeedAdjuster.MIN, SpeedAdjuster.MAX
            )

    @staticmethod
    def map_range(x, in_min, in_max, out_min, out_max):
        """
        Maps a number from one range to another.
        Note: This implementation handles values < in_min
        differently than arduino's map function does.
        Copied from circuitpython simpleio

        :return: Returns value mapped to new range
        :rtype: float
        """
        in_range = in_max - in_min
        in_delta = x - in_min
        if in_range != 0:
            mapped = in_delta / in_range
        elif in_delta != 0:
            mapped = in_delta
        else:
            mapped = 0.5
        mapped *= out_max - out_min
        mapped += out_min
        if out_min <= out_max:
            return max(min(mapped, out_max), out_min)
        return min(max(mapped, out_max), out_min)


class GameOverException(Exception):
    """
    Exception that indicates the game is over.
    Message will contain the reason.
    """
