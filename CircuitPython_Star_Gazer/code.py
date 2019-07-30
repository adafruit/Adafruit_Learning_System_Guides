"""
This example will access an API, grab a number like hackaday skulls, github
stars, price of bitcoin, twitter followers... if you can find something that
spits out JSON data, we can display it!
"""
import gc
import time
import board
import busio
from digitalio import DigitalInOut, Direction
from Adafruit_CircuitPython_ESP_ATcontrol import adafruit_espatcontrol
from adafruit_ht16k33 import segments
import neopixel
import ujson

# Get wifi details and more from a settings.py file
try:
    from settings import settings
except ImportError:
    print("WiFi settings are kept in settings.py, please add them there!")
    raise

#              CONFIGURATION
PLAY_SOUND_ON_CHANGE = True
NEOPIXELS_ON_CHANGE = False
TIME_BETWEEN_QUERY = 0  # in seconds

# Some data sources and JSON locations to try out

# Github stars! You can query 1ce a minute without an API key token
DATA_SOURCE = "https://api.github.com/repos/adafruit/circuitpython"
if 'github_token' in settings:
    DATA_SOURCE += "?access_token="+settings['github_token']
DATA_LOCATION = ["stargazers_count"]



uart = busio.UART(board.TX, board.RX, timeout=0.1)
resetpin = DigitalInOut(board.D5)
rtspin = DigitalInOut(board.D9)

# Create the connection to the co-processor and reset
esp = adafruit_espatcontrol.ESP_ATcontrol(uart, 115200, run_baudrate=115200,
                                          reset_pin=resetpin,
                                          rts_pin=rtspin, debug=True)
esp.hard_reset()

# Create the I2C interface.
i2c = busio.I2C(board.SCL, board.SDA)
# Attach a 7 segment display and display -'s so we know its not live yet
display = segments.Seg7x4(i2c)
display.print('----')

powerpin = DigitalInOut(board.D10)
powerpin.direction = Direction.OUTPUT
powerpin.value = True
starpin = DigitalInOut(board.D11)
starpin.direction = Direction.OUTPUT
starpin.value = False

status = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)

# neopixels
if NEOPIXELS_ON_CHANGE:
    pixels = neopixel.NeoPixel(board.A1, 16, brightness=0.4, pixel_order=(1, 0, 2, 3))
    pixels.fill(0)

# music!
if PLAY_SOUND_ON_CHANGE:
    import audioio
    wave_file = open("coin.wav", "rb")
    wave = audioio.WaveFile(wave_file)

# we'll save the value in question
last_value = value = 0
the_time = None
times = 0

def chime_light():
    """Light up LEDs and play a tune"""
    if NEOPIXELS_ON_CHANGE:
        for i in range(0, 100, 10):
            pixels.fill((i, i, i))
    starpin.value = True

    if PLAY_SOUND_ON_CHANGE:
        with audioio.AudioOut(board.A0) as audio:
            audio.play(wave)
            while audio.playing:
                pass
    starpin.value = False

    if NEOPIXELS_ON_CHANGE:
        for i in range(100, 0, -10):
            pixels.fill((i, i, i))
        pixels.fill(0)

def get_value(response, location):
    """Extract a value from a json object, based on the path in 'location'"""
    try:
        print("Parsing JSON response...", end='')
        json = ujson.loads(response)
        print("parsed OK!")
        for x in location:
            json = json[x]
        return json
    except ValueError:
        print("Failed to parse json, retrying")
        return None

while True:
    try:
        status[0] = (0,0,100)
        while not esp.is_connected:
            # settings dictionary must contain 'ssid' and 'password' at a minimum
            status[0] = (100, 0, 0) # red = not connected
            esp.connect(settings)
        # great, lets get the data
        # get the time
        #the_time = esp.sntp_time

        print("Retrieving data source...", end='')
        status[0] = (100, 100, 0)   # yellow = fetching data
        header, body = esp.request_url(DATA_SOURCE)
        status[0] = (0, 0, 100)   # green = got data
        print("Reply is OK!")
    except (RuntimeError, adafruit_espatcontrol.OKError) as e:
        print("Failed to get data, retrying\n", e)
        continue
    #print('-'*40, "Size: ", len(body))
    #print(str(body, 'utf-8'))
    #print('-'*40)
    value = get_value(body, DATA_LOCATION)
    if not value:
        continue
    print(times, the_time, "value:", value)
    display.print(int(value))
    status[0] = (0, 0, 0)  # off = ready for next
    if last_value < value:
        chime_light() # animate the neopixels
        last_value = value
    times += 1
    # normally we wouldn't have to do this, but we get bad fragments
    header = body = None
    gc.collect()
    print(gc.mem_free())  # pylint: disable=no-member
    time.sleep(TIME_BETWEEN_QUERY)
