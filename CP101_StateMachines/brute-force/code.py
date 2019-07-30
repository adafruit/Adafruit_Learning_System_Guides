"""
New Year's Eve ball drop robot friend.

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

# pylint: disable=global-statement,stop-iteration-return,no-self-use

import time
import random
import board
import digitalio
import busio
import adafruit_ds3231
import audioio
import pulseio
from adafruit_motor import servo
import neopixel
from adafruit_debouncer import Debouncer

# Set to false to disable testing/tracing code
TESTING = True

# Implementation dependant things to tweak
NUM_PIXELS = 8               # number of neopixels in the striup
DROP_THROTTLE = -0.2         # servo throttle during ball drop
DROP_DURATION = 10.0         # how many seconds the ball takes to drop
RAISE_THROTTLE = 0.3         # servo throttle while raising the ball
FIREWORKS_DURATION = 60.0    # how many second the fireworks last

# Pins
NEOPIXEL_PIN = board.D5
POWER_PIN = board.D10
SWITCH_PIN = board.D9
SERVO_PIN = board.A1

# States
WAITING_STATE = 0
PAUSED_STATE = 1
DROPPING_STATE = 2
BURST_STATE = 3
SHOWER_STATE = 4
RAISING_STATE = 5
IDLE_STATE = 6
RESET_STATE = 7


################################################################################
# Setup hardware

# Power to the speaker and neopixels must be enabled using this pin

enable = digitalio.DigitalInOut(POWER_PIN)
enable.direction = digitalio.Direction.OUTPUT
enable.value = True

i2c = busio.I2C(board.SCL, board.SDA)
rtc = adafruit_ds3231.DS3231(i2c)

audio = audioio.AudioOut(board.A0)

strip = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=1, auto_write=False)
strip.fill(0)                          # NeoPixels off ASAP on startup
strip.show()

switch_io = digitalio.DigitalInOut(SWITCH_PIN)
switch_io.direction = digitalio.Direction.INPUT
switch_io.pull = digitalio.Pull.UP

switch = Debouncer(switch_io)

# create a PWMOut object on Pin A2.
pwm = pulseio.PWMOut(SERVO_PIN, duty_cycle=2 ** 15, frequency=50)

# Create a servo object, my_servo.
servo = servo.ContinuousServo(pwm)
servo.throttle = 0.0

# Set the time for testing
# Once finished testing, the time can be set using the REPL using similar code
if TESTING:
    #                     year, mon, date, hour, min, sec, wday, yday, isdst
    t = time.struct_time((2018,  12,   31,   23,  58,  55,    1,   -1,    -1))
    # you must set year, mon, date, hour, min, sec and weekday
    # yearday is not supported, isdst can be set but we don't do anything with it at this time
    print("Setting time to:", t)
    rtc.datetime = t
    print()

################################################################################
# Variables

firework_color = 0
firework_step_time = 0
burst_count = 0
shower_count = 0
firework_stop_time = 0
pixel_count = min([NUM_PIXELS // 2, 20])
pixels = []
pixel_index = 0


################################################################################
# Support functions

def log(s):
    """Print the argument if testing/tracing is enabled."""
    if TESTING:
        print(s)

# Random color

def random_color_byte():
    """ Return one of 32 evenly spaced byte values.
    This provides random colors that are fairly distinctive."""
    return random.randrange(0, 256, 16)

def random_color():
    """Return a random color"""
    red = random_color_byte()
    green = random_color_byte()
    blue = random_color_byte()
    return (red, green, blue)

# Color cycling.

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return 0, 0, 0
    if pos < 85:
        return int(255 - pos*3), int(pos*3), 0
    if pos < 170:
        pos -= 85
        return 0, int(255 - pos*3), int(pos*3)
    pos -= 170
    return int(pos * 3), 0, int(255 - (pos*3))

def cycle_sequence(seq):
    while True:
        for elem in seq:
            yield elem

def rainbow_lamp(seq):
    g = cycle_sequence(seq)
    while True:
        strip.fill(wheel(next(g)))
        strip.show()
        yield

# Fireworks effects

def reset_fireworks(time_now):
    """As indicated, reset the fireworks system's variables."""
    global firework_color, burst_count, shower_count, firework_step_time
    firework_color = random_color()
    burst_count = 0
    shower_count = 0
    strip.fill(0)
    strip.show()
    firework_step_time = time_now + 0.05


def burst(time_now):
    """Show a burst of color on all pixels, fading in, holding briefly,
    then fading out.  Each call to this does one step in that
    process. Return True once the sequence is finished."""
    global firework_step_time, burst_count, shower_count
    log("burst %d" % (burst_count))
    if burst_count == 0:
        strip.brightness = 0.0
        strip.fill(firework_color)
    elif burst_count == 22:
        shower_count = 0
        firework_step_time = time_now + 0.3
        return True
    if time_now < firework_step_time:
        return False
    elif burst_count < 11:
        strip.brightness = burst_count / 10.0
        firework_step_time = time_now + 0.08
    elif burst_count == 11:
        firework_step_time = time_now + 0.3
    elif burst_count > 11:
        strip.brightness = 1.0 - ((burst_count - 11) / 10.0)
        firework_step_time = time_now + 0.08
    strip.show()
    burst_count += 1
    return False

def shower(time_now):
    """Show a shower of sparks effect.
    Each call to this does one step in the process. Return True once the
    sequence is finished."""
    global firework_step_time, pixels, pixel_index, shower_count
    log("Shower %d" % (shower_count))
    if shower_count == 0:                 # Initialize on the first step
        strip.fill(0)
        strip.brightness = 1.0
        pixels = [None] * pixel_count
        pixel_index = 0
    if time_now < firework_step_time:
        return False
    if shower_count == NUM_PIXELS:
        strip.fill(0)
        strip.show()
        return True
    if pixels[pixel_index]:
        strip[pixels[pixel_index]] = 0
    random_pixel = random.randrange(NUM_PIXELS)
    pixels[pixel_index] = random_pixel
    strip[random_pixel] = firework_color
    strip.show()
    pixel_index = (pixel_index + 1) % pixel_count
    shower_count += 1
    firework_step_time = time_now + 0.1
    return False

def start_playing(fname):
    sound_file = open(fname, 'rb')
    wav = audioio.WaveFile(sound_file)
    audio.play(wav, loop=False)

def stop_playing():
    if audio.playing:
        audio.stop()

def almost_NY():
    rtc_now = rtc.datetime
    return (rtc_now.tm_mday == 31 and
            rtc_now.tm_mon == 12 and
            rtc_now.tm_hour == 23 and
            rtc_now.tm_min == 59 and
            rtc_now.tm_sec == 50)



state = WAITING_STATE
paused_state = None
paused_servo = 0.0
switch_pressed_at = 0
drop_finish_time = 0

while True:
    test_trigger = False
    now = time.monotonic()
    t = rtc.datetime
    switch.update()

    # The machine sits in paused state until the switch is pressed again in
    # which case the machine goes back to the state it was in when paused (and
    # resumes the audio and servo as it was) or the switch is held for a second
    # in which case it goes to the reset state.
    if state == PAUSED_STATE:
        log("Paused")
        if switch.fell:
            if audio.paused:
                audio.resume()
            servo.throttle = paused_servo
            paused_servo = 0.0
            state = paused_state
        elif not switch.value:
            if now - switch_pressed_at > 1.0:
                state = RESET_STATE
        continue

    # There is a special check here for a switch press in any state other than
    # waiting. If there is a press, the current state, audio, and servo values
    # are saved and paused state is entered
    if switch.fell and state != WAITING_STATE:
        switch_pressed_at = now
        paused_state = state
        if audio.playing:
            audio.pause()
        paused_servo = servo.throttle
        servo.throttle = 0.0
        state = PAUSED_STATE
        continue

    # Waiting state handles waiting until 23:59 on NYE or until the switch is
    # pressed. When either happens, the song is played and the servo starts
    # droppping the ball. As well, a rainbow effect is started on the LEDs and
    # the machine moves to dropping state.
    if state == WAITING_STATE:
        log("Waiting")
        if switch.fell:
            while not switch.rose:
                switch.update()
            test_trigger = True

        if test_trigger or almost_NY():
            test_trigger = False
            # Play the song
            start_playing('./countdown.wav')

            # Drop the ball
            servo.throttle = DROP_THROTTLE

            # color show in the ball
            rainbow = rainbow_lamp(range(0, 256, 2))
            log("1 minute to midnight")
            rainbow_time = now + 0.1

            drop_finish_time = now + DROP_DURATION
            state = DROPPING_STATE

    # In dropping the ball is dropping, colors are cycling, and the song is
    # playing. After the machine has been in this state long enough (set by
    # DROP_DURATION) it cleans up and switches to fireworks mode (burst to be
    # exact).
    elif state == DROPPING_STATE:
        log("Dropping")
        if now >= drop_finish_time:
            log("***Midnight")
            servo.throttle = 0.0
            stop_playing()
            start_playing('./Auld_Lang_Syne.wav')
            reset_fireworks(now)
            firework_stop_time = now + FIREWORKS_DURATION
            state = BURST_STATE
            continue
        if now >= rainbow_time:
            next(rainbow)
            rainbow_time = now + 0.1

    # This state shows a burst of light (vi the burst function. It stays in
    # this mode until burst is finished, indicated by burst returning
    # True. When that happens the machine moves to the shower state.
    elif state == BURST_STATE:
        log("Burst")
        if burst(now):
            state = SHOWER_STATE
            shower_count = 0

    # This state shows a shower-of-sparks effect until the shower function
    # returns True. If it's time to stop the fireworks effects the machine
    # moves to the idle state. Otherwise if loops back to the burst state.
    elif state == SHOWER_STATE:
        log("Shower")
        if shower(now):
            if now >= firework_stop_time:
                state = IDLE_STATE
            else:
                state = BURST_STATE
                reset_fireworks(now)

    # The idle state currently just jumps into the waiting state.
    elif state == IDLE_STATE:
        log("Idle")
        state = WAITING_STATE

    # This state resets the LEDs and audio, starts the servo raising the ball
    # and moves to the raising state.
    elif state == RESET_STATE:
        log("Reset")
        strip.fill(0)
        strip.brightness = 1.0
        strip.show()
        if audio.playing:
            audio.stop()
        servo.throttle = RAISE_THROTTLE
        state = RAISING_STATE

    # This state simply waits until the switch is released at which time it
    # stops the servo and moves to the waiting state.
    elif state == RAISING_STATE:
        log("Raise")
        if switch.rose:
            servo.throttle = 0.0
            state = WAITING_STATE
