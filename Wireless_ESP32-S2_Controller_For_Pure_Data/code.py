# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

from os import getenv
import ipaddress
import wifi
import socketpool
import board
import simpleio
import adafruit_tsc2007
import adafruit_adxl34x

# Get WiFi details, ensure these are setup in settings.toml
ssid = getenv("CIRCUITPY_WIFI_SSID")
password = getenv("CIRCUITPY_WIFI_PASSWORD")

if None in [ssid, password]:
    raise RuntimeError(
        "WiFi settings are kept in settings.toml, "
        "please add them there. The settings file must contain "
        "'CIRCUITPY_WIFI_SSID', 'CIRCUITPY_WIFI_PASSWORD', "
        "at a minimum."
    )

#  I2C setup for STEMMA port
i2c = board.STEMMA_I2C()

#  touchscreen setup for TSC2007
irq_dio = None
tsc = adafruit_tsc2007.TSC2007(i2c, irq=irq_dio)

#  accelerometer setup
accelerometer = adafruit_adxl34x.ADXL343(i2c)
accelerometer.enable_tap_detection()

#  MIDI notes - 2 octaves of Cmaj7 triad
notes = [48, 52, 55, 59, 60, 64, 67, 71]
#  reads touch input
point = tsc.touch
#  accelerometer x coordinate
acc_x = 0
#  accelerometer y coordinate
acc_y = 0
#  last accelerometer x coordinate
last_accX = 0
#  last accelerometer y coordinate
last_accY = 0
#  mapped value for touchscreen x coordinate
x_map = 0
#  mapped value for touchscreen y coordinate
y_map = 0
#  last mapped value for touchscreen x coordinate
last_x = 0
#  last mapped value for touchscreen y coordinate
last_y = 0
#  state for whether synth is running
run = 0
#  tap detection state
last_tap = False
#  new value detection state
new_val = False

# URLs to fetch from
HOST = getenv("host")
PORT = 12345
TIMEOUT = 5
INTERVAL = 5
MAXBUF = 256

#  connect to WIFI
print(f"Connecting to {ssid}")
wifi.radio.connect(ssid, password)
print(f"Connected to {ssid}!")

pool = socketpool.SocketPool(wifi.radio)

ipv4 = ipaddress.ip_address(pool.getaddrinfo(HOST, PORT)[0][4][0])

buf = bytearray(MAXBUF)

print("Create TCP Client Socket")
s = pool.socket(pool.AF_INET, pool.SOCK_STREAM)

print("Connecting")
s.connect((HOST, PORT))

while True:
    #  tap detection
    #  if tap is detected and the synth is not running...
    if accelerometer.events["tap"] and not last_tap and not run:
        #  run is updated to 1
        run = 1
        #  last_tap is reset
        last_tap = True
        print("running")
        #  message is sent to Pd to start the synth
        #  all Pd messages need to end with a ";"
        size = s.send(str.encode(' '.join(["run", str(run), ";"])))
    #  if tap is detected and the synth is running...
    if accelerometer.events["tap"] and not last_tap and run:
        #  run is updated to 0
        run = 0
        #  last_tap is reset
        last_tap = True
        print("not running")
        #  message is sent to Pd to stop the synth
        #  all Pd messages need to end with a ";"
        size = s.send(str.encode(' '.join(["run", str(run), ";"])))
    #  tap detection debounce
    if not accelerometer.events["tap"] and last_tap:
        last_tap = False

    #  if the touchscreen is touched...
    if tsc.touched:
        #  point holds touch data
        point = tsc.touch
        #  x coordinate is remapped to 0 - 8
        x_map = simpleio.map_range(point["x"], 0, 4095, 0, 8)
        #  y coordinate is remapped to 0 - 8
        y_map = simpleio.map_range(point["y"], 0, 4095, 0, 8)

    #  accelerometer x value is remapped for synth filter
    acc_x = simpleio.map_range(accelerometer.acceleration[0], -10, 10, 450, 1200)
    #  accelerometer y value is remapped for synth filter
    acc_y = simpleio.map_range(accelerometer.acceleration[1], -10, 10, 250, 750)

    #  if any of the values are different from the last value...
    if x_map != last_x:
        #  last value is updated
        last_x = x_map
        #  new value is detected
        new_val = True
    if y_map != last_y:
        last_y = y_map
        new_val = True
    if int(acc_x) != last_accX:
        last_accX = int(acc_x)
        new_val = True
    if int(acc_y) != last_accY:
        last_accY = int(acc_y)
        new_val = True

    #  if a new value is detected...
    if new_val:
        #  note index is updated to y coordinate on touch screen
        note = notes[int(y_map)]
        #  message with updated values is sent via socket to Pd
        #  all Pd messages need to end with a ";"
        size = s.send(str.encode(' '.join(["x", str(x_map), ";",
                                           "y", str(y_map), ";",
                                           "aX", str(acc_x), ";",
                                           "aY", str(acc_y), ";",
                                           "n", str(note), ";"])))
        #  new_val is reset
        new_val = False
