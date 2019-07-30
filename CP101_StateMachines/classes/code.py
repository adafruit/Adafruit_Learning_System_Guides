"""
Class based state machine implementation

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""

# pylint: disable=global-statement,stop-iteration-return,no-self-use,useless-super-delegation

import time
import random
import board
import  digitalio
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
# Global Variables

pixel_count = min([NUM_PIXELS // 2, 20])

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

def burst(machine, time_now):
    """Show a burst of color on all pixels, fading in, holding briefly,
    then fading out.  Each call to this does one step in that
    process. Return True once the sequence is finished."""
    if machine.burst_count == 0:
        strip.brightness = 0.0
        strip.fill(machine.firework_color)
    elif machine.burst_count == 22:
        machine.firework_step_time = time_now + 0.3
        return True
    if time_now < machine.firework_step_time:
        return False
    elif machine.burst_count < 11:
        strip.brightness = machine.burst_count / 10.0
        machine.firework_step_time = time_now + 0.08
    elif machine.burst_count == 11:
        machine.firework_step_time = time_now + 0.3
    elif machine.burst_count > 11:
        strip.brightness = 1.0 - ((machine.burst_count - 11) / 10.0)
        machine.firework_step_time = time_now + 0.08
    strip.show()
    machine.burst_count += 1
    return False

def shower(machine, time_now):
    """Show a shower of sparks effect.
    Each call to this does one step in the process. Return True once the
    sequence is finished."""
    if machine.shower_count == 0:                 # Initialize on the first step
        strip.fill(0)
        strip.brightness = 1.0
        machine.pixels = [None] * pixel_count
        machine.pixel_index = 0
    if time_now < machine.firework_step_time:
        return False
    if machine.shower_count == NUM_PIXELS:
        strip.fill(0)
        strip.show()
        return True
    if machine.pixels[machine.pixel_index]:
        strip[machine.pixels[machine.pixel_index]] = 0
    random_pixel = random.randrange(NUM_PIXELS)
    machine.pixels[machine.pixel_index] = random_pixel
    strip[random_pixel] = machine.firework_color
    strip.show()
    machine.pixel_index = (machine.pixel_index + 1) % pixel_count
    machine.shower_count += 1
    machine.firework_step_time = time_now + 0.1
    return False

def start_playing(fname):
    sound_file = open(fname, 'rb')
    wav = audioio.WaveFile(sound_file)
    audio.play(wav, loop=False)

def stop_playing():
    if audio.playing:
        audio.stop()


################################################################################
# State Machine

class StateMachine(object):

    def __init__(self):
        self.state = None
        self.states = {}
        self.firework_color = 0
        self.firework_step_time = 0
        self.burst_count = 0
        self.shower_count = 0
        self.firework_stop_time = 0
        self.paused_state = None
        self.pixels = []
        self.pixel_index = 0

    def add_state(self, state):
        self.states[state.name] = state

    def go_to_state(self, state_name):
        if self.state:
            log('Exiting %s' % (self.state.name))
            self.state.exit(self)
        self.state = self.states[state_name]
        log('Entering %s' % (self.state.name))
        self.state.enter(self)

    def update(self):
        if self.state:
            log('Updating %s' % (self.state.name))
            self.state.update(self)

    # When pausing, don't exit the state
    def pause(self):
        self.state = self.states['paused']
        log('Pausing')
        self.state.enter(self)

    # When resuming, don't re-enter the state
    def resume_state(self, state_name):
        if self.state:
            log('Exiting %s' % (self.state.name))
            self.state.exit(self)
        self.state = self.states[state_name]
        log('Resuming %s' % (self.state.name))

    def reset_fireworks(self):
        """As indicated, reset the fireworks system's variables."""
        self.firework_color = random_color()
        self.burst_count = 0
        self.shower_count = 0
        self.firework_step_time = time.monotonic() + 0.05
        strip.fill(0)
        strip.show()




################################################################################
# States


# Abstract parent state class.

class State(object):

    def __init__(self):
        pass

    @property
    def name(self):
        return ''

    def enter(self, machine):
        pass

    def exit(self, machine):
        pass

    def update(self, machine):
        if switch.fell:
            machine.paused_state = machine.state.name
            machine.pause()
            return False
        return True


# Wait for 10 seconds to midnight or the witch to be pressed,
# then drop the ball.

class WaitingState(State):

    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return 'waiting'

    def enter(self, machine):
        State.enter(self, machine)

    def exit(self, machine):
        State.exit(self, machine)

    def almost_NY(self):
        now = rtc.datetime
        return (now.tm_mday == 31 and
                now.tm_mon == 12 and
                now.tm_hour == 23 and
                now.tm_min == 59 and
                now.tm_sec == 50)

    def update(self, machine):
        # No super call to check for switch press to pause
        # switch press here drops the ball
        if switch.fell or self.almost_NY():
            machine.go_to_state('dropping')

# Drop the ball, playing the countdown and showing
# a rainbow effect.

class DroppingState(State):

    def __init__(self):
        super().__init__()
        self.rainbow = None
        self.rainbow_time = 0
        self.drop_finish_time = 0

    @property
    def name(self):
        return 'dropping'

    def enter(self, machine):
        State.enter(self, machine)
        now = time.monotonic()
        start_playing('./countdown.wav')
        servo.throttle = DROP_THROTTLE
        self.rainbow = rainbow_lamp(range(0, 256, 2))
        self.rainbow_time = now + 0.1
        self.drop_finish_time = now + DROP_DURATION

    def exit(self, machine):
        State.exit(self, machine)
        servo.throttle = 0.0
        stop_playing()
        machine.reset_fireworks()
        machine.firework_stop_time = time.monotonic() + FIREWORKS_DURATION

    def update(self, machine):
        if State.update(self, machine):
            now = time.monotonic()
            if now >= self.drop_finish_time:
                machine.go_to_state('burst')
            if now >= self.rainbow_time:
                next(self.rainbow)
                self.rainbow_time = now + 0.1


# Show a fireworks explosion: a burst of color. Then switch to a shower of sparks.

class BurstState(State):

    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return 'burst'

    def enter(self, machine):
        State.enter(self, machine)

    def exit(self, machine):
        State.exit(self, machine)
        machine.shower_count = 0

    def update(self, machine):
        if State.update(self, machine):
            if burst(machine, time.monotonic()):
                machine.go_to_state('shower')


# Show a shower of sparks following an explosion

class ShowerState(State):

    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return 'shower'

    def enter(self, machine):
        State.enter(self, machine)

    def exit(self, machine):
        State.exit(self, machine)
        machine.reset_fireworks()

    def update(self, machine):
        if State.update(self, machine):
            if shower(machine, time.monotonic()):
                if time.monotonic() >= machine.firework_stop_time:
                    machine.go_to_state('idle')
                else:
                    machine.go_to_state('burst')


# Do nothing, wait to be reset

class IdleState(State):

    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return 'idle'

    def enter(self, machine):
        State.enter(self, machine)

    def exit(self, machine):
        State.exit(self, machine)

    def update(self, machine):
        State.update(self, machine)


# Reset the LEDs and audio, start the servo raising the ball
# When the switch is released, stop the ball and move to waiting

class RaisingState(State):

    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return 'raising'

    def enter(self, machine):
        State.enter(self, machine)
        strip.fill(0)
        strip.brightness = 1.0
        strip.show()
        if audio.playing:
            audio.stop()
        servo.throttle = RAISE_THROTTLE

    def exit(self, machine):
        State.exit(self, machine)
        servo.throttle = 0.0

    def update(self, machine):
        if State.update(self, machine):
            if switch.rose:
                machine.go_to_state('waiting')


# Pause, resuming whem the switch is pressed again.
# Reset if the switch has been held for a second.

class PausedState(State):

    def __init__(self):
        super().__init__()
        self.switch_pressed_at = 0
        self.paused_servo = 0

    @property
    def name(self):
        return 'paused'

    def enter(self, machine):
        State.enter(self, machine)
        self.switch_pressed_at = time.monotonic()
        if audio.playing:
            audio.pause()
        self.paused_servo = servo.throttle
        servo.throttle = 0.0

    def exit(self, machine):
        State.exit(self, machine)

    def update(self, machine):
        if switch.fell:
            if audio.paused:
                audio.resume()
            servo.throttle = self.paused_servo
            self.paused_servo = 0.0
            machine.resume_state(machine.paused_state)
        elif not switch.value:
            if time.monotonic() - self.switch_pressed_at > 1.0:
                machine.go_to_state('raising')

################################################################################
# Create the state machine

pretty_state_machine = StateMachine()
pretty_state_machine.add_state(WaitingState())
pretty_state_machine.add_state(DroppingState())
pretty_state_machine.add_state(BurstState())
pretty_state_machine.add_state(ShowerState())
pretty_state_machine.add_state(IdleState())
pretty_state_machine.add_state(RaisingState())
pretty_state_machine.add_state(PausedState())

pretty_state_machine.go_to_state('waiting')

while True:
    switch.update()
    pretty_state_machine.update()
