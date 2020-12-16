"""CircuitPython Essentials Capacitive Touch example"""
import time
import board
import touchio

touch_pad = board.A0  # Will not work for Circuit Playground Express!
# touch_pad = board.A1  # For Circuit Playground Express

touch = touchio.TouchIn(touch_pad)

while True:
    if touch.value:
        print("Touched!")
    time.sleep(0.05)
