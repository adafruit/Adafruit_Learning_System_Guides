# SPDX-FileCopyrightText: 2023 Carter N. for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import board
import digitalio
import adafruit_si4713
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import st7789
import mpd

#--| User Config |-----------------------------------
FREQ = 89.00
PLAYLIST = "test"
STATION_NAME = "PiPyPirate Radio"
UPDATE_RATE = 0.5
#----------------------------------------------------

#==| SETUP |=========================================================

# Display
disp = st7789.ST7789(
    board.SPI(),
    height=240,
    y_offset=80,
    rotation=180,
    cs=digitalio.DigitalInOut(board.CE0),
    dc=digitalio.DigitalInOut(board.D25),
    rst=digitalio.DigitalInOut(board.D24),
    baudrate=64000000,
)

backlight = digitalio.DigitalInOut(board.D22)
backlight.switch_to_output()
backlight.value = True

background = Image.open("radio_bg.png")
STAT_FNT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf", 55)
STAT_CLR = (30, 100, 200)
INFO_FNT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
ARTS_CLR = (0, 100, 0)
ALBM_CLR = (0, 100, 0)
TITL_CLR = (0, 100, 0)
PROG_CLR = (0, 100, 0)

# Buttons
button1 = digitalio.DigitalInOut(board.D23)
button1.switch_to_input(pull=digitalio.Pull.UP)
button2 = digitalio.DigitalInOut(board.D24)
button2.switch_to_input(pull=digitalio.Pull.UP)

# Radio
radio = adafruit_si4713.SI4713(
    board.I2C(),
    reset=digitalio.DigitalInOut(board.D26),
    timeout_s = 0.5
)
radio.tx_frequency_khz = int(FREQ * 1000)
radio.tx_power = 115
radio.configure_rds(0xADAF, station=STATION_NAME.encode())

# MPD
mpc = mpd.MPDClient()
mpc.connect("localhost", 6600)
mpc.stop()
mpc.clear()
mpc.load(PLAYLIST)
mpc.play()
mpc.repeat(1)
#====================================================================

def button1_handler():
    if status['state'] == 'play':
        mpc.pause()
    else:
        mpc.play()

def button2_handler():
    mpc.next()

def update_display():
    image = background.copy()
    draw = ImageDraw.Draw(image)

    draw.text(
        (150, 20),
        "{:>5.1f}".format(FREQ),
        anchor="mt",
        font=STAT_FNT,
        fill=STAT_CLR
    )

    if status['state'] == 'play':
        r = 10 * (1 + int(time.monotonic() % 3))
        draw.arc( (30-r, 20-r, 30+r, 20+r),
            120, 60,
            fill = (0, 0, 0),
            width = 3
        )

    info = mpc.currentsong()
    artist = info.get('artist', 'unknown')
    album = info.get('album', 'unknown')
    song = info.get('title', 'unknown')
    draw.text( (5, 150), artist, font=INFO_FNT, fill=ARTS_CLR )
    draw.text( (5, 170), album, font=INFO_FNT, fill=ALBM_CLR)
    draw.text( (5, 190), song, font=INFO_FNT, fill=TITL_CLR)
    rds_info = "{}:{}:{}".format(artist, album, song)
    radio.rds_buffer = rds_info.encode()

    perc = float(status['elapsed']) / float(status['duration'])
    draw.rectangle( (5, 215, 235, 230), outline=PROG_CLR)
    draw.rectangle (
        (5, 215, 5 + int(230*perc), 230),
        fill=PROG_CLR
    )

    disp.image(image)

last_update = time.monotonic()

print("Now broadcasting {} on {}FM".format(STATION_NAME, FREQ))

while True:
    now = time.monotonic()
    try:
        status = mpc.status()
    except ConnectionError:
        mpc.connect("localhost", 6600)
        status = mpc.status()
    if not button1.value:
        button1_handler()
        while not button1.value:
            time.sleep(0.001)
    if not button2.value:
        button2_handler()
        while not button2.value:
            time.sleep(0.001)
    if now - last_update > UPDATE_RATE:
        update_display()
        last_update = now
