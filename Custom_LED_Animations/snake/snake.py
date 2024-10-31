# SPDX-FileCopyrightText: 2024 Tim Cocks
#
# SPDX-License-Identifier: MIT
"""
SnakeAnimation helper class
"""
import random
from micropython import const

from adafruit_led_animation.animation import Animation
from adafruit_led_animation.grid import PixelGrid, HORIZONTAL



class SnakeAnimation(Animation):
    UP = const(0x00)
    DOWN = const(0x01)
    LEFT = const(0x02)
    RIGHT = const(0x03)
    ALL_DIRECTIONS = [UP, DOWN, LEFT, RIGHT]
    DIRECTION_OFFSETS = {
        DOWN: (0, 1),
        UP: (0, -1),
        RIGHT: (1, 0),
        LEFT: (-1, 0)
    }

    def __init__(self, pixel_object, speed, color, width, height, snake_length=3):
        """
        Renders a snake that slithers around the 2D grid of pixels
        """
        super().__init__(pixel_object, speed, color)

        # how many segments the snake will have
        self.snake_length = snake_length

        # create a PixelGrid helper to access our strand as a 2D grid
        self.pixel_grid = PixelGrid(pixel_object, width, height,
                                    orientation=HORIZONTAL, alternating=False)

        # size variables
        self.width = width
        self.height = height

        # list that will hold locations of snake segments
        self.snake_pixels = []

        self.direction = None

        # initialize the snake
        self._new_snake()

    def _clear_snake(self):
        """
        Clear the snake segments and turn off all pixels
        """
        while len(self.snake_pixels) > 0:
            self.pixel_grid[self.snake_pixels.pop()] = 0x000000

    def _new_snake(self):
        """
        Create a new single segment snake. The snake has a random
        direction and location. Turn on the pixel representing the snake.
        """
        # choose a random direction and store it
        self.direction = random.choice(SnakeAnimation.ALL_DIRECTIONS)

        # choose a random starting tile
        starting_tile = (random.randint(0, self.width - 1), random.randint(0, self.height - 1))

        # add the starting tile to the list of segments
        self.snake_pixels.append(starting_tile)

        # turn on the pixel at the chosen location
        self.pixel_grid[self.snake_pixels[0]] = self.color

    def _can_move(self, direction):
        """
        returns true if the snake can move in the given direction
        """
        # location of the next tile if we would move that direction
        next_tile = tuple(map(sum, zip(
            SnakeAnimation.DIRECTION_OFFSETS[direction], self.snake_pixels[0])))

        # if the tile is one of the snake segments
        if next_tile in self.snake_pixels:
            # can't move there
            return False

        # if the tile is within the bounds of the grid
        if 0 <= next_tile[0] < self.width and 0 <= next_tile[1] < self.height:
            # can move there
            return True

        # return false if any other conditions not met
        return False


    def _choose_direction(self):
        """
        Choose a direction to go in. Could continue in same direction
        as it's already going, or decide to turn to a dirction that
        will allow movement.
        """

        # copy of all directions in a list
        directions_to_check = list(SnakeAnimation.ALL_DIRECTIONS)

        # if we can move the direction we're currently going
        if self._can_move(self.direction):
            # "flip a coin"
            if random.random() < 0.5:
                # on "heads" we stay going the same direction
                return self.direction

        # loop over the copied list of directions to check
        while len(directions_to_check) > 0:
            # choose a random one from the list and pop it out of the list
            possible_direction = directions_to_check.pop(
                random.randint(0, len(directions_to_check)-1))
            # if we can move the chosen direction
            if self._can_move(possible_direction):
                # return the chosen direction
                return possible_direction

        # if we made it through all directions and couldn't move in any of them
        # then raise the SnakeStuckException
        raise SnakeAnimation.SnakeStuckException


    def draw(self):
        """
        Draw the current frame of the animation
        """
        # if the snake is currently the desired length
        if len(self.snake_pixels) == self.snake_length:
            # remove the last segment from the list and turn it's LED off
            self.pixel_grid[self.snake_pixels.pop()] = 0x000000

        # if the snake is less than the desired length
        # e.g. because we removed one in the previous step
        if len(self.snake_pixels) < self.snake_length:
            # wrap with try to catch the SnakeStuckException
            try:
                # update the direction, could continue straight, or could change
                self.direction = self._choose_direction()

                # the location of the next tile where the head of the snake will move to
                next_tile = tuple(map(sum, zip(
                    SnakeAnimation.DIRECTION_OFFSETS[self.direction], self.snake_pixels[0])))

                # insert the next tile at list index 0
                self.snake_pixels.insert(0, next_tile)

                # turn on the LED for the tile
                self.pixel_grid[next_tile] = self.color

            # if the snake exception is caught
            except SnakeAnimation.SnakeStuckException:
                # clear the snake to get rid of the old one
                self._clear_snake()

                # make a new snake
                self._new_snake()

    class SnakeStuckException(RuntimeError):
        """
        Exception indicating the snake is stuck and can't move in any direction
        """
        def __init__(self):
            super().__init__("SnakeStuckException")
