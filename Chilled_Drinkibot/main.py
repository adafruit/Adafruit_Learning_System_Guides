# Chilled Drinkibot

from digitalio import DigitalInOut, Direction, Pull
import board
import time

led = DigitalInOut(board.D2)  # Button LED
led.direction = Direction.OUTPUT

button = DigitalInOut(board.D0)
button.direction = Direction.INPUT
button.pull = Pull.UP

chiller = DigitalInOut(board.D3)  # Pin to control the chiller and fan
chiller.direction = Direction.OUTPUT

pump = DigitalInOut(board.D4)  # Pin to control the pump

chillTime = 10  # How many seconds of cooling

pumpTime = 5  # How many seconds of pumping

while True:
    # we could also just do "led.value = not button.value" !
    if button.value:
        led.value = False
        chiller.value = True
        time.sleep(chillTime)
    else:
        led.value = True
        chiller.value = False

    time.sleep(0.01)  # debounce delay
