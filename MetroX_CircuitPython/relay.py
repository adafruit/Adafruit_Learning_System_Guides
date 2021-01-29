"""
'relay.py'.

=================================================
drives a small relay
"""

import time
import board
import digitalio

RELAY = digitalio.DigitalInOut(board.D2)
RELAY.switch_to_output()

while True:
    RELAY.value = not RELAY.value
    time.sleep(1)
