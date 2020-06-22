import board
import displayio
import busio
from digitalio import DigitalInOut
from analogio import AnalogIn
import neopixel
import adafruit_adt7410
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label
from adafruit_button import Button
import adafruit_touchscreen
import adafruit_minimqtt.adafruit_minimqtt as MQTT

# ------------- WiFi ------------- #

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# If you are using a board with pre-defined ESP32 Pins:
esp32_cs = DigitalInOut(board.ESP_CS)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
status_light = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=0.2)
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(esp, secrets, status_light)

# ------- Sensor Setup ------- #
# init. the temperature sensor
i2c_bus = busio.I2C(board.SCL, board.SDA)
adt = adafruit_adt7410.ADT7410(i2c_bus, address=0x48)
adt.high_resolution = True
temperature = "blaa"
# init. the light sensor
light_sensor = AnalogIn(board.LIGHT)

# init. the motion sensor
movement_sensor = DigitalInOut(board.D3)

button1_state = 0
button2_state = 0

# ------------- Screen eliments ------------- #

display = board.DISPLAY

# Backlight function
def set_backlight(val):
    """Adjust the TFT backlight.
    :param val: The backlight brightness. Use a value between ``0`` and ``1``, where ``0`` is
                off, and ``1`` is 100% brightness.
    """
    val = max(0, min(1.0, val))
    board.DISPLAY.auto_brightness = False
    board.DISPLAY.brightness = val


# Touchscreen setup
ts = adafruit_touchscreen.Touchscreen(
    board.TOUCH_XL,
    board.TOUCH_XR,
    board.TOUCH_YD,
    board.TOUCH_YU,
    calibration=((5200, 59000), (5800, 57000)),
    size=(320, 240),
)

# ---------- Set the font and preload letters ----------
# Be sure to put your font into a folder named "fonts".
font = bitmap_font.load_font("/fonts/Helvetica-Bold-16.bdf")
# This will preload the text images.
font.load_glyphs(b"abcdefghjiklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890- ()")

# ------------- User Inretface Eliments ------------- #

# Make the display context
splash = displayio.Group(max_size=200)
board.DISPLAY.show(splash)

# Make a background color fill
color_bitmap = displayio.Bitmap(320, 240, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0x3D0068
bg_sprite = displayio.TileGrid(color_bitmap, x=0, y=0, pixel_shader=color_palette)
splash.append(bg_sprite)

buttons = []
# Default button styling:
BUTTON_WIDTH = 100
BUTTON_HEIGHT = 100
BUTTON_MARGIN = 10

# Button Objects
button_1 = Button(
    x=BUTTON_MARGIN,
    y=BUTTON_MARGIN,
    width=BUTTON_WIDTH,
    height=BUTTON_HEIGHT,
    label="Button 1",
    label_font=font,
    style=Button.SHADOWROUNDRECT,
    label_color=0x505050,
    fill_color=0x9E9E9E,
    outline_color=0x464646,
)
buttons.append(button_1)

button_2 = Button(
    x=BUTTON_MARGIN,
    y=BUTTON_MARGIN * 2 + BUTTON_HEIGHT,
    width=BUTTON_WIDTH,
    height=BUTTON_HEIGHT,
    label="Button 2",
    label_font=font,
    style=Button.SHADOWROUNDRECT,
    label_color=0x505050,
    fill_color=0x9E9E9E,
    outline_color=0x464646,
)
buttons.append(button_2)

for b in buttons:
    splash.append(b.group)

# Text Label Objects
temperature_label = Label(font, text="temperature", color=0xE300D2, max_glyphs=40)
temperature_label.x = 130
temperature_label.y = 20
splash.append(temperature_label)

light_label = Label(font, text="lux", color=0xE300D2, max_glyphs=40)
light_label.x = 130
light_label.y = 40
splash.append(light_label)

motion_label = Label(font, text="motion", color=0xE300D2, max_glyphs=40)
motion_label.x = 130
motion_label.y = 60
splash.append(motion_label)

feed1_label = Label(font, text="MQTT feed1", color=0xE39300, max_glyphs=100)
feed1_label.x = 130
feed1_label.y = 130
splash.append(feed1_label)

feed2_label = Label(font, text="MQTT feed2", color=0x00DCE3, max_glyphs=100)
feed2_label.x = 130
feed2_label.y = 200
splash.append(feed2_label)

# ------------- MQTT Topic Setup ------------- #

mqtt_topic = "test/topic"
mqtt_temperature = "pyportal/temperature"
mqtt_lux = "pyportal/lux"
mqtt_PIR = "pyportal/pir"
mqtt_button1 = "pyportal/button1"
mqtt_button2 = "pyportal/button2"
mqtt_feed1 = "pyportal/feed1"
mqtt_feed2 = "pyportal/feed2"

# ------------- MQTT Functions ------------- #

# Define callback methods which are called when events occur
# pylint: disable=unused-argument, redefined-outer-name
def connect(client, userdata, flags, rc):
    # This function will be called when the client is connected
    # successfully to the broker.
    print("Connected to MQTT Broker!")
    print("Flags: {0}\n RC: {1}".format(flags, rc))


def disconnected(client, userdata, rc):
    # This method is called when the client is disconnected
    print("Disconnected from MQTT Broker!")


def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))


def publish(client, userdata, topic, pid):
    # This method is called when the client publishes data to a feed.
    print("Published to {0} with PID {1}".format(topic, pid))


def message(client, topic, message):
    """Method callled when a client's subscribed feed has a new
    value.
    :param str topic: The topic of the feed with a new value.
    :param str message: The new value
    """
    print("New message on topic {0}: {1}".format(topic, message))
    if topic == "pyportal/feed1":
        feed1_label.text = "Next Bus: {}".format(message)
    if topic == "pyportal/feed2":
        feed2_label.text = "Weather: \n    {}".format(message)
    if topic == "pyportal/button1":
        if message == "1":
            buttons[0].label = "ON"
            buttons[0].selected = False
            print("Button 1 ON")
        else:
            buttons[0].label = "OFF"
            buttons[0].selected = True
            print("Button 1 OFF")


# ------------- Network Connection ------------- #

# Connect to WiFi
print("Connecting to WiFi...")
wifi.connect()
print("Connected to WiFi!")

# Initialize MQTT interface with the esp interface
MQTT.set_socket(socket, esp)

# Set up a MiniMQTT Client
client = MQTT(
    broker=secrets["broker"],
    port=1883,
    username=secrets["user"],
    password=secrets["pass"],
)

# Connect callback handlers to client
client.on_connect = connect
client.on_disconnect = disconnected
client.on_subscribe = subscribe
client.on_publish = publish
client.on_message = message

print("Attempting to connect to %s" % client.broker)
client.connect()

print(
    "Subscribing to %s, %s, %s, and %s"
    % (mqtt_feed1, mqtt_feed2, mqtt_button1, mqtt_button2)
)
client.subscribe(mqtt_feed1)
client.subscribe(mqtt_feed2)
client.subscribe(mqtt_button1)
client.subscribe(mqtt_button2)

# ------------- Code Loop ------------- #
while True:
    # Poll the message queue
    client.loop()

    # Read sensor data and format
    light_value = lux = light_sensor.value
    light_label.text = "Light Sensor: {}".format(light_value)
    temperature = round(adt.temperature)
    temperature_label.text = "Temp Sensor: {}".format(temperature)
    movement_value = movement_sensor.value
    motion_label.text = "PIR Sensor: {}".format(movement_value)

    # Read display button press
    touch = ts.touch_point
    if touch:
        for i, b in enumerate(buttons):
            if b.contains(touch):
                print("Sending button%d pressed" % i)
                if i == 0:
                    # Toggle switch button type
                    if button1_state == 0:
                        button1_state = 1
                        b.label = "ON"
                        b.selected = False
                        print("Button 1 ON")
                    else:
                        button1_state = 0
                        b.label = "OFF"
                        b.selected = True
                        print("Button 1 OFF")
                    print("Sending button 1 state: ")
                    client.publish(mqtt_button1, button1_state)
                    # for debounce
                    while ts.touch_point:
                        print("Button 1 Pressed")
                if i == 1:
                    # Momentary button type
                    b.selected = True
                    print("Sending button 2 state: ")
                    client.publish(mqtt_button2, 1)
                    # for debounce
                    while ts.touch_point:
                        print("Button 2 Pressed")
                    print("Button 2 reliced")
                    print("Sending button 2 state: ")
                    client.publish(mqtt_button2, 0)
                    b.selected = False

    # Publish sensor data to MQTT
    print("Sending light sensor value: %d" % light_value)
    client.publish(mqtt_lux, light_value)

    print("Sending temperature value: %d" % temperature)
    client.publish(mqtt_temperature, temperature)

    print("Sending motion sensor value: %d" % movement_value)
    client.publish(mqtt_PIR, "{}".format(movement_value))
