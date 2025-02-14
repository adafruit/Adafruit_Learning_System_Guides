# SPDX-FileCopyrightText: 2024 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Karel the Robot code.py for devices with built-in display available
at board.DISPLAY.
"""
# pylint: disable=wildcard-import, unused-wildcard-import
from karel.circuitpythonkarel import *


# load a chapter. Edit the chapter filename to change chapters
# see available chapter files in chapters/ directory.
chapter_data = load_state_file("chapters/karel_ch01.json")


def main():
    """
    Karel main() function declaration.
    Put your code for Karel into this function.
    """
    ## START OF MAIN FUNCTION, YOUR CODE GOES BELOW HERE ##



    ## END OF MAIN FUNCTION, YOUR CODE GOES ABOVE HERE ##
    print(f"Goal state reached? {world.check_goal_state(chapter_data)}")


# call the main() function
main()

# Run forever so that the ending state of Karel and the world
# remains visible on the display.
while True:
    pass
