# SPDX-FileCopyrightText: 2020 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

class MatrixSand:
    """Class to simulate simplified sand physics."""

    def __init__(self, width, height):
        self._width = width
        self._height = height
        self._grains = [False] * width * height

    def __getitem__(self, value):
        if isinstance(value, tuple):
            value = value[0] + self._width * value[1]
        return self._grains[value]

    def __setitem__(self, value, key):
        if isinstance(value, tuple):
            value = value[0] + self._width * value[1]
        self._grains[value] = key

    def _side_count(self, upside_down=False):
        left = right = 0
        for x in range(self._width):
            for y in range(self._height):
                if x != y and self[x, y]:
                    if x > y:
                        right += 1
                    else:
                        left += 1
        if upside_down:
            return right, left
        else:
            return left, right

    def iterate(self, acceleration):
        """Update sand based on supplied acceleration tuple. Returns True if
        any motion occurred, otherwise False."""
        #pylint: disable=too-many-locals,too-many-nested-blocks,too-many-branches

        ax, ay, az = acceleration

        # if z dominates, don't do anything
        if abs(az) > abs(ax) and abs(az) > abs(ay):
            return False

        # unit vectors for accelo
        ix = iy = 0
        if abs(ax) > 0.01:
            ratio = abs(ay / ax)
            if ratio < 2.414: # tan(67.5deg)
                ix = 1 if ax > 0 else -1
            if ratio > 0.414: # tan(22.5deg)
                iy = 1 if ay > 0 else -1
        else:
            iy = 1 if ay > 0 else -1

        # buffer
        new_grains = self._grains[:]

        # flag to indicate change
        updated = False

        # loop through the grains
        for x in range(self._width):
            for y in range(self._height):
                # is there a grain here?
                if self[x, y]:
                    moved = False
                    # compute new location
                    newx = x + ix
                    newy = y + iy
                    # bounds check
                    newx = max(min(self._width-1, newx), 0)
                    newy = max(min(self._height-1, newy), 0)
                    # wants to move?
                    if x != newx or y != newy:
                        moved = True
                        # is it blocked?
                        if new_grains[newx + self._width * newy]:
                            # can we move diagonally?
                            if not new_grains[x + self._width * newy] and \
                               not new_grains[newx + self._width * y]:
                                # can move either way
                                # move away from fuller side
                                left, right = self._side_count(ax < 0 and ay < 0)
                                if left >= right:
                                    newy = y
                                elif right > left:
                                    newx = x
                            elif not new_grains[x + self._width * newy]:
                                # move in y only
                                newx = x
                            elif not new_grains[newx + self._width * y]:
                                # move in x only
                                newy = y
                            else:
                                # nope, totally blocked
                                moved = False
                    # did it move?
                    if moved:
                        new_grains[x + self._width * y] = False
                        new_grains[newx + self._width * newy] = True
                        updated = True

        # did things change?
        if updated:
            self._grains = new_grains

        return updated
