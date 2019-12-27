import time
import board
import busio
from digitalio import DigitalInOut
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_ntp import NTP
import adafruit_hashlib as hashlib
from adafruit_binascii import hexlify, unhexlify

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# https://github.com/pyotp/pyotp example
totp = [("Gmail   ", 'JBSWY3DPEHPK3PXP')]


TEST = True  # if you want to print out the tests the hashers
ALWAYS_ON = False  # Set to true if you never want to go to sleep!
ON_SECONDS = 60  # how long to stay on if not in always_on mode

EPOCH_DELTA = 946684800  # seconds between year 2000 and year 1970
SECS_DAY = 86400

# Create a SHA1 Object
SHA1 = hashlib.sha1

# PyPortal ESP32 AirLift Pins
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

# Initialize PyPortal ESP32 AirLift
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)


if TEST:
    print("===========================================")
    sha1_output = hexlify(SHA1(b'hello world').digest())
    assert sha1_output == b"2aae6c35c94fcfb415dbe95f408b9ce91ee846ed"


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
    hmac_out = hexlify(HMAC(KEY, MESSAGE).digest())
    assert hmac_out == b'e5dbcf9263188f9fce90df572afeb39b66b27198' 

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

if TEST:
    print("===========================================")
    assert (bytes(base32_decode("IFSGCZTSOVUXIIJB")) == b'Adafruit!!')

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


print("Connecting to AP...")
while not esp.is_connected:
    try:
        esp.connect_AP(secrets['ssid'], secrets['password'])
    except RuntimeError as e:
        print("could not connect to AP, retrying: ", e)
        continue

print("Connected to SSID: ", secrets['ssid'])

# Initialize the NTP object
ntp = NTP(esp)

# Fetch and set the microcontroller's current UTC time
# keep retrying until a valid time is returned
while not ntp.valid_time:
    ntp.set_time()
    print("Failed to obtain time, retrying in 15 seconds...")
    time.sleep(15)

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
    print("Unix time: ", unix_time)
    # We can do up to 3 per line on the Feather OLED
    for name, secret in totp:
        otp = generate_otp(unix_time // 30, secret)
        print(name + " OTP output: ", otp)  # serial debugging output
    # We'll update every 1/4 second, we can hash very fast so its no biggie!
    countdown -= 0.25
    time.sleep(0.25)