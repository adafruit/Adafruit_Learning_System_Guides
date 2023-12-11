# SPDX-FileCopyrightText: 2019 Dave Briccetti
#
# SPDX-License-Identifier: MIT

"""A shorter CapTouch program, for those comfortable with list
comprehensions and the enumerate function"""

import time

import board
import touchio

touchIns = [touchio.TouchIn(pin) for pin in
            (board.A1, board.A2, board.A3, board.A4, board.A5, board.A6, board.A7)]

while True:
    for i, touchIn in enumerate(touchIns):
        if touchIn.value:
            print('A%d touched!' % (i + 1))

    time.sleep(0.1)
