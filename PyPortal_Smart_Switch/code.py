import time
import gc
import board
import busio
from adafruit_esp32spi import adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi, adafruit_esp32spi_wifimanager
import adafruit_requests as requests
import digitalio
import analogio
from adafruit_pyportal import PyPortal
from adafruit_display_shapes.circle import Circle
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
import adafruit_touchscreen

from adafruit_minimqtt import MQTT

DISPLAY_COLOR = 0x006600
SWITCH_COLOR = 0x008800
SWITCH_FILL_COLOR = 0xffffff

# Switch location
SWITCHX = 260
SWITCHY = 4

FEED_NAME = "pyportal-switch"

months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def get_local_timestamp(location=None):
    # pylint: disable=line-too-long
    """Fetch and "set" the local time of this microcontroller to the local time at the location, using an internet time API.
    :param str location: Your city and country, e.g. ``"New York, US"``.
    """
    # pylint: enable=line-too-long
    api_url = None
    try:
        aio_username = secrets['aio_username']
        aio_key = secrets['aio_key']
    except KeyError:
        raise KeyError("\n\nOur time service requires a login/password to rate-limit. Please register for a free adafruit.io account and place the user/key in your secrets file under 'aio_username' and 'aio_key'")# pylint: disable=line-too-long

    location = secrets.get('timezone', location)
    if location:
        print("Getting time for timezone", location)
        api_url = (TIME_SERVICE + "&tz=%s") % (aio_username, aio_key, location)
    else: # we'll try to figure it out from the IP address
        print("Getting time from IP address")
        api_url = TIME_SERVICE % (aio_username, aio_key)
    api_url += TIME_SERVICE_TIMESTAMP
    try:
        print("api_url:",api_url)
        response = requests.get(api_url)
        times = response.text.split(' ')
        seconds = int(times[0])
        tzoffset = times[1]
        tzhours = int(tzoffset[0:3])
        tzminutes = int(tzoffset[3:5])
        tzseconds = tzhours * 60 * 60
        if tzseconds < 0:
            tzseconds -= tzminutes * 60
        else:
            tzseconds += tzminutes * 60
        print(seconds + tzseconds, tzoffset, tzhours, tzminutes)
    except KeyError:
        raise KeyError("Was unable to lookup the time, try setting secrets['timezone'] according to http://worldtimeapi.org/timezones")  # pylint: disable=line-too-long

    # now clean up
    response.close()
    response = None
    gc.collect()
    return int(seconds + tzseconds)

def create_text_areas(configs):
    """Given a list of area specifications, create and return text areas."""
    text_areas = []
    for cfg in configs:
        textarea = label.Label(cfg['font'], text=' '*cfg['size'])
        textarea.x = cfg['x']
        textarea.y = cfg['y']
        textarea.color = cfg['color']
        text_areas.append(textarea)
    return text_areas

class Switch(object):
    def __init__(self, pin, my_pyportal):
        self.switch = digitalio.DigitalInOut(pin)
        self.switch.direction = digitalio.Direction.OUTPUT
        rect = RoundRect(SWITCHX, SWITCHY, 31, 60, 16, outline=SWITCH_COLOR,
                         fill=SWITCH_FILL_COLOR, stroke=3)
        my_pyportal.splash.append(rect)
        self.circle_on = Circle(SWITCHX + 15, SWITCHY + 16, 10, fill=SWITCH_FILL_COLOR)
        my_pyportal.splash.append(self.circle_on)
        self.circle_off = Circle(SWITCHX + 15, SWITCHY + 42, 10, fill=DISPLAY_COLOR)
        my_pyportal.splash.append(self.circle_off)

    # turn switch on or off
    def enable(self, enable):
        print("turning switch to ", enable)
        self.switch.value = enable
        if enable:
            self.circle_off.fill = SWITCH_FILL_COLOR
            self.circle_on.fill = DISPLAY_COLOR
        else:
            self.circle_on.fill = SWITCH_FILL_COLOR
            self.circle_off.fill = DISPLAY_COLOR

    def toggle(self):
        if self.switch.value:
            self.enable(False)
        else:
            self.enable(True)

    def status(self):
        return self.switch.value

# you'll need to pass in an io username and key
TIME_SERVICE = "http://io.adafruit.com/api/v2/%s/integrations/time/strftime?x-aio-key=%s"
# See https://apidock.com/ruby/DateTime/strftime for full options
TIME_SERVICE_TIMESTAMP = '&fmt=%25s+%25z'

class Clock(object):
    def __init__(self, my_pyportal):
        self.low_light = False
        self.update_time = None
        self.snapshot_time = None
        self.pyportal = my_pyportal
        self.current_time = 0
        self.light = analogio.AnalogIn(board.LIGHT)
        text_area_configs = [dict(x=0, y=105, size=10, color=DISPLAY_COLOR, font=time_font),
                             dict(x=260, y=153, size=3, color=DISPLAY_COLOR, font=ampm_font),
                             dict(x=110, y=40, size=20, color=DISPLAY_COLOR, font=date_font)]
        self.text_areas = create_text_areas(text_area_configs)
        self.text_areas[2].text = "starting..."
        for ta in self.text_areas:
            self.pyportal.splash.append(ta)

    def adjust_backlight(self, force=False):
        """Check light level. Adjust the backlight and background image if it's dark."""
        if force or (self.light.value >= 1500 and self.low_light):
            self.pyportal.set_backlight(1.00)
            self.low_light = False
        elif self.light.value <= 1000 and not self.low_light:
            self.pyportal.set_backlight(0.1)
            self.low_light = True

    def tick(self, now):
        self.adjust_backlight()
        if (not self.update_time) or ((now - self.update_time) >= 300):
            # Update the time
            print("update the time")
            self.update_time = int(now)
            self.snapshot_time = get_local_timestamp(secrets['timezone'])
            self.current_time = time.localtime(self.snapshot_time)
        else:
            self.current_time = time.localtime(int(now) - self.update_time + self.snapshot_time)
        hour = self.current_time.tm_hour
        if hour > 12:
            hour = hour % 12
        if hour == 0:
            hour = 12
        time_string = '%2d:%02d' % (hour,self.current_time.tm_min)
        self.text_areas[0].text = time_string
        ampm_string = "AM"
        if self.current_time.tm_hour >= 12:
            ampm_string = "PM"
        self.text_areas[1].text = ampm_string
        self.text_areas[2].text = (months[int(self.current_time.tm_mon - 1)] +
                                   " " + str(self.current_time.tm_mday))
        try:
            board.DISPLAY.refresh(target_frames_per_second=60)
        except AttributeError:
            board.DISPLAY.refresh_soon()
            board.DISPLAY.wait_for_frame()

# Define callback methods which are called when events occur
# pylint: disable=unused-argument, redefined-outer-name
def connected(client, userdata, flags, rc):
    # This function will be called when the client is connected
    # successfully to the broker.
    onoff_feed = secrets['aio_username'] + '/feeds/' + FEED_NAME
    print('Connected to Adafruit IO! Listening for topic changes on %s' % onoff_feed)
    # Subscribe to all changes on the onoff_feed.
    client.subscribe(onoff_feed)

def disconnected(client, userdata, rc):
    # This method is called when the client is disconnected
    print('Disconnected from Adafruit IO!')

def message(client, topic, message):
    # This method is called when a topic the client is subscribed to
    # has a new message.
    print('New message on topic {0}: {1}'.format(topic, message))
    if message in ("ON","TRUE","1"):
        switch.enable(True)
    else:
        switch.enable(False)

############################################

try:
    from secrets import secrets
except ImportError:
    print("""WiFi settings are kept in secrets.py, please add them there!
the secrets dictionary must contain 'ssid' and 'password' at a minimum""")
    raise

esp32_cs = digitalio.DigitalInOut(board.ESP_CS)
esp32_ready = digitalio.DigitalInOut(board.ESP_BUSY)
esp32_reset = digitalio.DigitalInOut(board.ESP_RESET)

WIDTH = board.DISPLAY.width
HEIGHT = board.DISPLAY.height

ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=(
                                          (5200, 59000),
                                          (5800, 57000)
                                          ),
                                      size=(WIDTH, HEIGHT))

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset, debug=False)
requests.set_socket(socket, esp)

if esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
    print("ESP32 found and in idle mode")
    print("Firmware vers.", esp.firmware_version)
    print("MAC addr:", [hex(i) for i in esp.MAC_address])

pyportal = PyPortal(esp=esp,
                    external_spi=spi,
                    default_bg="/background.bmp")

ampm_font = bitmap_font.load_font("/fonts/RobotoMono-18.bdf")
ampm_font.load_glyphs(b'ampAMP')
date_font = bitmap_font.load_font("/fonts/RobotoMono-18.bdf")
date_font.load_glyphs(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')
time_font = bitmap_font.load_font("/fonts/RobotoMono-72.bdf")
time_font.load_glyphs(b'0123456789:')

clock = Clock(pyportal)

for ap in esp.scan_networks():
    print("\t%s\t\tRSSI: %d" % (str(ap['ssid'], 'utf-8'), ap['rssi']))

    print("Connecting to AP...")
    while not esp.is_connected:
        try:
            esp.connect_AP(secrets['ssid'], secrets['password'])
        except RuntimeError as e:
            print("could not connect to AP, retrying: ",e)
            continue
print("Connected to", str(esp.ssid, 'utf-8'), "\tRSSI:", esp.rssi)
print("My IP address is", esp.pretty_ip(esp.ip_address))


wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(
    esp, secrets, debug = True)


# Set up a MiniMQTT Client
mqtt_client = MQTT(socket,
                   broker='io.adafruit.com',
                   username=secrets['aio_username'],
                   password=secrets['aio_key'],
                   network_manager=wifi)

mqtt_client.on_connect = connected
mqtt_client.on_disconnect = disconnected
mqtt_client.on_message = message

mqtt_client.connect()

switch = Switch(board.D4, pyportal)

second_timer = time.monotonic()
while True:
    #time.sleep(1)
    p = ts.touch_point
    if p:
        #if p[0] >= 140 and p[0] <= 170 and p[1] >= 160 and p[1] <= 220:
        # touch anywhere on the screen
        print("touch!")
        clock.adjust_backlight(True)
        switch.toggle()
        time.sleep(1)

    # poll once per second
    if time.monotonic() - second_timer >= 1.0:
        second_timer = time.monotonic()
        # Poll the message queue
        try:
            mqtt_client.loop()
        except RuntimeError:
            print("reconnecting wifi")
            mqtt_client.reconnect_wifi()

        # Update the PyPortal display
        clock.tick(time.monotonic())
