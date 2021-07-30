"""
CircuitPython Touch Input Example - Blinking an LED using a capacitive touch pad.

This example is meant for boards that have capacitive touch pads, and no simple way to wire up
a button. If there is a simple way to wire up a button, or a button built into the board, use
the standard Digital Input template and example.

Update TOUCH_PAD_PIN to the pin for the capacitive touch pad you wish you use.

For example:
If are using a BLM Badge and plan to use the first pad, change TOUCH_PAD_PIN to CAP1.
"""
import board
import digitalio
import touchio

led = digitalio.DigitalInOut(board.D13)
led.direction = digitalio.Direction.OUTPUT

touch = touchio.TouchIn(board.TOUCH_PAD_PIN)

while True:
    if touch.value:
        led.value = True
    else:
        led.value = False
