import time
# base hardware stuff
import board
import rtc
import keypad
import rotaryio
import neopixel
# crypto stuff
import adafruit_pcf8523
import adafruit_hashlib as hashlib
# UI stuff
import displayio
import terminalio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_progressbar.horizontalprogressbar import HorizontalProgressBar
# HID keyboard stuff
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

#--| User Config |--------------------------------------------------------
UTC_OFFSET = -4        # time zone offset
USE_12HR = True        # set 12/24 hour format
DISPLAY_TIMEOUT = 60   # screen saver timeout in seconds
DISPLAY_RATE = 1       # screen refresh rate
#-------------------------------------------------------------------------

# Get sekrets from a secrets.py file
try:
    from secrets import secrets
    totp_keys = secrets["totp_keys"]
except ImportError:
    print("Secrets are kept in secrets.py, please add them there!")
    raise
except KeyError:
    print("TOTP info not found in secrets.py.")
    raise

# set board to use PCF8523 as its RTC
pcf = adafruit_pcf8523.PCF8523(board.I2C())
rtc.set_time_source(pcf)

#-------------------------------------------------------------------------
#                       H I D    S E T U P
#-------------------------------------------------------------------------
time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems
keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)  # We're in the US :)

#-------------------------------------------------------------------------
#                    D I S P L A Y    S E T U P
#-------------------------------------------------------------------------
display = board.DISPLAY

# Secret Code font by Matthew Welch
# http://www.squaregear.net/fonts/
font = bitmap_font.load_font("/secrcode_28.bdf")

name = label.Label(terminalio.FONT, text="?"*18, color=0xFFFFFF)
name.anchor_point = (0.0, 0.0)
name.anchored_position = (0, 0)

code = label.Label(font, text="123456", color=0xFFFFFF)
code.anchor_point = (0.5, 0.0)
code.anchored_position = (display.width // 2, 15)

rtc_date = label.Label(terminalio.FONT, text="2021/01/01")
rtc_date.anchor_point = (0.0, 0.5)
rtc_date.anchored_position = (0, 49)

rtc_time = label.Label(terminalio.FONT, text="12:34:56 AM")
rtc_time.anchor_point = (0.0, 0.5)
rtc_time.anchored_position = (0, 59)

progress_bar = HorizontalProgressBar((68, 46), (55, 17), bar_color=0xFFFFFF, min_value=0, max_value=30)

splash = displayio.Group()
splash.append(name)
splash.append(code)
splash.append(rtc_date)
splash.append(rtc_time)
splash.append(progress_bar)

display.show(splash)

#-------------------------------------------------------------------------
#                    H E L P E R    F U N C S
#-------------------------------------------------------------------------
def timebase(timetime):
    return (timetime - (UTC_OFFSET*3600)) // 30

def compute_codes(timestamp):
    codes = []
    for key in totp_keys:
        if key:
            codes.append(generate_otp(timestamp, key[1]))
        else:
            codes.append(None)
    return codes

def HMAC(k, m):
    """# HMAC implementation, as hashlib/hmac wouldn't fit
    From https://en.wikipedia.org/wiki/Hash-based_message_authentication_code

    """
    SHA1_BLOCK_SIZE = 64
    KEY_BLOCK = k + (b'\0' * (SHA1_BLOCK_SIZE - len(k)))
    KEY_INNER = bytes((x ^ 0x36) for x in KEY_BLOCK)
    KEY_OUTER = bytes((x ^ 0x5C) for x in KEY_BLOCK)
    inner_message = KEY_INNER + m
    outer_message = KEY_OUTER + hashlib.sha1(inner_message).digest()
    return hashlib.sha1(outer_message)

def base32_decode(encoded):
    missing_padding = len(encoded) % 8
    if missing_padding != 0:
        encoded += '=' * (8 - missing_padding)
    encoded = encoded.upper()
    chunks = [encoded[i:i + 8] for i in range(0, len(encoded), 8)]

    out = []
    for chunk in chunks:
        bits = 0
        bitbuff = 0
        for c in chunk:
            if 'A' <= c <= 'Z':
                n = ord(c) - ord('A')
            elif '2' <= c <= '7':
                n = ord(c) - ord('2') + 26
            elif c == '=':
                continue
            else:
                raise ValueError("Not base32")
            # 5 bits per 8 chars of base32
            bits += 5
            # shift down and add the current value
            bitbuff <<= 5
            bitbuff |= n
            # great! we have enough to extract a byte
            if bits >= 8:
                bits -= 8
                byte = bitbuff >> bits  # grab top 8 bits
                bitbuff &= ~(0xFF << bits)  # and clear them
                out.append(byte)  # store what we got
    return out

def int_to_bytestring(int_val, padding=8):
    result = []
    while int_val != 0:
        result.insert(0, int_val & 0xFF)
        int_val >>= 8
    result = [0] * (padding - len(result)) + result
    return bytes(result)

def generate_otp(int_input, secret_key, digits=6):
    """ HMAC -> OTP generator, pretty much same as
    https://github.com/pyotp/pyotp/blob/master/src/pyotp/otp.py

    """
    if int_input < 0:
        raise ValueError('input must be positive integer')
    hmac_hash = bytearray(
        HMAC(bytes(base32_decode(secret_key)),
             int_to_bytestring(int_input)).digest()
    )
    offset = hmac_hash[-1] & 0xf
    code = ((hmac_hash[offset] & 0x7f) << 24 |
            (hmac_hash[offset + 1] & 0xff) << 16 |
            (hmac_hash[offset + 2] & 0xff) << 8 |
            (hmac_hash[offset + 3] & 0xff))
    str_code = str(code % 10 ** digits)
    while len(str_code) < digits:
        str_code = '0' + str_code

    return str_code

#-------------------------------------------------------------------------
#                    M A C R O P A D    S E T U P
#-------------------------------------------------------------------------
key_pins = (
    board.KEY1,
    board.KEY2,
    board.KEY3,
    board.KEY4,
    board.KEY5,
    board.KEY6,
    board.KEY7,
    board.KEY8,
    board.KEY9,
    board.KEY10,
    board.KEY11,
    board.KEY12,
    board.BUTTON,
)

keys = keypad.Keys(key_pins, value_when_pressed=False, pull=True)

knob = rotaryio.IncrementalEncoder(board.ROTA, board.ROTB)

pixels = neopixel.NeoPixel(board.NEOPIXEL, 12)
pixels.fill(0)

######################################
# MAIN
######################################
awake = True
knob_pos = knob.position
current_key = key_pressed = 0
last_compute = last_update = wake_up_time = time.time()
totp_codes = compute_codes(timebase(last_compute))
while True:
    now = time.time()
    progress_bar.value = now % 30
    event = keys.events.get()
    # wakeup if knob turned or button pressed
    if knob.position != knob_pos or event:
        if not awake:
            last_update = 0 # force an update
        awake = True
        knob_pos = knob.position
        wake_up_time = now
    # handle key presses
    if event:
        if event.pressed:
            key_pressed = event.key_number
            # knob
            if key_pressed == 12:
                keyboard_layout.write(totp_codes[current_key])
                keyboard.send(Keycode.ENTER)
            # keeb
            elif key_pressed != current_key:
                # is it a configured key?
                if totp_keys[key_pressed]:
                    current_key = key_pressed
                    pixels.fill(0)
                    last_update = 0 # force an update
    # update codes
    if progress_bar.value < 0.5 and now - last_compute > 2:
        totp_codes = compute_codes(timebase(now))
        last_compute = now
    # update display
    if now - last_update > DISPLAY_RATE and awake:
        pixels[current_key] = totp_keys[current_key][2]
        name.text = totp_keys[current_key][0][:18]
        code.text = totp_codes[current_key]
        tt = time.localtime()
        if USE_12HR:
            hour = tt.tm_hour % 12
            ampm = "AM" if tt.tm_hour < 12 else "PM"
        else:
            hour = tt.tm_hour
            ampm = ""
        rtc_date.text = "{:4}/{:2}/{:2}".format(tt.tm_year, tt.tm_mon, tt.tm_mday)
        rtc_time.text = "{}:{:02}:{:02} {}".format(hour, tt.tm_min, tt.tm_sec, ampm)
        last_update = now
        splash.hidden = False
    # go to sleep after inactivity
    if awake and now - wake_up_time > DISPLAY_TIMEOUT:
        awake = False
        knob_pos = knob.position
        pixels.fill(0)
        splash.hidden = True
