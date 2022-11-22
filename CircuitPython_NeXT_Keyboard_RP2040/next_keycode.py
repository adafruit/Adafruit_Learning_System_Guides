from adafruit_hid.consumer_control_code import ConsumerControlCode as C
from adafruit_hid.keycode import Keycode as K

MASK_CC = 1 << 15


def is_cc(value):
    return value & MASK_CC


def cc_value(value):
    return value & ~MASK_CC


next_modifiers = [
    K.RIGHT_ALT,
    K.ALT,
    K.APPLICATION,  # right command
    K.COMMAND,
    K.RIGHT_SHIFT,
    K.SHIFT,
    K.CONTROL,
]

next_scancodes = {
    3: K.BACKSLASH,
    4: K.RIGHT_BRACKET,
    5: K.LEFT_BRACKET,
    6: K.I,
    7: K.O,
    8: K.P,
    9: K.LEFT_ARROW,
    11: K.KEYPAD_ZERO,
    12: K.KEYPAD_PERIOD,
    13: K.KEYPAD_ENTER,
    15: K.DOWN_ARROW,
    16: K.RIGHT_ARROW,
    17: K.KEYPAD_ONE,
    18: K.KEYPAD_FOUR,
    19: K.KEYPAD_SIX,
    20: K.KEYPAD_THREE,
    21: K.KEYPAD_PLUS,
    22: K.UP_ARROW,
    23: K.KEYPAD_TWO,
    24: K.KEYPAD_FIVE,
    27: K.BACKSPACE,
    28: K.EQUALS,
    29: K.MINUS,
    30: K.EIGHT,
    31: K.NINE,
    32: K.ZERO,
    33: K.KEYPAD_SEVEN,
    34: K.KEYPAD_EIGHT,
    35: K.KEYPAD_NINE,
    36: K.KEYPAD_MINUS,
    37: K.KEYPAD_ASTERISK,
    38: K.GRAVE_ACCENT,
    39: K.KEYPAD_EQUALS,
    40: K.KEYPAD_FORWARD_SLASH,
    42: K.RETURN,
    43: K.QUOTE,
    44: K.SEMICOLON,
    45: K.L,
    46: K.COMMA,
    47: K.PERIOD,
    48: K.FORWARD_SLASH,
    49: K.Z,
    50: K.X,
    51: K.C,
    52: K.V,
    53: K.B,
    54: K.M,
    55: K.N,
    56: K.SPACE,
    57: K.A,
    58: K.S,
    59: K.D,
    60: K.F,
    61: K.G,
    62: K.K,
    63: K.J,
    64: K.H,
    65: K.TAB,
    66: K.Q,
    67: K.W,
    68: K.E,
    69: K.R,
    70: K.U,
    71: K.Y,
    72: K.T,
    73: K.ESCAPE,
    74: K.ONE,
    75: K.TWO,
    76: K.THREE,
    77: K.FOUR,
    78: K.SEVEN,
    79: K.SIX,
    80: K.FIVE,
    26: C.VOLUME_INCREMENT | MASK_CC,
    2: C.VOLUME_DECREMENT | MASK_CC,
    25: C.BRIGHTNESS_INCREMENT | MASK_CC,
    1: C.BRIGHTNESS_DECREMENT | MASK_CC,
}
