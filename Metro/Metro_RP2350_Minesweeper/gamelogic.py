# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams for Adafruit Industries
# SPDX-License-Identifier: MIT

import random
from microcontroller import nvm
from adafruit_ticks import ticks_ms
from displayio import TileGrid

# Mine Densities are about the same as the original
DIFFICULTIES = (
    {
        'label': "Beginner",
        'grid_size': (8,8),
        'mines': 10,
    },
    {
        'label': "Intermediate",
        'grid_size': (14, 14),
        'mines': 30,
    },
    {
        'label': "Expert",
        'grid_size': (20, 14),
        'mines': 58,
    },
)

INFO_BAR_HEIGHT = 16

OPEN = 0
OPEN1 = 1
OPEN2 = 2
OPEN3 = 3
OPEN4 = 4
OPEN5 = 5
OPEN6 = 6
OPEN7 = 7
OPEN8 = 8

BLANK = 9
FLAG = 10
MINE_CLICKED = 11
MINE_FLAGGED_WRONG = 12
MINE = 13
MINE_QUESTION = 14
MINE_QUESTION_OPEN = 15

STATUS_NEWGAME = 0
STATUS_PLAYING = 1
STATUS_WON = 2
STATUS_LOST = 3

class GameLogic:
    def __init__(self, display):
        self._board_data = bytearray()
        self.game_board = None
        self._difficulty = nvm[0]
        if self._difficulty not in DIFFICULTIES:
            self._difficulty = 0
        self._display = display
        self._start_time = None
        self._end_time = None
        self._mine_count = 0
        self._status = STATUS_NEWGAME
        self.reset()

    def reset(self):
        if (self.grid_width * 16 > self._display.width or
            self.grid_height * 16 > self._display.height - INFO_BAR_HEIGHT):
            raise ValueError("Grid size exceeds display size")
        self._mine_count = DIFFICULTIES[self._difficulty]['mines']
        if self._mine_count > (self.grid_width - 1) * (self.grid_height - 1):
            raise ValueError("Too many mines for grid size")
        if self._mine_count < 10:
            raise ValueError("There must be at least 10 mines")
        self._board_data = bytearray(self.grid_width * self.grid_height)
        self._status = STATUS_NEWGAME
        self._start_time = None
        self._end_time = None

    def _seed_mines(self, coords):
        for _ in range(DIFFICULTIES[self._difficulty]['mines']):
            while True:
                mine_x = random.randint(0, self.grid_width - 1)
                mine_y = random.randint(0, self.grid_height - 1)
                if self._get_data(mine_x, mine_y) == 0 and (mine_x, mine_y) != coords:
                    self._set_data(mine_x, mine_y, MINE)
                    break
        self._compute_counts()

    def _set_data(self, x, y, value):
        self._board_data[y * self.grid_width + x] = value

    def _get_data(self, x, y):
        return self._board_data[y * self.grid_width + x]

    def _set_board(self, x, y, value):
        if not isinstance(self.game_board, TileGrid):
            raise ValueError("Game board not initialized")
        self.game_board[x, y] = value # pylint: disable=unsupported-assignment-operation

    def _get_board(self, x, y):
        if not isinstance(self.game_board, TileGrid):
            raise ValueError("Game board not initialized")
        return self.game_board[x, y] # pylint: disable=unsubscriptable-object

    def _compute_counts(self):
        """For each mine, increment the count in each non-mine square around it"""
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                if self._get_data(x, y) != MINE:
                    continue                  # keep looking for mines
                for dx in (-1, 0, 1):
                    if x + dx < 0 or x + dx >= self.grid_width:
                        continue              # off screen
                    for dy in (-1, 0, 1):
                        if y + dy < 0 or y + dy >= self.grid_height:
                            continue          # off screen
                        grid_value = self._get_data(x + dx, y + dy)
                        if grid_value == MINE:
                            continue          # don't process mines
                        self._set_data(x + dx, y + dy, grid_value + 1)

    def _flag_count(self):
        flags = 0
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                if self._get_board(x, y) == FLAG:
                    flags += 1
        return flags

    def expand_uncovered(self, start_x, start_y):
        # pylint: disable=too-many-nested-blocks
        number_uncovered = 1
        stack = [(start_x, start_y)]
        while len(stack) > 0:
            x, y = stack.pop()
            if self._get_board(x, y) == BLANK:
                under_the_tile = self._get_data(x, y)
                if under_the_tile <= OPEN8:
                    self._set_board(x, y, under_the_tile)
                    number_uncovered += 1
                    if under_the_tile == OPEN:
                        for dx in (-1, 0, 1):
                            if x + dx < 0 or x + dx >= self.grid_width:
                                continue              # off screen
                            for dy in (-1, 0, 1):
                                if y + dy < 0 or y + dy >= self.grid_height:
                                    continue          # off screen
                                if dx == 0 and dy == 0:
                                    continue          # don't process where the mine
                                stack.append((x + dx, y + dy))
        return number_uncovered

    def square_flagged(self, coords):
        if self._status in (STATUS_WON, STATUS_LOST):
            return False

        x, y = coords
        TOGGLE_STATES = (BLANK, FLAG, MINE_QUESTION)
        for state in TOGGLE_STATES:
            if self._get_board(x, y) == state:
                self._set_board(x, y,
                    TOGGLE_STATES[(TOGGLE_STATES.index(state) + 1) % len(TOGGLE_STATES)])
                break
        return True

    def square_clicked(self, coords):
        x, y = coords

        if self._status in (STATUS_WON, STATUS_LOST):
            return False

        # First click is never a mine, so start the game
        if self._status == STATUS_NEWGAME:
            self._seed_mines(coords)
            self._status = STATUS_PLAYING
            if self._start_time is None:
                self._start_time = ticks_ms()

        if self._get_board(x, y) != FLAG:
            under_the_tile = self._get_data(x, y)
            if under_the_tile == MINE:
                self._set_data(x, y, MINE_CLICKED)
                self._set_board(x, y, MINE_CLICKED)
                self._status = STATUS_LOST
                self.reveal_board()
                if self._end_time is None:
                    self._end_time = ticks_ms()
                return False          #lost
            elif OPEN1 <= under_the_tile <= OPEN8:
                self._set_board(x, y, under_the_tile)
            elif under_the_tile == OPEN:
                self._set_board(x, y, BLANK)
                self.expand_uncovered(x, y)
            else:
                raise ValueError(f'Unexpected value {under_the_tile} on board')
        return True

    def reveal_board(self):
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                if self._get_board(x, y) == FLAG and self._get_data(x, y) != MINE:
                    self._set_board(x, y, MINE_FLAGGED_WRONG)
                else:
                    self._set_board(x, y, self._get_data(x, y))

    def check_for_win(self):
        """Check for a complete, winning game. That's one with all squares uncovered
        and all bombs correctly flagged, with no non-bomb squares flaged.
        """
        if self._status in (STATUS_WON, STATUS_LOST):
            return None

        # first make sure everything has been explored and decided
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                if self._get_board(x, y) == BLANK or self._get_board(x, y) == MINE_QUESTION:
                    return None               # still ignored or question squares
        # then check for mistagged bombs
        for x in range(self.grid_width):
            for y in range(self.grid_height):
                if self._get_board(x, y) == FLAG and self._get_data(x, y) != MINE:
                    return False               # misflagged bombs, not done
        self._status = STATUS_WON
        if self._end_time is None:
            self._end_time = ticks_ms()
        return True               # nothing unexplored, and no misflagged bombs

    @property
    def grid_width(self):
        return DIFFICULTIES[self._difficulty]['grid_size'][0]

    @property
    def grid_height(self):
        return DIFFICULTIES[self._difficulty]['grid_size'][1]

    @property
    def status(self):
        return self._status

    @property
    def elapsed_time(self):
        """Elapsed time in seconds since the game started with a maximum of 999 seconds"""
        if self._start_time is None:
            return 0
        if self._end_time is None:
            return min(999, (ticks_ms() - self._start_time) // 1000)
        return min(999, (self._end_time - self._start_time) // 1000)

    @property
    def mines_left(self):
        # This number can be negative
        return self._mine_count - self._flag_count()

    @property
    def difficulty(self):
        return self._difficulty

    @difficulty.setter
    def difficulty(self, value):
        if not 0 <= value < len(DIFFICULTIES):
            raise ValueError("Invalid difficulty option")
        self._difficulty = value
        nvm[0] = value
        self.reset()
