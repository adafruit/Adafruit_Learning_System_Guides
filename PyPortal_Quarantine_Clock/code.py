import time
import board
import busio
import digitalio
from adafruit_esp32spi import adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_requests as requests
from adafruit_pyportal import PyPortal
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label

try:
    from secrets import secrets
except ImportError:
    print("""WiFi settings are kept in secrets.py, please add them there!
the secrets dictionary must contain 'ssid' and 'password' at a minimum""")
    raise

# Label colors
LABEL_DAY_COLOR = 0xFFFFFF
LABEL_TIME_COLOR = 0x2a8eba

# the current working directory (where this file is)
cwd = ("/"+__file__).rsplit('/', 1)[0]
background = None
# un-comment to set background image
# background = cwd+"/background.bmp"

# Descriptions of each hour
# https://github.com/mwfisher3/QuarantineClock/blob/master/today.html
time_names = ["midnight-ish", "late night", "late", "super late",
              "super early","really early","dawn","morning",
              "morning","mid-morning","mid-morning","late morning",
              "noon-ish","afternoon","afternoon","mid-afternoon",
              "late afternoon","early evening","early evening","dusk-ish",
              "evening","evening","late evening","late evening"]

# Days of the week
week_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

esp32_cs = digitalio.DigitalInOut(board.ESP_CS)
esp32_ready = digitalio.DigitalInOut(board.ESP_BUSY)
esp32_reset = digitalio.DigitalInOut(board.ESP_RESET)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset, debug=False)
requests.set_socket(socket, esp)

# initialize pyportal
pyportal = PyPortal(esp=esp,
                    external_spi=spi,
                    default_bg = None)

# set pyportal's backlight brightness
pyportal.set_backlight(0.7)

if esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
    print("ESP32 found and in idle mode")
    print("Firmware vers.", esp.firmware_version)
    print("MAC addr:", [hex(i) for i in esp.MAC_address])

print("Connecting to AP...")
while not esp.is_connected:
    try:
        esp.connect_AP(secrets['ssid'], secrets['password'])
    except RuntimeError as e:
        print("could not connect to AP, retrying: ", e)
        continue

# Set the font and preload letters
font_large = bitmap_font.load_font("/fonts/Helvetica-Bold-44.bdf")
font_small = bitmap_font.load_font("/fonts/Helvetica-Bold-24.bdf")
font_large.load_glyphs(b'abcdefghjiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890- ')
font_small.load_glyphs(b'abcdefghjiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890- ()')

# Set up label for the day
label_day = label.Label(font_large, color=LABEL_DAY_COLOR, max_glyphs=200)
label_day.x = board.DISPLAY.width // 7
label_day.y = 80
pyportal.splash.append(label_day)

# Set up label for the time
label_time = label.Label(font_small, color=LABEL_TIME_COLOR, max_glyphs=200)
label_time.x = board.DISPLAY.width // 4
label_time.y = 150
pyportal.splash.append(label_time)

refresh_time = None
while True:
    # only query the network time every hour
    if (not refresh_time) or (time.monotonic() - refresh_time) > 3600:
        try:
            print("Getting new time from internet...")
            pyportal.get_local_time(secrets['timezone'])
            refresh_time = time.monotonic()
            # set the_time
            the_time = time.localtime()
        except (ValueError, RuntimeError) as e:
            print("Failed to get data, retrying\n", e)
            esp.reset()
            continue

    # Convert tm_wday to name of day
    weekday = week_days[the_time.tm_wday]

    # set the day label's text
    label_day.text = weekday

    # set the time label's text
    label_time.text = "({})".format(time_names[the_time.tm_hour])

    # update every minute
    time.sleep(60)
