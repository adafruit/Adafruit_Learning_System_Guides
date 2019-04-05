"""Simple example to print when switch is pressed"""
import time
import digitalio
import board

switch = digitalio.DigitalInOut(board.D9)
switch.switch_to_input(pull=digitalio.Pull.UP)

while True:
    if not switch.value:
        print("Switch pressed!")
    time.sleep(0.1)
