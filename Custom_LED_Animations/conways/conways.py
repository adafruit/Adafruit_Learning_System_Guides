# SPDX-FileCopyrightText: 2024 Tim Cocks
#
# SPDX-License-Identifier: MIT
"""
ConwaysLifeAnimation helper class
"""
from micropython import const

from adafruit_led_animation.animation import Animation
from adafruit_led_animation.grid import PixelGrid, HORIZONTAL
import random


class ConwaysLifeAnimation(Animation):
    # Constants
    DIRECTION_OFFSETS = [
        (0, 1),
        (0, -1),
        (1, 0),
        (-1, 0),
        (1, 1),
        (-1, 1),
        (1, -1),
        (-1, -1)
    ]
    LIVE = const(0x01)
    DEAD = const(0x00)

    def __init__(self, pixel_object, speed, color, width, height, initial_cells, equilibrium_restart=True):
        """
        Conway's Game of Life implementation. Watch the cells live and die based on the classic rules.

        :param pixel_object: The initialised LED object.
        :param float speed: Animation refresh rate in seconds, e.g. ``0.1``.
        :param color: the color to use for live cells
        :param width: the width of the grid
        :param height: the height of the grid
        :param initial_cells: list of initial cells to be live
        :param equilibrium_restart: whether to restart when the simulation gets stuck unchanging
        """
        super().__init__(pixel_object, speed, color)

        # list to hold which cells are live
        self.drawn_pixels = []

        # store the initial cells
        self.initial_cells = initial_cells

        # PixelGrid helper to access the strand as a 2D grid
        self.pixel_grid = PixelGrid(pixel_object, width, height, orientation=HORIZONTAL, alternating=False)

        # size of the grid
        self.width = width
        self.height = height

        # equilibrium restart boolean
        self.equilibrium_restart = equilibrium_restart

        # counter to store how many turns since the last change
        self.equilibrium_turns = 0

        #self._init_cells()

    def _is_pixel_off(self, pixel):
        return pixel[0] == 0 and pixel[1] == 0 and pixel[2] == 0

    def _is_grid_empty(self):
        """
        Checks if the grid is empty.

        :return: True if there are no live cells, False otherwise
        """
        for y in range(self.height):
            for x in range(self.width):
                if not self._is_pixel_off(self.pixel_grid[x,y]):
                    return False

        return True

    def _init_cells(self):
        """
        Turn off all LEDs then turn on ones cooresponding to the initial_cells

        :return: None
        """
        self.pixel_grid.fill(0x000000)
        for cell in self.initial_cells:
            self.pixel_grid[cell] = self.color

    def _count_neighbors(self, cell):
        """
        Check how many live cell neighbors are found at the given location
        :param cell: the location to check
        :return: the number of live cell neighbors
        """
        neighbors = 0
        for direction in ConwaysLifeAnimation.DIRECTION_OFFSETS:
            try:
                if not self._is_pixel_off(self.pixel_grid[cell[0] + direction[0], cell[1] + direction[1]]):
                    neighbors += 1
            except IndexError:
                pass
        return neighbors

    def draw(self):
        """
        draw the current frame of the animation

        :return: None
        """
        # if there are no live cells
        if self._is_grid_empty():
            # spawn the inital_cells and return
            self._init_cells()
            return

        # list to hold locations to despawn live cells
        despawning_cells = []

        # list to hold locations spawn new live cells
        spawning_cells = []

        # loop over the grid
        for y in range(self.height):
            for x in range(self.width):

                # check and set the current cell type, live or dead
                if self._is_pixel_off(self.pixel_grid[x,y]):
                    cur_cell_type = ConwaysLifeAnimation.DEAD
                else:
                    cur_cell_type = ConwaysLifeAnimation.LIVE

                # get a count of the neigbors
                neighbors = self._count_neighbors((x, y))

                # if the current cell is alive
                if cur_cell_type == ConwaysLifeAnimation.LIVE:
                    # if it has fewer than 2 neighbors
                    if neighbors < 2:
                        # add its location to the despawn list
                        despawning_cells.append((x, y))

                    # if it has more than 3 neighbors
                    if neighbors > 3:
                        # add its location to the despawn list
                        despawning_cells.append((x, y))

                # if the current location is not a living cell
                elif cur_cell_type == ConwaysLifeAnimation.DEAD:
                    # if it has exactly 3 neighbors
                    if neighbors == 3:
                        # add the current location to the spawn list
                        spawning_cells.append((x, y))

        # loop over the despawn locations
        for cell in despawning_cells:
            # turn off LEDs at each location
            self.pixel_grid[cell] = 0x000000

        # loop over the spawn list
        for cell in spawning_cells:
            # turn on LEDs at each location
            self.pixel_grid[cell] = self.color

        # if equilibrium restart mode is enabled
        if self.equilibrium_restart:
            # if there were no cells spawned or despaned this round
            if len(despawning_cells) == 0 and len(spawning_cells) == 0:
                # increment equilibrium turns counter
                self.equilibrium_turns += 1
                # if the counter is 3 or higher
                if self.equilibrium_turns >= 3:
                    # go back to the initial_cells
                    self._init_cells()

                    # reset the turns counter to zero
                    self.equilibrium_turns = 0
