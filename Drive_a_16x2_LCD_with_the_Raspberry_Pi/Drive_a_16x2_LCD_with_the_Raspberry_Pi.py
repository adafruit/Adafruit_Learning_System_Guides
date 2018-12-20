import time
import board
import digitalio
import adafruit_character_lcd.character_lcd as characterlcd
import re
from subprocess import *
from time import sleep, strftime
from datetime import datetime

# Modify this if you have a different sized character LCD
lcd_columns = 16
lcd_rows = 2

# Raspberry Pi Pin Config:
lcd_rs = digitalio.DigitalInOut(board.D26)
lcd_en = digitalio.DigitalInOut(board.D19)
lcd_d7 = digitalio.DigitalInOut(board.D27)
lcd_d6 = digitalio.DigitalInOut(board.D22)
lcd_d5 = digitalio.DigitalInOut(board.D24)
lcd_d4 = digitalio.DigitalInOut(board.D25)
lcd_backlight = digitalio.DigitalInOut(board.D4)

# Initialise the lcd class
lcd = characterlcd.Character_LCD_Mono(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6,
                                      lcd_d7, lcd_columns, lcd_rows, lcd_backlight)

# looking for an active Ethernet or WiFi device
find_interface = "ip addr show | grep \"state UP\" | cut -d: -f2"

# find a live IP on the first LIVE network device
def parse_ip(device):
        find_ip = "ip addr show %s" % interface
        ip_parse = run_cmd(find_ip)
        for line in ip_parse.splitlines():
            if "inet " in line:
                ip = line.split(' ')[5]
                ip = ip.split('/')[0]
                return ip

def run_cmd(cmd):
        p = Popen(cmd, shell=True, stdout=PIPE)
        output = p.communicate()[0]
        return output.decode('ascii')

# wipe LCD screen before we start
lcd.clear()

while True:
        interface = run_cmd(find_interface)

        # date and time (line 1)
        lcd_line_1 = datetime.now().strftime('%b %d  %H:%M:%S\n') 

        # current ip address (line 2)
        lcd_line_2 = "IP " + parse_ip(interface)

        lcd.message = lcd_line_1 + lcd_line_2

        sleep(2)
