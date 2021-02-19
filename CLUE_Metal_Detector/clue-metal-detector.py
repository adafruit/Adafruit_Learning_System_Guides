# clue-metal-detector v1.6
# A simple metal detector using a minimum number of external components

# Tested with an Adafruit CLUE (Alpha) and CircuitPython 5.2.0
# Tested with an Adafruit Circuit Playground Bluefruit with TFT Gizmo
# and CircuitPython 5.2.0

# CLUE: Pad P0 is an output and pad P1 is an input
# CPB: Pad/STEMMA A1 is an output and Pad/STEMMA A2 is an input

# copy this file to CLUE/CPB board as code.py

# MIT License

# Copyright (c) 2020 Kevin J. Walters

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# pylint: disable=global-statement

import time
import math
import array
import os
import gc

import board
import pwmio
import analogio
import ulab

from displayio import Group
import terminalio

# These imports works on CLUE, CPB (and CPX on 5.x)
from audiocore import RawSample
try:
    from audioio import AudioOut
except ImportError:
    from audiopwmio import PWMAudioOut as AudioOut

# displayio graphical objects
from adafruit_display_text.label import Label
from adafruit_display_shapes.rect import Rect
from adafruit_display_shapes.circle import Circle


# Assuming CLUE if it's not a Circuit Playround (Bluefruit)
clue_less = "Circuit Playground" in os.uname().machine

if clue_less:
    # CPB with TFT Gizmo (240x240)
    from adafruit_circuitplayground import cp
    from adafruit_gizmo import tft_gizmo

    # Outputs
    display = tft_gizmo.TFT_Gizmo()
    audio_out = AudioOut(board.SPEAKER)
    min_audio_frequency = 100
    max_audio_frequency = 4000
    pixels = cp.pixels
    board_pin_output = board.A1

    # Enable the onboard amplifier for speaker
    cp._speaker_enable.value = True  # pylint: disable=protected-access

    # Inputs
    board_pin_input = board.A2
    magnetometer = None  # This indicates device is not present
    button_left = lambda: cp.button_b
    button_right = lambda: cp.button_a

else:
    # CLUE with builtin screen (240x240)
    from adafruit_clue import clue

    # Outputs
    display = board.DISPLAY
    audio_out = AudioOut(board.SPEAKER)
    min_audio_frequency = 100
    max_audio_frequency = 5000
    pixels = clue.pixel
    board_pin_output = board.P0

    # Inputs (buttons reversed as it is used upside-down with Gizmo)
    board_pin_input = board.P1
    magnetometer = lambda: clue.magnetic
    button_left = lambda: clue.button_a
    button_right = lambda: clue.button_b


# Globals variables used r/w in functions
last_frequency = 0
last_negbar_len = None
last_posbar_len = None
last_mag_radius = None
text_overlay_gob = None
voltage_barneg_dob = None
voltage_sep_dob = None
voltage_barpos_dob = None
magnet_circ_dob = None

# Globals
debug = 1
screen_height = display.height
screen_width = display.width
samples = []

# Other globals
quantize_tones = True
audio_on = True
screen_on = True
mu_output = False
neopixel_on = True

# Used to alternate/flash the NeoPixel
neopixel_alternate = True

# Some constants used in start_beep()
BASE_NOTE = 261.6256  # C4 (middle C)
QUANTIZE = 4          # determines the "scale"
POSTLOG_FACTOR = QUANTIZE / math.log(2)

AUDIO_MIDPOINT = 32768

# There's room for 80 pixels but 60 draws a bit quicker
VOLTAGE_BAR_WIDTH = 60
VOLTAGE_BAR_HEIGHT = 118
VOLTAGE_BAR_SEP_HEIGHT = 4
MAG_MAX_RADIUS = 50

VOLTAGE_FMT = "{:6.1f}"
MAG_FMT = "{:6.1f}"

INFO_FG_COLOR = 0x000080
INFO_BG_COLOR = 0xc0c000
BLACK_TUPLE = (0, 0, 0)

RED     = 0xff0000
GREEN75 = 0x00c000
BLUE    = 0x0000ff
WHITE75 = 0xc0c0c0

FONT_WIDTH, FONT_HEIGHT = terminalio.FONT.get_bounding_box()

# Thresholds below which audio is silent and NeoPixels are dark
threshold_voltage = 0.002
threshold_mag = 2.5


def d_print(level, *args, **kwargs):
    """A simple conditional print for debugging based on global debug level."""
    if not isinstance(level, int):
        print(level, *args, **kwargs)
    elif debug >= level:
        print(*args, **kwargs)


# Adapted and borrowed from clue-plotter v1.14
def wait_release(text_func, button_func, menu):
    """Calls button_func repeatedly waiting for it to return a false value
       and goes through menu list as time passes.

       The menu is a list of menu entries where each entry is a
       two element list of time passed in seconds and text to display
       for that period. Text is displayed by calling text_func(text).
       The entries must be in ascending time order."""

    start_t_ns = time.monotonic_ns()
    menu_option = None
    selected = False

    for menu_option, menu_entry in enumerate(menu):
        menu_time_ns = start_t_ns + int(menu_entry[0] * 1e9)
        menu_text = menu_entry[1]
        if menu_text:
            text_func(menu_text)
        while time.monotonic_ns() < menu_time_ns:
            if not button_func():
                selected = True
                break
        if menu_text:
            text_func("")
        if selected:
            break

    return (menu_option, (time.monotonic_ns() - start_t_ns) * 1e-9)


def popup_text(text_func, text, duration=1.0):
    """Place some text on the screen using info property of Plotter object
       for duration seconds."""
    text_func(text)
    time.sleep(duration)
    text_func(None)


def show_text(text):
    """Place text on the screen. Empty string or None clears it."""
    global screen_group, text_overlay_gob

    if text:
        font_scale = 3
        line_spacing = 1.25

        text_lines = text.split("\n")
        max_word_chars = max([len(word) for word in text_lines])
        # If too large reduce the scale to 2 and hope!
        if (max_word_chars * font_scale * FONT_WIDTH > screen_width
                or (len(text_lines) * font_scale
                    * FONT_HEIGHT * line_spacing) > screen_height):
            font_scale -= 1

        text_overlay_gob = Label(terminalio.FONT,
                                 text=text,
                                 scale=font_scale,
                                 background_color=INFO_FG_COLOR,
                                 color=INFO_BG_COLOR)
        # Centre the (left justified) text
        text_overlay_gob.x = (screen_width
                              - font_scale * FONT_WIDTH * max_word_chars) // 2
        text_overlay_gob.y = screen_height // 2
        screen_group.append(text_overlay_gob)
    else:
        if text_overlay_gob is not None:
            screen_group.remove(text_overlay_gob)
            text_overlay_gob = None


def voltage_bar_set(volt_diff):
    """Draw a bar based on positive or negative values.
       Width of 60 is performance compromise as more pixels take longer."""
    global voltage_sep_dob, voltage_barpos_dob, voltage_barneg_dob
    global last_negbar_len, last_posbar_len

    if voltage_sep_dob is None:
        voltage_sep_dob = Rect(160, VOLTAGE_BAR_HEIGHT,
                               VOLTAGE_BAR_WIDTH, VOLTAGE_BAR_SEP_HEIGHT,
                               fill=WHITE75)
        screen_group.append(voltage_sep_dob)

    if volt_diff < 0:
        negbar_len = max(min(-round(volt_diff * 5e3),
                             VOLTAGE_BAR_HEIGHT), 1)
        posbar_len = 1
    else:
        negbar_len = 1
        posbar_len = max(min(round(volt_diff * 5e3),
                             VOLTAGE_BAR_HEIGHT), 1)

    if posbar_len == last_posbar_len and negbar_len == last_negbar_len:
        return

    if voltage_barpos_dob is not None:
        screen_group.remove(voltage_barpos_dob)
    if posbar_len > 0:
        voltage_barpos_dob = Rect(160, VOLTAGE_BAR_HEIGHT - posbar_len,
                                  VOLTAGE_BAR_WIDTH, posbar_len,
                                  fill=GREEN75)
        screen_group.append(voltage_barpos_dob)
        last_posbar_len = posbar_len

    if voltage_barneg_dob is not None:
        screen_group.remove(voltage_barneg_dob)
    if negbar_len > 0:
        voltage_barneg_dob = Rect(160,
                                  VOLTAGE_BAR_HEIGHT + VOLTAGE_BAR_SEP_HEIGHT,
                                  VOLTAGE_BAR_WIDTH, negbar_len,
                                  fill=RED)
        screen_group.append(voltage_barneg_dob)
        last_negbar_len = negbar_len


def magnet_circ_set(mag_ut):
    """Display a filled circle to represent the magnetic value mag_ut in microteslas."""
    global magnet_circ_dob
    global last_mag_radius

    # map microteslas to a radius with minimum of 1 and
    # maximum of MAG_MAX_RADIUS
    radius = min(max(round(math.sqrt(mag_ut) * 4), 1), MAG_MAX_RADIUS)

    if radius == last_mag_radius:
        return

    if magnet_circ_dob is not None:
        screen_group.remove(magnet_circ_dob)
    magnet_circ_dob = Circle(60, 180, radius, fill=BLUE)
    screen_group.append(magnet_circ_dob)


def manual_screen_refresh(disp):
    """Refresh the screen as immediately as is currently possibly with refresh method."""
    refreshed = False
    while True:
        try:
            # 1000fps is fastest library allows - this high value
            # minimises any delays this refresh() method introduces
            refreshed = disp.refresh(minimum_frames_per_second=0,
                                     target_frames_per_second=1000)
        except RuntimeError:
            pass
        if refreshed:
            break


def neopixel_set(pix, d_volt, mag_ut):
    """Set all the NeoPixels to an alternating colour
       based on voltage difference and
       magnitude of magnetic flux density difference."""
    global neopixel_alternate

    np_r, np_g, np_b = BLACK_TUPLE
    if neopixel_alternate:
        # RGB values are 8bit, hence the cap of 255 using min()
        if abs(d_volt) > threshold_voltage:
            if d_volt < 0.0:
                np_r = min(round(-d_volt * 8e3), 255)
            else:
                np_g = min(round(d_volt * 8e3), 255)
        else:
            if mag_ut > threshold_mag:
                np_b = min(round(mag_ut * 6), 255)

    pix.fill((np_r, np_g, np_b))  # Note: double brackets to pass tuple
    neopixel_alternate = not neopixel_alternate


def start_beep(freq, wave, wave_idx):
    """Start playing a continous beep based on freq and waveform specified by wave_idx.
       A frequency of 0 will stop the note playing.
       This quantizes the notes into a scale to make beeping sound more pleasant.
       This modifies the sample_rate property of the RawSample objects.
       """
    global last_frequency
    if freq == 0:
        if last_frequency != 0:
            audio_out.stop()
            last_frequency = 0
        return

    if quantize_tones:
        note_freq = BASE_NOTE * 2**((round(math.log(freq / BASE_NOTE)
                                           * POSTLOG_FACTOR)) / QUANTIZE)
        d_print(3, "Quantize", freq, note_freq)
    else:
        note_freq = freq

    (waveform, wave_samples_n) = wave[wave_idx]
    new_freq = round(note_freq * wave_samples_n)
    # Only set the new frequency if it's not the same as last one
    if new_freq != last_frequency:
        waveform.sample_rate = new_freq
        audio_out.play(waveform, loop=True)
        last_frequency = new_freq


def make_sample_list(levels=10,
                     volume=32767,
                     range_l=24,
                     start_l=8):
    """Make a list of tuples of (RawSample, sample_length)
       with a sine wave of varying resolution from high to low.
       The lower resolutions sound crunchier and louder on the CLUE."""

    # Make a range of sample lengths, default is between 32 and 8
    sample_lens = [int((x*(range_l + .99)/(levels - 1)) + start_l)
                   for x in range(0, levels)]
    sample_lens.reverse()

    wavefs = []
    for s_len in sample_lens:
        raw_samples = array.array("H",
                                  [round(volume * math.sin(2 * math.pi
                                                           * (idx / s_len)))
                                   + AUDIO_MIDPOINT
                                   for idx in range(s_len)])
        sound_samples = RawSample(raw_samples)
        wavefs.append((sound_samples, s_len))

    return wavefs


waveforms = make_sample_list()

# For testing the waveforms
if debug >= 4:
    for idx in range(len(waveforms)):
        start_beep(440, waveforms, idx)
        time.sleep(0.1)
    start_beep(0, waveforms, 0)  # This silences it

# See https://forums.adafruit.com/viewtopic.php?f=60&t=164758 for
# a comparison and performance analysis of alternate techniques for this
def sample_sum(pin, num):
    """Sample the analogue value from pin num times and return the sum
       of the values."""
    global samples   # Not strictly needed - indicative of r/w use
    samples[:] = [pin.value for _ in range(num)]
    return sum(samples)


# Initialise detector display
# The units are created as separate text objects as they are static
# and this reduces the amount of redrawing for the dynamic numbers
FONT_SCALE = 3

if magnetometer is not None:
    magnet_value_dob = Label(font=terminalio.FONT,
                             text="----.-",
                             scale=FONT_SCALE,
                             color=0xc0c000)
    magnet_value_dob.y = 90

    magnet_units_dob = Label(font=terminalio.FONT,
                             text="uT",
                             scale=FONT_SCALE,
                             color=0xc0c000)
    magnet_units_dob.x = len(magnet_value_dob.text) * FONT_WIDTH * FONT_SCALE
    magnet_units_dob.y = magnet_value_dob.y

voltage_value_dob = Label(font=terminalio.FONT,
                          text="----.-",
                          scale=FONT_SCALE,
                          color=0x00c0c0)
voltage_value_dob.y = 30

voltage_units_dob = Label(font=terminalio.FONT,
                          text="mV",
                          scale=FONT_SCALE,
                          color=0x00c0c0)
voltage_units_dob.y = voltage_value_dob.y
voltage_units_dob.x = len(voltage_value_dob.text) * FONT_WIDTH * FONT_SCALE

# 9 elements, 4 added immediately, 4 later, 1 spare for on-screen text
screen_group = Group(max_size=4 + 4 + 1)
if magnetometer is not None:
    screen_group.append(magnet_value_dob)
    screen_group.append(magnet_units_dob)
screen_group.append(voltage_value_dob)
screen_group.append(voltage_units_dob)

# Initialise some displayio objects and append them
# The following four variables are set by these two functions
# voltage_barneg_dob, voltage_sep_dob, voltage_barpos_dob
# magnet_circ_dob
voltage_bar_set(0)
if magnetometer is not None:
    magnet_circ_set(0)

# Start-up splash screen
display.show(screen_group)

# Start-up splash screen
popup_text(show_text,
           "\n".join(["Button Guide",
                      "Left: audio",
                      "  2secs: NeoPixel",
                      "  4s: screen",
                      "  6s: Mu output",
                      "Right: recalibrate"]), duration=10)

# P1 or A2 for analogue input
pin_input = analogio.AnalogIn(board_pin_input)
CONV_FACTOR = pin_input.reference_voltage / 65535

# Start pwm output on P0 or A1
# 400kHz and 55000 (84%) duty_cycle were chosen empirically to maximise
# the voltage and the voltage drop detecting a small pair of metal scissors
pwm = pwmio.PWMOut(board_pin_output, frequency=400 * 1000,
                     duty_cycle=0, variable_frequency=True)
pwm.duty_cycle = 55000


# Get a baseline value for magnetometer
totals = [0.0] * 3
mag_samples_n = 10
if magnetometer is not None:
    for _ in range(mag_samples_n):
        mx, my, mz = magnetometer()
        totals[0] += mx
        totals[1] += my
        totals[2] += mz
        time.sleep(0.05)

base_mx = totals[0] / mag_samples_n
base_my = totals[1] / mag_samples_n
base_mz = totals[2] / mag_samples_n

# Wait a bit for P1/A2 input to stabilise
_ = sample_sum(pin_input, 3000) / 3000 * CONV_FACTOR
base_voltage = sample_sum(pin_input, 1000) / 1000 * CONV_FACTOR
voltage_value_dob.text = "{:6.1f}".format(base_voltage * 1000.0)

# Auto refresh off
display.auto_refresh = False

# Store two previous values of voltage to make a simple
# filtered value
voltage_zm1 = None
voltage_zm2 = None
filt_voltage = None

# Initialise the magnitude of the
# magnetic flux density difference from its baseline
mag_mag = 0.0

# Keep some historical voltage data to calculate median for re-baselining
# aiming for about 10 reads per second so this gives
# 20 seconds
voltage_hist = ulab.zeros(20 * 10 + 1, dtype=ulab.float)
voltage_hist_idx = 0
voltage_hist_complete = False
voltage_hist_median = None

# Reduce the frequency of the more heavyweight graphical changes
update_basic_graphics_period = 2
update_complex_graphics_period = 4
update_median_period = 5

counter = 0
while True:
    # Garbage collect now to reduce likelihood it occurs
    # during sample reading
    gc.collect()
    if debug >=2:
        d_print(2, "mem_free=" + str(gc.mem_free()))

    screen_updates = 0  # Used to determine if the screen needs a refresh

    # Take arithmetic mean of 500 samples but take a few more samples
    # if the loop isn't doing other work
    samples_to_read = 500  # About 23ms worth on CLUE
    update_basic_graphics = (screen_on
                             and counter % update_basic_graphics_period == 0)
    if not update_basic_graphics:
        samples_to_read += 150
    update_complex_graphics = (screen_on
                               and counter % update_complex_graphics_period == 0)
    if not update_complex_graphics:
        samples_to_read += 400
    update_median = counter % update_median_period == 0
    if not update_median:
        samples_to_read += 50
    # Read the analogue values from P1/A2
    sample_start_time_ns = time.monotonic_ns()
    voltage = (sample_sum(pin_input, samples_to_read)
               / samples_to_read * CONV_FACTOR)

    # Store the previous two voltage values
    voltage_zm2 = voltage_zm1
    voltage_zm1 = voltage

    if voltage_zm1 is None:
        voltage_zm1 = voltage
    if voltage_zm2 is None:
        voltage_zm2 = voltage

    filt_voltage = (voltage * 0.4
                    + voltage_zm1 * 0.3
                    + voltage_zm2 * 0.3)

    update_basic_graphics = counter % update_basic_graphics_period == 0
    update_complex_graphics = counter % update_complex_graphics_period == 0

    # Update text
    if update_basic_graphics:
        voltage_value_dob.text = VOLTAGE_FMT.format(filt_voltage * 1000.0)
        screen_updates += 1

    # Read magnetometer
    if magnetometer is not None:
        mx, my, mz = magnetometer()
        diff_x = mx - base_mx
        diff_y = my - base_my
        diff_z = mz - base_mz
        # Use the z value as a crude measure as this is
        # constant if the device is rotated and kept level
        mag_mag = math.sqrt(diff_z * diff_z)
    else:
        mag_mag = 0.0

    # Calculate a new audio frequency based on the absolute difference
    # in voltage being read - turn small voltages into 0 for silence
    # between 100Hz (won't be audible)
    # and 5000 (loud on CLUE's miniscule speaker)
    diff_v = filt_voltage - base_voltage
    abs_diff_v = abs(diff_v)
    if audio_on:
        if abs_diff_v > threshold_voltage or mag_mag > threshold_mag:
            frequency = min(min_audio_frequency + abs_diff_v * 5e5,
                            max_audio_frequency)
        else:
            frequency = 0  # silence
        start_beep(frequency, waveforms,
                   min(int(mag_mag / 2), len(waveforms) - 1))

    # Update the NeoPixel(s) if enabled
    if neopixel_on:
        neopixel_set(pixels, diff_v, mag_mag)

    # Update voltage bargraph
    if update_complex_graphics:
        voltage_bar_set(diff_v)
        screen_updates += 1

    # Update the magnetometer text value and the filled circle representation
    if magnetometer is not None:
        if update_basic_graphics:
            magnet_value_dob.text = MAG_FMT.format(mag_mag)
            screen_updates += 1
        if update_complex_graphics:
            magnet_circ_set(mag_mag)
            screen_updates += 1

    # Update the screen with a refresh if needed
    if screen_updates:
        manual_screen_refresh(display)

    # Send output to Mu in tuple format
    if mu_output:
        print((diff_v, mag_mag))

    # Check for buttons and just for this section of code turn back on
    # the screen auto-refresh so the menus actually appear!
    display.auto_refresh = True
    if button_left():
        opt, _ = wait_release(show_text,
                              button_left,
                              [(2,
                                "Audio "
                                + ("off" if audio_on else "on")),
                               (4,
                                "NeoPixel "
                                + ("off" if neopixel_on else "on")),
                               (6,
                                "Screen "
                                + ("off" if screen_on else "on")),
                               (8,
                                "Mu output "
                                + ("off" if mu_output else "on"))
                              ])
        if not screen_on or opt == 2:  # Screen toggle
            screen_on = not screen_on
            if screen_on:
                display.show(screen_group)
                display.brightness = 1.0
            else:
                display.show(None)
                display.brightness = 0.0
        elif opt == 0:  # Audio toggle
            audio_on = not audio_on
            if not audio_on:
                start_beep(0, waveforms, 0)  # Silence
        elif opt == 1:  # NeoPixel toggle
            neopixel_on = not neopixel_on
            if not neopixel_on:
                neopixel_set(pixels, 0.0, 0.0)
        else:  # Mu toggle
            mu_output = not mu_output

    # Set new baseline voltage and magnetometer on right button press
    if button_right():
        wait_release(show_text,
                     button_right,
                     [(2, "Recalibrate")])
        d_print(1, "Recalibrate")
        base_voltage = voltage
        voltage_hist_idx = 0
        voltage_hist_complete = False
        voltage_hist_median = None
        if magnetometer is not None:
            base_mx, base_my, base_mz = mx, my, mz

    display.auto_refresh = False

    # Add the current voltage to the historical list
    voltage_hist[voltage_hist_idx] = voltage
    if voltage_hist_idx >= len(voltage_hist) - 1:
        voltage_hist_idx = 0
        voltage_hist_complete = True
    else:
        voltage_hist_idx += 1

    # Adjust the reference base_voltage to the median of historical values
    if voltage_hist_complete and update_median:
        voltage_hist_median = ulab.numerical.sort(voltage_hist)[len(voltage_hist) // 2]
        base_voltage = voltage_hist_median

    d_print(2, counter, sample_start_time_ns / 1e9,
            voltage * 1000.0,
            mag_mag,
            filt_voltage * 1000.0, base_voltage, voltage_hist_median)

    counter += 1
