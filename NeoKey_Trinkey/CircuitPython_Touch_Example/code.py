"""NeoKey Trinkey Capacitive Touch Example"""
import time
import board
import touchio

touch = touchio.TouchIn(board.TOUCH)

while True:
    if touch.value:
        print("Pad touched!")
    time.sleep(0.1)
