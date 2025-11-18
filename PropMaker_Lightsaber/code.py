import time
import math
import gc
from digitalio import DigitalInOut, Direction, Pull
import audioio
import audiocore
import audiomixer
import busio
import board
import neopixel
import adafruit_lis3dh
from rainbowio import colorwheel
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.animation.blink import Blink
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.color import RED
import adafruit_fancyled.adafruit_fancyled as fancy
from adafruit_debouncer import Debouncer
from random import randint
import random


# SENSITIVITY
HIT = 400
SWING = 250
THRUST = 600
IDLE = 110

NUM_PIXELS = 144
NEOPIXEL_PIN = board.D5
POWER_PIN = board.D10
SWITCH_PIN = board.D9
SWITCH2_PIN = board.D13

enable = DigitalInOut(POWER_PIN)
enable.direction = Direction.OUTPUT
enable.value = False

red_led = DigitalInOut(board.D11)
red_led.direction = Direction.OUTPUT

speaker = audioio.AudioOut(board.A0, right_channel=board.A1)
mode = 0

strip = neopixel.NeoPixel(NEOPIXEL_PIN, NUM_PIXELS, brightness=0.75, auto_write=False)

strip.fill(0)
strip.show()

switch = DigitalInOut(SWITCH_PIN)
switch.direction = Direction.INPUT
switch.pull = Pull.UP

switch2 = DigitalInOut(SWITCH2_PIN)
switch2.direction = Direction.INPUT
switch2.pull = Pull.UP

switch2deb = Debouncer(switch2)


# Set up accelerometer on I2C bus, 4G range:
i2c = busio.I2C(board.SCL, board.SDA)
accel = adafruit_lis3dh.LIS3DH_I2C(i2c)
accel.range = adafruit_lis3dh.RANGE_4_G

# "Idle" color is 1/4 brightness, "swinging" color is full brightness...
COLOR_IDLE = colorwheel(85)
COLOR_HIT = (255, 255, 255)  # "hit" color is white

chase = Chase(strip, speed=0.01, color=COLOR_IDLE, size=100, spacing=1)
blink = Blink(strip, speed=0.001, color=COLOR_IDLE)
pulse = Pulse(strip, speed=0.01, period=10, color=COLOR_IDLE)

index = 0
awake = False
setup = False
setup2 = False
awake2 = False
#    [0],  # red
#    [10],  # orange
#    [30],  # yellow
#    [85],  # green
#    [137],  # cyan
#    [170],  # blue
#    [213],  # purple

counter = 85

idleWav = audiocore.WaveFile(open("sounds/idle.wav", "rb"))
hitWav = audiocore.WaveFile(open("sounds/hit.wav", "rb"))
hitWav2 = audiocore.WaveFile(open("sounds/hit2.wav", "rb"))
swingWav1 = audiocore.WaveFile(open("sounds/swing.wav", "rb"))
swingWav2 = audiocore.WaveFile(open("sounds/swing2.wav", "rb"))
swingWav3 = audiocore.WaveFile(open("sounds/swing3.wav", "rb"))
swingWav4 = audiocore.WaveFile(open("sounds/swing4.wav", "rb"))
swingWav5 = audiocore.WaveFile(open("sounds/swing5.wav", "rb"))
swingWav6 = audiocore.WaveFile(open("sounds/swing6.wav", "rb"))
laserHitWav = audiocore.WaveFile(open("sounds/laserHit.wav", "rb"))
setupMode = audiocore.WaveFile(open("sounds/setupMode.wav", "rb"))
marchWav = audiocore.WaveFile(open("sounds/march.wav", "rb"))
helloThere = audiocore.WaveFile(open("sounds/helloThere.wav", "rb"))

min_brightness = 150
max_brightness = 255
breathing_speed = 10
brightness = max_brightness
brightness_up = False
playCounter = 2


BLACK = fancy.CRGB(0, 0, 0)
WHITE = fancy.CRGB(255, 255, 255)


mixer = audiomixer.Mixer(
    voice_count=7,
    sample_rate=11025,
    channel_count=1,
    bits_per_sample=16,
    samples_signed=True,
)

def play_wav(name, loop=False):
    """
    Play a WAV file in the 'sounds' directory.
    @param name: partial file name string, complete name will be built around
                 this, e.g. passing 'foo' will play file 'sounds/foo.wav'.
    @param loop: if True, sound will repeat indefinitely (until interrupted
                 by another sound).
    """
    print("playing", name)
    try:
        wave_file = open("sounds/" + name + ".wav", "rb")
        wave = audiocore.WaveFile(wave_file)
        speaker.play(wave, loop=loop)
    except:
        return


def power(sound, duration, reverse):
    """
    Animate NeoPixels with accompanying sound effect for power on / off.
    @param sound:    sound name (similar format to play_wav() above)
    @param duration: estimated duration of sound, in seconds (>0.0)
    @param reverse:  if True, do power-off effect (reverses animation)
    """

    color = colorwheel(counter)
    if reverse:
        prev = NUM_PIXELS
    else:
        prev = 0
    gc.collect()  # Tidy up RAM now so animation's smoother
    start_time = time.monotonic()  # Save audio start time
    play_wav(sound)
    while True:
        elapsed = time.monotonic() - start_time  # Time spent playing sound
        if elapsed > duration:  # Past sound duration?
            break  # Stop animating
        fraction = elapsed / duration  # Animation time, 0.0 to 1.0
        if reverse:
            fraction = 1.0 - fraction  # 1.0 to 0.0 if reverse
        fraction = math.pow(fraction, 0.5)  # Apply nonlinear curve
        threshold = int(NUM_PIXELS * fraction + 0.5)
        num = threshold - prev  # Number of pixels to light on this pass
        if num != 0:
            if reverse:
                strip[threshold:prev] = [0] * -num
            else:
                strip[prev:threshold] = [COLOR_IDLE] * num
            strip.show()
            # NeoPixel writes throw off time.monotonic() ever so slightly
            # because interrupts are disabled during the transfer.
            # We can compensate somewhat by adjusting the start time
            # back by 30 microseconds per pixel.
            start_time -= NUM_PIXELS * 0.00003
            prev = threshold

    if reverse:
        strip.fill(0)  # At end, ensure strip is off
    else:
        strip.fill(COLOR_IDLE)  # or all pixels set on
    strip.show()
    while speaker.playing:  # Wait until audio done
        pass

def colorwheel2tuple(RGBint):
    Blue = RGBint & 255
    Green = (RGBint >> 8) & 255
    Red = (RGBint >> 16) & 255
    return [Red, Green, Blue]

def rainbow_cycle(wait):
    for j in range(255):
        for i in range(NUM_PIXELS):
            rc_index = (i * 256 // NUM_PIXELS) - j
            strip[i] = colorwheel(rc_index & 255)
        strip.show()
        time.sleep(wait)


def phaser_glow(color, wait):
    for j in range(255):
        for i in range(NUM_PIXELS):
            rc_index = (i * 256 // NUM_PIXELS) - j
            strip[i] = colorwheel(rc_index & 255)
        strip.show()
        time.sleep(wait)


def color_chase(color, wait):
    for i in range(NUM_PIXELS):
        strip[i] = color
        time.sleep(wait)
        strip.show()
    time.sleep(0.5)


def playSwing(num):
    if num == 1:
        swing = swingWav1
    elif num == 2:
        swing = swingWav2
    elif num == 3:
        swing = swingWav3
    elif num == 4:
        swing = swingWav4
    elif num == 5:
        swing = swingWav5
    else:
        swing = swingWav6

    return swing

def playHit(num):
    if num == 1:
        hit = hitWav
    elif num == 2:
        hit = hitWav2
    else:
        hit = hitWav

    return hit

# Main program loop, repeats indefinitely

while True:

    red_led.value = False
    color = colorwheel(counter)

    COLOR_IDLE = color

    if not switch2.value and setup:
        counter = counter + 5
        if counter >= 255:
            counter = 1
        color = colorwheel(counter)
        strip.fill(color)  # set to idle color
        strip.show()
        #mixer.voice[1].play(marchWav, loop=False)
        print("changing color " + str(color))


    if not switch2.value:
        for j in range(NUM_PIXELS):
            if(j>=65 and j<=85):
                strip[j] = [255,255,255]
            else:
                strip[j] = colorwheel2tuple(color)

        if not setup:
            mixer.voice[1].play(laserHitWav, loop=False)
        strip.show()
        time.sleep(0.25)
        strip.fill(color)
        strip.show()

    if not switch.value:  # button pressed?
        last_motion_at = time.monotonic()
        switched_pressed_duration = 0
        switch_pressed_at = time.monotonic()
        time.sleep(0.1)

        # Detect long press for setup mode
        while not switch.value:
            print(switched_pressed_duration)
            switched_pressed_duration = time.monotonic() - switch_pressed_at
            if switched_pressed_duration >= 2.0:
                break
            time.sleep(0.2)

        if switched_pressed_duration >= 2.0 and not awake:
            if not setup:
                print("show")
                enable.value = True
                setup = True
            else:
                #blink_switch_led(4)
                awake = False
                setup = False
                print("setup exited")
                mixer.voice[2].play(helloThere, loop=False)
                enable.value = False

        elif setup:
            print("setup")
            speaker.play(mixer)
            mixer.voice[2].play(setupMode, loop=False)
        elif awake:
            power("off", 1.15, True)  # Power down
            awake = False
            setup = False
            mode = 0  # OFF mode now
            enable.value = False
        else:
            enable.value = True
            power("on", 0.5, False)  # Power up!
            awake = True
            setup = False
            speaker.play(mixer)
            mixer.voice[0].level = 0.2
            mixer.voice[0].play(idleWav, loop=True)
            # play_wav('idle', loop=True)     # Play background hum sound
            mode = 1  # ON (idle) mode now


    # Motion detection
    if awake or setup:
        x, y, z = accel.acceleration
        accel_squared = z * z + x * x

        if accel_squared > IDLE:
            last_motion_at = time.monotonic()
            #pulse = Pulse(strip, speed=0.01, period=10, color=color)
            #pulse.animate()

        if (time.monotonic() - last_motion_at) > 90.0:
            if awake:
                power("off", 1.15, True)  # Power down
                awake = False
                setup = False
                mode = 0  # OFF mode now
                enable.value = False
            awake = False
            setup = False


        # Action loop
        if awake and not setup:
            if accel_squared > HIT:
                print("hit")
                for j in range(NUM_PIXELS):
                    if(j>=75 and j<=100):
                        strip[j] = [255,255,255]
                    else:
                        strip[j] = colorwheel2tuple(color)

                hit = playHit(random.randint(1, 2))
                mixer.voice[2].play(hit, loop=False)
                strip.show()
                time.sleep(0.25)
                strip.fill(color)
                strip.show()

            elif accel_squared > SWING:
                print("swing")
                swing = playSwing(random.randint(1, 3))
                mixer.voice[playCounter].play(swing, loop=False)
                if(playCounter < 6):
                    playCounter = playCounter + 1
                else:
                    playCounter = 2
                strip.brightness = 1   # make blinding
                strip.fill(color)
                strip.show()

