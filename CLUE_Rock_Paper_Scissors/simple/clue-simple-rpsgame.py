# clue-simple-rpsgame v1.3
# CircuitPython rock paper scissors game over Bluetooth LE

# Tested with CLUE and Circuit Playground Bluefruit Alpha with TFT Gizmo
# and CircuitPython and 5.3.0

# copy this file to CLUE/CPB board as code.py

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
import os
import struct
import sys

import board
from displayio import Group
import terminalio
import digitalio

from adafruit_ble import BLERadio
from adafruit_ble.advertising import Advertisement, LazyObjectField
from adafruit_ble.advertising.standard import ManufacturerData, ManufacturerDataField

from adafruit_display_text.label import Label


debug = 3

def d_print(level, *args, **kwargs):
    """A simple conditional print for debugging based on global debug level."""
    if not isinstance(level, int):
        print(level, *args, **kwargs)
    elif debug >= level:
        print(*args, **kwargs)


def tftGizmoPresent():
    """Determine if the TFT Gizmo is attached.
       The TFT's Gizmo circuitry for backlight features a 10k pull-down resistor.
       This attempts to verify the presence of the pull-down to determine
       if TFT Gizmo is present.
       Only use this on Circuit Playground Express (CPX)
       or Circuit Playground Bluefruit (CPB) boards."""
    present = True
    try:
        with digitalio.DigitalInOut(board.A3) as backlight_pin:
            backlight_pin.pull = digitalio.Pull.UP
            present = not backlight_pin.value
    except ValueError:
        # The Gizmo is already initialised, i.e. showing console output
        pass

    return present


# Assuming CLUE if it's not a Circuit Playround (Bluefruit)
clue_less = "Circuit Playground" in os.uname().machine

# Note: difference in pull-up and pull-down
#       and not use for buttons
if clue_less:
    # CPB with TFT Gizmo (240x240)

    # Outputs
    if tftGizmoPresent():
        from adafruit_gizmo import tft_gizmo
        display = tft_gizmo.TFT_Gizmo()
    else:
        display = None

    # Inputs
    # buttons reversed if it is used upside-down with Gizmo
    _button_a = digitalio.DigitalInOut(board.BUTTON_A)
    _button_a.switch_to_input(pull=digitalio.Pull.DOWN)
    _button_b = digitalio.DigitalInOut(board.BUTTON_B)
    _button_b.switch_to_input(pull=digitalio.Pull.DOWN)
    if display is None:
        def button_left():
            return _button_a.value
        def button_right():
            return _button_b.value
    else:
        def button_left():
            return _button_b.value
        def button_right():
            return _button_a.value

else:
    # CLUE with builtin screen (240x240)

    # Outputs
    display = board.DISPLAY

    # Inputs
    _button_a = digitalio.DigitalInOut(board.BUTTON_A)
    _button_a.switch_to_input(pull=digitalio.Pull.UP)
    _button_b = digitalio.DigitalInOut(board.BUTTON_B)
    _button_b.switch_to_input(pull=digitalio.Pull.UP)
    def button_left():
        return not _button_a.value
    def button_right():
        return not _button_b.value

if display is None:
    print("FATAL:", "This version of program only works with a display")
    sys.exit(1)

choices = ("rock", "paper", "scissors")
my_choice_idx = 0

# Top y position of first choice and pixel separate between choices
top_y_pos = 60
choice_sep = 60

DIM_TXT_COL_FG = 0x505050
DEFAULT_TXT_COL_FG = 0xa0a0a0
DEFAULT_TXT_COL_BG = 0x000000
CURSOR_COL_FG = 0xc0c000
OPP_CURSOR_COL_FG = 0x00c0c0


def setCursor(c_idx, who, visibility=None):
    """Set the position of the cursor on-screen to indicate the player's selection."""
    char = None

    if visibility == "show":
        char = ">"
    elif visibility == "hide":
        char = " "

    if 0 <= c_idx < len(choices):
        dob = cursor_dob if who == "mine" else opp_cursor_dob
        dob.y = top_y_pos + choice_sep * c_idx
        if char is not None:
            dob.text = char


def flashWinner(c_idx, who):
    """Invert foreground/background colour a few times
       to indicate the winning choice."""

    if who == "mine":
        sg_idx = rps_dob_idx[0] + c_idx
    elif who == "opp":
        sg_idx = rps_dob_idx[1] + c_idx
    else:
        raise ValueError("who is mine or opp")

    # An even number will leave colours on original values
    for _ in range(5 * 2):
        tmp_col = screen_group[sg_idx].color
        screen_group[sg_idx].color = screen_group[sg_idx].background_color
        screen_group[sg_idx].background_color = tmp_col
        time.sleep(0.5)


# The 6x14 terminalio classic font
FONT_WIDTH, FONT_HEIGHT = terminalio.FONT.get_bounding_box()
screen_group = Group()

# The position of the two players RPS Label objects inside screen_group
rps_dob_idx = []

# Create the simple arrow cursors
left_col = 20
right_col = display.width // 2 + left_col
for x_pos in (left_col, right_col):
    y_pos = top_y_pos
    rps_dob_idx.append(len(screen_group))
    for label_text in choices:
        rps_dob = Label(terminalio.FONT,
                        text=label_text,
                        scale=2,
                        color=DEFAULT_TXT_COL_FG,
                        background_color=DEFAULT_TXT_COL_BG)
        rps_dob.x = x_pos
        rps_dob.y = y_pos
        y_pos += 60
        screen_group.append(rps_dob)

cursor_dob = Label(terminalio.FONT,
                   text=">",
                   scale=3,
                   color=CURSOR_COL_FG)
cursor_dob.x = left_col - 20
setCursor(my_choice_idx, "mine")
cursor_dob.y = top_y_pos
screen_group.append(cursor_dob)

# Initially set to a space to not show it
opp_cursor_dob = Label(terminalio.FONT,
                       text=" ",
                       scale=3,
                       color=OPP_CURSOR_COL_FG,
                       background_color=DEFAULT_TXT_COL_BG)
opp_cursor_dob.x = right_col - 20
setCursor(my_choice_idx, "your")
opp_cursor_dob.y = top_y_pos
screen_group.append(opp_cursor_dob)

display.show(screen_group)

# From adafruit_ble.advertising
MANUFACTURING_DATA_ADT = 0xFF
ADAFRUIT_COMPANY_ID = 0x0822

# pylint: disable=line-too-long
# According to https://github.com/adafruit/Adafruit_CircuitPython_BLE/blob/master/adafruit_ble/advertising/adafruit.py
# 0xf000 (to 0xffff) is for range for Adafruit customers
RPS_ACK_ID = 0xfe30
RPS_DATA_ID = 0xfe31


class RpsAdvertisement(Advertisement):
    """Broadcast an RPS message.
       This is not connectable and elicits no scan_response based on defaults
       in Advertisement parent class."""

    flags = None

    _PREFIX_FMT = "<BHBH"
    _DATA_FMT = "8s"  # this NUL pads if necessary

    # match_prefixes tuple replaces deprecated prefix
    # comma for 1 element is very important!
    match_prefixes = (
        struct.pack(
            _PREFIX_FMT,
            MANUFACTURING_DATA_ADT,
            ADAFRUIT_COMPANY_ID,
            struct.calcsize("<H" + _DATA_FMT),
            RPS_DATA_ID
        ),
    )
    manufacturer_data = LazyObjectField(
        ManufacturerData,
        "manufacturer_data",
        advertising_data_type=MANUFACTURING_DATA_ADT,
        company_id=ADAFRUIT_COMPANY_ID,
        key_encoding="<H",
    )

    test_string = ManufacturerDataField(RPS_DATA_ID, "<" + _DATA_FMT)
    """RPS choice."""


NS_IN_S = 1000 * 1000  * 1000
MIN_SEND_TIME_NS = 6 * NS_IN_S
MAX_SEND_TIME_S = 20
MAX_SEND_TIME_NS = MAX_SEND_TIME_S * NS_IN_S

# 20ms is the minimum delay between advertising packets
# in Bluetooth Low Energy
# extra 10us deals with API floating point rounding issues
MIN_AD_INTERVAL = 0.02001

ble = BLERadio()

opponent_choice = None

timeout = False
round_no = 1
wins = 0
losses = 0
draws = 0
voids = 0

TOTAL_ROUND = 5


def evaluate_game(mine, yours):
    """Determine who won the game based on the two strings mine and yours_lc.
       Returns three booleans (win, draw, void)."""
    # Return with void at True if any input is None
    try:
        mine_lc = mine.lower()
        yours_lc = yours.lower()
    except AttributeError:
        return (False, False, True)

    r_win = r_draw = r_void = False
    # pylint: disable=too-many-boolean-expressions
    if (mine_lc == "rock" and yours_lc == "rock"
            or mine_lc == "paper" and yours_lc == "paper"
            or mine_lc == "scissors" and yours_lc == "scissors"):
        r_draw = True
    elif (mine_lc == "rock" and yours_lc == "paper"):
        pass  # r_win default is False
    elif (mine_lc == "rock" and yours_lc == "scissors"):
        r_win = True
    elif (mine_lc == "paper" and yours_lc == "rock"):
        r_win = True
    elif (mine_lc == "paper" and yours_lc == "scissors"):
        pass  # r_win default is False
    elif (mine_lc == "scissors" and yours_lc == "rock"):
        pass  # r_win default is False
    elif (mine_lc == "scissors" and yours_lc == "paper"):
        r_win = True
    else:
        r_void = True

    return (r_win, r_draw, r_void)


# Advertise for 20 seconds maximum and if a packet is received
# for 5 seconds after that
while True:
    if round_no > TOTAL_ROUND:
        print("Summary: ",
              "wins {:d}, losses {:d}, draws {:d}, void {:d}".format(wins, losses, draws, voids))

        # Reset variables for another game
        round_no = 1
        wins = 0
        losses = 0
        draws = 0
        voids = 0
        round_no = 1

    if button_left():
        while button_left():
            pass
        my_choice_idx = (my_choice_idx + 1) % len(choices)
        setCursor(my_choice_idx, "mine")

    if button_right():
        tx_message = RpsAdvertisement()

        choice = choices[my_choice_idx]
        tx_message.test_string = choice
        d_print(2, "TXing RTA", choice)

        opponent_choice = None
        ble.start_advertising(tx_message, interval=MIN_AD_INTERVAL)
        sending_ns = time.monotonic_ns()

        # Timeout value is in seconds
        # RSSI -100 is probably minimum, -128 would be 8bit signed min
        # window and interval are 0.1 by default - same value means
        # continuous scanning (sending Advertisement will interrupt this)
        for adv in ble.start_scan(RpsAdvertisement,
                                  minimum_rssi=-90,
                                  timeout=MAX_SEND_TIME_S):
            received_ns = time.monotonic_ns()
            d_print(2, "RXed RTA",
                    adv.test_string)
            opponent_choice_bytes = adv.test_string

            # Trim trailing NUL chars from bytes
            idx = 0
            while idx < len(opponent_choice_bytes):
                if opponent_choice_bytes[idx] == 0:
                    break
                idx += 1
            opponent_choice = opponent_choice_bytes[0:idx].decode("utf-8")
            break

        # We have received one message or exceeded MAX_SEND_TIME_S
        ble.stop_scan()

        # Ensure we send our message for a minimum period of time
        # constrained by the ultimate duration cap
        if opponent_choice is not None:
            timeout = False
            remaining_ns = MAX_SEND_TIME_NS - (received_ns - sending_ns)
            extra_ad_time_ns = min(remaining_ns, MIN_SEND_TIME_NS)
            # Only sleep if we need to, the value here could be a small
            # negative one too so this caters for this
            if extra_ad_time_ns > 0:
                sleep_t  = extra_ad_time_ns / NS_IN_S
                d_print(2, "Additional {:f} seconds of advertising".format(sleep_t))
                time.sleep(sleep_t)
        else:
            timeout = True

        ble.stop_advertising()

        d_print(1, "ROUND", round_no,
                "MINE", choice,
                "| OPPONENT", opponent_choice)
        win, draw, void = evaluate_game(choice, opponent_choice)

        if void:
            voids += 1
        else:
            opp_choice_idx = choices.index(opponent_choice)
            setCursor(opp_choice_idx, "opp", visibility="show")
            if draw:
                time.sleep(4)
                draws += 1
            elif win:
                flashWinner(my_choice_idx, "mine")
                wins += 1
            else:
                flashWinner(opp_choice_idx, "opp")
                losses += 1
            setCursor(opp_choice_idx, "opp", visibility="hide")
        d_print(1, "wins {:d}, losses {:d}, draws {:d}, void {:d}".format(wins, losses, draws, voids))

        round_no += 1
