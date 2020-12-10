import time
from adafruit_magtag.magtag import MagTag
import rtc

PET_NAME = "Midi"

magtag = MagTag()
magtag.network.connect()

magtag.add_text(
    text_font="/Lato-Bold-ltd-25.bdf",
    text_position=(10,5),
    text_anchor_point=(0,0),
    is_data=False,
)

magtag.add_text(
    text_font="/Montserrat-Regular-78.bdf",
    text_position=(10,45),
    text_anchor_point=(0,0),
    is_data=False,
)

while(True):

    if magtag.peripherals.button_a_pressed:
        magtag.network.get_local_time()
        now = rtc.RTC().datetime
        #set date
        date = (str(now.tm_mon), str(now.tm_mday), str(now.tm_year)[-2:])
        date = "/".join(date)
        magtag.set_text(PET_NAME + " was fed " + date, index = 0)
        #set time
        hour = now.tm_hour if now.tm_hour <= 12 else now.tm_hour - 12
        suffix = "a" if now.tm_hour < 12 else "p"
        time_string = str(hour) + ":" + str(now.tm_min) + suffix
        print(time_string)
        magtag.set_text(time_string, index = 1)
        time.sleep(2)

    time.sleep(0.01)