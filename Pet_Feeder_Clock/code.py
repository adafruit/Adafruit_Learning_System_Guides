import time
from adafruit_magtag.magtag import MagTag
import rtc

PET_NAME = "Midi"

magtag = MagTag()
magtag.auto_refresh = False
magtag.network.connect()

mid_x = magtag.graphics.display.width // 2 - 1
magtag.add_text(
    text_font="/Montserrat-Regular-78.bdf",
    text_position=(mid_x,6),
    text_anchor_point=(0.5,0),
    is_data=False,
)
magtag.set_text("00:00")

magtag.add_text(
    text_font="/CourierNewPSMT-18.bdf",
    text_position=(20,80),
    text_anchor_point=(0,0),
    is_data=False,
)
magtag.set_text("test:", index = 1)

magtag.add_text(
    text_font="/Montserrat-Regular-39.bdf",
    text_position=(132,80),
    text_anchor_point=(0,0),
    is_data=False,
)
magtag.set_text("00:00", index = 2)

def network_time():
    magtag.network.get_local_time()
    now = rtc.RTC().datetime
    return now

while(True):

    if magtag.peripherals.button_a_pressed:
        now = network_time()
        #set time
        hour = now.tm_hour if now.tm_hour <= 12 else now.tm_hour - 12
        suffix = "a" if now.tm_hour < 12 else "p"
        time_string = str(hour) + ":" + str(now.tm_min) + suffix
        print(time_string)
        magtag.set_text(time_string, index = 2)
        #magtag.show()
        time.sleep(2)

    time.sleep(0.01)