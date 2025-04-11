# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import os
import random
import time
from io import BytesIO

import terminalio

import adafruit_imageload
from displayio import Group, TileGrid, OnDiskBitmap, Palette, Bitmap
import bitmaptools
import msgpack
from tilepalettemapper import TilePaletteMapper
import ulab.numpy as np

from adafruit_display_text.bitmap_label import Label
from adafruit_displayio_layout.layouts.grid_layout import GridLayout
from adafruit_button import Button
from adafruit_progressbar.horizontalprogressbar import (
    HorizontalProgressBar,
    HorizontalFillDirection,
)

# pylint: disable=too-many-locals, too-many-nested-blocks, too-many-branches, too-many-statements
colors = [0x2244FF, 0xFFFF00]
STATE_TITLE = 0
STATE_PLAYING_OPEN = 1
STATE_PLAYING_SETCALLED = 2
STATE_GAMEOVER = 3

ACTIVE_TURN_TIME_LIMIT = 10.0


def random_selection(lst, count):
    """
    Select items randomly from a list of items.

    returns a list of length count containing the selected items.
    """
    if len(lst) < count:
        raise ValueError("Count must be less than or equal to length of list")
    selection = []
    while len(selection) < count:
        selection.append(lst.pop(random.randrange(len(lst))))
    return selection


def validate_set(card_1, card_2, card_3):
    """
    Check if a set of 3 cards is valid
    :param card_1: the first card
    :param card_2: the second card
    :param card_3: the third card
    :return: True if they are a valid set, False otherwise
    """
    matrix_sums = card_1.tuple + card_2.tuple + card_3.tuple
    for val in matrix_sums:
        if val % 3 != 0:
            return False
    return True


class Match3Card(Group):
    """
    Class representing a Match3 Card. Keeps track of shape, count, color, and fill.

    tuple value mappings:

    color, shape, fill, count
    0    , 1    , 2   , 1

    colors
    purple: 0
       red: 1
     green: 2

    shapes
    rectangle: 0
     triangle: 1
       circle: 2

    fill
    outline: 0
     filled: 1
    striped: 2

    count
      one: 0
      two: 1
    three: 2
    """

    TUPLE_VALUE_TO_TILE_INDEX_LUT = {
        # rectangle filled
        (0, 1, 0): 0,
        (0, 1, 1): 1,
        (0, 1, 2): 2,
        # triangle filled
        (1, 1, 0): 3,
        (1, 1, 1): 4,
        (1, 1, 2): 5,
        # circle filled
        (2, 1, 0): 6,
        (2, 1, 1): 13,
        (2, 1, 2): 20,
        # rectangle outline
        (0, 0, 0): 7,
        (0, 0, 1): 8,
        (0, 0, 2): 9,
        # triangle outline
        (1, 0, 0): 10,
        (1, 0, 1): 11,
        (1, 0, 2): 12,
        # circle outline
        (2, 0, 0): 21,
        (2, 0, 1): 22,
        (2, 0, 2): 23,
        # rectangle striped
        (0, 2, 0): 14,
        (0, 2, 1): 15,
        (0, 2, 2): 16,
        # triangle striped
        (1, 2, 0): 17,
        (1, 2, 1): 18,
        (1, 2, 2): 19,
        # circle striped
        (2, 2, 0): 24,
        (2, 2, 1): 25,
        (2, 2, 2): 26,
    }

    def __init__(self, card_tuple, **kwargs):
        # tile palette mapper to color the card
        self._mapper = TilePaletteMapper(kwargs["pixel_shader"], 5, 1, 1)
        kwargs["pixel_shader"] = self._mapper
        # tile grid to for the visible sprite
        self._tilegrid = TileGrid(**kwargs)
        self._tilegrid.x = 4
        self._tilegrid.y = 4
        # initialize super class Group
        super().__init__()
        # add tilegrid to self instance Group
        self.append(self._tilegrid)
        # numpy array of the card tuple values
        self._tuple = np.array(list(card_tuple), dtype=np.uint8)
        # set the sprite and color based on card attributes
        self._update_card_attributes()

    def _update_card_attributes(self):
        """
        set the sprite and color based on card attributes
        :return: None
        """
        # set color
        color_tuple_val = self._tuple[0]
        self._mapper[0] = [0, color_tuple_val + 2, 2, 3, 4]

        # set tile
        self._tilegrid[0] = Match3Card.TUPLE_VALUE_TO_TILE_INDEX_LUT[
            (self._tuple[1], self._tuple[2], self._tuple[3])
        ]

    def __str__(self):
        return self.tuple

    def __repr__(self):
        return self.tuple

    @property
    def tuple(self):
        """
        The tuple containing attributes values for this card.
        """
        return self._tuple

    def contains(self, coordinates):
        """
        Check if the cards bounding box contains the given coordinates.
        :param coordinates: the coordinates to check
        :return: True if the bounding box contains the given coordinates, False otherwise
        """
        return (
            self.x <= coordinates[0] <= self.x + self._tilegrid.tile_width
            and self.y <= coordinates[1] <= self.y + self._tilegrid.tile_height
        )


class Match3Game(Group):
    """
    Match3 Game helper class

    Holds visual elements, manages state machine.
    """

    def __init__(self, game_state=None, display_size=None, save_location=None):
        # initialize super Group instance
        super().__init__()
        self.game_state = game_state
        self.display_size = display_size

        # list of Match3Card instances representing the current deck
        self.play_deck = []

        # load the spritesheet
        self.card_spritesheet, self.card_palette = adafruit_imageload.load(
            "match3_cards_spritesheet.bmp"
        )

        # start in the TITLE state
        self.cur_state = STATE_TITLE

        # create a grid layout to help place cards neatly
        # into a grid on the display
        grid_size = (6, 3)
        self.card_grid = GridLayout(
            x=10, y=10, width=260, height=200, grid_size=grid_size
        )

        # no set button in the bottom right
        self.no_set_btn_bmp = OnDiskBitmap("btn_no_set.bmp")
        self.no_set_btn_bmp.pixel_shader.make_transparent(0)
        self.no_set_btn = TileGrid(
            bitmap=self.no_set_btn_bmp, pixel_shader=self.no_set_btn_bmp.pixel_shader
        )
        self.no_set_btn.x = display_size[0] - self.no_set_btn.tile_width
        self.no_set_btn.y = display_size[1] - self.no_set_btn.tile_height
        self.append(self.no_set_btn)

        # list to hold score labels, one for each player
        self.score_lbls = []

        # player scores start at 0
        self.scores = [0, 0]

        self.save_location = save_location

        # initialize and position the score labels
        for i in range(2):
            score_lbl = Label(terminalio.FONT, text=f"P{i + 1}:  0", color=colors[i])
            self.score_lbls.append(score_lbl)
            score_lbl.anchor_point = (1.0, 0.0)
            score_lbl.anchored_position = (display_size[0] - 2, 2 + i * 12)
            self.append(score_lbl)

        # deck count label in the bottom left
        self.deck_count_lbl = Label(
            terminalio.FONT, text=f"Deck: {len(self.play_deck)}"
        )
        self.deck_count_lbl.anchor_point = (0.0, 1.0)
        self.deck_count_lbl.anchored_position = (2, display_size[1] - 2)
        self.append(self.deck_count_lbl)

        # will hold active player index
        self.active_player = None

        # list of player index who have called no set
        self.no_set_called_player_indexes = []

        # active turn countdown progress bar
        # below the score labels
        self.active_turn_countdown = HorizontalProgressBar(
            (display_size[0] - 64, 30),
            (60, 6),
            direction=HorizontalFillDirection.LEFT_TO_RIGHT,
            min_value=0,
            max_value=ACTIVE_TURN_TIME_LIMIT * 10,
        )
        self.active_turn_countdown.hidden = True
        self.append(self.active_turn_countdown)

        # will hold the timestamp when active turn began
        self.active_turn_start_time = None

        # add the card grid to self instance Group
        self.append(self.card_grid)

        # list of card objects that have been clicked
        self.clicked_cards = []

        # list of coordinates that have been clicked
        self.clicked_coordinates = []

        # initialize title screen
        self.title_screen = Match3TitleScreen(display_size)
        self.append(self.title_screen)

        # set up the clicked card indicator borders
        self.clicked_card_indicator_palette = Palette(2)
        self.clicked_card_indicator_palette[0] = 0x000000
        self.clicked_card_indicator_palette.make_transparent(0)
        self.clicked_card_indicator_palette[1] = colors[0]
        self.clicked_card_indicator_bmp = Bitmap(24 + 8, 32 + 8, 2)
        self.clicked_card_indicator_bmp.fill(1)
        bitmaptools.fill_region(
            self.clicked_card_indicator_bmp,
            2,
            2,
            self.clicked_card_indicator_bmp.width - 2,
            self.clicked_card_indicator_bmp.height - 2,
            value=0,
        )
        self.clicked_card_indicators = []
        for _ in range(3):
            self.clicked_card_indicators.append(
                TileGrid(
                    bitmap=self.clicked_card_indicator_bmp,
                    pixel_shader=self.clicked_card_indicator_palette,
                )
            )

    def update_scores(self):
        """
        Update the score labels to reflect the current player scores
        :return: None
        """
        for player_index in range(2):
            prefix = ""
            if player_index == self.active_player:
                prefix = ">"
            if player_index in self.no_set_called_player_indexes:
                prefix = "*"
            self.score_lbls[player_index].text = (
                f"{prefix}P{player_index + 1}: {self.scores[player_index]}"
            )

    def save_game_state(self):
        """
        Save the game state to a file
        :return: None
        """
        # if there is a valid save location
        if self.save_location is not None:
            # create a dictionary object to store the game state
            game_state = {"scores": self.scores, "board": {}, "deck": []}
            # read the current board state into the dictionary object
            for _y in range(3):
                for _x in range(6):
                    try:
                        content = self.card_grid.get_content((_x, _y))
                        game_state["board"][f"{_x},{_y}"] = tuple(content.tuple)
                    except KeyError:
                        pass
            # read the current deck state into the dictionary object
            for card in self.play_deck:
                game_state["deck"].append(tuple(card.tuple))

            # msgpack the object and write it to a file
            b = BytesIO()
            msgpack.pack(game_state, b)
            b.seek(0)
            with open(self.save_location, "wb") as f:
                f.write(b.read())

    def load_from_game_state(self, game_state):
        """
        Load game state from a dictionary.
        :param game_state: The dictionary of game state to load
        :return: None
        """
        # loop over cards in the deck
        for card_tuple in game_state["deck"]:
            # create a card instance and add it to the deck
            self.play_deck.append(
                Match3Card(
                    card_tuple,
                    bitmap=self.card_spritesheet,
                    pixel_shader=self.card_palette,
                    tile_width=24,
                    tile_height=32,
                )
            )

        # loop over grid cells
        for y in range(3):
            for x in range(6):
                # if the current cell is in the board state of the save game
                if f"{x},{y}" in game_state["board"]:
                    # create a card instance and put it in the grid here
                    card_tuple = game_state["board"][f"{x},{y}"]
                    self.card_grid.add_content(
                        Match3Card(
                            card_tuple,
                            bitmap=self.card_spritesheet,
                            pixel_shader=self.card_palette,
                            tile_width=24,
                            tile_height=32,
                        ),
                        (x, y),
                        (1, 1),
                    )
        # set the scores from the game state
        self.scores = game_state["scores"]
        # update the visible score labels
        self.update_scores()
        # update the deck count label
        self.deck_count_lbl.text = f"Deck: {len(self.play_deck)}"

    def init_new_game(self):
        """
        Initialize a new game state.
        :return: None
        """
        self.play_deck = []
        # loop over the 3 possibilities in each of the 4 attributes
        for _color in range(0, 3):
            for _shape in range(0, 3):
                for _fill in range(0, 3):
                    for _count in range(0, 3):
                        # create a card instance with the current attributes
                        self.play_deck.append(
                            Match3Card(
                                (_color, _shape, _fill, _count),
                                bitmap=self.card_spritesheet,
                                pixel_shader=self.card_palette,
                                tile_width=24,
                                tile_height=32,
                            )
                        )

        # draw the starting cards at random
        starting_pool = random_selection(self.play_deck, 12)

        # put the starting cards into the grid layout
        for y in range(3):
            for x in range(4):
                self.card_grid.add_content(starting_pool[y * 4 + x], (x, y), (1, 1))

        # update the deck count label
        self.deck_count_lbl.text = f"Deck: {len(self.play_deck)}"

    def handle_right_click(self, player_index):
        """
        Handle right click event
        :param player_index: the index of the player who clicked
        :return: None
        """
        # if the current state is open play
        if self.cur_state == STATE_PLAYING_OPEN:
            # if there is no active player
            if self.active_player is None:
                # if the player who right clicked is in the no set called list
                if player_index in self.no_set_called_player_indexes:
                    # remove them from the no set called list
                    self.no_set_called_player_indexes.remove(player_index)
                # set the active player to the player that clicked
                self.active_player = player_index
                # set the clicked card indicators to the active player's color
                self.clicked_card_indicator_palette[1] = colors[player_index]
                # set the current state to the set called state
                self.cur_state = STATE_PLAYING_SETCALLED
                # store timestamp of when the active turn began
                self.active_turn_start_time = time.monotonic()
                # make the countdown progress bar visible
                self.active_turn_countdown.hidden = False
                # set the value to the maximum of the progress bar
                self.active_turn_countdown.value = 60
                # update the score labels to show the active player indicator
                self.update_scores()

    def handle_left_click(self, player_index, coords):
        """
        Handle left click events
        :param player_index: the index of the player who clicked
        :param coords: the coordinates where the mouse clicked
        :return: None
        """
        # if the current state is open playing
        if self.cur_state == STATE_PLAYING_OPEN:
            # if the click is on the no set button
            if self.no_set_btn.contains(coords):
                # if the player that clicked is not in the net set called list
                if player_index not in self.no_set_called_player_indexes:
                    # add them to the no set called list
                    self.no_set_called_player_indexes.append(player_index)

                    # if both players have called no set
                    if len(self.no_set_called_player_indexes) == 2:
                        # if there are no cards left in the deck
                        if len(self.play_deck) == 0:
                            # set the state to game over
                            self.cur_state = STATE_GAMEOVER
                            raise GameOverException()

                        # empty the no set called list
                        self.no_set_called_player_indexes = []

                        # find the empty cells in the card grid
                        empty_cells = self.find_empty_cells()
                        # if there are more than 3 empty cells
                        if len(empty_cells) >= 3:
                            # draw 3 new cards
                            _new_cards = random_selection(self.play_deck, 3)
                            # place them in 3 of the empty cells
                            for i, _new_card in enumerate(_new_cards):
                                self.card_grid.add_content(
                                    _new_card, empty_cells[i], (1, 1)
                                )

                        else:  # there are no 3 empty cells
                            # redraw the original grid with 12 new cards

                            # remove existing cards from the grid and
                            # return them to the deck.
                            for _y in range(3):
                                for _x in range(6):
                                    try:
                                        _remove_card = self.card_grid.pop_content(
                                            (_x, _y)
                                        )
                                        print(f"remove_card: {_remove_card}")
                                        self.play_deck.append(_remove_card)

                                    except KeyError:
                                        continue

                            # draw 12 new cards from the deck
                            starting_pool = random_selection(self.play_deck, 12)
                            # place them into the grid
                            for y in range(3):
                                for x in range(4):
                                    self.card_grid.add_content(
                                        starting_pool[y * 4 + x], (x + 1, y), (1, 1)
                                    )

                        # update the deck count label
                        self.deck_count_lbl.text = f"Deck: {len(self.play_deck)}"
                        # save the game state
                        self.save_game_state()

                    # update the score labels to show the no set called indicator(s)
                    self.update_scores()

        # if the current state is set called
        elif self.cur_state == STATE_PLAYING_SETCALLED:
            # if the player that clicked is the active player
            if player_index == self.active_player:
                # get the coordinates that were clicked adjusting for the card_grid position
                adjusted_coords = (
                    coords[0] - self.card_grid.x,
                    coords[1] - self.card_grid.y,
                    0,
                )
                # check which cell contains the clicked coordinates
                clicked_grid_cell_coordinates = self.card_grid.which_cell_contains(
                    coords
                )
                # print(clicked_grid_cell_coordinates)

                # if a cell in the grid was clicked
                if clicked_grid_cell_coordinates is not None:
                    # try to get the content of the clicked cell, a Card instance potentially
                    try:
                        clicked_cell_content = self.card_grid.get_content(
                            clicked_grid_cell_coordinates
                        )
                    except KeyError:
                        # if no content is in the cell just return
                        return

                    # check if the Card instance was clicked, and if the card
                    # isn't already in the list of clicked cards
                    if (
                        clicked_cell_content.contains(adjusted_coords)
                        and clicked_cell_content not in self.clicked_cards
                    ):

                        clicked_card = clicked_cell_content
                        # show the clicked card indicator in this cell
                        clicked_cell_content.insert(
                            0, self.clicked_card_indicators[len(self.clicked_cards)]
                        )
                        # add the card instance to the clicked cards list
                        self.clicked_cards.append(clicked_card)

                        # add the coordinates to the clicked coordinates list
                        self.clicked_coordinates.append(clicked_grid_cell_coordinates)

                        # if 3 cards have been clicked
                        if len(self.clicked_cards) == 3:
                            # check if the 3 cards make a valid set
                            valid_set = validate_set(self.clicked_cards[0],
                                                     self.clicked_cards[1],
                                                     self.clicked_cards[2])

                            # if they are a valid set
                            if valid_set:
                                # award a point to the active player
                                self.scores[self.active_player] += 1

                                # loop over the clicked coordinates
                                for coord in self.clicked_coordinates:
                                    # remove the old card from this cell
                                    _remove_card = self.card_grid.pop_content(coord)
                                    # remove border from Match3Card group
                                    _remove_card.pop(0)

                                # find empty cells in the grid
                                empty_cells = self.find_empty_cells()

                                # if there are at least 3 cards in the deck and
                                # at least 6 empty cells in the grid
                                if len(self.play_deck) >= 3 and len(empty_cells) > 6:
                                    # deal 3 new cards to empty spots in the grid
                                    for i in range(3):
                                        _new_card = random_selection(self.play_deck, 1)[
                                            0
                                        ]
                                        self.card_grid.add_content(
                                            _new_card, empty_cells[i], (1, 1)
                                        )
                                    # update the deck count label
                                    self.deck_count_lbl.text = (
                                        f"Deck: {len(self.play_deck)}"
                                    )

                                # there are not at least 3 cards in the deck
                                # and at least 6 empty cells
                                else:
                                    # if there are no empty cells
                                    if len(self.find_empty_cells()) == 0:
                                        # set the current state to game over
                                        self.cur_state = STATE_GAMEOVER
                                        raise GameOverException()

                            else:  # the 3 clicked cards are not a valid set

                                # remove the clicked card indicators
                                for _ in range(3):
                                    coords = self.clicked_coordinates.pop()
                                    self.card_grid.get_content(coords).pop(0)

                                # subtract a point from the active player
                                self.scores[self.active_player] -= 1

                            # save the game state
                            self.save_game_state()
                            # reset the clicked cards and coordinates lists
                            self.clicked_cards = []
                            self.clicked_coordinates = []

                            # set the current state to open play
                            self.cur_state = STATE_PLAYING_OPEN
                            # set active player and active turn vars
                            self.active_player = None
                            self.active_turn_start_time = None
                            self.active_turn_countdown.hidden = True
                            # update the score labels
                            self.update_scores()

        # if the current state is title state
        elif self.cur_state == STATE_TITLE:
            # if the resume button is visible and was clicked
            if (
                not self.title_screen.resume_btn.hidden
                and self.title_screen.resume_btn.contains(coords)
            ):

                # load the game from the given game state
                self.load_from_game_state(self.game_state)
                # hide the title screen
                self.title_screen.hidden = True  # pylint: disable=attribute-defined-outside-init
                # set the current state to open play
                self.cur_state = STATE_PLAYING_OPEN

            # if the new game button was clicked
            elif self.title_screen.new_game_btn.contains(coords):
                self.game_state = None
                # delete the autosave file
                try:
                    os.remove(self.save_location)
                    print("removed old game save file")
                except OSError:
                    pass
                # initialize a new game
                self.init_new_game()
                # hide the title screen
                self.title_screen.hidden = True  # pylint: disable=attribute-defined-outside-init
                # set the current state to open play
                self.cur_state = STATE_PLAYING_OPEN

    def find_empty_cells(self):
        """
        find the cells within the card grid that are empty
        :return: list of empty cell coordinate tuples.
        """
        empty_cells = []
        for x in range(6):
            for y in range(3):
                try:
                    _content = self.card_grid.get_content((x, y))
                except KeyError:
                    empty_cells.append((x, y))
        return empty_cells

    def update_active_turn_progress(self):
        """
        update the active turn progress bar countdown
        :return:
        """
        if self.cur_state == STATE_PLAYING_SETCALLED:
            time_diff = time.monotonic() - self.active_turn_start_time
            if time_diff > ACTIVE_TURN_TIME_LIMIT:
                self.scores[self.active_player] -= 1
                self.active_player = None
                self.update_scores()
                self.cur_state = STATE_PLAYING_OPEN
                self.active_turn_countdown.hidden = True
            else:
                self.active_turn_countdown.value = int(
                    (ACTIVE_TURN_TIME_LIMIT - time_diff) * 10
                )


class GameOverException(Exception):
    """
    Exception that indicates the game is over.
    Message will contain the reason.
    """


class Match3TitleScreen(Group):
    """
    Title screen for the Match3 game.
    """

    def __init__(self, display_size):
        super().__init__()
        self.display_size = display_size
        # background bitmap color
        bg_bmp = Bitmap(display_size[0] // 10, display_size[1] // 10, 1)
        bg_palette = Palette(1)
        bg_palette[0] = 0xFFFFFF
        bg_tg = TileGrid(bg_bmp, pixel_shader=bg_palette)
        bg_group = Group(scale=10)
        bg_group.append(bg_tg)
        self.append(bg_group)

        # load title card bitmap
        title_card_bmp = OnDiskBitmap("title_card_match3.bmp")
        title_card_tg = TileGrid(
            title_card_bmp, pixel_shader=title_card_bmp.pixel_shader
        )
        title_card_tg.x = 2
        if display_size[1] > 200:
            title_card_tg.y = 20
        self.append(title_card_tg)

        # make resume and new game buttons
        BUTTON_X = display_size[0] - 90
        BUTTON_WIDTH = 70
        BUTTON_HEIGHT = 20
        self.resume_btn = Button(
            x=BUTTON_X,
            y=40,
            width=BUTTON_WIDTH,
            height=BUTTON_HEIGHT,
            style=Button.ROUNDRECT,
            fill_color=0x6D2EDC,
            outline_color=0x888888,
            label="Resume",
            label_font=terminalio.FONT,
            label_color=0xFFFFFF,
        )
        self.append(self.resume_btn)
        self.new_game_btn = Button(
            x=BUTTON_X,
            y=40 + BUTTON_HEIGHT + 10,
            width=BUTTON_WIDTH,
            height=BUTTON_HEIGHT,
            style=Button.RECT,
            fill_color=0x0C9F0C,
            outline_color=0x111111,
            label="New Game",
            label_font=terminalio.FONT,
            label_color=0xFFFFFF,
        )
        self.append(self.new_game_btn)
