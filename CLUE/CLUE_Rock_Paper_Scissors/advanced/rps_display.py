# SPDX-FileCopyrightText: 2020 Kevin J Walters for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# MIT License

# Copyright (c) 2020 Kevin J. Walters

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import time

# These libraries need to be loaded for RPSDisplay class to work but
# will not be used when executed on the CPB without TFT Gizmo
import displayio
from displayio import Group
import terminalio

from adafruit_display_text.label import Label


BLUE=0x0000ff
BLACK=0x000000

DIM_TXT_COL_FG = 0x505050
DEFAULT_TXT_COL_FG = 0xa0a0a0
CURSOR_COL_FG = 0xc0c000
IWELCOME_COL_FG = 0x000010
WELCOME_COL_FG = 0x0000f0
BWHITE_COL_FG = 0xffffff
PLAYER_NAME_COL_FG = 0xc0c000
PLAYER_NAME_COL_BG = BLACK
OPP_NAME_COL_FG = 0x00c0c0
OPP_NAME_COL_BG = BLACK
ERROR_COL_FG = 0xff0000
TITLE_TXT_COL_FG = 0xc000c0
INFO_COL_FG = 0xc0c000
INFO_COL_BG = 0x000080
GS_COL = 0x202020
QM_SORT_FG = 0x808000
QM_SORTING_FG = 0xff8000
RED_COL = 0xff0000
ORANGE_COL = 0xff8000
YELLOW_COL = 0xffff00
DRAWLOSE_COL = 0x0000f0

# NeoPixel colours
GAMENO_GREEN = 0x001200
ROUNDNO_WHITE = 0x0181818
PLAYER_COL = 0xff0000
SCORE_COLS = (0x200600, 0x201300, 0x001200, 0x000020, 0x08000e, 0x140618)

# Colours for NeoPixels on display-less CPB
# Should be dim to avoid an opponent seeing choice from reflected light
# NB: these get << 5 in showPlayerVPlayerNeoPixels
CHOICE_COL = (0x040000,  # Red for Rock
              0x030004,  # Purple for Paper
              0x000004   # Sapphire blue for Scissors
             )


def blankScreen(disp, pix):
    # pylint: disable=unused-argument
    """A blank screen used to hide any serial console output."""
    if disp is None:
        return

    disp.root_group = Group()


class RPSDisplay():

    def __init__(self, disp, pix,
                 choices, sample, sample_victory,
                 max_players, button_y_pos,
                 sprite_filename,
                 sprite_transparent=0,
                 ble_color=0x000010):

        self.disp = disp
        self.std_brightness = self.disp.brightness if disp else None
        self.width = self.disp.width if disp else None
        self.height = self.disp.height if disp else None
        self.pix = pix
        self.pix_len = len(pix)
        self.sample = sample  # a SampleJukebox object
        self.choices = tuple(choices)
        self.sample_victory = dict(sample_victory)
        self.disp_group = None
        self.font = terminalio.FONT
        self.max_players = max_players
        self.button_y_pos = button_y_pos
        self.ble_color = ble_color

        # Top y position of first choice and pixel separate between choices
        self.top_y_pos = 60
        self.choice_sep = 60

        (self.font_width,
         self.font_height) = self.font.get_bounding_box()

        self.pl_x_pos = 10
        self.plrssi_x_rpos = self.width - 10 if self.width else None
        self.pl_y_cur_pos = 7
        self.pl_y_off = 2 * self.font_height + 1

        if disp is None:
            self.sprites = self.opp_sprites = self.sprite_size = None
        else:
            (self.sprites,
             self.opp_sprites,
             self.sprite_size) = self.loadSprites(sprite_filename,
                                                  transparent=sprite_transparent)


    @staticmethod
    def loadSprites(filename, transparent=0):
        """Load horizontal sprite sheet if running with a display
        """
        import adafruit_imageload # pylint: disable=import-outside-toplevel
        s_bit, s_pal = adafruit_imageload.load(filename,
                                               bitmap=displayio.Bitmap,
                                               palette=displayio.Palette)
        sprite_size = s_bit.height
        num_sprites = s_bit.width // s_bit.height

        # For default value, make the first colour transparent
        if transparent is not None:
            s_pal.make_transparent(transparent)

        # Make some sprites from the sprite sheet
        # Sprites can only be in one layer (Group) at a time, need two copies
        # to allow representation of a draw on screen
        sprites = []
        opp_sprites = []
        for idx in range(num_sprites):
            sprite = displayio.TileGrid(s_bit, pixel_shader=s_pal,
                                        width=1, height=1,
                                        tile_width=sprite_size, tile_height=sprite_size)
            sprite[0] = idx
            sprites.append(sprite)

            opp_sprite = displayio.TileGrid(s_bit, pixel_shader=s_pal,
                                            width=1, height=1,
                                            tile_width=sprite_size, tile_height=sprite_size)
            opp_sprite[0] = idx
            opp_sprites.append(opp_sprite)

        return (sprites, opp_sprites, sprite_size)


    def choiceToPixIdx(self, idx):
        """This maps the three choices to three pixels.
           It is also used for game and round numbers.
           The starting position is 0 which is just left of USB connector
           on Circuit Playground boards and going clockwise - this avoids
           the NeoPixels near the buttons which are likely to be under fingers."""
        return -idx % self.pix_len


    def fadeUpDown(self, direction, duration=0.8, steps=10):
        """Fade the display up or down by varything the brightness of the backlight."""

        if self.disp is None:
            return

        if duration == 0.0:
            self.disp.brightness = 0.0 if direction == "down" else self.std_brightness
            return

        if direction == "down":
            step_iter = range(steps - 1, -1, -1)
        elif direction == "up":
            step_iter = range(1, steps + 1)
        else:
            raise ValueError("up or down")

        time_step = duration / steps
        for bri in [idx * self.std_brightness / steps for idx in step_iter]:
            self.disp.brightness = bri
            time.sleep(time_step)


    def showGroup(self, new_group):
        self.disp_group = new_group
        self.disp.root_group = new_group


    def emptyGroup(self, dio_group):
        """Recursive depth first removal of anything in a Group.
           Intended to be used to clean-up a previous screen
           which may have elements in the new screen
           as elements cannot be in two Groups at once since this
           will cause "ValueError: Layer already in a group".
           This only deletes Groups, it does not del the non-Group content."""
        if dio_group is None:
            return

        # Go through Group in reverse order
        for idx in range(len(dio_group) - 1, -1, -1):
            # Avoiding isinstance here as Label is a sub-class of Group!
            # pylint: disable=unidiomatic-typecheck
            if type(dio_group[idx]) == Group:
                self.emptyGroup(dio_group[idx])
            del dio_group[idx]


    def showChoice(self,
                   ch_idx,
                   game_no=None, round_no=None, rounds_tot=None,
                   won_sf=None, drew_sf=None, lost_sf=None):
        """Show player's choice on NeoPixels or display.
           The display also has game and round info and win/draw summary.
           This removes all the graphical objects and re-adds them which
           causes visible flickering during an update - this could be
           improved by only replacing / updating what needs changing.
        """
        if self.disp is None:
            self.pix.fill(BLACK)
            self.pix[self.choiceToPixIdx(ch_idx)] = CHOICE_COL[ch_idx]
            return

        self.emptyGroup(self.disp_group)
        # Would be slightly better to create this Group once and re-use it
        round_choice_group = Group()

        if round_no is not None:
            title_dob = Label(self.font,
                              text="Game {:d}  Round {:d}/{:d}".format(game_no,
                                                                       round_no,
                                                                       rounds_tot),
                              scale=2,
                              color=TITLE_TXT_COL_FG)
            title_dob.x = round((self.width
                                 - len(title_dob.text) * 2 * self.font_width) // 2)
            title_dob.y = round(self.font_height // 2)
            round_choice_group.append(title_dob)

        if won_sf is not None:
            gamesum_dob = Label(self.font,
                                text="Won {:d} Drew {:d} Lost {:d}".format(won_sf,
                                                                           drew_sf,
                                                                           lost_sf),
                                scale=2,
                                color=TITLE_TXT_COL_FG)
            gamesum_dob.x = round((self.width
                                   - len(gamesum_dob.text) * 2 * self.font_width) // 2)
            gamesum_dob.y = round(self.height - 2 * self.font_height // 2)
            round_choice_group.append(gamesum_dob)

        s_group = Group(scale=3)
        s_group.x = 32
        s_group.y = (self.height - 3 * self.sprite_size) // 2
        s_group.append(self.sprites[ch_idx])
        round_choice_group.append(s_group)

        self.showGroup(round_choice_group)


    def introductionScreen(self):
        # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        """Introduction screen."""
        if self.disp is not None:
            self.emptyGroup(self.disp_group)
            intro_group = Group()
            welcometo_dob = Label(self.font,
                                  text="Welcome To",
                                  scale=3,
                                  color=IWELCOME_COL_FG)
            welcometo_dob.x = (self.width - 10 * 3 * self.font_width) // 2
            # Y pos on screen looks lower than I would expect
            welcometo_dob.y = 3 * self.font_height // 2
            intro_group.append(welcometo_dob)

            extra_space = 8
            spacing = 3 * self.sprite_size + extra_space
            y_adj = (-6, -2, -2)
            for idx, sprite in enumerate(self.sprites):
                s_group = Group(scale=3)
                s_group.x = -96
                s_group.y = round((self.height - 1.5 * self.sprite_size) / 2
                                  + (idx - 1) * spacing) + y_adj[idx]
                s_group.append(sprite)
                intro_group.append(s_group)

            arena_dob = Label(self.font,
                              text="Arena",
                              scale=3,
                              color=IWELCOME_COL_FG)
            arena_dob.x = (self.width - 5 * 3 * self.font_width) // 2
            arena_dob.y = self.height - 3 * self.font_height // 2
            intro_group.append(arena_dob)

            self.showGroup(intro_group)

        # The color modification here is fragile as it only works
        # if the text colour is blue, i.e. data is in lsb only
        self.sample.play("welcome-to")
        while self.sample.playing():
            if self.disp is not None and intro_group[0].color < WELCOME_COL_FG:
                intro_group[0].color += 0x10
                time.sleep(0.120)

        onscreen_x_pos = 96

        # Move each sprite onto the screen while saying its name with wav file
        anims = (("rock", 10, 1, 0.050),
                 ("paper", 11, 2, 0.050),
                 ("scissors", 7, 3, 0.050))
        for idx, (audio_name, x_shift, grp_idx, delay_s) in enumerate(anims):
            if self.disp is None:
                self.showChoice(idx)  # Use for NeoPixels
            self.sample.play(audio_name)
            # Audio needs to be long enough to finish movement
            while self.sample.playing():
                if self.disp is not None:
                    if intro_group[grp_idx].x < onscreen_x_pos:
                        intro_group[grp_idx].x += x_shift
                        time.sleep(delay_s)

        # Set NeoPixels back to black
        if self.disp is None:
            self.pix.fill(BLACK)

        self.sample.play("arena")
        while self.sample.playing():
            if self.disp is not None and intro_group[4].color < WELCOME_COL_FG:
                intro_group[4].color += 0x10
                time.sleep(0.060)

        # Button Guide for those with a display
        if self.disp is not None:
            left_dob = Label(self.font,
                             text="< Select    ",
                             scale=2,
                             color=INFO_COL_FG,
                             background_color=INFO_COL_BG)
            left_width = len(left_dob.text) * 2 * self.font_width
            left_dob.x = -left_width
            left_dob.y = self.button_y_pos
            intro_group.append(left_dob)

            right_dob = Label(self.font,
                              text=" Transmit >",
                              scale=2,
                              color=INFO_COL_FG,
                              background_color=INFO_COL_BG)
            right_width = len(right_dob.text) * 2 * self.font_width
            right_dob.x = self.width
            right_dob.y = self.button_y_pos
            intro_group.append(right_dob)

            # Move left button text onto screen, then right
            steps = 20
            for x_pos in [left_dob.x + round(left_width * x / steps)
                          for x in range(1, steps + 1)]:
                left_dob.x = x_pos
                time.sleep(0.06)

            for x_pos in [right_dob.x - round(right_width * x / steps)
                          for x in range(1, steps + 1)]:
                right_dob.x = x_pos
                time.sleep(0.06)

            time.sleep(8)  # leave on screen for further 8 seconds


    def playerListScreen(self):
        if self.disp is None:
            return

        self.emptyGroup(self.disp_group)
        # The two multiplier allows for rssi as separate label
        playerlist_group = Group()
        self.showGroup(playerlist_group)


    def addPlayer(self, name, rssi=None):
        """Add a player to the player list.
           playerListScreen must be called prior to use."""
        if self.disp is None:
            return

        text_color = OPP_NAME_COL_FG if len(self.disp_group) else PLAYER_NAME_COL_FG
        pname_dob = Label(self.font,
                          text=name,
                          scale=2,
                          color=text_color)
        pname_dob.x = self.pl_x_pos
        pname_dob.y = self.pl_y_cur_pos
        self.disp_group.append(pname_dob)

        if rssi is not None:
            prssi_dob = Label(self.font,
                              text="{:4d}".format(round(rssi)),
                              scale=2,
                              color=text_color)
            prssi_dob.x = self.plrssi_x_rpos - 4 * 2 * self.font_width
            prssi_dob.y = self.pl_y_cur_pos
            self.disp_group.append(prssi_dob)

        self.pl_y_cur_pos += self.pl_y_off


    def flashNeoPixels(self, col):
        """The briefest of flashes on the NeoPixels."""
        self.pix.fill(col)
        self.pix.fill(BLACK)


    def flashBLE(self):
        """A brief blue flash to indicate Bluetooth Low Energy activity."""
        self.flashNeoPixels(self.ble_color)


    def showGameRound(self, game_no=0, round_no=0, rounds_tot=None):
        # pylint: disable=unused-argument
        """Show the game and round number on NeoPixels for screenless devices.
           Only used for Gizmo-less CPB."""
        if self.disp is not None:
            return

        # Gradually light NeoPixels in green to show game number
        for p_idx in range(game_no):
            self.pix[self.choiceToPixIdx(p_idx)] = GAMENO_GREEN
            time.sleep(0.5)

        time.sleep(2)

        # Flash white five times at position to indicate round number
        bg_col = self.pix[round_no - 1]
        for _ in range(5):
            pix_idx = self.choiceToPixIdx(round_no - 1)
            self.pix[pix_idx] = ROUNDNO_WHITE
            time.sleep(0.1)
            self.pix[pix_idx] = bg_col
            time.sleep(0.3)

        self.pix.fill(BLACK)


    def showGameResultScreen(self, pla, sco, rounds_tot=None):
        # pylint: disable=unused-argument,too-many-locals,too-many-statements
        """Display a high score table with a visual bubble sort
           slow enough to see the algorithm at work."""
        self.fadeUpDown("down")
        self.emptyGroup(self.disp_group)

        # Score list group + background + question mark for sorting
        gs_group = Group()

        # Pale grey large GAME SCORES background
        bg_scale = 6
        sbg_dob1 = Label(self.font,
                         text="GAME",
                         scale=bg_scale,
                         color=GS_COL)
        sbg_dob1.x = (self.width - 4 * bg_scale * self.font_width) // 2
        sbg_dob1.y = self.height // 4
        sbg_dob2 = Label(self.font,
                         text="SCORES",
                         scale=bg_scale,
                         color=GS_COL)
        sbg_dob2.x = (self.width - 6 * bg_scale * self.font_width) // 2
        sbg_dob2.y = self.height // 4 * 3
        gs_group.append(sbg_dob1)
        gs_group.append(sbg_dob2)
        self.showGroup(gs_group)
        self.fadeUpDown("up")

        # Calculate maximum length player name
        # and see if scores happen to already be in order
        max_len = 0
        prev_score = sco[0]
        descending = True
        for idx, (name, _) in enumerate(pla):
            max_len = max(max_len, len(name))
            if sco[idx] > prev_score:
                descending = False
            prev_score = sco[idx]

        fmt = "{:" + str(max_len) + "s} {:2d}"
        x_pos = (self.width - (max_len + 3) * 2 * self.font_width) // 2
        scale = 2
        spacing = 4 if len(pla) <= 6 else 0
        top_y_pos = round((self.height
                           - len(pla) * scale * self.font_height
                           - (len(pla) - 1) * spacing) / 2
                          + scale * self.font_height / 2)
        scores_group = Group()
        gs_group.append(scores_group)
        for idx, (name, _) in enumerate(pla):
            op_dob = Label(self.font,
                           text=fmt.format(name, sco[idx]),
                           scale=2,
                           color=(PLAYER_NAME_COL_FG if idx == 0 else OPP_NAME_COL_FG))
            op_dob.x = x_pos
            op_dob.y = top_y_pos + idx * (scale * self.font_height + spacing)
            scores_group.append(op_dob)
            time.sleep(0.2)

        # Sort the entries if needed
        sort_scores = list(sco)  # Make an independent local copy
        if not descending:
            empty_group = Group()  # minor hack to aid swaps in scores_group
            step = 3
            qm_dob = Label(self.font,
                           text="?",
                           scale=2,
                           color=QM_SORT_FG)
            qm_dob.x = round(x_pos - 1.5 * scale * self.font_width)
            gs_group.append(qm_dob)
            while True:
                swaps = 0
                for idx in range(0, len(sort_scores) -1):
                    above_score = sort_scores[idx]
                    above_y = scores_group[idx].y
                    below_y = scores_group[idx + 1].y
                    qm_dob.y = (above_y + below_y) // 2
                    if above_score < sort_scores[idx + 1]:
                        qm_dob.text = "<"
                        qm_dob.color = QM_SORTING_FG
                        swaps += 1

                        # make list of steps
                        range_y = below_y - above_y
                        offsets = list(range(step, range_y + 1, step))
                        # Ensure this goes to the exact final position
                        if offsets[-1] != range_y:
                            offsets.append(range_y)

                        for offset in offsets:
                            scores_group[idx].y = above_y + offset
                            scores_group[idx + 1].y = below_y - offset
                            time.sleep(0.050)

                        # swap the scores around
                        sort_scores[idx] = sort_scores[idx + 1]
                        sort_scores[idx + 1] = above_score

                        # swap the graphical objects around using empty_group
                        # to avoid ValueError: Layer already in a group
                        old_above_dob = scores_group[idx]
                        old_below_dob = scores_group[idx + 1]
                        scores_group[idx + 1] = empty_group
                        scores_group[idx] = old_below_dob
                        scores_group[idx + 1] = old_above_dob

                        qm_dob.text = "?"
                        qm_dob.color = QM_SORT_FG
                        time.sleep(0.2)
                    else:
                        time.sleep(0.6)

                if swaps == 0:
                    break   # Sort complete if no values were swapped
            gs_group.remove(qm_dob)


    def showGameResultNeoPixels(self, pla, sco, rounds_tot=None):
        # pylint: disable=unused-argument
        """Display a high score table on NeoPixels.
           Sorted into highest first order then displayed by
           flashing position pixel to indicate player number and
           gradually lighting up pixels in a circle using rainbow
           colours for each revolution of the NeoPixels starting at orange.
           """
        def selectSecondElem(seq):
            """Used in a sort() method to sort my second element in a list."""
            return seq[1]

        # Sort the scores into highest first order
        idx_n_score = [(s, sco[s]) for s in range(len(sco))]
        idx_n_score.sort(key=selectSecondElem, reverse=True)
        ##idx_n_score.sort(key=lambda s: s[1], reverse=True)

        bg_col = BLACK
        for idx, score in idx_n_score:
            playerIdx = self.choiceToPixIdx(idx)
            for scoreRise in range(score):
                scoreIdx = self.choiceToPixIdx(scoreRise)
                rev = min(scoreRise // self.pix_len, len(SCORE_COLS) - 1)
                self.pix[scoreIdx] = SCORE_COLS[rev]
                if scoreIdx == playerIdx:
                    bg_col = SCORE_COLS[rev]
                time.sleep(0.09)
                self.pix[playerIdx] = PLAYER_COL
                time.sleep(0.09)
                self.pix[playerIdx] = bg_col

            for _ in range(4):
                self.pix[playerIdx] = bg_col
                time.sleep(0.5)
                self.pix[playerIdx] = PLAYER_COL
                time.sleep(0.5)

            self.pix.fill(BLACK)


    def showGameResult(self, pla, sco, rounds_tot=None):

        if self.disp is None:
            self.showGameResultNeoPixels(pla, sco, rounds_tot=rounds_tot)
        else:
            self.showGameResultScreen(pla, sco, rounds_tot=rounds_tot)

        # Sound samples for exceptional scores
        if sco[0] == 0:
            self.sample.play("humiliation")
        elif sco[0] >= int((len(sco) - 1) * rounds_tot * 1.5):
            self.sample.play("excellent")

        if self.disp is not None:
            time.sleep(10)  # Leave displayed scores visible

        self.sample.wait()


    def winnerWav(self, mine_idx, yours_idx):
        """Return the sound file to play to describe victory or None for draw."""

        # Take the first characters
        mine = self.choices[mine_idx][0]
        yours = self.choices[yours_idx][0]

        return self.sample_victory.get(mine + yours)


    def showPlayerVPlayerScreen(self, me_name, op_name, my_ch_idx, op_ch_idx,
                                result, summary, win, draw, void):
        # pylint: disable=too-many-locals,too-many-branches,too-many-statements
        """Display a win, draw, lose or error message."""
        self.fadeUpDown("down")
        self.emptyGroup(self.disp_group)

        if void:
            error_tot = 3
            error_group = Group()
            # Opponent's name helps pinpoint the error
            op_dob = Label(self.font,
                           text=op_name,
                           scale=2,
                           color=OPP_NAME_COL_FG)
            op_dob.x = 40
            op_dob.y = self.font_height
            error_group.append(op_dob)
            self.showGroup(error_group)
            self.fadeUpDown("up", duration=0.4)
            if result is not None:
                self.sample.play(result)
            font_scale = 2
            # Attempting to put the three pieces of "Error!" text on screen
            # synchronised with the sound sample repeating the word
            for idx in range(error_tot):
                error_dob = Label(self.font,
                                  text="Error!",
                                  scale=font_scale,
                                  color=ERROR_COL_FG)
                error_dob.x = 40
                error_dob.y = 60 + idx * 60
                error_group.append(error_dob)
                time.sleep(0.5)  # Small attempt to synchronise audio with text
                font_scale += 1

        else:
            # Would be slightly better to create this Group once and re-use it
            pvp_group = Group()

            # Add player's name and sprite just off left side of screen
            # and opponent's just off right
            player_detail = [[me_name, self.sprites[my_ch_idx], -16 - 3 * self.sprite_size,
                              PLAYER_NAME_COL_FG, PLAYER_NAME_COL_BG],
                             [op_name, self.opp_sprites[op_ch_idx], 16 + self.width,
                              OPP_NAME_COL_FG, OPP_NAME_COL_BG]]
            idx_lr = [0, 1]  # index for left and right sprite
            if win:
                player_detail.reverse()  # this player is winner so put last
                idx_lr.reverse()

            # Add some whitespace around winner's name
            player_detail[1][0] = " " + player_detail[1][0] + " "

            for (name, sprite,
                 start_x,
                 fg, bg) in player_detail:
                s_group = Group(scale=2)  # Audio is choppy at scale=3
                s_group.x = start_x
                s_group.y = (self.height - 2 * (self.sprite_size + self.font_height)) // 2

                s_group.append(sprite)
                p_name_dob = Label(self.font,
                                   text=name,
                                   scale=1,  # This is scaled by the group
                                   color=fg,
                                   background_color=bg)
                # Centre text below sprite - values are * Group scale
                p_name_dob.x = (self.sprite_size - len(name) * self.font_width) // 2
                p_name_dob.y = self.sprite_size + 4
                s_group.append(p_name_dob)

                pvp_group.append(s_group)

            if draw:
                sum_text = "Draw"
            elif win:
                sum_text = "You win"
            else:
                sum_text = "You lose"
            # Text starts invisible (BLACK) and color is later changed
            summary_dob = Label(self.font,
                                text=sum_text,
                                scale=3,
                                color=BLACK)
            summary_dob.x = round((self.width
                                   - 3 * self.font_width * len(sum_text)) / 2)
            summary_dob.y = round(self.height - (3 * self.font_height / 2))
            pvp_group.append(summary_dob)

            self.showGroup(pvp_group)
            self.fadeUpDown("up", duration=0.4)

            # Start audio half way through animations
            if draw:
                # Move sprites onto the screen leaving them at either side
                for idx in range(16):
                    pvp_group[idx_lr[0]].x += 6
                    pvp_group[idx_lr[1]].x -= 6
                    if idx == 8 and result is not None:
                        self.sample.play(result)
                    time.sleep(0.2)
            else:
                # Move sprites together, winning sprite overlaps and covers loser
                for idx in range(16):
                    pvp_group[idx_lr[0]].x += 10
                    pvp_group[idx_lr[1]].x -= 10
                    if idx == 8 and result is not None:
                        self.sample.play(result)
                    time.sleep(0.2)

            self.sample.wait()  # Wait for first sample to finish

            if summary is not None:
                self.sample.play(summary)

            # Flash colours for win, fad up to blue for rest
            if not draw and win:
                colours = [YELLOW_COL, ORANGE_COL, RED_COL] * 5
            else:
                colours = [DRAWLOSE_COL * sc // 15 for sc in range(1, 15 + 1)]
            for col in colours:
                summary_dob.color = col
                time.sleep(0.120)

        self.sample.wait()  # Ensure second sample has completed


    def showPlayerVPlayerNeoPixels(self, op_idx, my_ch_idx, op_ch_idx,
                                   result, summary, win, draw, void):
        # pylint: disable=too-many-locals
        """This indicates the choices by putting the colours
           associated with rock paper scissors on the first pixel
           for the player and on subsequent pixels for opponents.
           A win brightens the winning pixel as the result audio plays.
           Pixel order is based on the game's definition and not
           the native NeoPixel list order.
           Errors are indicated by flashing all pixels but keeping the
           opponent's one dark."""

        pix_op_idx = self.choiceToPixIdx(op_idx)
        if void:
            if result is not None:
                self.sample.play(result)
            ramp_updown = (list(range(8, 128 + 1, 8))
                           + list(range(128 - 8, 0 - 1, -8)))
            # This fills all NeoPixels so will clear the RPS choice
            for _ in range(3):
                for ramp in ramp_updown:
                    self.pix.fill((ramp, 0, 0))  # modulate red led from RGB
                    self.pix[pix_op_idx] = BLACK  # blackout the opponent pixel
                    time.sleep(0.013)  # attempt to to sync with audio

        else:
            if result is not None:
                self.sample.play(result)

            # Clear the RPS choice and show the player and opponent choices
            self.pix.fill(BLACK)
            if draw:
                self.pix[0] = CHOICE_COL[my_ch_idx] << 2
                self.pix[pix_op_idx] = CHOICE_COL[op_ch_idx] << 2
                time.sleep(0.25)
            else:
                self.pix[0] = CHOICE_COL[my_ch_idx]
                self.pix[pix_op_idx] = CHOICE_COL[op_ch_idx]
                # Brighten the pixel for winner
                brigten_idx = 0 if win else pix_op_idx
                for _ in range(5):
                    rr, gg, bb = self.pix[brigten_idx]
                    self.pix[brigten_idx] = (rr << 1, gg << 1, bb << 1)
                    time.sleep(0.45)

            if summary is not None:
                self.sample.wait()
                self.sample.play(summary)
        self.sample.wait()  # Ensure first or second sample have completed
        time.sleep(0.5)
        self.pix.fill(BLACK)


    def showPlayerVPlayer(self,
                          me_name, op_name, op_idx, my_ch_idx, op_ch_idx,
                          win, draw, void):
        if void:
            result_wav = "error"
            summary_wav = None
        elif draw:
            result_wav = None
            summary_wav = "draw"
        else:
            result_wav = self.winnerWav(my_ch_idx, op_ch_idx)
            summary_wav = "you-win" if win else "you-lose"

        if self.disp is None:
            self.showPlayerVPlayerNeoPixels(op_idx,
                                            my_ch_idx, op_ch_idx,
                                            result_wav, summary_wav, win, draw, void)
        else:
            self.showPlayerVPlayerScreen(me_name, op_name,
                                         my_ch_idx, op_ch_idx,
                                         result_wav, summary_wav, win, draw, void)
