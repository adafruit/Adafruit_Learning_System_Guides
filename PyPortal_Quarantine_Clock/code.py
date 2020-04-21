import time
import gc
import board
import displayio
import busio
from adafruit_esp32spi import adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
import adafruit_requests as requests
import digitalio
import analogio
from adafruit_pyportal import PyPortal
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
import adafruit_touchscreen


try:
    from secrets import secrets
except ImportError:
    print("""WiFi settings are kept in secrets.py, please add them there!
the secrets dictionary must contain 'ssid' and 'password' at a minimum""")
    raise

esp32_cs = digitalio.DigitalInOut(board.ESP_CS)
esp32_ready = digitalio.DigitalInOut(board.ESP_BUSY)
esp32_reset = digitalio.DigitalInOut(board.ESP_RESET)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset, debug=False)
requests.set_socket(socket, esp)


def wday_to_weekday_name(tm_wday):
    """Returns the name of the weekday based on tm_wday value.
    :param int tm_wday: Days since Sunday.

    """
    switch = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",}
    return switch.get(tm_wday, "Not found")

# initialize pyportal
pyportal = PyPortal(esp=esp,
                    external_spi=spi)

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
font_large = bitmap_font.load_font("/fonts/Helvetica-Bold-36.bdf")
font_small = bitmap_font.load_font("/fonts/Helvetica-Bold-24.bdf")
font_large.load_glyphs(b'abcdefghjiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890- ')
font_small.load_glyphs(b'abcdefghjiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890- ()')


# Set up display group
splash = displayio.Group(max_size=10) # The Main Display Group
view = displayio.Group(max_size=15) # Group for Text objects
splash.append(view)

# Set up label for the day
label_day = label.Label(font_large, color=0xFFFFFF, max_glyphs=200)
label_day.x = board.DISPLAY.width // 4
label_day.y = 70
view.append(label_day)

# Set up label for the time
label_time = label.Label(font_small, color=0x538ab1, max_glyphs=200)
label_time.x = board.DISPLAY.width // 4
label_time.y = 150
view.append(label_time)

# Show group splash
board.DISPLAY.show(splash)

# Obtain local time from Time API
pyportal.get_local_time(secrets['timezone'])
the_time = time.localtime()

# Convert tm_wday to name of day
weekday = wday_to_weekday_name(the_time.tm_wday)
# Set label_day
label_day.text = "{}".format(weekday)


# Time descriptions
time_name = ["midnight-ish", "late night", "late", "super late",
            "super early","really early","dawn","morning",
            "morning","mid-morning","mid-morning","late morning",
            "noon-ish","afternoon","afternoon","mid-afternoon",
            "late afternoon","early evening","early evening","dusk-ish",
            "evening","evening","late evening","late evening"]

label_time.text = "({})".format(time_name[the_time.tm_hour])


while True:
    pass