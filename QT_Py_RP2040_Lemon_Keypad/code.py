import time
import digitalio
import board
import usb_hid
import neopixel
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
from adafruit_led_animation.animation.pulse import Pulse
from adafruit_led_animation.animation.solid import Solid
from adafruit_led_animation.group import AnimationGroup
from adafruit_led_animation.sequence import AnimationSequence

from adafruit_led_animation.color import WHITE, BLACK

pixel_pin = board.A3
num_pixels = 7

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=.3, auto_write=False)
internal_pixel = neopixel.NeoPixel(board.NEOPIXEL, 1, brightness=1, auto_write=False)

# The button pins we'll use, each will have an internal pullup
buttonpins = [board.A0, board.A1, board.A2, board.D8, board.D9, board.D10]

# The keycode sent for each button, will be paired with a control key
buttonkeys = [
    ConsumerControlCode.PLAY_PAUSE,
    ConsumerControlCode.FAST_FORWARD,
    ConsumerControlCode.VOLUME_INCREMENT,
    ConsumerControlCode.MUTE,
    ConsumerControlCode.VOLUME_DECREMENT,
    ConsumerControlCode.REWIND
]

# the keyboard object!
cc = ConsumerControl(usb_hid.devices)
# our array of button objects
buttons = []

# make all pin objects, make them inputs w/pullups
for pin in buttonpins:
    button = digitalio.DigitalInOut(pin)
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP
    buttons.append(button)

animations = AnimationSequence(
    AnimationGroup(
        Pulse(pixels, speed=0.05, color=WHITE, period=6),
        Solid(internal_pixel,color=BLACK),
    ),
)

print("Waiting for button presses")

while True:
    # animate neopixel jewel
    animations.animate()
    # check each button
    for button in buttons:
        if not button.value:  # pressed?
            i = buttons.index(button)

            print("Button #%d Pressed" % i)

            while not button.value:
                pass  # wait for it to be released!
            # type the keycode!
            k = buttonkeys[i]  # get the corresp. keycode
            cc.send(k)
    time.sleep(0.01)
