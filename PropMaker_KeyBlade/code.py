"""
Prop-Maker based Key Blade.
Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!
Written by Kattni Rembor for Adafruit Industries
Copyright (c) 2019 Adafruit Industries
Licensed under the MIT license.
All text above must be included in any redistribution.
"""

import time
import digitalio
import audioio
import busio
import board
import neopixel
import adafruit_lis3dh

# CUSTOMISE COLORS HERE:
COLOR = (255, 0, 0)  # Default is red
ALT_COLOR = (255, 18, 0)  # Default alternate is orange

# CUSTOMISE IDLE PULSE SPEED HERE: 0 is fast, above 0 slows down
IDLE_PULSE_SPEED = 0.03  # Default is 0.03 seconds

# CUSTOMISE BRIGHTNESS HERE: must be a number between 0 and 1
IDLE_PULSE_BRIGHTNESS = 0.3  # Default maximum idle pulse brightness is 30%
SWING_BRIGHTNESS = 0.4  # Default swing brightness is 40%
HIT_BRIGHTNESS = 1  # Default hit brightness is 100%

# CUSTOMISE SENSITIVITY HERE: smaller numbers = more sensitive to motion
HIT_THRESHOLD = 650
SWING_THRESHOLD = 125

# Set to the length in seconds of the "on.wav" file
POWER_ON_SOUND_DURATION = 1.7

NUM_PIXELS = 40  # Number of pixels used in project
NEOPIXEL_PIN = board.D5
POWER_PIN = board.D10

enable = digitalio.DigitalInOut(POWER_PIN)
enable.direction = digitalio.Direction.OUTPUT
enable.value = False

strip = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=1, auto_write=False)
strip.fill(0)  # NeoPixels off ASAP on startup
strip.show()

audio = audioio.AudioOut(board.A0)  # Speaker

# Set up accelerometer on I2C bus, 4G range:
i2c = busio.I2C(board.SCL, board.SDA)
accel = adafruit_lis3dh.LIS3DH_I2C(i2c)
accel.range = adafruit_lis3dh.RANGE_4_G

COLOR_HIT = COLOR  # "hit" color is COLOR set above
COLOR_SWING = ALT_COLOR  # "swing" color is ALT_COLOR set above


def play_wav(name, loop=False):
    """
    Play a WAV file in the 'sounds' directory.
    :param name: partial file name string, complete name will be built around
                 this, e.g. passing 'foo' will play file 'sounds/foo.wav'.
    :param loop: if True, sound will repeat indefinitely (until interrupted
                 by another sound).
    """
    print("playing", name)
    try:
        wave_file = open('sounds/' + name + '.wav', 'rb')
        wave = audioio.WaveFile(wave_file)
        audio.play(wave, loop=loop)
    except:  # pylint: disable=bare-except
        return


def power_on(sound, duration):
    """
    Animate NeoPixels with accompanying sound effect for power on.
    :param sound: sound name (similar format to play_wav() above)
    :param duration: estimated duration of sound, in seconds (>0.0)
    """
    prev = 0
    start_time = time.monotonic()  # Save audio start time
    play_wav(sound)
    while True:
        elapsed = time.monotonic() - start_time  # Time spent playing sound
        if elapsed > duration:  # Past sound duration?
            break  # Stop animating
        animation_time = elapsed / duration  # Animation time, 0.0 to 1.0
        threshold = int(NUM_PIXELS * animation_time + 0.5)
        num = threshold - prev  # Number of pixels to light on this pass
        if num != 0:
            strip[prev:threshold] = [ALT_COLOR] * num
            strip.show()
            prev = threshold


def mix(color_1, color_2, weight_2):
    """
    Blend between two colors with a given ratio.
    :param color_1:  first color, as an (r,g,b) tuple
    :param color_2:  second color, as an (r,g,b) tuple
    :param weight_2: Blend weight (ratio) of second color, 0.0 to 1.0
    :return (r,g,b) tuple, blended color
    """
    if weight_2 < 0.0:
        weight_2 = 0.0
    elif weight_2 > 1.0:
        weight_2 = 1.0
    weight_1 = 1.0 - weight_2
    return (int(color_1[0] * weight_1 + color_2[0] * weight_2),
            int(color_1[1] * weight_1 + color_2[1] * weight_2),
            int(color_1[2] * weight_1 + color_2[2] * weight_2))


mode = 0  # Initial mode = OFF

# Setup idle pulse
min_idle_brightness = 0  # Minimum brightness of idle pulse
max_idle_brightness = IDLE_PULSE_BRIGHTNESS  # Maximum brightness of idle pulse
idle_direction = 1  # Initial idle pulse direction

# Main loop
while True:

    if mode == 0:  # If currently off...
        enable.value = True
        power_on('on', POWER_ON_SOUND_DURATION)  # Power up!
        play_wav('idle', loop=True)  # Play idle sound now
        mode = 1  # Idle mode

        # Setup for idle pulse
        min_idle_brightness = 0
        idle_direction = 0.01
        strip.brightness = min_idle_brightness
        strip.fill(COLOR)
        strip.show()

    elif mode >= 1:  # If not OFF mode...
        x, y, z = accel.acceleration  # Read accelerometer
        accel_total = x * x + z * z
        # (Y axis isn't needed, due to the orientation that the Prop-Maker
        # Wing is mounted.  Also, square root isn't needed, since we're
        # comparing thresholds...use squared values instead.)
        if accel_total > HIT_THRESHOLD:  # Large acceleration = HIT
            TRIGGER_TIME = time.monotonic()  # Save initial time of hit
            play_wav('hit')  # Start playing 'hit' sound
            COLOR_ACTIVE = COLOR_HIT  # Set color to fade from
            strip.brightness = HIT_BRIGHTNESS  # Hit flash brightness
            mode = 3  # HIT mode
        elif mode == 1 and accel_total > SWING_THRESHOLD:  # Mild = SWING
            TRIGGER_TIME = time.monotonic()  # Save initial time of swing
            play_wav('swing')  # Start playing 'swing' sound
            COLOR_ACTIVE = COLOR_SWING  # Set color to fade from
            mode = 2  # SWING mode

        elif mode == 1:
            # Idle pulse
            min_idle_brightness += idle_direction  # Pulse up
            if min_idle_brightness >= max_idle_brightness or min_idle_brightness <= 0:  # Then...
                idle_direction = -idle_direction  # Pulse down
            strip.brightness = min_idle_brightness
            strip.show()
            time.sleep(IDLE_PULSE_SPEED)  # Idle pulse speed set above
        elif mode > 1:  # If in SWING or HIT mode...
            if audio.playing:  # And sound currently playing...
                blend = time.monotonic() - TRIGGER_TIME  # Time since triggered
                if mode == 2:  # If SWING,
                    blend = abs(0.5 - blend) * 2.0  # ramp up, down
                    strip.brightness = SWING_BRIGHTNESS  # Swing brightness
                strip.fill(mix(COLOR_ACTIVE, COLOR, blend))  # Fade from hit/swing to base color
                strip.show()
            else:  # No sound now, but still SWING or HIT modes
                play_wav('idle', loop=True)  # Resume idle sound
                mode = 1  # Return to idle mode
