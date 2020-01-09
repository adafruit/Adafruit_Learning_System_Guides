import time

import board
import busio
from digitalio import DigitalInOut
import displayio
import terminalio
from simpleio import map_range
import adafruit_hashlib as hashlib
import adafruit_touchscreen
from adafruit_button import Button
from adafruit_progressbar import ProgressBar
from adafruit_display_text.label import Label
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_ntp import NTP
from adafruit_pyportal import PyPortal


# Background Color
BACKGROUND = 0x0

# Button color
BTN_COLOR = 0xFFFFFF

# Button text color
BTN_TEXT_COLOR = 0x0

# Set to true if you never want to go to sleep!
ALWAYS_ON = True

# How long to stay on if not in always_on mode
ON_SECONDS = 60

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Initialize PyPortal Display
display = board.DISPLAY

WIDTH = board.DISPLAY.width
HEIGHT = board.DISPLAY.height
ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=(
                                          (5200, 59000),
                                          (5800, 57000)
                                          ),
                                      size=(WIDTH, HEIGHT))

# Create a SHA1 Object
SHA1 = hashlib.sha1

# PyPortal ESP32 AirLift Pins
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

# Initialize PyPortal ESP32 AirLift
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

def HMAC(k, m):
    """# HMAC implementation, as hashlib/hmac wouldn't fit
    From https://en.wikipedia.org/wiki/Hash-based_message_authentication_code

    """
    SHA1_BLOCK_SIZE = 64
    KEY_BLOCK = k + (b'\0' * (SHA1_BLOCK_SIZE - len(k)))
    KEY_INNER = bytes((x ^ 0x36) for x in KEY_BLOCK)
    KEY_OUTER = bytes((x ^ 0x5C) for x in KEY_BLOCK)
    inner_message = KEY_INNER + m
    outer_message = KEY_OUTER + SHA1(inner_message).digest()
    return SHA1(outer_message)

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
            elif n == '=':
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

def display_otp_key(secret_name, secret_otp):
    """Updates the displayio labels to display formatted OTP key and name.

    """
    # display the key's name
    label_title.text = secret_name
    # format and display the OTP
    label_secret.text = "{} {}".format(str(secret_otp)[0:3], str(secret_otp)[3:6])
    print("OTP Name: {}\nOTP Key: {}".format(secret_name, secret_otp))

print("===========================================")

# GFX Font
font = terminalio.FONT

# Initialize new PyPortal object
pyportal = PyPortal(esp=esp,
                    external_spi=spi)

# Root DisplayIO
root_group = displayio.Group(max_size=100)
display.show(root_group)

BACKGROUND = BACKGROUND if isinstance(BACKGROUND, int) else 0x0
bg_bitmap = displayio.Bitmap(display.width, display.height, 1)
bg_palette = displayio.Palette(1)
bg_palette[0] = BACKGROUND
background = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette)

# Create a new DisplayIO group
splash = displayio.Group(max_size=15)

splash.append(background)

key_group = displayio.Group(scale=5)
# We'll use a default text placeholder for this label
label_secret = Label(font, text="000 000")
label_secret.x = (display.width // 2) // 13
label_secret.y = 17
key_group.append(label_secret)

label_title = Label(font, max_glyphs=14)
label_title.text = "  Loading.."
label_title.x = 0
label_title.y = 5
key_group.append(label_title)

# append key_group to splash
splash.append(key_group)

# Show the group
display.show(splash)

print("Connecting to AP...")
while not esp.is_connected:
    try:
        esp.connect_AP(secrets['ssid'], secrets['password'])
    except RuntimeError as e:
        print("Could not connect to AP, retrying: ", e)
        continue

print("Connected to ", secrets['ssid'])

# Initialize the NTP object
ntp = NTP(esp)

# Fetch and set the microcontroller's current UTC time
# keep retrying until a valid time is returned
while not ntp.valid_time:
    ntp.set_time()
    print("Could not obtain NTP, re-fetching in 5 seconds...")
    time.sleep(5)

# Get the current time in seconds since Jan 1, 1970
t = time.time()
print("Seconds since Jan 1, 1970: {} seconds".format(t))

# Instead of using RTC which means converting back and forth
# we'll just keep track of seconds-elapsed-since-NTP-call
mono_time = int(time.monotonic())
print("Monotonic time", mono_time)

# Add buttons to the interface
assert len(secrets['totp_keys']) < 6, "This code can only display 5 keys at a time"

# generate buttons
buttons = []

btn_x = 5
for i in secrets['totp_keys']:
    button = Button(name=i[0], x=btn_x,
                    y=175, width=60,
                    height=60, label=i[0].strip(" "),
                    label_font=font, label_color=BTN_TEXT_COLOR,
                    fill_color=BTN_COLOR, style=Button.ROUNDRECT)
    buttons.append(button)
    # add padding btween buttons
    btn_x += 63

# append buttons to splash group
for b in buttons:
    splash.append(b.group)

# refrsh timer label
label_timer = Label(font, max_glyphs=2)
label_timer.x = (display.width // 2) // 13
label_timer.y = 15
splash.append(label_timer)

# create a new progress bar
progress_bar = ProgressBar(display.width//5, 125,
                           200, 30, bar_color = 0xFFFFFF)

splash.append(progress_bar)

# how long to stay on if not in always_on mode
countdown = ON_SECONDS

# current button state, defaults to first item in totp_keys
current_button = secrets['totp_keys'][0][0]
buttons[0].selected = True

while ALWAYS_ON or (countdown > 0):
    # Calculate current time based on NTP + monotonic
    unix_time = t - mono_time + int(time.monotonic())

    # Update the key refresh timer
    timer = time.localtime(time.time()).tm_sec
    # timer resets on :00/:30
    if timer > 30:
        countdown = 60 - timer
    else:
        countdown = 30 - timer
    print('NTP Countdown: {}%'.format(countdown))
    # change the timer bar's color if text is about to refresh
    progress_bar.fill = 0xFFFFFF
    if countdown < 5:
        progress_bar.fill = 0xFF0000

    # update the progress_bar with countdown
    countdown = map_range(countdown, 0, 30, 0.0, 1.0)
    progress_bar.progress = countdown

    # poll the touchscreen
    p = ts.touch_point
    # if the touchscreen was pressed
    if p:
        for i, b in enumerate(buttons):
            if b.contains(p):
                b.selected = True
                for name, secret in secrets['totp_keys']:
                    # check if button name is the same as a key name
                    if b.name == name:
                        current_button = name
                        # Generate OTP
                        otp = generate_otp(unix_time // 30, secret)
                        display_otp_key(name, otp)
            else:
                b.selected = False
    else:
        for name, secret in secrets['totp_keys']:
            if current_button == name:
                # Generate OTP
                otp = generate_otp(unix_time // 30, secret)
                display_otp_key(name, otp)
    # We'll update every 1/4 second, we can hash very fast so its no biggie!
    countdown -= 0.25
    time.sleep(0.25)
