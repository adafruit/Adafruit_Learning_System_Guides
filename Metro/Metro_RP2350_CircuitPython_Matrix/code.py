# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
Matrix rain visual effect

Largely ported from Arduino version in Metro_HSTX_Matrix to
CircuitPython by claude with some additional tweaking to the
colors and refresh functionality.
"""
import sys
import random
import time
import displayio
import supervisor
from displayio import Group, TileGrid
from tilepalettemapper import TilePaletteMapper
from adafruit_fruitjam.peripherals import request_display_config
import adafruit_imageload


# use the built-in HSTX display
request_display_config(320, 240)
display = supervisor.runtime.display

# screen size in tiles, tiles are 16x16
SCREEN_WIDTH = display.width // 16
SCREEN_HEIGHT = display.height // 16

# disable auto_refresh, we'll call refresh() after each frame
display.auto_refresh = False

# group to hold visual elements
main_group = Group()

# show the group on the display
display.root_group = main_group

# Color gradient list from white to dark green
COLORS = [
    0xFFFFFF,
    0x88FF88,
    0x00FF00,
    0x00DD00,
    0x00BB00,
    0x009900,
    0x007700,
    0x006600,
    0x005500,
    0x005500,
    0x003300,
    0x003300,
    0x002200,
    0x002200,
    0x001100,
    0x001100,
]

# Palette to use with the mapper. Has 1 extra color
# so it can have black at index 0
shader_palette = displayio.Palette(len(COLORS) + 1)
# set black at index 0
shader_palette[0] = 0x000000

# set the colors from the gradient above in the
# remaining indexes
for i in range(0, len(COLORS)):
    shader_palette[i + 1] = COLORS[i]

# mapper to change colors of tiles within the grid
if sys.implementation.version[0] == 9:
    grid_color_shader = TilePaletteMapper(
        shader_palette, 2, SCREEN_WIDTH, SCREEN_HEIGHT
    )
elif sys.implementation.version[0] >= 10:
    grid_color_shader = TilePaletteMapper(shader_palette, 2)

# load the spritesheet
katakana_bmp, katakana_pixelshader = adafruit_imageload.load("matrix_characters.bmp")

# how many characters are in the sprite sheet
char_count = katakana_bmp.width // 16

# grid to display characters within
display_text_grid = TileGrid(
    bitmap=katakana_bmp,
    width=SCREEN_WIDTH,
    height=SCREEN_HEIGHT,
    tile_height=16,
    tile_width=16,
    pixel_shader=grid_color_shader,
)

# flip x to get backwards characters
display_text_grid.flip_x = True

# add the text grid to main_group, so it will be visible on the display
main_group.append(display_text_grid)


# Define structures for character streams
class CharStream:
    def __init__(self):
        self.x = 0  # X position
        self.y = 0  # Y position (head of the stream)
        self.length = 0  # Length of the stream
        self.speed = 0  # How many frames to wait before moving
        self.countdown = 0  # Counter for movement
        self.active = False  # Whether this stream is currently active
        self.chars = [" "] * 30  # Characters in the stream


# Array of character streams
streams = [CharStream() for _ in range(250)]

# Stream creation rate (higher = more frequent new streams)
STREAM_CREATION_CHANCE = 65  # % chance per frame to create new stream

# Initial streams to create at startup
INITIAL_STREAMS = 30


def init_streams():
    """Initialize all streams as inactive"""
    for _ in range(len(streams)):
        streams[_].active = False

    # Create initial streams for immediate visual impact
    for _ in range(INITIAL_STREAMS):
        create_new_stream()


def create_new_stream():
    """Create a new active stream"""
    # Find an inactive stream
    for _ in range(len(streams)):
        if not streams[_].active:
            # Initialize the stream
            streams[_].x = random.randint(0, SCREEN_WIDTH - 1)
            streams[_].y = random.randint(-5, -1)  # Start above the screen
            streams[_].length = random.randint(5, 20)
            streams[_].speed = random.randint(0, 3)
            streams[_].countdown = streams[_].speed
            streams[_].active = True

            # Fill with random characters
            for j in range(streams[_].length):
                # streams[i].chars[j] = get_random_char()
                streams[_].chars[j] = random.randrange(0, char_count)
            return


def update_streams():
    """Update and draw all streams"""
    # Clear the display (we'll implement this by looping through display grid)
    for x in range(SCREEN_WIDTH):
        for y in range(SCREEN_HEIGHT):
            display_text_grid[x, y] = 0  # Clear character

    # Count active streams (for debugging if needed)
    active_count = 0

    for _ in range(len(streams)):
        if streams[_].active:
            active_count += 1
            streams[_].countdown -= 1

            # Time to move the stream down
            if streams[_].countdown <= 0:
                streams[_].y += 1
                streams[_].countdown = streams[_].speed

                # Change a random character in the stream
                random_index = random.randint(0, streams[_].length - 1)
                # streams[i].chars[random_index] = get_random_char()
                streams[_].chars[random_index] = random.randrange(0, char_count)

            # Draw the stream
            draw_stream(streams[_])

            # Check if the stream has moved completely off the screen
            if streams[_].y - streams[_].length > SCREEN_HEIGHT:
                streams[_].active = False


def draw_stream(stream):
    """Draw a single character stream"""
    for _ in range(stream.length):
        y = stream.y - _

        # Only draw if the character is on screen
        if 0 <= y < SCREEN_HEIGHT and 0 <= stream.x < SCREEN_WIDTH:
            # Set the character
            display_text_grid[stream.x, y] = stream.chars[_]

            if _ + 1 < len(COLORS):
                grid_color_shader[stream.x, y] = [0, _ + 1]
            else:
                grid_color_shader[stream.x, y] = [0, len(COLORS) - 1]
    # Occasionally change a character in the stream
    if random.randint(0, 99) < 25:  # 25% chance
        idx = random.randint(0, stream.length - 1)
        stream.chars[idx] = random.randrange(0, 112)


def setup():
    """Initialize the system"""
    # Seed the random number generator
    random.seed(int(time.monotonic() * 1000))

    # Initialize all streams
    init_streams()


def loop():
    """Main program loop"""
    # Update and draw all streams
    update_streams()

    # Randomly create new streams at a higher rate
    if random.randint(0, 99) < STREAM_CREATION_CHANCE:
        create_new_stream()

    display.refresh()
    available = supervisor.runtime.serial_bytes_available
    if available:
        c = sys.stdin.read(available)
        if c.lower() == "q":
            supervisor.reload()


# Main program
setup()
while True:
    loop()
