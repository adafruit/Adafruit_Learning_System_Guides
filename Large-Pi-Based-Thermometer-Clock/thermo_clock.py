import glob
import time
import datetime
from adafruit_ht16k33 import segments
import board
import busio
import digitalio

switch_pin = digitalio.DigitalInOut(board.D18)
switch_pin.direction = digitalio.Direction.INPUT
switch_pin.pull = digitalio.Pull.UP

# Create the I2C interface.
i2c = busio.I2C(board.SCL, board.SDA)

# Create the LED segment class.
# This creates a 7 segment 4 character display:
display = segments.Seg7x4(i2c)

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines

def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_c, temp_f

def display_temp():
    temp = read_temp()[1] # F
#   temp = read_temp()[0] # C
    display.print(int(temp))

def display_time():
    now = datetime.datetime.now()
    hour = now.hour
    minute = now.minute
    second = now.second
    clock = int('%i%i' % (hour,minute))          # concat hour + minute
    display.print(clock)

    # Toggle colon when displaying time
    if second % 2:
        display.print(':')                      # Enable colon every other second
    else:
        display.print(';')                      # Turn off colon

display.fill(0)

while True:
    if not switch_pin.value:
        display_temp()
    else:
        display_time()
    time.sleep(0.5)
