"""
HalloWing GPS Tour Guide

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""
from math import sin, cos, radians, atan2, sqrt
import board
from digitalio import DigitalInOut, Direction, Pull
import displayio
import audioio
from busio import UART
import adafruit_gps
from adafruit_debouncer import Debouncer

uart = UART(board.TX, board.RX, baudrate=9600, timeout=3000)
gps = adafruit_gps.GPS(uart)

# Initialize the GPS module by changing what data it sends and at what rate.

# Turn on the basic GGA and RMC info (what you typically want)
gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')

# Set update rate to once a second (1hz) which is what you typically want.
gps.send_command(b'PMTK220,1000')

switch_io = DigitalInOut(board.SENSE)
switch_io.direction = Direction.INPUT
switch_io.pull = Pull.UP

switch = Debouncer(switch_io)

audio = audioio.AudioOut(board.A0)

backlight = DigitalInOut(board.TFT_BACKLIGHT)
backlight.direction = Direction.OUTPUT
backlight.value = False

splash = displayio.Group()
board.DISPLAY.show(splash)


def play_wave(filename):
    try:
        wave_file = open(filename, "rb")
        wave = audioio.WaveFile(wave_file)
        audio.play(wave)
        while audio.playing:
            pass
        wave_file.close()
    except OSError:
        pass

def show_image(filename):
    image_file = None
    try:
        image_file = open(filename, "rb")
    except OSError:
        image_file = open("missing.bmp", "rb")
    odb = displayio.OnDiskBitmap(image_file)
    face = displayio.Sprite(odb, pixel_shader=displayio.ColorConverter(), position=(0, 0))
    backlight.value = False
    splash.append(face)
    board.DISPLAY.wait_for_frame()
    backlight.value = True


def distance_between(location_1, location_2):
    """Find the distance betweeto a lat/long"""
    R = 3959                           # radius of Earth in miles
    lat1 = location_1[0]
    lat2 = location_2[0]
    lon1 = location_1[1]
    lon2 = location_2[1]
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = sin(delta_lat / 2) * sin(delta_lat / 2) + \
        cos(lat1) * cos(lat2) * \
        sin(delta_lon / 2) * sin(delta_lon / 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


previous_num = 0
previous_distance_code = 0
num = 0
image = None
name = None
detail = None
distance = 1000

show_image("welcome.bmp")

# File with place data
# lat,long,image-file,spoken-name-file,detail-file

locations = []
with open("locations.txt", "r") as f:
    for line in f:
        f_num, f_lat, f_lon, f_image, f_name, f_detail = line.split(',')
        lat_lon = (radians(float(f_lat)), radians(float(f_lon)))
        locations.append((int(f_num), lat_lon, f_image, f_name, f_detail))

while True:
    splash.pop()
    show_image("acquiring_fix.bmp")

    gps.update()
    while not gps.has_fix:
        gps.update()

    while gps.has_fix:
        gps.update()
        switch.update()

        # find the closest listed location
        if (gps.latitude is not None) and (gps.longitude is not None):
            here = (radians(gps.latitude), radians(gps.longitude))
            distance = 10000
            for loc in locations:
                f_dist = distance_between(loc[1], here)
                if f_dist < distance:
                    num, distance, image, name, detail = loc[0], f_dist, loc[2], loc[3], loc[4]

        # categorize the distance
        if distance < 0.1:
            distance_code = 1
        elif distance < 0.5:
            distance_code = 2
        elif distance < 1.0:
            distance_code = 3
        else:
            distance_code = 4

        # play the name when asked
        if switch.fell:
            play_wave(name)
            if previous_distance_code == 1 and distance_code == 1 and previous_num == num:
                play_wave(detail)

        # update the display if the location or distance category has changed
        # if it's relly close, show the image and play the details
        if num != previous_num or distance_code != previous_distance_code:
            play_wave("computerbeep.wav")
            previous_num = num
            previous_distance_code = distance_code
            if distance_code == 1:
                splash.pop()
                show_image(image)
                play_wave(name)
                play_wave(detail)
            elif distance_code == 2:
                splash.pop()
                show_image("green_circle.bmp")
            elif distance_code == 3:
                splash.pop()
                show_image("yellow_circle.bmp")
            else:
                splash.pop()
                show_image("red_circle.bmp")
