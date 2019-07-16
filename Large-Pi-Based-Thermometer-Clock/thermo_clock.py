import glob
import time
import datetime
from Adafruit_LED_Backpack import SevenSegment
import board
import digitalio

switch_pin = digitalio.DigitalInOut(board.D18)
switch_pin.direction = digitalio.Direction.INPUT
switch_pin.pull = digitalio.Pull.UP

segment = SevenSegment.SevenSegment(address=0x70)
# Initialize the display. Must be called once before using the display.
segment.begin()

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
    segment.set_colon(False)
    temp = int(read_temp()[1]) # F
#   temp = int(read_temp()[0]) # C
    sign = (temp < 0)
    temp = abs(temp)
    digit_1 = int(temp % 10)
    temp = temp / 10
    digit_2 = int(temp % 10)
    temp = temp / 10
    digit_3 = int(temp % 10)
    if sign :
        segment.set_digit_raw(0, 0x40)      # - sign
    if digit_3 > 0 :
        segment.set_digit(0, digit_3)       # Hundreds
    else:
        segment.set_digit_raw(0, 0)
    if digit_2 > 0 :
        segment.set_digit(1, digit_2)       # Tens
    else:
        segment.set_digit_raw(1, 0)
    segment.set_digit(2, digit_1)           # Ones
    segment.set_digit_raw(3, 0x71) #F       # Temp units letter
#   segment.set_digit_raw(3, 0x39) #C

def display_time():
    now = datetime.datetime.now()
    hour = now.hour
    minute = now.minute
    second = now.second
    # Set hours
    segment.set_digit(0, int(hour / 10))        # Tens
    segment.set_digit(1, hour % 10)             # Ones
    # Set minutes
    segment.set_digit(2, int(minute / 10))      # Tens
    segment.set_digit(3, minute % 10)           # Ones
    # Toggle colon
    segment.set_colon(second % 2)               # Toggle colon at 1Hz


while True:
    segment.clear()
    if not switch_pin.value:
        display_temp()
    else :
        display_time()
    segment.write_display()
    time.sleep(0.5)
