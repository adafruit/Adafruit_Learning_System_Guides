# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import json
import board
from digitalio import DigitalInOut, Direction, Pull
from adafruit_ht16k33.segments import Seg14x4
from cedargrove_nau7802 import NAU7802
from calibration import calibration
import rtc
import socketpool
import wifi
import adafruit_ntp
from adafruit_azureiot import IoTCentralDevice

#  I2C setup with STEMMA port
i2c = board.STEMMA_I2C()
#  alphanumeric segment displpay setup
#  using two displays together
display = Seg14x4(i2c, address=(0x70, 0x71))
#  start-up text
display.print("*HELLO* ")
#  button LEDs
blue = DigitalInOut(board.A1)
blue.direction = Direction.OUTPUT
green = DigitalInOut(board.A3)
green.direction = Direction.OUTPUT
#  buttons setup
blue_btn = DigitalInOut(board.A0)
blue_btn.direction = Direction.INPUT
blue_btn.pull = Pull.UP
green_btn = DigitalInOut(board.A2)
green_btn.direction = Direction.INPUT
green_btn.pull = Pull.UP
# nau7802 setup
nau7802 = NAU7802(board.STEMMA_I2C(), address=0x2A, active_channels=2)
nau7802.gain = 128
enabled = nau7802.enable(True)

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

print("Connecting to WiFi...")
wifi.radio.connect(secrets["ssid"], secrets["password"])

print("Connected to WiFi!")
#  check system time
if time.localtime().tm_year < 2022:
    print("Setting System Time in UTC")
    pool = socketpool.SocketPool(wifi.radio)
    ntp = adafruit_ntp.NTP(pool, tz_offset=-4)
    # NOTE: This changes the system time so make sure you aren't assuming that time
    # doesn't jump.
    rtc.RTC().datetime = ntp.datetime

else:
    print("Year seems good, skipping set time.")

# Create an IoT Central device client and connect
esp = None
pool = socketpool.SocketPool(wifi.radio)
device = IoTCentralDevice(
    pool, esp, secrets['id_scope'], secrets['device_id'], secrets['device_primary_key']
)
display.fill(0)
display.print("DIALING*")
print("Connecting to Azure IoT Central...")
device.connect()
display.print("CONNECTD")
print("Connected to Azure IoT Central!")
device.disconnect()
print("Disconnected")
#  zeroing function
def zero_channel():
    """Initiate internal calibration for current channel; return raw zero
    offset value. Use when scale is started, a new channel is green_btned, or to
    adjust for measurement drift. Remove weight and tare from load cell before
    executing."""
    blue.value = True
    print(
        "channel %1d calibrate.INTERNAL: %5s"
        % (nau7802.channel, nau7802.calibrate("INTERNAL"))
    )
    blue.value = False
    print(
        "channel %1d calibrate.OFFSET:   %5s"
        % (nau7802.channel, nau7802.calibrate("OFFSET"))
    )
    blue.value = True
    zero_offset = read_raw_value(100)  # Read 100 samples to establish zero offset
    print("...channel %1d zeroed" % nau7802.channel)
    blue.value = False
    return zero_offset
#  read raw value function
def read_raw_value(samples=100):
    """Read and average consecutive raw sample values. Return average raw value."""
    sample_sum = 0
    sample_count = samples
    while sample_count > 0:
        if nau7802.available:
            sample_sum = sample_sum + nau7802.read()
            sample_count -= 1
    return int(sample_sum / samples)
#  function for finding the average of an array
def find_average(num):
    count = 0
    for n in num:
        count = count + n
    average = count / len(num)
    return average
#  calibration function
def calculateCalibration(array):
    for _ in range(10):
        blue.value = True
        green.value = False
        nau7802.channel = 1
        print("channel %1.0f raw value: %7.0f" % (nau7802.channel, abs(read_raw_value())))
        array.append(abs(read_raw_value()))
        blue.value = False
        green.value = True
        time.sleep(1)
    green.value = False
    avg = find_average(array)
    return avg
#  blink LED function
def blink(led, amount, count):
    for _ in range(count):
        led.value = True
        time.sleep(amount)
        led.value = False
        time.sleep(amount)
#  send data to azure with ounces and grams
def send_to_azure(current_oz, current_grams):
    #  turn on green LED
    green.value = True
    display.print("DIALING*")
    #  connect to azure
    device.reconnect()
    #  turn on blue LED
    blue.value = True
    display.print("CONNECTD")
    time.sleep(1)
    display.print("SENDING!")
    #  send JSON of ounces and grams
    message = {"Ounces": current_oz, "Grams": current_grams}
    device.send_telemetry(json.dumps(message))
    display.fill(0)
    display.print("SENT!")
    #  disconnect and turn off LEDs
    device.disconnect()
    green.value = False
    blue.value = False
#  zeroing on startup
display.fill(0)
display.marquee("CLEAR SCALE CLEAR", 0.3, False)
time.sleep(2)
display.fill(0)
display.print("ZEROING")
time.sleep(3)
#  zeroing each channel
nau7802.channel = 1
zero_channel()  # Calibrate and zero channel
display.fill(0)
display.print("STARTING")

#  variables and states
clock = time.monotonic() #  time.monotonic() device
reset_clock = time.monotonic()
long_clock = time.monotonic()
mode = "run"
mode_names = ["SHOW OZ?", "   GRAMS?", "   ZERO?", "CALIBRTE", " OFFSET?", "TO AZURE"]
stage = 0
zero_stage = 0
weight_avg = 0
zero_avg = 0
show_oz = True
show_grams = False
zero_out = False
calibrate_mode = False
blue_btn_pressed = False
green_btn_pressed = False
run_mode = True
avg_read = []
avg_grams = []
avg_oz = []
values = []
val_offset = 0
avg_values = []

#  initial reading from the scale
for w in range(5):
    nau7802.channel = 1
    value = read_raw_value()
    #  takes value reading and divides with by the offset value
    #  to get the weight in grams
    grams = value / calibration['offset_val']
    avg_read.append(grams)
    if len(avg_read) > 4:
        the_avg = find_average(avg_read)
        oz = the_avg / 28.35
        display.print("   %0.1f oz" % oz)
        avg_read.clear()
    time.sleep(1)

while True:
    #  button debouncing
    if blue_btn.value and blue_btn_pressed:
        blue_btn_pressed = False
    if green_btn.value and green_btn_pressed:
        green_btn_pressed = False
        green.value = False
    #  default run mode
    #  checks NAU7802 every 2 seconds
    if run_mode is True and (time.monotonic() - clock) > 2:
        nau7802.channel = 1
        value = read_raw_value()
        value = abs(value) - val_offset
        values.append(value)
        #  takes value reading and divides with by the offset value
        #  to get the weight in grams
        grams = value / calibration['offset_val']
        oz = grams / 28.35
        avg_grams.append(grams)
        avg_oz.append(oz)
        if show_oz is True:
            #  append reading
            avg_read.append(oz)
            label = "oz"
        if show_grams is True:
            avg_read.append(grams)
            label = "g"
        if len(avg_read) > 10:
            the_avg = find_average(avg_read)
            the_grams = find_average(avg_grams)
            the_ounces = find_average(avg_oz)
            display.print("   %0.1f %s" % (the_avg, label))
            avg_read.clear()
            avg_grams.clear()
            avg_oz.clear()
            val_offset += 10
        clock = time.monotonic()
    if (time.monotonic() - reset_clock) > 43200:
        run_mode = False
        show_oz = False
        show_grams = False
        zero_out = True
        reset_clock = time.monotonic()
    #  if you press the change mode button
    if (not green_btn.value and not green_btn_pressed) and run_mode:
        green.value = True
        #  disables run mode (stops weighing)
        run_mode = False
        show_oz = False
        show_grams = False
        #  mode is set to 0
        mode = 0
        #  display shows the mode option
        display.print(mode_names[mode])
        blue.value = True
        green_btn_pressed = True
    #  advances through the modes menu
    if (not green_btn.value and not green_btn_pressed) and mode != "run":
        green.value = True
        #  counts up to 4 and loops back to 0
        mode = (mode+1) % 6
        #  updates display
        display.print(mode_names[mode])
        green_btn_pressed = True
    #  if you select show_oz
    if (not blue_btn.value and not blue_btn_pressed) and mode == 0:
        #  show_oz is set as the state
        show_oz = True
        label = "oz"
        blue.value = False
        #  goes back to weighing mode
        mode = "run"
        blue_btn_pressed = True
        display.print("   %0.1f %s" % (the_avg, label))
        run_mode = True
    #  if you select show_grams
    if (not blue_btn.value and not blue_btn_pressed) and mode == 1:
        #  show_grams is set as the state
        show_grams = True
        label = "g"
        blue.value = False
        #  goes back to weighing mode
        mode = "run"
        blue_btn_pressed = True
        display.print("   %0.1f %s" % (the_avg, label))
        run_mode = True
    #  if you select zero_out
    if (not blue_btn.value and not blue_btn_pressed) and mode == 2:
        #  zero_out is set as the state
        #  can zero out the scale without full recalibration
        zero_out = True
        blue.value = False
        mode = "run"
        blue_btn_pressed = True
    #  if you select calibrate_mode
    if (not blue_btn.value and not blue_btn_pressed) and mode == 3:
        #  calibrate_mode is set as the state
        #  starts up the calibration process
        calibrate_mode = True
        blue.value = False
        mode = "run"
        blue_btn_pressed = True
    #  if you select the offset
    if (not blue_btn.value and not blue_btn_pressed) and mode == 4:
        #  displays the curren offset value stored in the code
        blue.value = False
        display.fill(0)
        display.print("%0.4f" % calibration['offset_val'])
        time.sleep(5)
        mode = "run"
        #  goes back to weighing mode
        show_oz = True
        label = "oz"
        display.print("   %0.1f %s" % (the_avg, label))
        run_mode = True
        blue_btn_pressed = True
    if (not blue_btn.value and not blue_btn_pressed) and mode == 5:
        blue.value = False
        display.fill(0)
        #  sends data to azure
        send_to_azure(the_ounces, the_grams)
        time.sleep(1)
        mode = "run"
        #  goes back to weighing mode
        show_oz = True
        label = "oz"
        display.print("   %0.1f %s" % (the_avg, label))
        run_mode = True
        blue_btn_pressed = True
    #  if the zero_out state is true
    if zero_out and zero_stage == 0:
        blue_btn_pressed = True
        #  clear the scale for zeroing
        display.fill(0)
        display.print("REMOVE ")
        zero_stage = 1
        blue.value = True
        green.value = True
    if (not blue_btn.value and not blue_btn_pressed) and zero_stage == 1:
        green.value = False
        #  updates display
        display.fill(0)
        display.print("ZEROING")
        blue.value = False
        #  runs zero_channel() function on both channels
        nau7802.channel = 1
        zero_channel()
        display.fill(0)
        display.print("ZEROED ")
        zero_out = False
        zero_stage = 0
        #  goes into weighing mode
        val_offset = 0
        run_mode = True
        show_oz = True
        label = "oz"
        display.print("   %0.1f %s" % (the_avg, label))
    #  the calibration process
    #  each step is counted in stage
    #  blue button is pressed to advance to the next stage
    if calibrate_mode is True and stage == 0:
        blue_btn_pressed = True
        #  clear the scale for zeroing
        display.fill(0)
        display.print("REMOVE ")
        stage = 1
        blue.value = True
    #  stage 2
    if (not blue_btn.value and not blue_btn_pressed) and stage == 1:
        blue_btn_pressed = True
        #  runs the zero out function
        display.fill(0)
        display.print("ZEROING")
        blue.value = False
        nau7802.channel = 1
        zero_channel()
        display.fill(0)
        display.print("ZEROED ")
        stage = 2
        blue.value = True
    #  stage 3
    if (not blue_btn.value and not blue_btn_pressed) and stage == 2:
        blue_btn_pressed = True
        blue.value = False
        display.print("STARTING")
        blink(blue, 0.5, 3)
        zero_readings = []
        display.print("AVG ZERO")
        #  runs the calculateCallibration function
        #  takes 10 raw readings, stores them into an array and gets an average
        zero_avg = calculateCalibration(zero_readings)
        stage = 3
        display.fill(0)
        display.print("DONE")
        blue.value = True
    #  stage 4
    if (not blue_btn.value and not blue_btn_pressed) and stage == 3:
        #  place the known weight item
        #  item's weight matches calibration['weight'] in grams
        blue_btn_pressed = True
        blue.value = False
        display.fill(0)
        display.print("PUT ITEM")
        stage = 4
        blue.value = True
    #  stage 5
    if (not blue_btn.value and not blue_btn_pressed) and stage == 4:
        blue_btn_pressed = True
        blue.value = False
        display.fill(0)
        display.print("WEIGHING")
        weight_readings = []
        #  weighs the item 10 times, stores the readings in an array & averages them
        weight_avg = calculateCalibration(weight_readings)
        #  calculates the new offset value
        calibration['offset_val'] = (weight_avg-zero_avg) / calibration['weight']
        display.marquee("%0.2f - CALIBRATED " % calibration['offset_val'], 0.3, False)
        stage = 5
        display.fill(0)
        display.print("DONE")
        blue.value = True
    #  final stage
    if (not blue_btn.value and not blue_btn_pressed) and stage == 5:
        blue_btn_pressed = True
        zero_readings.clear()
        weight_readings.clear()
        calibrate_mode = False
        blue.value = False
        #  goes back into weighing mode
        show_oz = True
        label = "oz"
        display.print("   %0.1f %s" % (the_avg, label))
        val_offset = 0
        run_mode = True
        #  resets stage
        stage = 0
