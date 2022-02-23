# SPDX-FileCopyrightText: 2020 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import displayio
from adafruit_clue import clue
from simpleio import map_range
from adafruit_bitmap_font import bitmap_font
from adafruit_lsm6ds.lsm6ds33 import LSM6DS33
from adafruit_lsm6ds import Rate, AccelRange
from adafruit_progressbar.progressbar import ProgressBar
from adafruit_display_text.label import Label

#  turns off onboard NeoPixel to conserve battery
clue.pixel.brightness = (0.0)

#  accessing the Clue's accelerometer
sensor = LSM6DS33(board.I2C())

#  step goal
step_goal = 10000

#  onboard button states
a_state = False
b_state = False

#  array to adjust screen brightness
bright_level = [0, 0.5, 1]

countdown = 0 #  variable for the step goal progress bar
clock = 0 #  variable used to keep track of time for the steps per hour counter
clock_count = 0 #  holds the number of hours that the step counter has been running
clock_check = 0 #  holds the result of the clock divided by 3600 seconds (1 hour)
last_step = 0 #  state used to properly counter steps
mono = time.monotonic() #  time.monotonic() device
mode = 1 #  state used to track screen brightness
steps_log = 0 #  holds total steps to check for steps per hour
steps_remaining = 0 #  holds the remaining steps needed to reach the step goal
sph = 0 #  holds steps per hour

#  variables to hold file locations for background and fonts
clue_bgBMP = "/clue_bgBMP.bmp"
small_font = "/fonts/Roboto-Medium-16.bdf"
med_font = "/fonts/Roboto-Bold-24.bdf"
big_font = "/fonts/Roboto-Black-48.bdf"

#  glyphs for fonts
glyphs = b'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-,.: '

#  loading bitmap fonts
small_font = bitmap_font.load_font(small_font)
small_font.load_glyphs(glyphs)
med_font = bitmap_font.load_font(med_font)
med_font.load_glyphs(glyphs)
big_font = bitmap_font.load_font(big_font)
big_font.load_glyphs(glyphs)

#  creating display and default brightness
clue_display = board.DISPLAY
clue_display.brightness = 0.5

#  graphics group
clueGroup = displayio.Group()

#  loading bitmap background
# CircuitPython 6 & 7 compatible
clue_bg = displayio.OnDiskBitmap(open(clue_bgBMP, "rb"))
clue_tilegrid = displayio.TileGrid(
    clue_bg, pixel_shader=getattr(clue_bg, 'pixel_shader', displayio.ColorConverter())
)
clueGroup.append(clue_tilegrid)

# # CircuitPython 7+ compatible
# clue_bg = displayio.OnDiskBitmap(clue_bgBMP)
# clue_tilegrid = displayio.TileGrid(clue_bg, pixel_shader=clue_bg.pixel_shader)
# clueGroup.append(clue_tilegrid)

#  creating the ProgressBar object
bar_group = displayio.Group()
prog_bar = ProgressBar(1, 1, 239, 25, bar_color=0x652f8f)
bar_group.append(prog_bar)

clueGroup.append(bar_group)

#  text for step goal
steps_countdown = Label(small_font, text='%d Steps Remaining' % step_goal, color=clue.WHITE)
steps_countdown.x = 55
steps_countdown.y = 12

#  text for steps
text_steps = Label(big_font, text="0     ", color=0xe90e8b)
text_steps.x = 45
text_steps.y = 70

#  text for steps per hour
text_sph = Label(med_font, text=" -- ", color=0x29abe2)
text_sph.x = 8
text_sph.y = 195

#  adding all text to the display group
clueGroup.append(text_sph)
clueGroup.append(steps_countdown)
clueGroup.append(text_steps)

#  sending display group to the display at startup
clue_display.show(clueGroup)

#  setting up the accelerometer and pedometer
sensor.accelerometer_range = AccelRange.RANGE_2G
sensor.accelerometer_data_rate = Rate.RATE_26_HZ
sensor.gyro_data_rate = Rate.RATE_SHUTDOWN
sensor.pedometer_enable = True

while True:

    #  button debouncing
    if not clue.button_a and not a_state:
        a_state = True
    if not clue.button_b and not b_state:
        b_state = True

    #  setting up steps to hold step count
    steps = sensor.pedometer_steps

    #  creating the data for the ProgressBar
    countdown = map_range(steps, 0, step_goal, 0.0, 1.0)

    #  actual counting of the steps
    #  if a step is taken:
    if abs(steps-last_step) > 1:
        step_time = time.monotonic()
        #  updates last_step
        last_step = steps
        #  updates the display
        text_steps.text = '%d' % steps
        clock = step_time - mono

        #  logging steps per hour
        if clock > 3600:
            #  gets number of hours to add to total
            clock_check = clock / 3600
            #  logs the step count as of that hour
            steps_log = steps
            #  adds the hours to get a new hours total
            clock_count += round(clock_check)
            #  divides steps by hours to get steps per hour
            sph = steps_log / clock_count
            #  adds the sph to the display
            text_sph.text = '%d' % sph
            #  resets clock to count to the next hour again
            clock = 0
            mono = time.monotonic()

        #  adjusting countdown to step goal
        prog_bar.progress = float(countdown)

    #  displaying countdown to step goal
    if step_goal - steps > 0:
        steps_remaining = step_goal - steps
        steps_countdown.text = '%d Steps Remaining' % steps_remaining
    else:
        steps_countdown.text = 'Steps Goal Met!'

    #  adjusting screen brightness, a button decreases brightness
    if clue.button_a and a_state:
        mode -= 1
        a_state = False
        if mode < 0:
            mode = 0
            clue_display.brightness = bright_level[mode]
        else:
            clue_display.brightness = bright_level[mode]
    #  b button increases brightness
    if clue.button_b and b_state:
        mode += 1
        b_state = False
        if mode > 2:
            mode = 2
            clue_display.brightness = bright_level[mode]
        else:
            clue_display.brightness = bright_level[mode]

    time.sleep(0.001)
