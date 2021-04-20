import time
import board
import neopixel
import touchio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

#  setup for onboard neopixels
pixel_pin = board.NEOPIXEL
num_pixels = 4

pixels = neopixel.NeoPixel(pixel_pin, num_pixels, brightness=0.05, auto_write=False)

#  setup for cap touch pads
top_touch = touchio.TouchIn(board.TOUCH1)
bot_touch = touchio.TouchIn(board.TOUCH2)

#  HID keyboard input setup
keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)
#  variable for the ALT key
alt_key = Keycode.ALT

#  rainbow cycle animation
def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def rainbow_cycle(wait):
    for j in range(255):
        for i in range(num_pixels):
            rc_index = (i * 256 // num_pixels) + j
            pixels[i] = wheel(rc_index & 255)
        pixels.show()
        time.sleep(wait)

#  variables for colors
RED = (255, 0, 0)
GREEN = (0, 255, 0)

#  state machines
#  cap touch debouncing
bot_pressed = False
top_pressed = False
#  default mute states
mic_mute = True
vid_mute = True
#  time.monotonic() tracker
clock = time.monotonic()
#  tracking for initiating an exit from the meeting
escape = False
escape_1 = False
escape_2 = False

while True:
    #  cap touch debouncing
    if not top_touch.value and top_pressed:
        top_pressed = False
    if not bot_touch.value and bot_pressed:
        bot_pressed = False
    #  if your mic is muted...
    if mic_mute:
        #  neopixels are red
        pixels[0] = RED
        pixels[1] = RED
        pixels.show()
    #  if your camera is muted...
    if vid_mute:
        #  neopixels are red
        pixels[2] = RED
        pixels[3] = RED
        pixels.show()
    #  if your mic is NOT muted...
    if not mic_mute:
        #  neopixels are green
        pixels[0] = GREEN
        pixels[1] = GREEN
        pixels.show()
    #  if your camera is NOT muted...
    if not vid_mute:
        #  neopixels are green
        pixels[2] = GREEN
        pixels[3] = GREEN
        pixels.show()
    #  if you are leaving the meeting...
    if escape:
        #  neopixels are rainbow
        rainbow_cycle(0)
        #  resets exit states
        escape = False
        escape_1 = False
        escape_2 = False
        mic_mute = True
        vid_mute = True
    #  if you press the top touch cap touch pad...
    if (top_touch.value and not top_pressed):
        top_pressed = True
        #  start time count for exit
        clock = time.monotonic()
        #  slight delay so that you don't automatically mute/unmute
        #  if your intent is to exit
        time.sleep(0.12)
        #  if after the delay you're still pressing the cap touch pad...
        if top_touch.value and top_pressed:
            print("escape top")
            #  initial escape state is set to true
            escape_1 = True
        #  if you aren't still pressing the cap touch pad...
        else:
            #  if your camera was muted...
            if vid_mute:
                print("top")
                #  your camera is NOT muted
                vid_mute = False
                #  resets escape state just in case
                escape_1 = False
            #  if your camera was NOT muted...
            elif not vid_mute:
                print("top")
                #  your camera is muted
                vid_mute = True
                #  resets escape state just in case
                escape_1 = False
            #  sends camera mute/unmute shortcut
            keyboard.send(alt_key, Keycode.V)
    #  if you press the top touch cap touch pad...
    if (bot_touch.value and not bot_pressed):
        bot_pressed = True
        #  start time count for exit
        clock = time.monotonic()
        #  slight delay so that you don't automatically mute/unmute
        #  if your intent is to exit
        time.sleep(0.12)
        #  if after the delay you're still pressing the cap touch pad...
        if bot_touch.value and bot_pressed:
            print("escape bot")
            #  initial escape state is set to true
            escape_2 = True
        #  if you aren't still pressing the cap touch pad...
        else:
            #  if your mic was muted...
            if mic_mute:
                print("bot")
                #  your mic is NOT muted
                mic_mute = False
                #  resets escape state just in case
                escape_2 = False
            #  if your mic was NOT muted...
            elif not mic_mute:
                print("bot")
                #  your mic is muted
                mic_mute = True
                #  resets escape state just in case
                escape_2 = False
            #  sends mic mute/unmute shortcut
            keyboard.send(alt_key, Keycode.A)
    #  if you held down both cap touch pads and 2 seconds has passed...
    if ((clock + 2) < time.monotonic()) and (escape_1 and escape_2):
        print("escape")
        #  full escape state is set
        escape = True
        #  sends exit meeting shortcut
        keyboard.send(alt_key, Keycode.Q)
        #  brief delay for confirmation window to open
        time.sleep(0.1)
        #  sends enter to confirm meeting exit
        keyboard.send(Keycode.ENTER)
