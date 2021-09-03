import time

import adafruit_ssd1306
import bitbangio as io
import board
import network
import ntptime
import ubinascii
import uhashlib

# pylint: disable=broad-except

# https://github.com/pyotp/pyotp example
totp = [("Discord ", 'JBSWY3DPEHPK3PXP'),
        ("Gmail   ", 'abcdefghijklmnopqrstuvwxyz234567'),
        ("Accounts", 'asfdkwefoaiwejfa323nfjkl')]
ssid = 'my_wifi_ssid'
password = 'my_wifi_password'

TEST = False  # if you want to print out the tests the hashers
ALWAYS_ON = False  # Set to true if you never want to go to sleep!
ON_SECONDS = 60  # how long to stay on if not in always_on mode

i2c = io.I2C(board.SCL, board.SDA)
oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

# Gimme a welcome screen!
oled.fill(0)
oled.text('CircuitPython', 0, 0)
oled.text('PyTOTP Pal!', 0, 10)
oled.text(' <3 adafruit <3 ', 0, 20)
oled.show()
time.sleep(0.25)

EPOCH_DELTA = 946684800  # seconds between year 2000 and year 1970
SECS_DAY = 86400

SHA1 = uhashlib.sha1

if TEST:
    print("===========================================")
    print("SHA1 test: ", ubinascii.hexlify(SHA1(b'hello world').digest()))
    # should be 2aae6c35c94fcfb415dbe95f408b9ce91ee846ed


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


if TEST:
    KEY = b'abcd'
    MESSAGE = b'efgh'
    print("===========================================")
    print("HMAC test: ", ubinascii.hexlify(HMAC(KEY, MESSAGE).digest()))
    # should be e5dbcf9263188f9fce90df572afeb39b66b27198


# Base32 decoder, since base64 lib wouldnt fit


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


if TEST:
    print("===========================================")
    print("Base32 test: ", bytes(base32_decode("IFSGCZTSOVUXIIJB")))
    # should be "Adafruit!!"


# Turns an integer into a padded-with-0x0 bytestr


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

# Set up networking
sta_if = network.WLAN(network.STA_IF)

oled.fill(0)
oled.text('Connecting to', 0, 0)
oled.text(ssid, 0, 10)
oled.show()

if not sta_if.isconnected():
    print("Connecting to SSID", ssid)
    sta_if.active(True)
    sta_if.connect(ssid, password)
    while not sta_if.isconnected():
        pass
print("Connected! IP = ", sta_if.ifconfig()[0])

# Done! Let them know we made it
oled.text("IP: " + sta_if.ifconfig()[0], 0, 20)
oled.show()
time.sleep(0.25)

# Get the latest time from NTP
t = None
while not t:
    try:
        t = ntptime.time()
    except Exception:
        pass
    time.sleep(0.1)

# NTP time is seconds-since-2000
print("NTP time: ", t)

# But we need Unix time, which is seconds-since-1970
t += EPOCH_DELTA
print("Unix time: ", t)

# Instead of using RTC which means converting back and forth
# we'll just keep track of seconds-elapsed-since-NTP-call
mono_time = int(time.monotonic())
print("Monotonic time", mono_time)

countdown = ON_SECONDS  # how long to stay on if not in always_on mode
while ALWAYS_ON or (countdown > 0):
    # Calculate current time based on NTP + monotonic
    unix_time = t - mono_time + int(time.monotonic())
    print("Unix time: ", unix_time)

    # Clear the screen
    oled.fill(0)
    y = 0
    # We can do up to 3 per line on the Feather OLED
    for name, secret in totp:
        otp = generate_otp(unix_time // 30, secret)
        print(name + " OTP output: ", otp)  # serial debugging output
        oled.text(name + ": " + str(otp), 0, y)  # display name & OTP on OLED
        y += 10  # Go to next line on OLED
    # Display a little bar that 'counts down' how many seconds you have left
    oled.framebuf.line(0, 31, 128 - (unix_time % 30) * 4, 31, True)
    oled.show()
    # We'll update every 1/4 second, we can hash very fast so its no biggie!
    countdown -= 0.25
    time.sleep(0.25)

# All these hashes will be lost in time(), like tears in rain. Time to die
oled.fill(0)
oled.show()
