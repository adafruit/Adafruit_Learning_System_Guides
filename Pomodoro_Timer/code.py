"""
The MIT License (MIT)

Copyright (c) 2018 Dave Astels

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
# pylint: disable=global-statement

import time
from math import ceil
import board
import rotaryio
import neopixel
from adafruit_debouncer import Debouncer
import digitalio
import pulseio

# Setup the hardware

encoder = rotaryio.IncrementalEncoder(board.D9, board.D7)
button_io = digitalio.DigitalInOut(board.D10)
button_io.direction = digitalio.Direction.INPUT
button_io.pull = digitalio.Pull.UP
button = Debouncer(button_io)
strip = neopixel.NeoPixel(board.D11, 16, brightness=1, auto_write=False)

last_position = 0

def check_encoder():
    """Check if the encoder has been rotated.
    returns the direction (-1 or +1) if it has, 0 if not.
    """

    global last_position
    position = encoder.position
    if position > last_position:
        direction = 1
    elif position < last_position:
        direction = -1
    else:
        direction = 0
    last_position = position
    return direction


def show_time(color, value, bright):
    """Show remaining time on the ring.
    :param int color: the RGB value to use
    :param int value: how many pixels to light
    :param boolean bright: whether the highest pixel should be brighter (i.e white)
    """
    strip.fill(0x000000)
    if value > 0:
        for i in range(1, value + 1):
            strip[16 - i] = color
        if bright:
            strip[16 - value] = 0x404040
    strip.show()


def set_timer(color, value):
    """Set a time remaing value
    :param int color: the color to use on the ring
    :param int value: the initial value (number of pixels to light)
    Returns the new setting
    """
    global last_position
    time_setting = value
    last_position = encoder.position
    for i in range(16):
        strip[i] = color
        strip.show()
    for i in range(16):
        strip[i] = 0x000000
        strip.show()
    while True:
        show_time(color, time_setting, False)
        button.update()
        if button.fell:
            return time_setting
        direction = check_encoder()
        time_setting += direction
        if time_setting > 16:
            time_setting = 16
        if time_setting < 0:
            time_setting = 0


def beep(count, duration, interstitial, freq):
    """Make some noise
    :param int count: the number of beeps to make
    :param float duration: the length (in seconds) of each beep
    :param float interstitial: the length (in seconds) of the silence between beeps
    :param int freq: the frequency of the beeps
    """
    pwm = pulseio.PWMOut(board.D12, duty_cycle = 0, frequency=freq)
    for _ in range(count):
        pwm.duty_cycle = 0x7FFF
        time.sleep(duration)
        pwm.duty_cycle = 0
        time.sleep(interstitial)
    pwm.deinit()


def compute_mode_settings(new_mode):
    """Compute settings for a new mode
    :param boolean new_mode: the new mode
    Returns
      boolean mode       - the new mode
      int dial_color     - the dial color for the new mode
      int time_remaining - the initial time-remaining for the new mode
      int increment      - the pixel increment for the new mode
    """
    work_time_increment = 600
    break_time_increment = 300

    if new_mode:
        return True, 0x400000, work_time * work_time_increment, work_time_increment
    else:
        return False, 0x004000, break_time * break_time_increment, break_time_increment


# Initialize things

strip.fill(0x000000)
strip.show()
work_time = 6
break_time = 2
time_to_check = 0
state = False
mode, dial_color, time_remaining, increment = compute_mode_settings(True)

# The main loop

while True:
    # check whether the rotary encoder has been pushed. If so enter time-set mode.
    button.update()
    if button.fell:
        work_time = set_timer(0x400000, work_time)
        break_time = set_timer(0x004000, break_time)
        strip.fill(0x000000)
        strip.show()
        mode, dial_color, time_remaining, increment = compute_mode_settings(True)

    now = time.monotonic()
    if now >= time_to_check:          #only check each second
        time_remaining -= 1
        if time_remaining <= 0:       # time to switch modes?
            strip.fill(0x000000)      # clear the dial
            strip.show()              # make some noise
            beep(2, 0.5, 0.25, 4000)
            mode, dial_color, time_remaining, increment = compute_mode_settings(not mode)
        state = not state             # have the top pixel toggle between the dial color and white
        show_time(dial_color, ceil(time_remaining / increment), state)   #update the dial
        time_to_check = now + 1.0
