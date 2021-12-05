# SPDX-FileCopyrightText: 2021 Tim C, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
This examples shows how to update your label with new text.
"""
import time
import board
import displayio
import terminalio
from adafruit_display_text import label

# built-in display
display = board.DISPLAY

# Make the display context
main_group = displayio.Group()
display.show(main_group)

# create the label
updating_label = label.Label(
    font=terminalio.FONT, text="Time Is:\n{}".format(time.monotonic()), scale=2
)

# set label position on the display
updating_label.anchor_point = (0, 0)
updating_label.anchored_position = (20, 20)

# add label to group that is showing on display
main_group.append(updating_label)

# Main loop
while True:

    # update text property to change the text showing on the display
    updating_label.text = "Time Is:\n{}".format(time.monotonic())

    time.sleep(1)
