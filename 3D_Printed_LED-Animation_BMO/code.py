# SPDX-FileCopyrightText: 2014 Phil Burgess for Adafruit Industries
# SPDX-FileCopyrightText: 2018 Phil Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Trinket/Gemma + LED matrix backpack jewelry.  Plays animated
# sequence on LED matrix. Press reset button to display again.

import time
import adafruit_ht16k33.matrix
import board
import busio as io
import touchio

touch = touchio.TouchIn(board.D1)

i2c = io.I2C(board.SCL, board.SDA)
matrix = adafruit_ht16k33.matrix.Matrix8x8(i2c)

# pixels initializers
x_pix = y_pix = 8
x = y = 0
matrix.fill(0)
matrix.show()

# seconds to pause between frames
frame_delay = [.25, .25, .25, .25, .25, .25, .25, .25, .25, .25]

# counter for animation frames
frame_count = 0

# repeat entire animation multiple times
reps = 255
rep_count = reps

# animation bitmaps
animation = [
    # frame 1
    [[1, 1, 1, 1, 1, 1, 1, 1], [1, 0, 0, 1, 1, 0, 0, 1],
     [1, 0, 0, 1, 1, 0, 0, 1], [1, 1, 1, 1, 1, 1, 1, 1],
     [1, 0, 0, 0, 0, 0, 0, 1], [1, 1, 0, 0, 0, 0, 1, 1],
     [1, 1, 1, 0, 0, 1, 1, 1], [1, 1, 1, 1, 1, 1, 1, 1]],
    # frame 2
    [[1, 1, 1, 1, 1, 1, 1, 1], [1, 0, 0, 1, 1, 0, 0, 1],
     [1, 0, 0, 1, 1, 0, 0, 1], [1, 1, 1, 1, 1, 1, 1, 1],
     [1, 0, 1, 1, 1, 1, 0, 1], [1, 0, 1, 1, 1, 1, 0, 1],
     [1, 1, 0, 0, 0, 0, 1, 1], [1, 1, 1, 1, 1, 1, 1, 1]],
    # frame 3
    [[1, 1, 1, 1, 1, 1, 1, 1], [1, 0, 0, 1, 1, 0, 0, 1],
     [1, 0, 0, 1, 1, 0, 0, 1], [1, 1, 1, 1, 1, 1, 1, 1],
     [1, 0, 0, 0, 0, 0, 0, 1], [1, 1, 0, 0, 0, 0, 1, 1],
     [1, 1, 1, 0, 0, 1, 1, 1], [1, 1, 1, 1, 1, 1, 1, 1]],
    # frame 4
    [[1, 1, 1, 1, 1, 1, 1, 1], [1, 0, 0, 1, 1, 0, 0, 1],
     [1, 0, 0, 1, 1, 0, 0, 1], [1, 1, 1, 1, 1, 1, 1, 1],
     [1, 0, 1, 1, 1, 1, 0, 1], [1, 0, 1, 1, 1, 1, 0, 1],
     [1, 1, 0, 0, 0, 0, 1, 1], [1, 1, 1, 1, 1, 1, 1, 1]],
    # frame 5
    [[1, 1, 1, 1, 1, 1, 1, 1], [1, 0, 0, 1, 1, 0, 0, 1],
     [1, 0, 0, 1, 1, 0, 0, 1], [1, 1, 1, 1, 1, 1, 1, 1],
     [1, 1, 1, 1, 1, 1, 1, 1], [1, 1, 1, 1, 1, 1, 1, 1],
     [1, 0, 0, 0, 0, 0, 0, 1], [1, 1, 1, 1, 1, 1, 1, 1]],
    # frame 6
    [[1, 1, 1, 1, 1, 1, 1, 1], [1, 0, 0, 1, 1, 0, 0, 1],
     [1, 0, 0, 1, 1, 0, 0, 1], [1, 1, 1, 1, 1, 1, 1, 1],
     [1, 1, 1, 0, 0, 1, 1, 1], [1, 1, 0, 1, 1, 0, 1, 1],
     [1, 1, 1, 0, 0, 1, 1, 1], [1, 1, 1, 1, 1, 1, 1, 1]],
    # frame 7
    [[1, 1, 1, 1, 1, 1, 1, 1], [1, 0, 1, 1, 1, 1, 0, 1],
     [0, 0, 0, 1, 1, 0, 0, 0], [1, 0, 1, 1, 1, 1, 0, 1],
     [1, 1, 1, 0, 0, 1, 1, 1], [1, 1, 0, 1, 1, 0, 1, 1],
     [1, 1, 1, 0, 0, 1, 1, 1], [1, 1, 1, 1, 1, 1, 1, 1]],
    # frame 8
    [[1, 1, 1, 1, 1, 1, 1, 1], [1, 1, 1, 1, 1, 1, 1, 1],
     [0, 0, 0, 1, 1, 0, 0, 0], [1, 1, 1, 1, 1, 1, 1, 1],
     [1, 1, 1, 0, 0, 1, 1, 1], [1, 1, 0, 1, 1, 0, 1, 1],
     [1, 1, 1, 0, 0, 1, 1, 1], [1, 1, 1, 1, 1, 1, 1, 1]],
    # frame 9
    [[1, 1, 1, 1, 1, 1, 1, 1], [1, 0, 1, 1, 1, 1, 0, 1],
     [0, 0, 0, 1, 1, 0, 0, 0], [1, 0, 1, 1, 1, 1, 0, 1],
     [1, 1, 1, 0, 0, 1, 1, 1], [1, 1, 0, 1, 1, 0, 1, 1],
     [1, 1, 1, 0, 0, 1, 1, 1], [1, 1, 1, 1, 1, 1, 1, 1]],
]

#
# run until we are out of animation frames
# use Gemma's built-in reset button or switch to restart
#
# populate matrix
while True:

    if frame_count < len(animation) and rep_count >= 0:
        for x in range(x_pix):
            for y in range(y_pix):
                matrix.pixel(x, y, animation[frame_count][x][y])

        # next animation frame
        frame_count += 1

        # show animation
        matrix.show()

        # pause for effect
        time.sleep(frame_delay[frame_count])

    else:

        matrix.fill(0)
        matrix.show()
        time.sleep(.1)

        # track repitions
        rep_count -= 1

        # play it again
        frame_count = 0

        # A0/D1 pin has been touched
        # reset animation
        if touch.value:
            frame_count = 0
            rep_count = reps
