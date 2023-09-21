# SPDX-FileCopyrightText: 2017 John Park for Adafruit Industries
# Modified 2023 by Erin St Blaine
#
# SPDX-License-Identifier: MIT


import board
import pulseio
import neopixel
import adafruit_irremote
from rainbowio import colorwheel
from adafruit_led_animation.sequence import AnimationSequence
from adafruit_led_animation.animation.solid import Solid
from adafruit_led_animation.animation.rainbow import Rainbow
from adafruit_led_animation.animation.sparkle import Sparkle
from adafruit_led_animation.animation.rainbowchase import RainbowChase
from adafruit_led_animation.animation.rainbowcomet import RainbowComet
from adafruit_led_animation.animation.chase import Chase
from adafruit_led_animation.animation.comet import Comet
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.animation.SparklePulse import SparklePulse
import adafruit_led_animation.color as color

NUMBER_OF_PIXELS = 85
pixels = neopixel.NeoPixel(board.D13, NUMBER_OF_PIXELS)

# Define the brightness levels and their corresponding values
# Start at a non-blinding brightness.
BRIGHTNESS_LEVELS = (0.025, 0.05, 0.1, 0.2, 0.4, 0.6, 0.7, 0.8, 1.0)
brightness_index = 2
pixels.brightness = BRIGHTNESS_LEVELS[brightness_index]

pulsein = pulseio.PulseIn(board.A0, maxlen=120, idle_state=True)
decoder = adafruit_irremote.GenericDecode()

SPEEDS = (0.25, 0.125, 0.1, 0.08, 0.05, 0.02, 0.01)  # Customize speed levels here
speed_index = 4

def setup_animations():
    """Set up all the available animations."""
    # Animation Setup
    rainbow = Rainbow(pixels, speed=SPEEDS[speed_index], period=2, name="rainbow", step=3)
    sparkle = Sparkle(pixels, speed=SPEEDS[speed_index], color=color.WHITE, name="sparkle")
    solid = Solid(pixels, color=colorwheel(0), name="solid")
    # Make the Solid animation changeable quickly.
    solid.speed = 0.01
    off = Solid(pixels, color=color.BLACK, name="off")
    rainbow = Rainbow(pixels, speed=SPEEDS[speed_index], period=6, name="rainbow", step=2.4)
    rainbow_carousel = RainbowChase(pixels, speed=SPEEDS[speed_index], size=4, spacing=1, step=20)
    party_chase = RainbowChase(pixels, speed=SPEEDS[speed_index], size=1, spacing=5, step=6)
    rainbow_chase2 = RainbowChase(pixels, speed=SPEEDS[speed_index], size=10, spacing=1, step=18)
    chase = Chase(pixels, speed=SPEEDS[speed_index], color=color.RED, size=1, spacing=6)
    rainbow_comet2 = RainbowComet(
        pixels, speed=0.02, tail_length=104, colorwheel_offset=80, bounce=False)
    rainbow_comet3 = RainbowComet(
        pixels, speed=SPEEDS[speed_index], tail_length=25,
        colorwheel_offset=128, step=4, bounce=False)
    lava = Comet(pixels, speed=SPEEDS[speed_index],
                 color=color.ORANGE, tail_length=40, bounce=False)
    sparkle1 = Sparkle(pixels, speed=SPEEDS[speed_index], color=color.BLUE, num_sparkles=10)
    pulse = Pulse(pixels, speed=0.1, color=color.AMBER, period=3)
    sparkle_pulse = SparklePulse(pixels, speed=0.05, period=2, color=color.JADE, max_intensity=3)

    # Animation Sequence Playlist -- rearrange to change the order of animations
    # advance_interval is None, so the animations change only under user control.
    all_animations = AnimationSequence(
        rainbow,
        rainbow_chase2,
        rainbow_carousel,
        party_chase,
        rainbow_comet2,
        rainbow_comet3,
        sparkle_pulse,
        pulse,
        chase,
        rainbow,
        solid,
        sparkle,
        lava,
        sparkle1,
        off,
        auto_clear=True,
        auto_reset=True,
        advance_interval=None,
    )
    return all_animations

# IR Remote Mapping for the Adafruit mini IR remote
# https://www.adafruit.com/product/389

CMD_1 = 247          #  1: [255, 2, 247, 8]
CMD_2 = 119          #  2: [255, 2, 119, 136]
CMD_3 = 183          #  3: [255, 2, 183, 72]
CMD_4 = 215          #  4: [255, 2, 215, 40]
CMD_5 = 87           #  5: [255, 2, 87, 168]
CMD_6 = 151          #  6: [255, 2, 151, 104]
CMD_7 = 231          #  7: [255, 2, 231, 24]
CMD_8 = 103          #  8: [255, 2, 103, 152]
CMD_9 = 167          #  9: [255, 2, 167, 88]
CMD_0 = 207          #  0: [255, 2, 207, 48]

CMD_UP = 95          # ^ : [255, 2, 95, 160]
CMD_DOWN = 79        # v : [255, 2, 79, 176]
CMD_RIGHT = 175      # > : [255, 2, 175, 80]
CMD_LEFT = 239       # < : [255, 2, 239, 16]

CMD_ENTER_SAVE = 111 # Enter/Save: [255, 2, 111, 144]
CMD_SETUP = 223      # Setup: [255, 2, 223, 32]
CMD_STOP_MODE = 159  # Stop/Mode: [255, 2, 159, 96]
CMD_BACK = 143       # Back: [255, 2, 143, 112]

CMD_VOL_DOWN = 255   # Vol - : [255, 2, 255, 0]
CMD_VOL_UP = 191     # Vol + : [255, 2, 191, 64]
CMD_PLAY_PAUSE = 127 # Play/Pause: [255, 2, 127, 128]
CMD_REPEAT = True    # short code: repeat of previous command


def read_command():
    """Try to read an IR command. If none seen or if error, return None."""
    try:
        pulses = decoder.read_pulses(pulsein, blocking=False)
        if pulses:
            code = decoder.decode_bits(pulses)
            if len(code) > 3:
                print("Decoded:", code)
                return code[2]
        # if code is less than or equal to 3 characters long or no pulses received
        return None
    except adafruit_irremote.IRNECRepeatException:  # unusual short code!
        print("NEC repeat!")
        return CMD_REPEAT
    except adafruit_irremote.IRDecodeException as e:  # failed to decode
        print("Failed to decode:", e)
        return None
    except MemoryError as e:
        print("Memory error: ", e)
        return None

SOLID_COLORS = {
    CMD_0 : color.BLACK,
    CMD_1 : color.RED,
    CMD_2 : color.GREEN,
    CMD_3 : color.WHITE,
    CMD_4 : color.BLUE,
    CMD_5 : color.PINK,
    CMD_6 : color.YELLOW,
    CMD_7 : color.PURPLE,
    CMD_8 : color.TEAL,
    CMD_9 : color.ORANGE,
    }

# main program

animations = setup_animations()
last_command = None

while True:
    command = read_command()
    if command is None:
        # Nothing read, just keep animating.
        animations.animate() # Run one animation cycle.
        continue

    if command == CMD_REPEAT:
        command = last_command

    last_command = command
    print("Command", command)


    # See if the command was a number button. Fetch the animation color if it is.
    solid_color = SOLID_COLORS.get(command, None)
    if solid_color:
        # Jump to the "solid" animation. Set its color to
        # the chosen color.
        animations.activate("solid")
        animations.current_animation.color = solid_color
    elif command == CMD_LEFT:
        animations.previous()
    elif command == CMD_RIGHT:
        animations.next()
    elif command == CMD_DOWN:
        # Slow down current animation
        if speed_index > 0:
            speed_index -= 1
            animations.current_animation.speed = SPEEDS[speed_index]
        print("speed of current animation is now:", animations.current_animation.speed)
    elif command == CMD_UP:
        if speed_index < len(SPEEDS) - 1:
            speed_index += 1
            animations.current_animation.speed = SPEEDS[speed_index]
        print("speed of current animation is now:", animations.current_animation.speed)
    elif command == CMD_VOL_DOWN:
        if brightness_index > 0:
            brightness_index -= 1
            pixels.brightness = BRIGHTNESS_LEVELS[brightness_index]
        print("brightness:", pixels.brightness)
    elif command == CMD_VOL_UP:
        if brightness_index < len(BRIGHTNESS_LEVELS) - 1:
            brightness_index += 1
            pixels.brightness = BRIGHTNESS_LEVELS[brightness_index]
            print("brightness:", pixels.brightness)
