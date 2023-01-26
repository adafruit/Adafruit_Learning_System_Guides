# SPDX-FileCopyrightText: 2018 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# Modified by Jonathan Seyfert, 2022-01-22
# to keep code from crashing when WiFi or IP is unavailable
from subprocess import Popen, PIPE
from time import sleep, perf_counter
from datetime import datetime
import board
import digitalio
import adafruit_character_lcd.character_lcd as characterlcd

# Modify this if you have a different sized character LCD
lcd_columns = 16
lcd_rows = 2

# compatible with all versions of RPI as of Jan. 2019
# v1 - v3B+
lcd_rs = digitalio.DigitalInOut(board.D22)
lcd_en = digitalio.DigitalInOut(board.D17)
lcd_d4 = digitalio.DigitalInOut(board.D25)
lcd_d5 = digitalio.DigitalInOut(board.D24)
lcd_d6 = digitalio.DigitalInOut(board.D23)
lcd_d7 = digitalio.DigitalInOut(board.D18)


# Initialise the lcd class
lcd = characterlcd.Character_LCD_Mono(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6,
                                      lcd_d7, lcd_columns, lcd_rows)

# looking for an active Ethernet or WiFi device
def find_interface():
#    dev_name = 0 # sets dev_name so that function does not return Null and crash code
    find_device = "ip addr show"
    interface_parse = run_cmd(find_device)
    for line in interface_parse.splitlines():
        if "state UP" in line:
            dev_name = line.split(':')[1]
            return dev_name
    return 1 # avoids returning Null if "state UP" doesn't exist

# find an active IP on the first LIVE network device
def parse_ip():
    if interface == 1: # if true, no device is in "state UP", skip IP check
        return "not assigned " # display "IP not assigned"
    ip = "0"
    find_ip = "ip addr show %s" % interface
    ip_parse = run_cmd(find_ip)
    for line in ip_parse.splitlines():
        if "inet " in line:
            ip = line.split(' ')[5]
            ip = ip.split('/')[0]
            return ip # returns IP address, if found
    return "pending      " # display "IP pending" when "state UP", but no IPv4 address yet

# run unix shell command, return as ASCII
def run_cmd(cmd):
    p = Popen(cmd, shell=True, stdout=PIPE)
    output = p.communicate()[0]
    return output.decode('ascii')

# wipe LCD screen before we start
lcd.clear()


# before we start the main loop - detect active network device and ip address
# set timer to = perf_counter(), for later use in IP update check
interface = find_interface()
ip_address = parse_ip()
timer = perf_counter()

while True:
    # check for new IP addresses, at a slower rate than updating the clock
    if perf_counter() - timer >= 15:
        interface = find_interface()
        ip_address = parse_ip()
        timer = perf_counter()

    # date and time
    lcd_line_1 = datetime.now().strftime('%b %d  %H:%M:%S\n')

    # current ip address
    lcd_line_2 = "IP " + ip_address

    # combine both lines into one update to the display
    lcd.message = lcd_line_1 + lcd_line_2

    sleep(1)
