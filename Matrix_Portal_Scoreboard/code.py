# Scoreboard matrix display
# uses AdafruitIO to set scores and team names for a scoreboard
# Perfect for cornhole, ping pong, and other games

import time
import board
import terminalio
from adafruit_matrixportal.matrixportal import MatrixPortal

# --- Display setup ---
matrixportal = MatrixPortal(status_neopixel=board.NEOPIXEL, debug=False)

RED_COLOR = 0xAA0000
BLUE_COLOR = 0x0000AA

# Red Score
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(4, int(matrixportal.graphics.display.height * 0.75) - 3),
    text_color=RED_COLOR,
    text_scale=2,
)

# Blue Score
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(36, int(matrixportal.graphics.display.height * 0.75) - 3),
    text_color=BLUE_COLOR,
    text_scale=2,
)

# Red Team name
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(4, int(matrixportal.graphics.display.height * 0.25) - 4),
    text_color=RED_COLOR,
)

# Blue Team name
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(36, int(matrixportal.graphics.display.height * 0.25) - 4),
    text_color=BLUE_COLOR,
)

# Static 'Connecting' Text
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(59, 0),
)

SCORES_RED_FEED = "scores-group.red-team-score-feed"
SCORES_BLUE_FEED = "scores-group.blue-team-score-feed"
TEAM_RED_FEED = "scores-group.red-team-name"
TEAM_BLUE_FEED = "scores-group.blue-team-name"
UPDATE_DELAY = 4

matrixportal.set_text_color(RED_COLOR, 0)
matrixportal.set_text_color(BLUE_COLOR, 1)


def show_connecting(show):
    if show:
        matrixportal.set_text(".", 4)
    else:
        matrixportal.set_text(" ", 4)


def get_last_data(feed_key):
    feed = matrixportal.get_io_feed(feed_key, detailed=True)
    value = feed["details"]["data"]["last"]
    if value is not None:
        return value["value"]
    return None


def customize_team_names():
    team_red = "Red"
    team_blue = "Blue"

    show_connecting(True)
    team_name = get_last_data(TEAM_RED_FEED)
    if team_name is not None:
        print("Team {} is now Team {}".format(team_red, team_name))
        team_red = team_name
    matrixportal.set_text(team_red, 2)
    team_name = get_last_data(TEAM_BLUE_FEED)
    if team_name is not None:
        print("Team {} is now Team {}".format(team_blue, team_name))
        team_blue = team_name
    matrixportal.set_text(team_blue, 3)
    show_connecting(False)


def update_scores():
    print("Updating data from Adafruit IO")
    show_connecting(True)

    score_red = get_last_data(SCORES_RED_FEED)
    if score_red is None:
        score_red = 0
    matrixportal.set_text(score_red, 0)

    score_blue = get_last_data(SCORES_BLUE_FEED)
    if score_blue is None:
        score_blue = 0
    matrixportal.set_text(score_blue, 1)
    show_connecting(False)


customize_team_names()
update_scores()
last_update = time.monotonic()

while True:
    # Set the red score text
    if time.monotonic() > last_update + UPDATE_DELAY:
        update_scores()
        last_update = time.monotonic()
