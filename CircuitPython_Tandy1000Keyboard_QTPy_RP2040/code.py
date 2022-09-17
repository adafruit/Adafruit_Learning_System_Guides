import time
import digitalio
import array
import board
import rp2pio
import adafruit_pioasm
from adafruit_hid.keyboard import Keyboard
import usb_hid
from adafruit_hid.keycode import Keycode as K

tandy1000_keycodes = [
None, K.ESCAPE, K.ONE, K.TWO, K.THREE, K.FOUR, K.FIVE, K.SIX, K.SEVEN, K.EIGHT, K.NINE, K.ZERO, K.MINUS, K.EQUALS, K.BACKSPACE, K.TAB, K.Q, K.W, K.E, K.R, K.T, K.Y, K.U, K.I, K.O, K.P, K.LEFT_BRACKET, K.RIGHT_BRACKET, K.ENTER, K.LEFT_CONTROL, K.A, K.S, K.D, K.F, K.G, K.H, K.J, K.K, K.L, K.SEMICOLON, K.QUOTE, K.UP_ARROW, K.LEFT_SHIFT, K.LEFT_ARROW, K.Z, K.X, K.C, K.V, K.B, K.N, K.M, K.COMMA, K.PERIOD, K.FORWARD_SLASH, K.RIGHT_SHIFT, K.PRINT_SCREEN, K.LEFT_ALT, K.SPACE, K.CAPS_LOCK, K.F1, K.F2, K.F3, K.F4, K.F5, K.F6, K.F7, K.F8, K.F9, K.F10, K.KEYPAD_NUMLOCK, K.PAUSE, K.KEYPAD_SEVEN, K.KEYPAD_EIGHT, K.KEYPAD_NINE, K.DOWN_ARROW, K.KEYPAD_FOUR, K.KEYPAD_FIVE, K.KEYPAD_SIX, K.RIGHT_ARROW, K.KEYPAD_ONE, K.KEYPAD_TWO, K.KEYPAD_THREE, K.KEYPAD_ZERO, K.KEYPAD_MINUS, (K.LEFT_CONTROL, K.PAUSE), K.KEYPAD_PLUS, K.KEYPAD_PERIOD, K.KEYPAD_ENTER, K.HOME, K.F11, K.F12
]

LOCK_KEYS = (K.CAPS_LOCK, K.KEYPAD_NUMLOCK)
LOCK_STATE = {
    K.CAPS_LOCK: False,
    K.KEYPAD_NUMLOCK: False,
}
KEYPAD_NUMLOCK_LOOKUP = [
    {
        K.KEYPAD_PLUS: K.INSERT,
        K.KEYPAD_MINUS: K.DELETE,

        K.KEYPAD_SEVEN: K.BACKSLASH,
        K.KEYPAD_EIGHT: (K.LEFT_SHIFT, K.GRAVE_ACCENT),
        K.KEYPAD_NINE: K.PAGE_UP,

        K.KEYPAD_FOUR: (K.LEFT_SHIFT, K.BACKSLASH),
        #K.KEYPAD_FIVE: 
        #K.KEYPAD_SIX: 

        K.KEYPAD_ONE: K.END,
        K.KEYPAD_TWO: K.GRAVE_ACCENT,
        K.KEYPAD_THREE: K.PAGE_DOWN,

        K.KEYPAD_ZERO: K.ZERO,
        K.KEYPAD_PERIOD: K.PERIOD,
    },
    {
        K.KEYPAD_PLUS: (K.LEFT_SHIFT, K.EQUALS),
        K.KEYPAD_MINUS: K.MINUS,

        K.KEYPAD_SEVEN: K.SEVEN,
        K.KEYPAD_EIGHT: K.EIGHT,
        K.KEYPAD_NINE: K.NINE,

        K.KEYPAD_FOUR: K.FOUR,
        K.KEYPAD_FIVE: K.FIVE,
        K.KEYPAD_SIX: K.SIX,

        K.KEYPAD_ONE: K.ONE,
        K.KEYPAD_TWO: K.TWO,
        K.KEYPAD_THREE: K.THREE,

        K.KEYPAD_ZERO: K.ZERO,
        K.KEYPAD_PERIOD: K.PERIOD,
    }
]

# D10 = blue   = CN2 = RESET
# D11 = white  = CN1 = DATA
# D12 = green  = CN3 = CLOCK
# D13 = yellow = CN4 = /BUSY

KBD_NRESET = board.MISO
KBD_DATA = board.RX
KBD_CLOCK = board.SCK # Note that KBD_CLOCK must be 1 GPIO above KBD_DATA
KBD_NBUSY = board.MOSI

# Assert busy
busy_out = digitalio.DigitalInOut(KBD_NBUSY)
busy_out.switch_to_output(False, digitalio.DriveMode.OPEN_DRAIN)

# Reset the keyboard
reset_out = digitalio.DigitalInOut(KBD_NRESET)
reset_out.switch_to_output(False, digitalio.DriveMode.OPEN_DRAIN)
time.sleep(.1)
reset_out.value = True

program = adafruit_pioasm.Program("""
    wait 1 pin 1
    in pins, 1
    wait 0 pin 1
""")

sm = rp2pio.StateMachine(program.assembled,
    first_in_pin = KBD_DATA,
    in_pin_count = 2,
    pull_in_pin_up = 0b11,
    auto_push=True,
    push_threshold=8,
    in_shift_right=True,
    frequency=8_000_000,
    **program.pio_kwargs)

buf = array.array('B', [0])

MASK_LEFT_SHIFT = K.modifier_bit(K.LEFT_SHIFT)
MASK_RIGHT_SHIFT = K.modifier_bit(K.RIGHT_SHIFT)
MASK_ANY_SHIFT = (MASK_LEFT_SHIFT | MASK_RIGHT_SHIFT)

# Now ready to get keystrokes
kbd = Keyboard(usb_hid.devices)
busy_out.value = True
while True:
    sm.readinto(buf, swap=False)
    val = buf[0]
    pressed = not (val & 0x80)
    key_number = val & 0x7f

    keycode = tandy1000_keycodes[key_number]
    if keycode is None:
        continue
    keycode = KEYPAD_NUMLOCK_LOOKUP[LOCK_STATE[K.KEYPAD_NUMLOCK]].get(keycode, keycode)
    if pressed:
        if keycode in LOCK_KEYS:
            LOCK_STATE[keycode] = True
        elif LOCK_STATE[K.CAPS_LOCK] and K.A <= keycode <= K.Z:
            old_report_modifier = kbd.report_modifier[0]
            kbd.report_modifier[0] = (old_report_modifier & ~MASK_RIGHT_SHIFT) ^ MASK_LEFT_SHIFT
            kbd.press(keycode)
            kbd.release_all()
            kbd.report_modifier[0] = old_report_modifier
            continue
        elif isinstance(keycode, tuple):
            old_report_modifier = kbd.report_modifier[0]
            kbd.report_modifier[0] = 0
            kbd.press(*keycode)
            kbd.release_all()
            kbd.report_modifier[0] = old_report_modifier
        else:
            kbd.press(keycode)

    else:
        if keycode in LOCK_KEYS:
            LOCK_STATE[keycode] = False
        elif isinstance(keycode, tuple):
            pass
        else:
            kbd.release(keycode)

    print(kbd.report)
