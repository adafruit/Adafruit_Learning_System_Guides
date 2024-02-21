# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import json
import time
import digitalio
import supervisor
import simpleio
import vectorio
import board
import terminalio
import rtc
import socketpool
import wifi
import displayio
import adafruit_ntp
from adafruit_display_text import bitmap_label,  wrap_text_to_lines
from adafruit_bitmap_font import bitmap_font
from adafruit_azureiot import IoTHubDevice
import adafruit_bme680
from adafruit_lc709203f import LC709203F, PackSize

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

print("Connecting to WiFi...")
wifi.radio.connect(secrets["ssid"], secrets["password"])

print("Connected to WiFi!")

#  ntp clock - update tz_offset to your timezone
pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=0)
rtc.RTC().datetime = ntp.datetime

if time.localtime().tm_year < 2022:
    print("Setting System Time in UTC")
    rtc.RTC().datetime = ntp.datetime

else:
    print("Year seems good, skipping set time.")

esp = None
pool = socketpool.SocketPool(wifi.radio)
# Create an IoT Hub device client and connect
device = IoTHubDevice(pool, esp, secrets["device_connection_string"])

print("Connecting to Azure IoT Hub...")

# Connect to IoT Central
device.connect()

print("Connected to Azure IoT Hub!")

cal = ntp.datetime
year = cal[0]
mon = cal[1]
day = cal[2]
hour = cal[3]
minute = cal[4]

i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c, debug=False)

# change this to match the location's pressure (hPa) at sea level
bme680.sea_level_pressure = 1013.25

temperature_offset = -5

# Create sensor object, using the board's default I2C bus.
i2c = board.I2C()  # uses board.SCL and board.SDA
# i2c = board.STEMMA_I2C()  # For using the built-in STEMMA QT connector on a microcontroller
battery_monitor = LC709203F(i2c)

# Update to match the mAh of your battery for more accurate readings.
# Can be MAH100, MAH200, MAH400, MAH500, MAH1000, MAH2000, MAH3000.
# Choose the closest match. Include "PackSize." before it, as shown.
battery_monitor.pack_size = PackSize.MAH2000

temp = int((bme680.temperature * 9/5) + (32 + temperature_offset))
humidity = int(bme680.relative_humidity)
pressure = int(bme680.pressure)
battery = battery_monitor.cell_percent

#  setup boot button as input
button = digitalio.DigitalInOut(board.BUTTON)
button.switch_to_input(pull=digitalio.Pull.UP)

#  display setup
display = board.DISPLAY

palette0 = displayio.Palette(2)
palette0[0] = 0x00FF00
palette0[1] = 0xFF0000

#  load bitmap
bitmap = displayio.OnDiskBitmap("/bmeTFT.bmp")
tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
group = displayio.Group()
group.append(tile_grid)
#  rectangle for battery life monitor
#  vectorio allows for resizing in the loop
rect = vectorio.Rectangle(pixel_shader=palette0, width=22, height=10, x=12, y=116, color_index = 0)
group.append(rect)
#  bitmap font
font_file = "/roundedHeavy-26.bdf"
font = bitmap_font.load_font(font_file)
#  text elements
temp_text = bitmap_label.Label(font, text="%0.1f° F" % temp, x=20, y=80, color=0xFFFFFF)
humid_text = bitmap_label.Label(font, text="%0.1f %%" % humidity, x=95, y=80, color=0xFFFFFF)
press_text = bitmap_label.Label(font, text="%0.2f" % pressure, x=170, y=80, color=0xFFFFFF)
time_text = bitmap_label.Label(terminalio.FONT,
            text="\n".join(wrap_text_to_lines
            ("Data sent on %s/%s/%s at %s:%s" % (mon,day,year,hour,minute), 20)),
            x=125, y=105, color=0xFFFFFF)
group.append(temp_text)
group.append(humid_text)
group.append(press_text)
group.append(time_text)
display.root_group = group

#  clock to count down to sending data to Azure
azure_clock = 500
#  clock to count down to updating TFT
feather_clock = 30
#  button debounce state
button_pressed = False

while True:
    try:
        if button.value and button_pressed:
            button_pressed = False
        if not button.value and not button_pressed:
            print("getting msg")
			#  pack message
            message = {"Temperature": temp,
                       "Humidity": humidity,
                       "Pressure": pressure,
                       "BatteryPercent": battery,
                       "FeatherConnected": 1}
            print("sending json")
            device.send_device_to_cloud_message(json.dumps(message))
            print("data sent")
        #  read BME sensor
        temp = int((bme680.temperature * 9/5) + (32 + temperature_offset))
        humidity = int(bme680.relative_humidity)
        pressure = int(bme680.pressure)
		#  log battery %
        battery = battery_monitor.cell_percent
		#  map range of battery charge to rectangle size on screen
        battery_display = round(simpleio.map_range(battery, 0, 100, 0, 22))
		#  update rectangle to reflect battery charge
        rect.width = int(battery_display)
		#  if below 20%, change rectangle color to red
        if battery_monitor.cell_percent < 20:
            rect.color_index = 1
		#  when the azure clock runs out
        if azure_clock > 500:
            print("getting ntp date/time")
            cal = ntp.datetime
            year = cal[0]
            mon = cal[1]
            day = cal[2]
            hour = cal[3]
            minute = cal[4]
            time.sleep(2)
            print("getting msg")
			#  pack message
            message = {"Temperature": temp,
                       "Humidity": humidity,
                       "Pressure": pressure,
                       "BatteryPercent": battery}
            print("sending json")
            device.send_device_to_cloud_message(json.dumps(message))
            print("data sent")
            clock_view = "%s:%s" % (hour, minute)
            if minute < 10:
                clock_view = "%s:0%s" % (hour, minute)
            print("updating time text")
            time_text.text="\n".join(wrap_text_to_lines
            ("Data sent on %s/%s/%s at %s" % (mon,day,year,clock_view), 20))
			#  reset azure clock
            azure_clock = 0
        #  when the feather clock runs out
        if feather_clock > 30:
            print("updating screen")
            temp_text.text = "%0.1f° F" % temp
            humid_text.text = "%0.1f %%" % humidity
            press_text.text = "%0.2f" % pressure
			#  reset feather clock
            feather_clock = 0
		#  if no clocks are running out
		#  increase counts by 1
        else:
            feather_clock += 1
            azure_clock += 1
		#  ping azure
        device.loop()
    #  if something disrupts the loop, reconnect
    # pylint: disable=broad-except
    except (ValueError, RuntimeError, OSError, ConnectionError) as e:
        print("Network error, reconnecting\n", str(e))
        time.sleep(60)
        supervisor.reload()
        continue
	#  delay
    time.sleep(1)
