import array
import board
import rp2pio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode as K
import adafruit_pioasm

# from https://www.scs.stanford.edu/10wi-cs140/pintos/specs/kbd/scancodes-9.html
# translating from "Set 1" to USB using the adafruit_hid keycode names
# fmt: off
xt_keycodes = [
    None, K.ESCAPE, K.ONE, K.TWO, K.THREE, K.FOUR, K.FIVE, K.SIX,
    K.SEVEN, K.EIGHT, K.NINE, K.ZERO, K.MINUS, K.EQUALS, K.BACKSPACE, K.TAB, K.Q,
    K.W, K.E, K.R, K.T, K.Y, K.U, K.I, K.O, K.P, K.LEFT_BRACKET, K.RIGHT_BRACKET,
    K.RETURN, K.LEFT_CONTROL, K.A, K.S, K.D, K.F, K.G, K.H, K.J, K.K, K.L,
    K.SEMICOLON, K.QUOTE, K.GRAVE_ACCENT, K.SHIFT, K.BACKSLASH, K.Z, K.X, K.C, K.V,
    K.B, K.N, K.M, K.COMMA, K.PERIOD, K.FORWARD_SLASH, K.RIGHT_SHIFT,
    K.KEYPAD_ASTERISK, K.OPTION, K.SPACEBAR, K.CAPS_LOCK, K.F1, K.F2, K.F3, K.F4,
    K.F5, K.F6, K.F7, K.F8, K.F9, K.F10, K.KEYPAD_NUMLOCK, K.SCROLL_LOCK,
    K.KEYPAD_SEVEN, K.KEYPAD_EIGHT, K.KEYPAD_NINE, K.KEYPAD_MINUS, K.KEYPAD_FOUR,
    K.KEYPAD_FIVE, K.KEYPAD_SIX, K.KEYPAD_PLUS, K.KEYPAD_ONE, K.KEYPAD_TWO,
    K.KEYPAD_THREE, K.KEYPAD_ZERO, K.KEYPAD_PERIOD, None, None, None, K.F11, K.F12
]
# fmt: on

program = adafruit_pioasm.Program("""
    wait 0 pin 2
    in pins, 1
    wait 1 pin 2
""",
build_debuginfo=True)

sm = rp2pio.StateMachine(program.assembled,
    first_in_pin = board.MISO,
    in_pin_count = 3,
    pull_in_pin_up = 0b111,
    auto_push=True,
    push_threshold=10,
    in_shift_right=True,
    frequency=8_000_000,
    **program.pio_kwargs)

buf = array.array('H', [0])

print("Ready to type")
kbd = Keyboard(usb_hid.devices)
while True:
    sm.readinto(buf, swap=False)
    val = buf[0]
    pressed = not (val & 0x8000)
    key_number = (val >> 8) & 0x7f
    keycode = xt_keycodes[key_number]
    print(f"{keycode} {'PRESSED' if pressed else 'released'}")
    if keycode is None:
        continue
    if pressed:
        kbd.press(keycode)
    else:
        kbd.release(keycode)
