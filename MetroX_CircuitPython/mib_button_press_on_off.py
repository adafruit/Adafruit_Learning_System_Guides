"""
'button_press_on_off.py'.

=================================================
lightswitch-like operation with two buttons and a led
"""

import board
import digitalio

led = digitalio.DigitalInOut(board.D13)
led.switch_to_output()
btn1 = digitalio.DigitalInOut(board.D2)
btn1.switch_to_input()
btn2 = digitalio.DigitalInOut(board.D3)
btn2.switch_to_input()


while True:
    if not btn1.value:
        led.value = False
    elif not btn2.value:
        led.value = True
