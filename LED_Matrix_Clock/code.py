# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

'''LED Matrix Alarm Clock'''
import os
import ssl
import time
import random
import wifi
import socketpool
import microcontroller
import board
import audiocore
import audiobusio
import audiomixer
import adafruit_is31fl3741
from adafruit_is31fl3741.adafruit_rgbmatrixqt import Adafruit_RGBMatrixQT
import adafruit_ntp
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff
from rainbowio import colorwheel
from adafruit_seesaw import digitalio, rotaryio, seesaw
from adafruit_debouncer import Button

timezone = -4 # your timezone offset
alarm_hour = 12 # hour is 24 hour for alarm to denote am/pm
alarm_min = 00 # minutes
alarm_volume = 1 # float 0.0 to 1.0
hour_12 = True # 12 hour or 24 hour time
no_alarm_plz = False
BRIGHTNESS = 128 # led brightness (0-255)

# I2S pins for Audio BFF
DATA = board.A0
LRCLK = board.A1
BCLK = board.A2

# connect to WIFI
wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}")

context = ssl.create_default_context()
pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=timezone, cache_seconds=3600)

# Initialize I2C
i2c = board.STEMMA_I2C()

# Initialize both matrix displays
matrix1 = Adafruit_RGBMatrixQT(i2c, address=0x30, allocate=adafruit_is31fl3741.PREFER_BUFFER)
matrix2 = Adafruit_RGBMatrixQT(i2c, address=0x31, allocate=adafruit_is31fl3741.PREFER_BUFFER)
matrix1.global_current = 0x05
matrix2.global_current = 0x05
matrix1.set_led_scaling(BRIGHTNESS)
matrix2.set_led_scaling(BRIGHTNESS)
matrix1.enable = True
matrix2.enable = True
matrix1.fill(0x000000)
matrix2.fill(0x000000)
matrix1.show()
matrix2.show()

audio = audiobusio.I2SOut(BCLK, LRCLK, DATA)
wavs = []
for filename in os.listdir('/'):
    if filename.lower().endswith('.wav') and not filename.startswith('.'):
        wavs.append("/"+filename)
mixer = audiomixer.Mixer(voice_count=1, sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True, buffer_size=32768)
mixer.voice[0].level = alarm_volume
wav_filename = wavs[random.randint(0, (len(wavs))-1)]
wav_file = open(wav_filename, "rb")
audio.play(mixer)

def open_audio():
    n = wavs[random.randint(0, (len(wavs))-1)]
    f = open(n, "rb")
    w = audiocore.WaveFile(f)
    return w

seesaw = seesaw.Seesaw(i2c, addr=0x36)
seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
ss_pin = digitalio.DigitalIO(seesaw, 24)
button = Button(ss_pin, long_duration_ms=1000)

button_held = False
encoder = rotaryio.IncrementalEncoder(seesaw)
last_position = 0

# Simple 5x7 font bitmap patterns for digits 0-9
FONT_5X7 = {
    '0': [
        0b01110,
        0b10001,
        0b10011,
        0b10101,
        0b11001,
        0b10001,
        0b01110
    ],
    '1': [
        0b00100,
        0b01100,
        0b00100,
        0b00100,
        0b00100,
        0b00100,
        0b01110
    ],
    '2': [
        0b01110,
        0b10001,
        0b00001,
        0b00010,
        0b00100,
        0b01000,
        0b11111
    ],
    '3': [
        0b11111,
        0b00010,
        0b00100,
        0b00010,
        0b00001,
        0b10001,
        0b01110
    ],
    '4': [
        0b00010,
        0b00110,
        0b01010,
        0b10010,
        0b11111,
        0b00010,
        0b00010
    ],
    '5': [
        0b11111,
        0b10000,
        0b11110,
        0b00001,
        0b00001,
        0b10001,
        0b01110
    ],
    '6': [
        0b00110,
        0b01000,
        0b10000,
        0b11110,
        0b10001,
        0b10001,
        0b01110
    ],
    '7': [
        0b11111,
        0b00001,
        0b00010,
        0b00100,
        0b01000,
        0b01000,
        0b01000
    ],
    '8': [
        0b01110,
        0b10001,
        0b10001,
        0b01110,
        0b10001,
        0b10001,
        0b01110
    ],
    '9': [
        0b01110,
        0b10001,
        0b10001,
        0b01111,
        0b00001,
        0b00010,
        0b01100
    ],
    ' ': [
        0b00000,
        0b00000,
        0b00000,
        0b00000,
        0b00000,
        0b00000,
        0b00000
    ]
}

def draw_pixel_flipped(matrix, x, y, color):
    """Draw a pixel with 180-degree rotation"""
    flipped_x = 12 - x
    flipped_y = 8 - y
    if 0 <= flipped_x < 13 and 0 <= flipped_y < 9:
        matrix.pixel(flipped_x, flipped_y, color)

def draw_char(matrix, char, x, y, color):
    """Draw a character at position x,y on the specified matrix (flipped)"""
    if char in FONT_5X7:
        bitmap = FONT_5X7[char]
        for row in range(7):
            for col in range(5):
                if bitmap[row] & (1 << (4 - col)):
                    draw_pixel_flipped(matrix, x + col, y + row, color)

def draw_colon_split(y, color):
    """Draw a split colon with 2x2 dots between the displays"""
    # Top dot - left half on matrix1, right half on matrix2
    draw_pixel_flipped(matrix1, 12, y+1, color)  # Top-left
    draw_pixel_flipped(matrix1, 12, y + 2, color)  # Bottom-left
    draw_pixel_flipped(matrix2, 0, y+1, color)   # Top-right
    draw_pixel_flipped(matrix2, 0, y + 2, color)   # Bottom-right

    # Bottom dot - left half on matrix1, right half on matrix2
    draw_pixel_flipped(matrix1, 12, y + 4, color)  # Top-left
    draw_pixel_flipped(matrix1, 12, y + 5, color)  # Bottom-left
    draw_pixel_flipped(matrix2, 0, y + 4, color)   # Top-right
    draw_pixel_flipped(matrix2, 0, y + 5, color)   # Bottom-right

def draw_text(text, color=0xFFFFFF):
    """Draw text across both matrices with proper spacing"""
    # Clear both displays
    matrix1.fill(0x000000)
    matrix2.fill(0x000000)

    # For "12:00" layout with spacing:
    # "1" at x=0 on matrix1 (5 pixels wide)
    # "2" at x=6 on matrix1 (5 pixels wide, leaving 1-2 pixels space before colon)
    # ":" split between matrix1 and matrix2
    # "0" at x=2 on matrix2 (leaving 1-2 pixels space after colon)
    # "0" at x=8 on matrix2 (5 pixels wide)

    y = 1  # Vertical position

    # Draw first two digits on matrix1
    if len(text) >= 2:
        draw_char(matrix1, text[0], 0, y, color)   # First digit at x=0
        draw_char(matrix1, text[1], 6, y, color)   # Second digit at x=6 (leaves space for colon)

    # Draw the colon split between displays
    if len(text) >= 3 and text[2] == ':':
        draw_colon_split(y, color)

    # Draw last two digits on matrix2
    if len(text) >= 5:
        draw_char(matrix2, text[3], 2, y, color)   # Third digit at x=2 (leaves space after colon)
        draw_char(matrix2, text[4], 8, y, color)   # Fourth digit at x=8

    # Update both displays
    matrix1.show()
    matrix2.show()
    print("updated matrices")

refresh_clock = ticks_ms()
refresh_timer = 3600 * 1000
clock_clock = ticks_ms()
clock_timer = 1000
first_run = True
new_time = False
color_value = 0
COLOR = colorwheel(0)
time_str = "00:00"
set_alarm = 0
active_alarm = False
alarm = f"{alarm_hour:02}:{alarm_min:02}"

while True:

    button.update()
    if button.long_press:
        # long press to set alarm & turn off alarm
        if set_alarm == 0 and not active_alarm:
            set_alarm = 1
            draw_text(f"{alarm_hour:02}:  ", COLOR)
        if active_alarm:
            mixer.voice[0].stop()
            active_alarm = False
            BRIGHTNESS = 128
            matrix1.set_led_scaling(BRIGHTNESS)
            matrix2.set_led_scaling(BRIGHTNESS)
    if button.short_count == 1:
        # short press to set hour and minute
        set_alarm = (set_alarm + 1) % 3
        if set_alarm == 0:
            draw_text(time_str, COLOR)
        elif set_alarm == 2:
            draw_text(f"  :{alarm_min:02}", COLOR)
    if button.short_count == 3:
        no_alarm_plz = not no_alarm_plz
        print(f"alarms off? {no_alarm_plz}")

    position = -encoder.position
    if position != last_position:
        if position > last_position:
            # when setting alarm, rotate through hours/minutes
            # when not, change color for LEDs
            if set_alarm == 0:
                color_value = (color_value + 5) % 255
            elif set_alarm == 1:
                alarm_hour = (alarm_hour + 1) % 24
            elif set_alarm == 2:
                alarm_min = (alarm_min + 1) % 60
        else:
            if set_alarm == 0:
                color_value = (color_value - 5) % 255
            elif set_alarm == 1:
                alarm_hour = (alarm_hour - 1) % 24
            elif set_alarm == 2:
                alarm_min = (alarm_min - 1) % 60
        alarm = f"{alarm_hour:02}:{alarm_min:02}"
        COLOR = colorwheel(color_value)
        if set_alarm == 0:
            draw_text(time_str, COLOR)
        elif set_alarm == 1:
            draw_text(f"{alarm_hour:02}:  ", COLOR)
        elif set_alarm == 2:
            draw_text(f"  :{alarm_min:02}", COLOR)
        last_position = position

    # resync with NTP time server every hour
    if set_alarm == 0:
        if ticks_diff(ticks_ms(), refresh_clock) >= refresh_timer or first_run:
            try:
                print("Getting time from internet!")
                now = ntp.datetime
                print(now)
                total_seconds = time.mktime(now)
                first_run = False
                am_pm_hour = now.tm_hour
                if hour_12:
                    hours = am_pm_hour % 12
                    if hours == 0:
                        hours = 12
                else:
                    hours = am_pm_hour
                time_str = f"{hours:02}:{now.tm_min:02}"
                print(time_str)
                mins = now.tm_min
                seconds = now.tm_sec
                draw_text(time_str, COLOR)
                refresh_clock = ticks_add(refresh_clock, refresh_timer)
            except Exception as e: # pylint: disable=broad-except
                print("Some error occured, retrying! -", e)
                time.sleep(10)
                microcontroller.reset()

        # keep time locally between NTP server syncs
        if ticks_diff(ticks_ms(), clock_clock) >= clock_timer:
            seconds += 1
            # print(seconds)
            if seconds > 59:
                mins += 1
                seconds = 0
                new_time = True
            if mins > 59:
                am_pm_hour += 1
                mins = 0
                new_time = True
            if hour_12:
                hours = am_pm_hour % 12
                if hours == 0:
                    hours = 12
            else:
                hours = am_pm_hour
            if new_time:
                time_str = f"{hours:02}:{mins:02}"
                new_time = False
                print(time_str)
                draw_text(time_str, COLOR)
                if f"{am_pm_hour:02}:{mins:02}" == alarm and not no_alarm_plz:
                    print("alarm!")
                    # grab a new wav file from the wavs list
                    wave = open_audio()
                    mixer.voice[0].play(wave, loop=True)
                    active_alarm = True
            if active_alarm:
                # blink the clock characters
                if BRIGHTNESS:
                    BRIGHTNESS = 0
                else:
                    BRIGHTNESS = 128
                matrix1.set_led_scaling(BRIGHTNESS)
                matrix2.set_led_scaling(BRIGHTNESS)
            clock_clock = ticks_add(clock_clock, clock_timer)     
