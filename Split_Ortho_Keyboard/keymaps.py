# SPDX-FileCopyrightText: Copyright (c) 2022 John Park & Tod Kurt for Adafruit Industries
#
# SPDX-License-Identifier: MIT
from adafruit_hid.keycode import Keycode
# https://docs.circuitpython.org/projects/hid/en/latest/api.html#adafruit-hid-keycode-keycode
# keymap is keynumber, (modifier, keycode)
# lower keymap layer
km_lf_0 = {
            (1) : (0, Keycode.F11),
            (2) : (0, Keycode.F1),
            (3) : (0, Keycode.F2),
            (4) : (0, Keycode.F3),
            (5) : (0, Keycode.F4),
            (6) : (0, Keycode.F5),

            (11) : (0, None),
            (12) : (0, None),
            (13) : (0, None),
            (14) : (0, None),
            (15) : (0, None),
            (16) : (0, None),

            (21) : (0, None),
            (22) : (0, None),
            (23) : (0, None),
            (24) : (0, None),
            (25) : (0, None),
            (26) : (0, None),

            (31) : (0, None),
            (32) : (0, None),
            (33) : (0, None),
            (34) : (0, None),
            (35) : (0, None),
            (36) : (0, None),

            (41) : (0, Keycode.CONTROL),
            (42) : (0, Keycode.GUI),
            (43) : (0, Keycode.ALT),
            (44) : (0, Keycode.GUI),
            (45) : (1, Keycode.L),  # lower (the keycode doesn't matter here, it's never typed)
            (46) : (0, Keycode.SPACE)
}

km_rt_0 = {
            (1) : (0, Keycode.F6),
            (2) : (0, Keycode.F7),
            (3) : (0, Keycode.F8),
            (4) : (0, Keycode.F9),
            (5) : (0, Keycode.F10),
            (6) : (0, Keycode.F12),

            (11) : (0, Keycode.HOME),
            (12) : (0, Keycode.PAGE_DOWN),
            (13) : (0, Keycode.PAGE_UP),
            (14) : (0, Keycode.END),
            (15) : (0, Keycode.INSERT),
            (16) : (0, Keycode.DELETE),

            (21) : (0, None),
            (22) : (0, None),
            (23) : (0, None),
            (24) : (0, None),
            (25) : (0, None),
            (26) : (0, None),

            (31) : (0, None),
            (32) : (0, None),
            (33) : (0, None),
            (34) : (0, None),
            (35) : (0, None),
            (36) : (0, None),

            (41) : (0, Keycode.SPACE),
            (42) : (2, Keycode.R),  # raise
            (43) : (0, Keycode.LEFT_ARROW),
            (44) : (0, Keycode.DOWN_ARROW),
            (45) : (0, Keycode.UP_ARROW),
            (46) : (0, Keycode.RIGHT_ARROW)
}

# main keymap layer
km_lf_1 = {
            (1) : (0, Keycode.GRAVE_ACCENT),
            (2) : (0, Keycode.ONE),
            (3) : (0, Keycode.TWO),
            (4) : (0, Keycode.THREE),
            (5) : (0, Keycode.FOUR),
            (6) : (0, Keycode.FIVE),

            (11) : (0, Keycode.ESCAPE),
            (12) : (0, Keycode.Q),
            (13) : (0, Keycode.W),
            (14) : (0, Keycode.E),
            (15) : (0, Keycode.R),
            (16) : (0, Keycode.T),

            (21) : (0, Keycode.TAB),
            (22) : (0, Keycode.A),
            (23) : (0, Keycode.S),
            (24) : (0, Keycode.D),
            (25) : (0, Keycode.F),
            (26) : (0, Keycode.G),

            (31) : (0, Keycode.SHIFT),
            (32) : (0, Keycode.Z),
            (33) : (0, Keycode.X),
            (34) : (0, Keycode.C),
            (35) : (0, Keycode.V),
            (36) : (0, Keycode.B),

            (41) : (0, Keycode.CONTROL),
            (42) : (0, Keycode.GUI),
            (43) : (0, Keycode.ALT),
            (44) : (0, Keycode.GUI),
            (45) : (1, Keycode.L),  # lower
            (46) : (0, Keycode.SPACE)
}

km_rt_1 = {
            (1) : (0, Keycode.SIX),
            (2) : (0, Keycode.SEVEN),
            (3) : (0, Keycode.EIGHT),
            (4) : (0, Keycode.NINE),
            (5) : (0, Keycode.ZERO),
            (6) : (0, Keycode.BACKSPACE),

            (11) : (0, Keycode.Y),
            (12) : (0, Keycode.U),
            (13) : (0, Keycode.I),
            (14) : (0, Keycode.O),
            (15) : (0, Keycode.P),
            (16) : (0, Keycode.BACKSLASH),

            (21) : (0, Keycode.H),
            (22) : (0, Keycode.J),
            (23) : (0, Keycode.K),
            (24) : (0, Keycode.L),
            (25) : (0, Keycode.SEMICOLON),
            (26) : (0, Keycode.QUOTE),

            (31) : (0, Keycode.N),
            (32) : (0, Keycode.M),
            (33) : (0, Keycode.COMMA),
            (34) : (0, Keycode.PERIOD),
            (35) : (0, Keycode.FORWARD_SLASH),
            (36) : (0, Keycode.ENTER),

            (41) : (0, Keycode.SPACE),
            (42) : (2, Keycode.R),  # raise
            (43) : (0, Keycode.LEFT_ARROW),
            (44) : (0, Keycode.DOWN_ARROW),
            (45) : (0, Keycode.UP_ARROW),
            (46) : (0, Keycode.RIGHT_ARROW)
}

# upper keymap layer
km_lf_2 = {
            (1) : (0, None),
            (2) : (0, None),
            (3) : (0, None),
            (4) : (0, None),
            (5) : (0, None),
            (6) : (0, None),

            (11) : (0, Keycode.ESCAPE),
            (12) : (0, None),
            (13) : (0, None),
            (14) : (0, None),
            (15) : (0, None),
            (16) : (0, None),

            (21) : (0, Keycode.TAB),
            (22) : (0, None),
            (23) : (0, None),
            (24) : (0, Keycode.MINUS),
            (25) : (0, Keycode.EQUALS),
            (26) : (7, Keycode.BACKSLASH),  # PIPE '|'

            (31) : (0, Keycode.SHIFT),
            (32) : (0, None),
            (33) : (0, None),
            (34) : (7, Keycode.MINUS),  # UNDERSCORE
            (35) : (0, Keycode.KEYPAD_PLUS),
            (36) : (0, Keycode.BACKSLASH),

            (41) : (0, Keycode.CONTROL),
            (42) : (0, Keycode.GUI),
            (43) : (0, Keycode.ALT),
            (44) : (0, Keycode.GUI),
            (45) : (1, Keycode.L),  # lower
            (46) : (0, Keycode.SPACE)
}

km_rt_2 = {
            (1) : (0, None),
            (2) : (0, None),
            (3) : (0, None),
            (4) : (0, None),
            (5) : (0, None),
            (6) : (0, Keycode.BACKSPACE),

            (11) : (0, None),
            (12) : (0, None),
            (13) : (0, None),
            (14) : (0, None),
            (15) : (0, None),
            (16) : (0, Keycode.BACKSLASH),

            (21) : (0, None),
            (22) : (0, Keycode.LEFT_BRACKET),
            (23) : (0, Keycode.RIGHT_BRACKET),
            (24) : (0, None),
            (25) : (0, None),
            (26) : (0, Keycode.QUOTE),

            (31) : (0, None),
            (32) : (7, Keycode.LEFT_BRACKET),
            (33) : (7, Keycode.RIGHT_BRACKET),
            (34) : (0, None),
            (35) : (0, None),
            (36) : (0, Keycode.ENTER),

            (41) : (0, Keycode.SPACE),
            (42) : (2, Keycode.R),  # raise
            (43) : (0, Keycode.LEFT_ARROW),
            (44) : (0, Keycode.DOWN_ARROW),
            (45) : (0, Keycode.UP_ARROW),
            (46) : (0, Keycode.RIGHT_ARROW)
}

# put the keymaps in layer lists for easy iteration later
keymaps_1 = (km_lf_0, km_rt_0)
keymaps_2 = (km_lf_1, km_rt_1)
keymaps_3 = (km_lf_2, km_rt_2)
layer_keymaps = (keymaps_1, keymaps_2, keymaps_3)
