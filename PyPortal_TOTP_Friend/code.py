import time

import board
import busio
from digitalio import DigitalInOut

import adafruit_hashlib as hashlib
import adafruit_touchscreen
import displayio
import neopixel
import terminalio
from adafruit_binascii import hexlify, unhexlify
from adafruit_bitmap_font import bitmap_font
from adafruit_button import Button
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_display_text.label import Label
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_ntp import NTP
from adafruit_pyportal import PyPortal

# Background/Images
BACKGROUND = 0x059ACE

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



# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

TEST = True  # if you want to print out the tests the hashers
ALWAYS_ON = True  # Set to true if you never want to go to sleep!
ON_SECONDS = 60  # how long to stay on if not in always_on mode

# Create a SHA1 Object
SHA1 = hashlib.sha1

# PyPortal ESP32 AirLift Pins
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

# Initialize PyPortal ESP32 AirLift
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)


# HMAC implementation, as hashlib/hmac wouldn't fit
# From https://en.wikipedia.org/wiki/Hash-based_message_authentication_code
def HMAC(k, m):
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

def int_to_bytestring(i, padding=8):
    result = []
    while i != 0:
        result.insert(0, i & 0xFF)
        i >>= 8
    result = [0] * (padding - len(result)) + result
    return bytes(result)


# HMAC -> OTP generator, pretty much same as
# https://github.com/pyotp/pyotp/blob/master/src/pyotp/otp.py

def generate_otp(int_input, secret_key, digits=6):
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


print("===========================================")

# GFX Font
font = terminalio.FONT


# Initialize new PyPortal object
pyportal = PyPortal(esp=esp,
                    external_spi=spi)

# Root DisplayIO
root_group = displayio.Group(max_size=200)
display.show(root_group)

# TODO: Add press-able icon group

BACKGROUND = BACKGROUND if isinstance(BACKGROUND, int) else 0x000000
bg_bitmap = displayio.Bitmap(display.width, display.height, 1)
bg_palette = displayio.Palette(1)
bg_palette[0] = BACKGROUND
background = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette)

# Text DisplayIO
splash = displayio.Group(max_size=100)

splash.append(background)


key_group = displayio.Group(scale=5)
# We'll use a default text placeholder for this label
label_key = Label(font, text="000 000")
label_key.x = (display.width // 2) // 13
label_key.y = 15
key_group.append(label_key)

label_title = Label(font, max_glyphs=14)
label_title.x = (display.width // 2) // 10
label_title.y = 5
key_group.append(label_title)

splash.append(key_group)

# Create a label to monitor the status
label_status = Label(font, max_glyphs=45)
label_status.x = (display.width // 2) - 50
label_status.y = 120
splash.append(label_status)

# Show the group
display.show(splash)


print("Connecting to AP...")
label_status.text = "Connecting to AP..."
while not esp.is_connected:
    try:
        esp.connect_AP(secrets['ssid'], secrets['password'])
    except RuntimeError as e:
        print("could not connect to AP, retrying: ", e)
        label_status.text("Retrying...")
        continue

label_status.text = "Connected! Fetching NTP..."
#label_status.text("Connected to {}, fetching NTP...".format(secrets['ssid']))
print("Connected to SSID: ", secrets['ssid'])

# Initialize the NTP object
ntp = NTP(esp)

# Fetch and set the microcontroller's current UTC time
# keep retrying until a valid time is returned
while not ntp.valid_time:
    ntp.set_time()
    print("Failed to obtain time, retrying in 5 seconds...")
    time.sleep(5)

# Clear the status label
label_status.text = ""

# Add buttons to the interface
# TODO: Generate them like in https://learn.adafruit.com/pyportal-philips-hue-lighting-controller/code-walkthrough
# TODO: Make these dynamically based on what is store in secrets.py 
# TODO: Add icons to buttons instead of text

BUTTON_WIDTH = 60
BUTTON_HEIGHT = 60
BUTTON_MARGIN = 20
buttons = []

button_0 =  Button(name='Gmail',x=0, y=130,
                  width=BUTTON_WIDTH, height=BUTTON_HEIGHT,
                  label="Gmail", label_font=font, style=Button.ROUNDRECT,  fill_color=0xFF0000)
buttons.append(button_0)


button_1 =  Button(name='Discord',x=70, y=130,
                  width=BUTTON_WIDTH, height=BUTTON_HEIGHT,
                  label="Discord", label_font=font, style=Button.ROUNDRECT,  fill_color=0x9900FF)
buttons.append(button_1)

for b in buttons:
    splash.append(b.group)


# Get the current time in seconds since Jan 1, 1970
t = time.time()
print("Seconds since Jan 1, 1970: {} seconds".format(t))

# Instead of using RTC which means converting back and forth
# we'll just keep track of seconds-elapsed-since-NTP-call
mono_time = int(time.monotonic())
print("Monotonic time", mono_time)

countdown = ON_SECONDS  # how long to stay on if not in always_on mode
while ALWAYS_ON or (countdown > 0):
    # Calculate current time based on NTP + monotonic
    unix_time = t - mono_time + int(time.monotonic())
    p = ts.touch_point
    if p:
        print(p)
        for i, b in enumerate(buttons):
            if b.contains(p):
                print("Button %d pressed" % i)
                b.selected = True
                for name, secret in secrets['totp_keys']:
                    print(b.name)
                    if b.name == name:
                        print('button selected: ', name)
                        otp = generate_otp(unix_time // 30, secret)
                        # TODO: This needs to get cleaned up into a one-liner
                        otp = str(otp)
                        formatted_otp = "{} {}".format(otp[0:3],otp[3:6])
                        label_key.text = formatted_otp
                        label_title.text = name
                        print(name + " OTP output: ", otp)  # serial debugging output
            else:
                b.selected = False
    # We'll update every 1/4 second, we can hash very fast so its no biggie!
    countdown -= 0.25
    time.sleep(0.25)
