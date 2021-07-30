"""
CircuitPython Digital Input Example - Blinking an LED using a button switch.

Update BUTTON_PIN to the pin to which you have connected the button (in the case of an external
button), or to the pin connected to the built-in button (in the case of boards with built-in
buttons).

For example:
If you connected a button switch to D1, change BUTTON_PIN to D1.
If using a CPX, to use button A, change BUTTON_PIN to BUTTON_A.
"""
import board
import digitalio

led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT

button = digitalio.DigitalInOut(board.BUTTON_PIN)
button.switch_to_input(pull=digitalio.Pull.UP)

while True:
    if not button.value:
        led.value = True
    else:
        led.value = False
