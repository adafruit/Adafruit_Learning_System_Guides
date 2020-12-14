import time
from adafruit_magtag.magtag import MagTag
import rtc

PET_NAME = "Midi"

magtag = MagTag()

mid_x = magtag.graphics.display.width // 2 - 1
magtag.add_text(
    text_font="/Montserrat-Regular-78.bdf",
    text_position=(mid_x,10),
    text_anchor_point=(0.5,0),
    is_data=False,
)
magtag.set_text("00:00", auto_refresh = False)

magtag.add_text(
    text_font="/Arial-12.bdf",
    text_position=(48  ,94),
    text_anchor_point=(0,0),
    line_spacing=0.7,
    is_data=False,
)
magtag.set_text("last feeding:", index = 1, auto_refresh = False)

magtag.add_text(
    text_font="/Montserrat-Regular-39.bdf",
    text_position=(141,86),
    text_anchor_point=(0,0),
    is_data=False,
)
magtag.set_text("00:00", index = 2)

def network_time():
    magtag.network.get_local_time()
    now = rtc.RTC().datetime
    return now

def time_for_display(new_time):
    hour = new_time.tm_hour if new_time.tm_hour <= 12 else new_time.tm_hour - 12
    suffix = "a" if new_time.tm_hour < 12 else "p"
    time_string = str(hour) + ":" + str(new_time.tm_min) + suffix
    return time_string

magtag.network.connect()

# Set initial clock time
# pylint: disable=bare-except
try:
    DATETIME = network_time()
except:
    DATETIME = time.localtime()
LAST_SYNC = time.mktime(DATETIME)

LAST_DISPLAY = 0


while(True):

    NOW = time.time() # Current epoch time in seconds

    # Sync with time server every hour
    if NOW - LAST_SYNC > 60 * 60:
        try:
            DATETIME = network_time()
            LAST_SYNC = time.mktime(DATETIME)
            continue # Time may have changed; refresh NOW value
        except:
            # if unable to sync time, try again in 30 min
            LAST_SYNC += 30 * 60 # 30 minutes -> seconds

    if NOW - LAST_DISPLAY > 60:
        # display new time
        magtag.set_text(time_for_display(DATETIME), index = 0)
        # increment local time
        diff_secs = NOW - LAST_DISPLAY
        new_secs = time.mktime(DATETIME) + diff_secs
        DATETIME = time.localtime(new_secs) # OverflowError: overflow converting long int to machine word
        LAST_DISPLAY = NOW

    if magtag.peripherals.button_a_pressed:
        magtag.set_text(time_for_display(DATETIME), index = 2)
        #magtag.show()
        time.sleep(2)

    time.sleep(0.01)