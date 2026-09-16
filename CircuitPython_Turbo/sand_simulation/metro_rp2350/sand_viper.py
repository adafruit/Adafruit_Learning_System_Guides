# SPDX-FileCopyrightText: 2026 Tim Cocks for Adafruit Industries (algorithm)
# SPDX-FileCopyrightText: 2017 Phillip Burgess for Adafruit Industries (algorithm)
# SPDX-License-Identifier: MIT
"""Accelerometer 'sand' kernels as @micropython.viper, ported from LED_Sand.ino.

Positions are in grain units, 256 to a cell as in the original, so grains move
in sub-cell steps. Everything is integer because viper has no float type; the
only divisions are in the velocity clamp and in splitting up fast moves,
and only grains above one cell per frame take either path.

All state lives in caller-owned buffers, so the kernels allocate nothing.
new() returns them in this order:

  grains  array('i')   5 ints per grain: x, y, velocity x, velocity y, color
  grid    bytearray    one byte per cell, row by row: 0 = empty, 1 = grain,
                       2 = obstacle
  pixels  bytearray    RGB565 pixels, cell_size x cell_size per cell; hand
                       this to picogame.Canvas(buffer=...)
  params  array('i')   settings in and results out, one int per PARAM_* slot
                       below, then the backdrop's cell colors

The kernels take buffers rather than Python objects because viper reads and
writes a ptr8/ptr16/ptr32 argument directly as memory, with no object
overhead. That is also why the settings travel in one int array instead of
as separate arguments: a PARAM_* name is a const(), so viper compiles
params[PARAM_GRID_WIDTH] to a load from a fixed offset.

The kernels write pixels directly, behind the Canvas's back. step() reports
the rectangle it touched (the "dirty" rectangle) so the caller can tell the
Canvas to redraw it.

A backdrop is a picture, one color per cell, that shows wherever no
grain is, in place of the background color: backdrop() sets it up, and marks
the cells of it that grains can't enter (as Adafruit_PixelDust's setPixel()
does). Since grains never enter an obstacle, the kernels never repaint one.
"""

import array

import micropython
from micropython import const

# pylint: disable=undefined-variable, too-many-statements, too-many-locals, too-many-nested-blocks, too-many-branches

# The slots of params, as indexes into it.
PARAM_GRID_WIDTH = const(0)  # grid width in cells
PARAM_GRID_HEIGHT = const(1)  # grid height in cells
PARAM_GRAIN_COUNT = const(2)  # number of grains, < grid width * height
PARAM_CELL_SIZE = const(3)  # pixels per cell edge
PARAM_BACKGROUND = const(4)  # background color
PARAM_RANDOM_STATE = const(5)  # random number generator's state, updated in place
PARAM_ACCEL_X = const(6)  # acceleration this frame, grain units per frame
PARAM_ACCEL_Y = const(7)
PARAM_JITTER_RANGE = const(8)  # each axis's velocity gets 0 .. jitter range - 1 added
PARAM_DIRTY_LEFT = const(9)  # out: dirty cells are [left, right) x [top, bottom)
PARAM_DIRTY_TOP = const(10)
PARAM_DIRTY_RIGHT = const(11)
PARAM_DIRTY_BOTTOM = const(12)
PARAM_TOP_LEFT_COLOR = const(13)  # out: pixel color at the dirty rect's top-left corner
PARAM_BOTTOM_RIGHT_COLOR = const(14)  # out: pixel color at its bottom-right corner
PARAM_MAX_SPEED = const(15)  # top speed, grain units per frame; 256 is one cell
PARAM_BACKDROP_X = const(16)  # backdrop's top-left cell; may be off the grid
PARAM_BACKDROP_Y = const(17)
PARAM_BACKDROP_WIDTH = const(18)  # backdrop size in cells, 0 for none
PARAM_BACKDROP_HEIGHT = const(19)
# Backdrop colors from here to the end, row by row:
# params[PARAM_BACKDROP_COLORS + row * backdrop_width + column]
PARAM_BACKDROP_COLORS = const(20)


def new(
    grid_width,
    grid_height,
    grain_count,
    cell_size,
    background=0,
    seed=12345,
    backdrop_cells=0,
):
    """Allocate the four state buffers, with room in params for a backdrop of
    up to `backdrop_cells` cells. Fill in grain colors, maybe backdrop(), then
    place()."""
    if not 0 < grain_count < grid_width * grid_height:
        raise ValueError(
            "grain_count must be between 1 and grid_width * grid_height - 1"
        )
    # Largest first, each at its final size: a 320x240 canvas is 150 KB of
    # contiguous heap, and growing an array element by element leaves holes.
    pixels = bytearray(grid_width * cell_size * grid_height * cell_size * 2)
    grid = bytearray(grid_width * grid_height)
    grains = array.array("i", [0]) * (5 * grain_count)
    params = array.array("i", [0]) * (PARAM_BACKDROP_COLORS + backdrop_cells)
    params[PARAM_GRID_WIDTH] = grid_width
    params[PARAM_GRID_HEIGHT] = grid_height
    params[PARAM_GRAIN_COUNT] = grain_count
    params[PARAM_CELL_SIZE] = cell_size
    params[PARAM_BACKGROUND] = background
    params[PARAM_RANDOM_STATE] = seed & 0x3FFFFFFF
    params[PARAM_JITTER_RANGE] = 1
    params[PARAM_MAX_SPEED] = 256
    return grains, grid, pixels, params


def backdrop(grid, params, x, y, width, height, colors, solid):
    """Show a width x height picture with its top-left cell at (x, y), which
    may be off the grid. colors and solid go through the picture's cells row
    by row, giving each cell's color and whether grains are kept out of it.
    Call before place(), which paints it."""
    if len(params) < PARAM_BACKDROP_COLORS + width * height:
        raise ValueError(
            "params has no room for the backdrop: pass new() backdrop_cells=width*height"
        )
    grid_width = params[PARAM_GRID_WIDTH]
    grid_height = params[PARAM_GRID_HEIGHT]
    # Clear any earlier backdrop's obstacles.
    for cell in range(grid_width * grid_height):
        if grid[cell] == 2:
            grid[cell] = 0
    params[PARAM_BACKDROP_X] = x
    params[PARAM_BACKDROP_Y] = y
    params[PARAM_BACKDROP_WIDTH] = width
    params[PARAM_BACKDROP_HEIGHT] = height
    for row in range(height):
        for column in range(width):
            index = row * width + column
            params[PARAM_BACKDROP_COLORS + index] = colors[index]
            if (
                solid[index]
                and 0 <= x + column < grid_width
                and 0 <= y + row < grid_height
            ):
                grid[(y + row) * grid_width + x + column] = 2
    obstacle_count = sum(1 for occupancy in grid if occupancy == 2)
    if params[PARAM_GRAIN_COUNT] >= grid_width * grid_height - obstacle_count:
        raise ValueError("more grains than free cells")


# The random source is a 30-bit LCG. 30 bits, not 32, so every constant is a small int
# and so the masked result is identical under viper's wrapping arithmetic and CPython's bigints.
#
# Shifting a grain unit position right by 8 (>> 8) divides by 256, giving the
# cell it is in. A cell's index in grid is cell_y * grid_width + cell_x.
#
# Each grain is five ints in grains, starting at grains[offset]:
# offset + 0 and + 1 are its x and y, + 2 and + 3 its velocity, + 4 its color.


@micropython.viper
def place(grains: ptr32, grid: ptr8, pixels: ptr16, params: ptr32):
    """Scatter the grains over distinct free cells at rest and paint the
    canvas: background, backdrop, then grains. Obstacles stay in place."""
    grid_width = params[PARAM_GRID_WIDTH]
    grid_height = params[PARAM_GRID_HEIGHT]
    grain_count = params[PARAM_GRAIN_COUNT]
    cell_size = params[PARAM_CELL_SIZE]
    background = params[PARAM_BACKGROUND]
    random_state = params[PARAM_RANDOM_STATE]
    backdrop_x = params[PARAM_BACKDROP_X]
    backdrop_y = params[PARAM_BACKDROP_Y]
    backdrop_width = params[PARAM_BACKDROP_WIDTH]
    backdrop_height = params[PARAM_BACKDROP_HEIGHT]
    cell_count = grid_width * grid_height
    row_stride = grid_width * cell_size  # pixels in one row of the canvas

    # Take the grains off the grid, leaving obstacles where they are.
    cell = 0
    while cell < cell_count:
        if grid[cell] == 1:
            grid[cell] = 0
        cell += 1
    cell_y = 0
    while cell_y < grid_height:
        cell_x = 0
        while cell_x < grid_width:
            color = background
            backdrop_col = cell_x - backdrop_x
            backdrop_row = cell_y - backdrop_y
            if (
                0 <= backdrop_col < backdrop_width
                and 0 <= backdrop_row < backdrop_height
            ):
                color = params[
                    PARAM_BACKDROP_COLORS + backdrop_row * backdrop_width + backdrop_col
                ]
            # Fill the cell's square of pixels, one row at a time.
            pixel_index = cell_y * cell_size * row_stride + cell_x * cell_size
            row = 0
            while row < cell_size:
                row_end = pixel_index + cell_size
                while pixel_index < row_end:
                    pixels[pixel_index] = color
                    pixel_index += 1
                pixel_index += row_stride - cell_size  # to the next row's start
                row += 1
            cell_x += 1
        cell_y += 1

    grain = 0
    offset = 0
    while grain < grain_count:
        random_state = (random_state * 1664525 + 1013904223) & 0x3FFFFFFF
        cell = (random_state >> 4) % cell_count
        while grid[cell] != 0:
            random_state = (random_state * 1664525 + 1013904223) & 0x3FFFFFFF
            cell = (random_state >> 4) % cell_count
        grid[cell] = 1
        cell_x = cell % grid_width
        cell_y = cell // grid_width
        # A random spot inside the cell, and not moving.
        grains[offset] = cell_x * 256 + ((random_state >> 12) & 255)
        grains[offset + 1] = cell_y * 256 + ((random_state >> 20) & 255)
        grains[offset + 2] = 0
        grains[offset + 3] = 0
        color = grains[offset + 4]
        pixel_index = cell_y * cell_size * row_stride + cell_x * cell_size
        row = 0
        while row < cell_size:
            row_end = pixel_index + cell_size
            while pixel_index < row_end:
                pixels[pixel_index] = color
                pixel_index += 1
            pixel_index += row_stride - cell_size
            row += 1
        grain += 1
        offset += 5
    params[PARAM_RANDOM_STATE] = random_state


@micropython.viper
def step(grains: ptr32, grid: ptr8, pixels: ptr16, params: ptr32) -> int:
    """Advance one frame. Returns how many grains changed cell; when that is
    nonzero, PARAM_DIRTY_LEFT .. PARAM_DIRTY_BOTTOM bound the cells repainted
    and PARAM_TOP_LEFT_COLOR / PARAM_BOTTOM_RIGHT_COLOR hold the colors of
    that rectangle's corner pixels."""
    grid_width = params[PARAM_GRID_WIDTH]
    grid_height = params[PARAM_GRID_HEIGHT]
    grain_count = params[PARAM_GRAIN_COUNT]
    cell_size = params[PARAM_CELL_SIZE]
    background = params[PARAM_BACKGROUND]
    random_state = params[PARAM_RANDOM_STATE]
    accel_x = params[PARAM_ACCEL_X]
    accel_y = params[PARAM_ACCEL_Y]
    jitter_range = params[PARAM_JITTER_RANGE]
    max_speed = params[PARAM_MAX_SPEED]
    max_speed_squared = max_speed * max_speed
    backdrop_x = params[PARAM_BACKDROP_X]
    backdrop_y = params[PARAM_BACKDROP_Y]
    backdrop_width = params[PARAM_BACKDROP_WIDTH]
    backdrop_height = params[PARAM_BACKDROP_HEIGHT]
    max_x = grid_width * 256 - 1  # largest position, in grain units
    max_y = grid_height * 256 - 1
    row_stride = grid_width * cell_size  # pixels in one row of the canvas

    # The rectangle of cells repainted this frame, left and top inclusive,
    # right and bottom exclusive.
    dirty_left = grid_width
    dirty_top = grid_height
    dirty_right = 0
    dirty_bottom = 0
    grains_moved = 0
    grain = 0
    offset = 0
    while grain < grain_count:
        # Apply the acceleration vector, plus a little randomness so tall
        # stacks topple, then clip speed to max_speed. The clip is on the 2D
        # vector so diagonal motion isn't faster. The randomness is 15 random
        # bits (0 to 32767) scaled to 0 .. jitter_range - 1.
        random_state = (random_state * 1664525 + 1013904223) & 0x3FFFFFFF
        velocity_x = (
            grains[offset + 2]
            + accel_x
            + ((((random_state >> 15) & 0x7FFF) * jitter_range) >> 15)
        )
        random_state = (random_state * 1664525 + 1013904223) & 0x3FFFFFFF
        velocity_y = (
            grains[offset + 3]
            + accel_y
            + ((((random_state >> 15) & 0x7FFF) * jitter_range) >> 15)
        )
        # Compare squares, so the square root is only needed when too fast.
        speed_squared = velocity_x * velocity_x + velocity_y * velocity_y
        if speed_squared > max_speed_squared:
            # Integer Newton square root: after the first guess every guess
            # is >= floor(sqrt(speed_squared)), and they fall until they
            # reach it. That is >= |velocity_x|, |velocity_y|, so neither
            # component comes out above max_speed.
            speed = (max_speed + speed_squared // max_speed) >> 1
            while True:
                next_guess = (speed + speed_squared // speed) >> 1
                if next_guess >= speed:
                    break
                speed = next_guess
            # Scale both components by max_speed / speed. Negative ones are
            # made positive first, so they round toward zero too.
            if velocity_x < 0:
                velocity_x = 0 - ((0 - velocity_x) * max_speed // speed)
            else:
                velocity_x = velocity_x * max_speed // speed
            if velocity_y < 0:
                velocity_y = 0 - ((0 - velocity_y) * max_speed // speed)
            else:
                velocity_y = velocity_y * max_speed // speed

        # Collisions are only right for moves of at most one cell per axis,
        # so a faster grain moves in `substeps` equal steps of (step_x,
        # step_y), the first extra_x (extra_y) of them one unit longer so
        # they add up to exactly (velocity_x, velocity_y). Each substep is
        # the original single move. An axis that bounces stops for the rest
        # of the frame, as it would in one move; its extra_x or extra_y
        # becomes -1 to say so.
        substeps = 1
        step_x = velocity_x
        step_y = velocity_y
        extra_x = 0
        extra_y = 0
        if speed_squared > 65536:
            # Maybe faster than one cell (256 units) per frame on some axis.
            # (speed_squared is from before the clamp, so this also catches
            # grains clamped to max_speed.) Speed here means velocity
            # without its sign.
            fastest_speed = velocity_x
            if fastest_speed < 0:
                fastest_speed = 0 - fastest_speed
            speed_y = velocity_y
            if speed_y < 0:
                speed_y = 0 - speed_y
            if speed_y > fastest_speed:
                fastest_speed = speed_y
            if fastest_speed > 256:
                substeps = (fastest_speed + 255) >> 8  # cells to cover, rounded up
                step_x = velocity_x // substeps
                extra_x = velocity_x - step_x * substeps
                step_y = velocity_y // substeps
                extra_y = velocity_y - step_y * substeps

        # Move the grain, treating all the others as stationary. A bounce
        # is `velocity = (0 - velocity) >> 1`, reversing at half speed.
        start_x = grains[offset]
        start_y = grains[offset + 1]
        start_cell = (start_y >> 8) * grid_width + (start_x >> 8)
        grain_x = start_x
        grain_y = start_y
        current_cell = start_cell
        substep = 0
        while substep < substeps:
            next_x = grain_x + step_x
            if substep < extra_x:
                next_x += 1
            next_y = grain_y + step_y
            if substep < extra_y:
                next_y += 1
            # Bounce off the edges of the grid.
            if next_x > max_x:
                next_x = max_x
                velocity_x = (0 - velocity_x) >> 1
                step_x = 0
                extra_x = -1
            elif next_x < 0:
                next_x = 0
                velocity_x = (0 - velocity_x) >> 1
                step_x = 0
                extra_x = -1
            if next_y > max_y:
                next_y = max_y
                velocity_y = (0 - velocity_y) >> 1
                step_y = 0
                extra_y = -1
            elif next_y < 0:
                next_y = 0
                velocity_y = (0 - velocity_y) >> 1
                step_y = 0
                extra_y = -1

            # Bounce off whatever is in the cell it would move into.
            next_cell = (next_y >> 8) * grid_width + (next_x >> 8)
            if next_cell != current_cell and grid[next_cell] != 0:
                cell_distance = next_cell - current_cell
                if cell_distance < 0:
                    cell_distance = 0 - cell_distance
                if cell_distance == 1:  # blocked left or right: cancel x
                    next_x = grain_x
                    velocity_x = (0 - velocity_x) >> 1
                    step_x = 0
                    extra_x = -1
                    next_cell = current_cell
                elif cell_distance == grid_width:  # blocked above or below: cancel y
                    next_y = grain_y
                    velocity_y = (0 - velocity_y) >> 1
                    step_y = 0
                    extra_y = -1
                    next_cell = current_cell
                else:
                    # Diagonal. Try sliding along one axis alone, faster
                    # first; either one alone is sure to change cell.
                    current_speed_x = velocity_x
                    if current_speed_x < 0:
                        current_speed_x = 0 - current_speed_x
                    current_speed_y = velocity_y
                    if current_speed_y < 0:
                        current_speed_y = 0 - current_speed_y
                    if current_speed_x >= current_speed_y:
                        next_cell = (grain_y >> 8) * grid_width + (next_x >> 8)
                        if grid[next_cell] == 0:  # x alone is free
                            next_y = grain_y
                            velocity_y = (0 - velocity_y) >> 1
                            step_y = 0
                            extra_y = -1
                        else:
                            next_cell = (next_y >> 8) * grid_width + (grain_x >> 8)
                            if grid[next_cell] == 0:  # y alone is free
                                next_x = grain_x
                                velocity_x = (0 - velocity_x) >> 1
                                step_x = 0
                                extra_x = -1
                            else:  # neither: stay put, bounce on both axes
                                next_x = grain_x
                                next_y = grain_y
                                velocity_x = (0 - velocity_x) >> 1
                                velocity_y = (0 - velocity_y) >> 1
                                step_x = 0
                                extra_x = -1
                                step_y = 0
                                extra_y = -1
                                next_cell = current_cell
                    else:
                        next_cell = (next_y >> 8) * grid_width + (grain_x >> 8)
                        if grid[next_cell] == 0:  # y alone is free
                            # The original bounces vy here, against its own
                            # comment; x is the axis being cancelled.
                            next_x = grain_x
                            velocity_x = (0 - velocity_x) >> 1
                            step_x = 0
                            extra_x = -1
                        else:
                            next_cell = (grain_y >> 8) * grid_width + (next_x >> 8)
                            if grid[next_cell] == 0:  # x alone is free
                                next_y = grain_y
                                velocity_y = (0 - velocity_y) >> 1
                                step_y = 0
                                extra_y = -1
                            else:  # neither: stay put, bounce on both axes
                                next_x = grain_x
                                next_y = grain_y
                                velocity_x = (0 - velocity_x) >> 1
                                velocity_y = (0 - velocity_y) >> 1
                                step_x = 0
                                extra_x = -1
                                step_y = 0
                                extra_y = -1
                                next_cell = current_cell
            grain_x = next_x
            grain_y = next_y
            current_cell = next_cell
            if step_x == 0 and extra_x <= 0 and step_y == 0 and extra_y <= 0:
                break  # stopped on both axes, so the other substeps would do nothing
            substep += 1
        # Rebound no faster than the original's top speed of one cell per
        # frame allows. v /= -2 from three cells per frame would bounce
        # grains nine times as high, and the sand would take longer to settle.
        if extra_x < 0:  # bounced in x this frame
            if velocity_x > 128:
                velocity_x = 128
            elif velocity_x < -128:
                velocity_x = -128
        if extra_y < 0:  # bounced in y this frame
            if velocity_y > 128:
                velocity_y = 128
            elif velocity_y < -128:
                velocity_y = -128
        grains[offset] = grain_x
        grains[offset + 1] = grain_y
        grains[offset + 2] = velocity_x
        grains[offset + 3] = velocity_y

        # The grain's own start cell is still marked in grid while it moves,
        # which is harmless: each axis only moves one way, so no substep can
        # return to it.
        if current_cell != start_cell:
            grid[start_cell] = 0
            grid[current_cell] = 1
            grains_moved += 1
            # Erase the old cell, to the backdrop if it's on it...
            cell_x = start_x >> 8
            cell_y = start_y >> 8
            if cell_x < dirty_left:
                dirty_left = cell_x
            if cell_x >= dirty_right:
                dirty_right = cell_x + 1
            if cell_y < dirty_top:
                dirty_top = cell_y
            if cell_y >= dirty_bottom:
                dirty_bottom = cell_y + 1
            color = background
            backdrop_col = cell_x - backdrop_x
            backdrop_row = cell_y - backdrop_y
            if (
                0 <= backdrop_col < backdrop_width
                and 0 <= backdrop_row < backdrop_height
            ):
                color = params[
                    PARAM_BACKDROP_COLORS + backdrop_row * backdrop_width + backdrop_col
                ]
            pixel_index = cell_y * cell_size * row_stride + cell_x * cell_size
            row = 0
            while row < cell_size:
                row_end = pixel_index + cell_size
                while pixel_index < row_end:
                    pixels[pixel_index] = color
                    pixel_index += 1
                pixel_index += row_stride - cell_size
                row += 1
            # ...and draw the new one.
            cell_x = grain_x >> 8
            cell_y = grain_y >> 8
            if cell_x < dirty_left:
                dirty_left = cell_x
            if cell_x >= dirty_right:
                dirty_right = cell_x + 1
            if cell_y < dirty_top:
                dirty_top = cell_y
            if cell_y >= dirty_bottom:
                dirty_bottom = cell_y + 1
            color = grains[offset + 4]
            pixel_index = cell_y * cell_size * row_stride + cell_x * cell_size
            row = 0
            while row < cell_size:
                row_end = pixel_index + cell_size
                while pixel_index < row_end:
                    pixels[pixel_index] = color
                    pixel_index += 1
                pixel_index += row_stride - cell_size
                row += 1
        grain += 1
        offset += 5

    params[PARAM_RANDOM_STATE] = random_state
    params[PARAM_DIRTY_LEFT] = dirty_left
    params[PARAM_DIRTY_TOP] = dirty_top
    params[PARAM_DIRTY_RIGHT] = dirty_right
    params[PARAM_DIRTY_BOTTOM] = dirty_bottom
    if grains_moved != 0:
        params[PARAM_TOP_LEFT_COLOR] = pixels[
            dirty_top * cell_size * row_stride + dirty_left * cell_size
        ]
        params[PARAM_BOTTOM_RIGHT_COLOR] = pixels[
            (dirty_bottom * cell_size - 1) * row_stride + dirty_right * cell_size - 1
        ]
    return grains_moved
