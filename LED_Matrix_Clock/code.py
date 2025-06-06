# SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

'''LED Matrix Alarm Clock with Scrolling Wake Up Text and Winking Eyes'''
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

# Configuration
timezone = -4
alarm_hour = 11
alarm_min = 36
alarm_volume = .2
hour_12 = True
no_alarm_plz = False
BRIGHTNESS_DAY = 200
BRIGHTNESS_NIGHT = 50

# I2S pins for Audio BFF
DATA = board.A0
LRCLK = board.A1
BCLK = board.A2

# Connect to WIFI
wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD"))
print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}")

context = ssl.create_default_context()
pool = socketpool.SocketPool(wifi.radio)
ntp = adafruit_ntp.NTP(pool, tz_offset=timezone, cache_seconds=3600)

# Initialize I2C and displays
i2c = board.STEMMA_I2C()
matrix1 = Adafruit_RGBMatrixQT(i2c, address=0x30, allocate=adafruit_is31fl3741.PREFER_BUFFER)
matrix2 = Adafruit_RGBMatrixQT(i2c, address=0x31, allocate=adafruit_is31fl3741.PREFER_BUFFER)

# Configure displays
for m in [matrix1, matrix2]:
    m.global_current = 0x05
    m.set_led_scaling(BRIGHTNESS_DAY)
    m.enable = True
    m.fill(0x000000)
    m.show()

# Audio setup
audio = audiobusio.I2SOut(BCLK, LRCLK, DATA)
wavs = ["/"+f for f in os.listdir('/') if f.lower().endswith('.wav') and not f.startswith('.')]
mixer = audiomixer.Mixer(voice_count=1, sample_rate=22050, channel_count=1,
                         bits_per_sample=16, samples_signed=True, buffer_size=32768)
mixer.voice[0].level = alarm_volume
audio.play(mixer)

def open_audio():
    """Open a random WAV file"""
    filename = random.choice(wavs)
    return audiocore.WaveFile(open(filename, "rb"))

def update_brightness(hour_24):
    """Update LED brightness based on time of day"""
    brightness = BRIGHTNESS_NIGHT if (hour_24 >= 20 or hour_24 < 7) else BRIGHTNESS_DAY
    matrix1.set_led_scaling(brightness)
    matrix2.set_led_scaling(brightness)
    return brightness

# Seesaw setup for encoder and button
seesaw = seesaw.Seesaw(i2c, addr=0x36)
seesaw.pin_mode(24, seesaw.INPUT_PULLUP)
button = Button(digitalio.DigitalIO(seesaw, 24), long_duration_ms=1000)
encoder = rotaryio.IncrementalEncoder(seesaw)
last_position = 0

# Font definitions
FONT_5X7 = {
    '0': [0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110],
    '1': [0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    '2': [0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111],
    '3': [0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110],
    '4': [0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010],
    '5': [0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110],
    '6': [0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110],
    '7': [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000],
    '8': [0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110],
    '9': [0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100],
    ' ': [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
    'W': [0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001],
    'A': [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    'K': [0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001],
    'E': [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111],
    'U': [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    'P': [0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
    'O': [0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    'N': [0b10001, 0b11001, 0b10101, 0b10101, 0b10011, 0b10001, 0b10001],
    'F': [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000]
}

# Eye patterns
EYE_OPEN = [0b10101, 0b01110, 0b10001, 0b10101, 0b10001, 0b01110, 0b00000]
EYE_CLOSED = [0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000]

class Display:
    """Handle all display operations"""
    def __init__(self, m1, m2):
        self.matrix1 = m1
        self.matrix2 = m2

    def clear(self):
        """Clear both displays"""
        self.matrix1.fill(0x000000)
        self.matrix2.fill(0x000000)

    def show(self):
        """Update both displays"""
        self.matrix1.show()
        self.matrix2.show()

    def pixel(self, matrix, x, y, color): # pylint: disable=no-self-use
        """Draw a pixel with 180-degree rotation"""
        fx, fy = 12 - x, 8 - y
        if 0 <= fx < 13 and 0 <= fy < 9:
            matrix.pixel(fx, fy, color)

    def draw_char(self, matrix, char, x, y, color):
        """Draw a character at position x,y"""
        if char.upper() in FONT_5X7:
            bitmap = FONT_5X7[char.upper()]
            for row in range(7):
                for col in range(5):
                    if bitmap[row] & (1 << (4 - col)):
                        self.pixel(matrix, x + col, y + row, color)

    def draw_colon(self, y, color, is_pm=False):
        """Draw colon split between displays with optional PM indicator"""
        # Two dots for the colon
        for dy in [(1, 2), (4, 5)]:
            for offset in dy:
                self.pixel(self.matrix1, 12, y + offset, color)
                self.pixel(self.matrix2, 0, y + offset, color)
        # PM indicator dot
        if is_pm:
            self.pixel(self.matrix1, 12, y + 6, color)
            self.pixel(self.matrix2, 0, y + 6, color)

    def draw_time(self, time_str, color, is_pm=False):
        """Draw time display across both matrices"""
        self.clear()
        y = 1
        # Draw digits
        if len(time_str) >= 5:
            self.draw_char(self.matrix1, time_str[0], 0, y, color)
            self.draw_char(self.matrix1, time_str[1], 6, y, color)
            self.draw_colon(y, color, is_pm)
            self.draw_char(self.matrix2, time_str[3], 2, y, color)
            self.draw_char(self.matrix2, time_str[4], 8, y, color)
        self.show()

    def draw_scrolling_text(self, text, offset, color):
        """Draw scrolling text across both matrices"""
        self.clear()
        char_width = 6
        total_width = 26
        # Calculate position for smooth scrolling
        y = 1
        for i, char in enumerate(text):
            # Start from right edge and move left
            char_x = total_width - offset + (i * char_width)
            # Draw character if any part is visible
            if -6 < char_x < total_width:
                if char_x < 13:  # On matrix1
                    self.draw_char(self.matrix1, char, char_x, y, color)
                else:  # On matrix2
                    self.draw_char(self.matrix2, char, char_x - 13, y, color)
        self.show()

    def draw_eye(self, matrix, pattern, color):
        """Draw eye pattern centered on matrix"""
        x, y = 4, 1  # Center position
        for row in range(7):
            for col in range(5):
                if pattern[row] & (1 << (4 - col)):
                    self.pixel(matrix, x + col, y + row, color)

    def wink_animation(self, color):
        """Perform winking animation"""
        # Sequence: open -> left wink -> open -> right wink -> open
        sequences = [
            (EYE_OPEN, EYE_OPEN),
            (EYE_CLOSED, EYE_OPEN),
            (EYE_OPEN, EYE_OPEN),
            (EYE_OPEN, EYE_CLOSED),
            (EYE_OPEN, EYE_OPEN)
        ]
        for left_eye, right_eye in sequences:
            self.clear()
            self.draw_eye(self.matrix1, left_eye, color)
            self.draw_eye(self.matrix2, right_eye, color)
            self.show()
            time.sleep(0.3)

    def blink_time(self, time_str, color, is_pm=False, count=3):
        """Blink time display for mode changes"""
        for _ in range(count):
            self.clear()
            self.show()
            time.sleep(0.2)
            self.draw_time(time_str, color, is_pm)
            time.sleep(0.2)

# Initialize display handler
display = Display(matrix1, matrix2)

# State variables
class State:
    """Track all state variables"""
    def __init__(self):
        self.color_value = 0
        self.color = colorwheel(0)
        self.is_pm = False
        self.alarm_is_pm = False
        self.time_str = "00:00"
        self.set_alarm = 0
        self.active_alarm = False
        self.alarm_str = f"{alarm_hour:02}:{alarm_min:02}"
        self.current_brightness = BRIGHTNESS_DAY
        # Timers
        self.refresh_timer = Timer(3600000)  # 1 hour
        self.clock_timer = Timer(1000)       # 1 second
        self.wink_timer = Timer(30000)       # 30 seconds
        self.scroll_timer = Timer(80)        # Scroll speed
        self.blink_timer = Timer(500)        # Blink speed
        self.alarm_status_timer = Timer(100) # Status scroll
        # Display state
        self.scroll_offset = 0
        self.blink_state = True
        self.showing_status = False
        self.status_start_time = 0
        self.alarm_start_time = 0
        # Time tracking
        self.first_run = True
        self.seconds = 0
        self.mins = 0
        self.am_pm_hour = 0

class Timer:
    """Simple timer helper"""
    def __init__(self, interval):
        self.interval = interval
        self.last_tick = ticks_ms()

    def check(self):
        """Check if timer has elapsed"""
        if ticks_diff(ticks_ms(), self.last_tick) >= self.interval:
            self.last_tick = ticks_add(self.last_tick, self.interval)
            return True
        return False

    def reset(self):
        """Reset timer"""
        self.last_tick = ticks_ms()

# Initialize state
state = State()

def format_time_display(hour_24, minute, use_12hr=True):
    """Format time for display with AM/PM detection"""
    if use_12hr:
        hour = hour_24 % 12
        if hour == 0:
            hour = 12
        is_pm = hour_24 >= 12
    else:
        hour = hour_24
        is_pm = False
    return f"{hour:02}:{minute:02}", is_pm

def sync_time():
    """Sync with NTP server"""
    try:
        print("Getting time from internet!")
        now = ntp.datetime
        state.am_pm_hour = now.tm_hour
        state.mins = now.tm_min
        state.seconds = now.tm_sec
        state.time_str, state.is_pm = format_time_display(state.am_pm_hour, state.mins, hour_12)
        update_brightness(state.am_pm_hour)
        if not state.active_alarm and not state.showing_status:
            display.draw_time(state.time_str, state.color, state.is_pm)
        print(f"Time: {state.time_str}")
        state.first_run = False
        return True
    except Exception as e: # pylint: disable=broad-except
        print(f"Error syncing time: {e}")
        return False

# Main loop
while True:
    button.update()

    # Handle button presses
    if button.long_press:
        if state.set_alarm == 0 and not state.active_alarm:
            # Enter alarm setting mode
            state.blink_timer.reset()
            state.set_alarm = 1
            state.alarm_is_pm = alarm_hour >= 12 if hour_12 else False
            hour_str, _ = format_time_display(alarm_hour, 0, hour_12)
            display.blink_time(hour_str[:2] + ":  ", state.color, state.alarm_is_pm)
            # Draw the alarm hour after blinking to keep it displayed
            display.draw_time(hour_str[:2] + ":  ", state.color, state.alarm_is_pm)
        elif state.active_alarm:
            # Stop alarm
            mixer.voice[0].stop()
            state.active_alarm = False
            update_brightness(state.am_pm_hour)
            state.scroll_offset = 0
            # Immediately redraw the current time
            display.draw_time(state.time_str, state.color, state.is_pm)
            print("Alarm silenced")

    if button.short_count == 1:  # Changed from == 1 to >= 1 for better detection
        # Cycle through alarm setting modes
        state.set_alarm = (state.set_alarm + 1) % 3
        if state.set_alarm == 0:
            # Exiting alarm setting mode - redraw current time
            state.wink_timer.reset()
            display.draw_time(state.time_str, state.color, state.is_pm)
        elif state.set_alarm == 1:
            # Entering hour setting
            hour_str, _ = format_time_display(alarm_hour, 0, hour_12)
            display.draw_time(hour_str[:2] + ":  ", state.color, state.alarm_is_pm)
              # Reset timer to prevent immediate blinking
        elif state.set_alarm == 2:
            # Entering minute setting
            display.blink_time(f"  :{alarm_min:02}", state.color, state.alarm_is_pm)
            # Draw the minutes after blinking to keep them displayed
            display.draw_time(f"  :{alarm_min:02}", state.color, state.alarm_is_pm)
              # Reset timer to prevent immediate blinking

    if button.short_count == 3:  # Changed for better detection
        # Toggle alarm on/off
        no_alarm_plz = not no_alarm_plz
        print(f"Alarm disabled: {no_alarm_plz}")
        state.showing_status = True
        state.status_start_time = ticks_ms()
        state.scroll_offset = 0

    # Handle encoder (your existing code)
    position = -encoder.position
    if position != last_position:
        delta = 1 if position > last_position else -1
        if state.set_alarm == 0:
            # Change color
            state.color_value = (state.color_value + delta * 5) % 255
            state.color = colorwheel(state.color_value)
            display.draw_time(state.time_str, state.color, state.is_pm)
        elif state.set_alarm == 1:
            # Change hour
            alarm_hour = (alarm_hour + delta) % 24
            state.alarm_is_pm = alarm_hour >= 12 if hour_12 else False
            hour_str, _ = format_time_display(alarm_hour, 0, hour_12)
            display.draw_time(hour_str[:2] + ":  ", state.color, state.alarm_is_pm)
        elif state.set_alarm == 2:
            # Change minute
            alarm_min = (alarm_min + delta) % 60
            display.draw_time(f"  :{alarm_min:02}", state.color, state.alarm_is_pm)
        state.alarm_str = f"{alarm_hour:02}:{alarm_min:02}"
        last_position = position

    # Handle alarm status display
    if state.showing_status:
        if state.alarm_status_timer.check():
            status_text = "OFF " if no_alarm_plz else "ON "
            display.draw_scrolling_text(status_text, state.scroll_offset, state.color)
            text_width = 4*6 if no_alarm_plz else 3*6
            state.scroll_offset += 1
            # Reset when text has completely scrolled off
            if state.scroll_offset > text_width + 18:
                state.scroll_offset = 0
                state.showing_status = False
                if state.set_alarm == 0 and not state.active_alarm:
                    display.draw_time(state.time_str, state.color, state.is_pm)

    # Handle active alarm scrolling
    if state.active_alarm:
        # Auto-silence alarm after 1 minute
        if ticks_diff(ticks_ms(), state.alarm_start_time) >= 60000:
            mixer.voice[0].stop()
            state.active_alarm = False
            update_brightness(state.am_pm_hour)
            state.scroll_offset = 0
            display.draw_time(state.time_str, state.color, state.is_pm)
            print("Alarm auto-silenced")
        elif state.scroll_timer.check():
            display.draw_scrolling_text("WAKE UP ", state.scroll_offset, state.color)
            text_width = 8 * 6  # "WAKE UP " is 8 characters
            state.scroll_offset += 1
            # Reset when text has completely scrolled off
            if state.scroll_offset > text_width + 26:
                state.scroll_offset = 0

    # Handle alarm setting mode blinking
    elif state.set_alarm > 0:
        # Only blink if enough time has passed since mode change
        if state.blink_timer.check():
            state.blink_state = not state.blink_state
            if state.blink_state:
                # Redraw during the "on" part of blink
                if state.set_alarm == 1:
                    hour_str, _ = format_time_display(alarm_hour, 0, hour_12)
                    display.draw_time(hour_str[:2] + ":  ", state.color, state.alarm_is_pm)
                else:
                    display.draw_time(f"  :{alarm_min:02}", state.color, state.alarm_is_pm)
            else:
                # Only clear display during the "off" part of blink
                display.clear()
                display.show()

    # Normal mode operations
    else:  # state.set_alarm == 0
        # Winking animation
        if not state.active_alarm and not state.showing_status and state.wink_timer.check():
            print("Winking!")
            display.wink_animation(state.color)
            display.draw_time(state.time_str, state.color, state.is_pm)

        # Time sync
        if state.refresh_timer.check() or state.first_run:
            if not sync_time():
                time.sleep(10)
                microcontroller.reset()

        # Local timekeeping
        if state.clock_timer.check():
            state.seconds += 1
            if state.seconds > 59:
                state.seconds = 0
                state.mins += 1
                if state.mins > 59:
                    state.mins = 0
                    state.am_pm_hour = (state.am_pm_hour + 1) % 24
                    update_brightness(state.am_pm_hour)
                # Update display
                state.time_str, state.is_pm = format_time_display(state.am_pm_hour,
                                                                  state.mins, hour_12)
                if not state.active_alarm and not state.showing_status:
                    display.draw_time(state.time_str, state.color, state.is_pm)
                # Check alarm
                if f"{state.am_pm_hour:02}:{state.mins:02}" == state.alarm_str and not no_alarm_plz:
                    print("ALARM!")
                    wave = open_audio()
                    mixer.voice[0].play(wave, loop=True)
                    state.active_alarm = True
                    state.alarm_start_time = ticks_ms()
                    state.scroll_offset = 0
