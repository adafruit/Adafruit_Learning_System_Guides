import time
from adafruit_magtag.magtag import MagTag

USE_AMPM_TIME = True
weekdays = ("mon", "tue", "wed", "thur", "fri", "sat", "sun")
last_sync = None
last_minute = None

magtag = MagTag()

magtag.graphics.set_background("/background.bmp")

mid_x = magtag.graphics.display.width // 2 - 1
magtag.add_text(
    text_font="Lato-Regular-74.bdf",
    text_position=(mid_x,10),
    text_anchor_point=(0.5,0),
    is_data=False,
)
magtag.set_text("00:00a", auto_refresh = False)

magtag.add_text(
    text_font="/BebasNeueRegular-41.bdf",
    text_position=(126,86), #was 141
    text_anchor_point=(0,0),
    is_data=False,
)
magtag.set_text("DAY 00:00a", index = 1, auto_refresh = False)

def hh_mm(time_struct, twelve_hour=True):
    """ Given a time.struct_time, return a string as H:MM or HH:MM, either
        12- or 24-hour style depending on twelve_hour flag.
    """
    postfix = ""
    if twelve_hour:
        if time_struct.tm_hour > 12:
            hour_string = str(time_struct.tm_hour - 12) # 13-23 -> 1-11 (pm)
            postfix = "p"
        elif time_struct.tm_hour > 0:
            hour_string = str(time_struct.tm_hour) # 1-12
            postfix = "a"
        else:
            hour_string = '12' # 0 -> 12 (am)
            postfix = "a"
    else:
        hour_string = '{hh:02d}'.format(hh=time_struct.tm_hour)
    return hour_string + ':{mm:02d}'.format(mm=time_struct.tm_min) + postfix

while True:
    if not last_sync or (time.monotonic() - last_sync) > 3600:
        # at start or once an hour
        magtag.network.get_local_time()
        last_sync = time.monotonic()

    # get current time
    now = time.localtime()

    # minute updated, refresh display!
    if not last_minute or (last_minute != now.tm_min):  # minute has updated
        magtag.set_text(hh_mm(now, USE_AMPM_TIME), index = 0)
        last_minute = now.tm_min

    # timestamp
    if magtag.peripherals.button_a_pressed:
        out = weekdays[now.tm_wday] + " " + hh_mm(now, USE_AMPM_TIME)
        magtag.set_text(out, index = 1)
        while magtag.peripherals.button_a_pressed: # wait till released
            pass
