import json
import random
import terminalio
from adafruit_display_shapes.rect import Rect
from adafruit_magtag.magtag import MagTag
magtag = MagTag()

# ---------------------------------
# Prepare text regions
# ---------------------------------

# Fetch list of chapters
MAX_LLEN = 8
data = {}
with open("deck.json") as fp:
    data = json.load(fp)
chap_list = list(data.keys())
num_chap = len(chap_list)
list_len = min(num_chap,MAX_LLEN)

# Print list of chapters
for i in range(list_len):
    magtag.add_text(
        text_font=terminalio.FONT,
        text_position=(10, 3+(i*10)),
        line_spacing=1.0,
        text_anchor_point=(0, 0), # Top left
        is_data=False,            # Text will be set manually
    )
    if i == 0:
        magtag.set_text("> " + chap_list[i], i, auto_refresh=False)
    else:
        magtag.set_text("  " + chap_list[i], i, auto_refresh=False)

# Add button labels at the bottom of the screen
BUTTON_TEXT_IDX = list_len
magtag.graphics.splash.append(Rect(0, magtag.graphics.display.height - 14,
                                   magtag.graphics.display.width,
                                   magtag.graphics.display.height, fill=0x0))
magtag.add_text(
    text_font=terminalio.FONT,
    text_position=(3, magtag.graphics.display.height - 14),
    text_color=0xFFFFFF,
    line_spacing=1.0,
    text_anchor_point=(0, 0), # Top left
    is_data=False,            # Text will be set manually
)
magtag.set_text("Select        Up          Down        Begin",
                BUTTON_TEXT_IDX, auto_refresh=False)

# Add message label at the top of the screen
MSG_TEXT_IDX = list_len + 1
magtag.add_text(
    text_font=terminalio.FONT,
    text_position=(3, magtag.graphics.display.height - 30),
    line_spacing=1.0,
    text_anchor_point=(0, 0), # Top left
    is_data=False,            # Text will be set manually
)
magtag.set_text("Press Begin to default to all chapters", MSG_TEXT_IDX)

# Empty text region for card displays
CARD_TEXT_IDX = list_len + 2
magtag.add_text(
    text_font="yasashi20.pcf",
    text_position=(
        magtag.graphics.display.width // 2,
        magtag.graphics.display.height // 2,
    ),
    line_spacing=0.85,
    text_anchor_point=(0.5, 0.5),
)

# Button management
curr_btns = [False] * 4
prev_btns = [False] * 4
BTN_A = 0
BTN_B = 1
BTN_C = 2
BTN_D = 3
def update_button(idx, pressed):
    curr_btns[idx] = pressed
    if curr_btns[idx] and not prev_btns[idx]:
        print("Exit menu")
        return True
    prev_btns[idx] = curr_btns[idx]
    return False

# Cursor settings
cursor_pos = 0
list_offset = 0
selected = [False] * num_chap
btn_updated = False

# ---------------------------------
# Program Loop
# ---------------------------------

while True:

    # ---------------------------------
    # Chapter Select
    # ---------------------------------

    while True:
        if btn_updated:
            # Clear default message only when items are selected
            if any(selected):
                magtag.set_text("", MSG_TEXT_IDX, auto_refresh=False)
            else:
                magtag.set_text("Press Begin to default to all chapters",
                                MSG_TEXT_IDX, auto_refresh=False)

            magtag.peripherals.neopixels.fill((128, 0, 0))
            for i in range(list_len):
                prefix = ""
                if i == cursor_pos:
                    prefix += ">"
                else:
                    prefix += " "
                if selected[i + list_offset]:
                    prefix += "*"
                else:
                    prefix += " "
                magtag.set_text(prefix + chap_list[i+list_offset],
                                i, auto_refresh=False)
            magtag.refresh()
            magtag.peripherals.neopixels.fill((0, 0, 0))
            btn_updated = False
        # UP
        if update_button(BTN_B, magtag.peripherals.button_b_pressed):
            cursor_pos -= 1
            btn_updated = True
        # DOWN
        if update_button(BTN_C, magtag.peripherals.button_c_pressed):
            cursor_pos += 1
            btn_updated = True
        # SELECT
        if update_button(BTN_A, magtag.peripherals.button_a_pressed):
            selected[cursor_pos + list_offset] = not selected[cursor_pos + list_offset]
            btn_updated = True
        # BEGIN
        if update_button(BTN_D, magtag.peripherals.button_d_pressed):
            # if nothing was selected, default to all decks
            magtag.peripherals.neopixels.fill((128, 0, 0))
            if not any(selected):
                selected = [True] * list_len
            break
        # detect if you're past the list bounds
        if cursor_pos == MAX_LLEN:
            cursor_pos = MAX_LLEN - 1
            if (num_chap - list_offset - 1) > MAX_LLEN:
                list_offset += 1

        if cursor_pos == -1:
            cursor_pos = 0
            if list_offset > 0:
                list_offset -= 1

    # ---------------------------------
    # Deck Loop
    # ---------------------------------

    # Clear the menu and message box
    for i in range(list_len):
        magtag.set_text("", i, auto_refresh=False)
    magtag.set_text("", MSG_TEXT_IDX,auto_refresh=False)

    # Grab the cards from the chapters we want, and shuffle them
    cards = []
    for i in range(len(selected)):
        if selected[i]:
            cards.extend(data[chap_list[i]])
    cards = sorted(cards, key=lambda _: random.random())

    # make a separate holding deck for cards the user gets wrong
    forgotten_cards = []

    exit_called = False
    while True:
        for card in cards:
            magtag.set_text("Exit          --          --          Turn Over",
                            BUTTON_TEXT_IDX,auto_refresh=False)
            text = '\n'.join(magtag.wrap_nicely(card[0], 11))
            magtag.set_text(text, CARD_TEXT_IDX)
            magtag.peripherals.neopixels.fill((0, 0, 0))

            while True:
                # EXIT
                if update_button(BTN_A, magtag.peripherals.button_a_pressed):
                    exit_called = True
                    break
                # TURN
                if update_button(BTN_D, magtag.peripherals.button_d_pressed):
                    break
            magtag.peripherals.neopixels.fill((128, 0, 0))
            if exit_called:
                break

            magtag.set_text("Exit          --          Forgot      Good",
                            BUTTON_TEXT_IDX,auto_refresh=False)
            text = '\n'.join(magtag.wrap_nicely(card[1], 11))
            text += '\n'
            text += '\n'.join(magtag.wrap_nicely(card[2], 20))
            magtag.set_text(text, CARD_TEXT_IDX)
            magtag.peripherals.neopixels.fill((0, 0, 0))

            while True:
                # EXIT
                if update_button(BTN_A, magtag.peripherals.button_a_pressed):
                    exit_called = True
                    break
                # FORGOT
                if update_button(BTN_C, magtag.peripherals.button_c_pressed):
                    forgotten_cards.append(card)
                    break
                # GOOD
                if update_button(BTN_D, magtag.peripherals.button_d_pressed):
                    break
            magtag.peripherals.neopixels.fill((128, 0, 0))
            if exit_called:
                break
            # Next card
        # If there were forgotten cards, make them the new deck and restart
        if forgotten_cards:
            cards = forgotten_cards
            forgotten_cards = []
        else:
            break

    # ---------------------------------
    # Complete and Reset
    # ---------------------------------

    # Show completion text if deck was finished
    if not exit_called:
        magtag.set_text("--            --          --          --",
                        BUTTON_TEXT_IDX,auto_refresh=False)
        magtag.set_text("Complete!", CARD_TEXT_IDX)
    else:
        exit_called = False

    # Clear and reprint list of chapters
    magtag.set_text("", CARD_TEXT_IDX, auto_refresh=False)
    for i in range(list_len):
        if i == 0:
            magtag.set_text("> " + chap_list[i], i, auto_refresh=False)
        else:
            magtag.set_text("  " + chap_list[i], i, auto_refresh=False)
    magtag.set_text("Select        Up          Down        Begin",
                    BUTTON_TEXT_IDX, auto_refresh=False)
    magtag.set_text("Press Begin to default to all chapters", MSG_TEXT_IDX)

    # Reset cursor:
    cursor_pos = 0
    list_offset = 0
    selected = [False] * list_len
    btn_updated = False

    # Done resetting, return to chapter selection
    magtag.peripherals.neopixels.fill((0, 0, 0))
