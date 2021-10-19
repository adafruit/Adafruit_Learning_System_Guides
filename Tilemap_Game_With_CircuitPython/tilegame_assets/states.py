# SPDX-FileCopyrightText: 2020 FoamyGuy for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# State machine constants

# playing the game: draw the map, listen for D-pad buttons to move player
STATE_PLAYING = 0

# player beat this map level
STATE_MAPWIN = 1

# waiting for player to press A button to continue
STATE_WAITING = 2

# player lost by touching sparky
STATE_LOST_SPARKY = 3

# minerva shows a fun fact
STATE_MINERVA = 4
