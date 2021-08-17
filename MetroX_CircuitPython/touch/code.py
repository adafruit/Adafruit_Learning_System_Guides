"""
'touch.py'
=================================================
capactive touch with the Adafruit Metro
requires:
- touchio
"""
import time
import board
import digitalio
import touchio

led = digitalio.DigitalInOut(board.D13)
led.switch_to_output()
touch = touchio.TouchIn(board.A1)

while True:
    if touch.value:
        led.value = True
    else:
        led.value = False
    time.sleep(1)
