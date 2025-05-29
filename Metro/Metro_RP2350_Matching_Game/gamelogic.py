# SPDX-FileCopyrightText: 2025 Melissa LeBlanc-Williams for Adafruit Industries
# SPDX-License-Identifier: MIT

import random
import time
from adafruit_ticks import ticks_ms

GAMEBOARD_POSITION = (55, 8)

SELECTOR_SPRITE = 9
EMPTY_SPRITE = 10
DEBOUNCE_TIME = 0.1  # seconds for debouncing mouse clicks

class GameBoard:
    "Contains the game board"
    def __init__(self, game_grid, swap_piece, selected_piece_group):
        self.x = GAMEBOARD_POSITION[0]
        self.y = GAMEBOARD_POSITION[1]
        self._game_grid = game_grid
        self._selected_coords = None
        self._selected_piece = selected_piece_group[0]
        self._selector = selected_piece_group[1]
        self._swap_piece = swap_piece
        self.selected_piece_group = selected_piece_group

    def add_game_piece(self, column, row, piece_type):
        if 0 <= column < self.columns and 0 <= row < self.rows:
            if self._game_grid[(column, row)] != EMPTY_SPRITE:
                raise ValueError("Position already occupied")
            self._game_grid[(column, row)] = piece_type
        else:
            raise IndexError("Position out of bounds")

    def remove_game_piece(self, column, row):
        if 0 <= column < self.columns and 0 <= row < self.rows:
            self._game_grid[(column, row)] = EMPTY_SPRITE
        else:
            raise IndexError("Position out of bounds")

    def reset(self):
        for column in range(self.columns):
            for row in range(self.rows):
                if self._game_grid[(column, row)] != EMPTY_SPRITE:
                    self.remove_game_piece(column, row)

    def move_game_piece(self, old_x, old_y, new_x, new_y):
        if 0 <= old_x < self.columns and 0 <= old_y < self.rows:
            if 0 <= new_x < self.columns and 0 <= new_y < self.rows:
                if self._game_grid[(new_x, new_y)] == EMPTY_SPRITE:
                    self._game_grid[(new_x, new_y)] = self._game_grid[(old_x, old_y)]
                    self._game_grid[(old_x, old_y)] = EMPTY_SPRITE
                else:
                    raise ValueError("New position already occupied")
            else:
                raise IndexError("New position out of bounds")
        else:
            raise IndexError("Old position out of bounds")

    @property
    def columns(self):
        return self._game_grid.width

    @property
    def rows(self):
        return self._game_grid.height

    @property
    def selected_piece(self):
        if self._selected_coords is not None and self._selected_piece[0] != EMPTY_SPRITE:
            return self._selected_piece[0]
        return None

    @property
    def swap_piece(self):
        return self._swap_piece

    def set_swap_piece(self, column, row):
        # Set the swap piece to the piece at the specified coordinates
        piece = self.get_piece(column, row)
        if self._swap_piece[0] is None and self._swap_piece[0] == EMPTY_SPRITE:
            raise ValueError("Can't swap an empty piece")
        if self._swap_piece.hidden:
            self._swap_piece[0] = piece
            self._swap_piece.x = column * 32 + self.x
            self._swap_piece.y = row * 32 + self.y
            self._swap_piece.hidden = False
            self._game_grid[(column, row)] = EMPTY_SPRITE
        else:
            self._game_grid[(column, row)] = self._swap_piece[0]
            self._swap_piece[0] = EMPTY_SPRITE
            self._swap_piece.hidden = True

    @property
    def selected_coords(self):
        if self._selected_coords is not None:
            return self._selected_coords
        return None

    @property
    def selector_hidden(self):
        return self._selector.hidden

    @selector_hidden.setter
    def selector_hidden(self, value):
        # Set the visibility of the selector
        self._selector.hidden = value

    def set_selected_coords(self, column, row):
        # Set the selected coordinates to the specified column and row
        if 0 <= column < self.columns and 0 <= row < self.rows:
            self._selected_coords = (column, row)
            self.selected_piece_group.x = column * 32 + self.x
            self.selected_piece_group.y = row * 32 + self.y
        else:
            raise IndexError("Selected coordinates out of bounds")

    def select_piece(self, column, row, show_selector=True):
        # Take care of selecting a piece
        piece = self.get_piece(column, row)
        if self.selected_piece is None and piece == EMPTY_SPRITE:
            # If no piece is selected and the clicked piece is empty, do nothing
            return

        if (self.selected_piece is not None and
            (self._selected_coords[0] != column or self._selected_coords[1] != row)):
            # If a piece is already selected and the coordinates don't match, do nothing
            return

        if self.selected_piece is None:
            # No piece selected, so select the specified piece
            self._selected_piece[0] = self.get_piece(column, row)
            self._selected_coords = (column, row)
            self.selected_piece_group.x = column * 32 + self.x
            self.selected_piece_group.y = row * 32 + self.y
            self.selected_piece_group.hidden = False
            self.selector_hidden = not show_selector
            self._game_grid[(column, row)] = EMPTY_SPRITE
        else:
            self._game_grid[(column, row)] = self._selected_piece[0]
            self._selected_piece[0] = EMPTY_SPRITE
            self.selected_piece_group.hidden = True
            self._selected_coords = None

    def get_piece(self, column, row):
        if 0 <= column < self.columns and 0 <= row < self.rows:
            return self._game_grid[(column, row)]
        return None

    @property
    def game_grid_copy(self):
        # Return a copy of the game grid as a 2D list
        return [[self._game_grid[(x, y)] for x in range(self.columns)] for y in range(self.rows)]

class GameLogic:
    "Contains the Logic to examine the game board and determine if a move is valid."
    def __init__(self, display, game_grid, swap_piece, selected_piece_group, game_pieces):
        self._display = display
        self.game_board = GameBoard(game_grid, swap_piece, selected_piece_group)
        self._score = 0
        self._available_moves = []
        if not 3 <= game_pieces <= 8:
            raise ValueError("game_pieces must be between 3 and 8")
        self._game_pieces = game_pieces  # Number of different game pieces
        self._last_update_time = ticks_ms() # For hint timing
        self._last_click_time = ticks_ms()  # For debouncing mouse clicks

    def piece_clicked(self, coords):
        """ Handle a piece click event. """
        if ticks_ms() <= self._last_click_time:
            self._last_click_time -= 2**29 # ticks_ms() wraps around after 2**29 ms

        if ticks_ms() <= self._last_click_time + (DEBOUNCE_TIME * 1000):
            print("Debouncing click, too soon after last click.")
            return
        self._last_click_time = ticks_ms()  # Update last click time

        column, row = coords
        self._last_update_time = ticks_ms()
        # Check if the clicked piece is valid
        if not 0 <= column < self.game_board.columns or not 0 <= row < self.game_board.rows:
            print(f"Clicked coordinates ({column}, {row}) are out of bounds.")
            return

        # If clicked piece is empty and no piece is selected, do nothing
        if (self.game_board.get_piece(column, row) == EMPTY_SPRITE and
            self.game_board.selected_piece is None):
            print(f"No piece at ({column}, {row}) and no piece selected.")
            return

        if self.game_board.selected_piece is None:
            # If no piece is selected, select the piece at the clicked coordinates
            self.game_board.select_piece(column, row)
            return

        if (self.game_board.selected_coords is not None and
            (self.game_board.selected_coords[0] == column and
             self.game_board.selected_coords[1] == row)):
            # If the clicked piece is already selected, deselect it
            self.game_board.select_piece(column, row)
            return

        # If piece is selected and the new coordinates are 1 position
        # away horizontally or vertically, swap the pieces
        if self.game_board.selected_coords is not None:
            previous_x, previous_y = self.game_board.selected_coords
            if ((abs(previous_x - column) == 1 and previous_y == row) or
                (previous_x == column and abs(previous_y - row) == 1)):
                # Swap the pieces
                self.swap_selected_piece(column, row)

    def show_hint(self):
        """ Show a hint by selecting a random available
        move and swapping the pieces back and forth. """
        if self._available_moves:
            move = random.choice(self._available_moves)
            from_coords = move['from']
            to_coords = move['to']
            self.game_board.select_piece(from_coords[0], from_coords[1])
            self.animate_swap(to_coords[0], to_coords[1])
            self.game_board.select_piece(from_coords[0], from_coords[1])
            self.animate_swap(to_coords[0], to_coords[1])
            self._last_update_time = ticks_ms()     # Reset hint timer

    def swap_selected_piece(self, column, row):
        """ Swap the selected piece with the piece at the specified column and row.
        If the swap is not valid, revert to the previous selection. """
        old_coords = self.game_board.selected_coords
        self.animate_swap(column, row)
        if not self.update():
            self.game_board.select_piece(column, row, show_selector=False)
            self.animate_swap(old_coords[0], old_coords[1])

    def animate_swap(self, column, row):
        """ Copy the pieces to separate tilegrids, animate the swap, and update the game board. """
        if 0 <= column < self.game_board.columns and 0 <= row < self.game_board.rows:
            selected_coords = self.game_board.selected_coords
            if selected_coords is None:
                print("No piece selected to swap.")
                return

            # Set the swap piece value to the column, row value
            self.game_board.set_swap_piece(column, row)
            self.game_board.selector_hidden = True

            # Calculate the steps for animation to move the pieces in the correct direction
            selected_piece_steps = (
                (self.game_board.swap_piece.x - self.game_board.selected_piece_group.x) // 32,
                (self.game_board.swap_piece.y - self.game_board.selected_piece_group.y) // 32
            )
            swap_piece_steps = (
                (self.game_board.selected_piece_group.x - self.game_board.swap_piece.x) // 32,
                (self.game_board.selected_piece_group.y - self.game_board.swap_piece.y) // 32
            )

            # Move the tilegrids in small steps to create an animation effect
            for _ in range(32):
                # Move the selected piece tilegrid to the swap piece position
                self.game_board.selected_piece_group.x += selected_piece_steps[0]
                self.game_board.selected_piece_group.y += selected_piece_steps[1]
                # Move the swap piece tilegrid to the selected piece position
                self.game_board.swap_piece.x += swap_piece_steps[0]
                self.game_board.swap_piece.y += swap_piece_steps[1]
                time.sleep(0.002)

            # Set the existing selected piece coords to the swap piece value
            self.game_board.set_swap_piece(selected_coords[0], selected_coords[1])

            # Update the selected piece coordinates to the new column, row
            self.game_board.set_selected_coords(column, row)

            # Deselect the selected piece (which sets the value)
            self.game_board.select_piece(column, row)

    def apply_gravity(self):
        """ Go through each column from the bottom up and move pieces down
        continue until there are no more pieces to move """
        # pylint:disable=too-many-nested-blocks
        while True:
            moved = False
            for x in range(self.game_board.columns):
                for y in range(self.game_board.rows - 1, -1, -1):
                    piece = self.game_board.get_piece(x, y)
                    if piece != EMPTY_SPRITE:
                        # Check if the piece can fall
                        for new_y in range(y + 1, self.game_board.rows):
                            if self.game_board.get_piece(x, new_y) == EMPTY_SPRITE:
                                # Move the piece down
                                self.game_board.move_game_piece(x, y, x, new_y)
                                moved = True
                            break
                    # If the piece was in the top slot before falling, add a new piece
                    if y == 0 and self.game_board.get_piece(x, 0) == EMPTY_SPRITE:
                        self.game_board.add_game_piece(x, 0, random.randint(0, self._game_pieces))
                        moved = True
            if not moved:
                break

    def check_for_matches(self):
        """ Scan the game board for matches of 3 or more in a row or column """
        matches = []
        for x in range(self.game_board.columns):
            for y in range(self.game_board.rows):
                piece = self.game_board.get_piece(x, y)
                if piece != EMPTY_SPRITE:
                    # Check horizontal matches
                    horizontal_match = [(x, y)]
                    for dx in range(1, 3):
                        if (x + dx < self.game_board.columns and
                            self.game_board.get_piece(x + dx, y) == piece):
                            horizontal_match.append((x + dx, y))
                        else:
                            break
                    if len(horizontal_match) >= 3:
                        matches.append(horizontal_match)

                    # Check vertical matches
                    vertical_match = [(x, y)]
                    for dy in range(1, 3):
                        if (y + dy < self.game_board.rows and
                            self.game_board.get_piece(x, y + dy) == piece):
                            vertical_match.append((x, y + dy))
                        else:
                            break
                    if len(vertical_match) >= 3:
                        matches.append(vertical_match)
        return matches

    def update(self):
        """ Update the game logic, check for matches, and apply gravity. """
        matches_found = False
        multiplier = 1
        matches = self.check_for_matches()
        while matches:
            if matches:
                for match in matches:
                    for x, y in match:
                        self.game_board.remove_game_piece(x, y)
                        self._score += 10 * multiplier * len(matches) * (len(match) - 2)
                time.sleep(0.5)  # Pause to show the match removal
                self.apply_gravity()
                matches_found = True
                matches = self.check_for_matches()
                multiplier += 1
        self._available_moves = self.find_all_possible_matches()
        print(f"{len(self._available_moves)} available moves found.")
        return matches_found

    def reset(self):
        """ Reset the game board and score. """
        self.game_board.reset()
        self._score = 0
        self._last_update_time = ticks_ms()
        self.apply_gravity()
        self.update()

    def check_match_after_move(self, row, column, direction, move_type='horizontal'):
        """ Move the piece in a copy of the board to see if it creates a match."""
        if move_type == 'horizontal':
            new_row, new_column = row, column + direction
        else:  # vertical
            new_row, new_column = row + direction, column

        # Check if move is within bounds
        if (new_row < 0 or new_row >= self.game_board.rows or
            new_column < 0 or new_column >= self.game_board.columns):
            return False, False

        # Create a copy of the grid with the moved piece
        new_grid = self.game_board.game_grid_copy
        piece = new_grid[row][column]
        new_grid[row][column], new_grid[new_row][new_column] = new_grid[new_row][new_column], piece

        # Check for horizontal matches at the new position
        horizontal_match = self.check_horizontal_match(new_grid, new_row, new_column, piece)

        # Check for vertical matches at the new position
        vertical_match = self.check_vertical_match(new_grid, new_row, new_column, piece)

        # Also check the original position for matches after the swap
        original_piece = new_grid[row][column]
        horizontal_match_orig = self.check_horizontal_match(new_grid, row, column, original_piece)
        vertical_match_orig = self.check_vertical_match(new_grid, row, column, original_piece)

        all_matches = (horizontal_match + vertical_match +
                       horizontal_match_orig + vertical_match_orig)

        return True, len(all_matches) > 0

    @staticmethod
    def check_horizontal_match(grid, row, column, piece):
        """Check for horizontal 3-in-a-row matches centered
        around or including the given position."""
        matches = []
        columns = len(grid[0])

        # Check all possible 3-piece horizontal combinations that include this position
        for start_column in range(max(0, column - 2), min(columns - 2, column + 1)):
            if (start_column + 2 < columns and
                grid[row][start_column] == piece and
                grid[row][start_column + 1] == piece and
                grid[row][start_column + 2] == piece):
                matches.append([(row, start_column),
                                (row, start_column + 1),
                                (row, start_column + 2)])

        return matches

    @staticmethod
    def check_vertical_match(grid, row, column, piece):
        """Check for vertical 3-in-a-row matches centered around or including the given position."""
        matches = []
        rows = len(grid)

        # Check all possible 3-piece vertical combinations that include this position
        for start_row in range(max(0, row - 2), min(rows - 2, row + 1)):
            if (start_row + 2 < rows and
                grid[start_row][column] == piece and
                grid[start_row + 1][column] == piece and
                grid[start_row + 2][column] == piece):
                matches.append([(start_row, column),
                                (start_row + 1, column),
                                (start_row + 2, column)])

        return matches

    def check_for_game_over(self):
        """ Check if there are no available moves left on the game board. """
        if not self._available_moves:
            return True
        return False

    def find_all_possible_matches(self):
        """
        Scan the entire game board to find all possible moves that would create a 3-in-a-row match.
        """
        possible_moves = []

        for row in range(self.game_board.rows):
            for column in range(self.game_board.columns):
                # Check move right
                can_move, creates_match = self.check_match_after_move(row, column, 1, 'horizontal')
                if can_move and creates_match:
                    possible_moves.append({
                        'from': (column, row),
                        'to': (column + 1, row),
                    })

                # Check move left
                can_move, creates_match = self.check_match_after_move(row, column, -1, 'horizontal')
                if can_move and creates_match:
                    possible_moves.append({
                        'from': (column, row),
                        'to': (column - 1, row),
                    })

                # Check move down
                can_move, creates_match = self.check_match_after_move(row, column, 1, 'vertical')
                if can_move and creates_match:
                    possible_moves.append({
                        'from': (column, row),
                        'to': (column, row + 1),
                    })

                # Check move up
                can_move, creates_match = self.check_match_after_move(row, column, -1, 'vertical')
                if can_move and creates_match:
                    possible_moves.append({
                        'from': (column, row),
                        'to': (column, row - 1),
                    })

        # Remove duplicates because from and to can be reversed
        unique_moves = set()
        for move in possible_moves:
            from_coords = tuple(move['from'])
            to_coords = tuple(move['to'])
            if from_coords > to_coords:
                unique_moves.add((to_coords, from_coords))
            else:
                unique_moves.add((from_coords, to_coords))
        possible_moves = [{'from': move[0], 'to': move[1]} for move in unique_moves]

        return possible_moves

    @property
    def score(self):
        return self._score

    @property
    def time_since_last_update(self):
        return (ticks_ms() - self._last_update_time) / 1000.0
