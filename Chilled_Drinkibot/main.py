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
pump.direction = Direction.OUTPUT

chillTime = 10  # How many seconds of cooling

pumpTime = 15  # How many seconds of pumping

while True:
    # we could also just do "led.value = not button.value" !
    if button.value:
        print('not')
        led.value = False
        chiller.value = False
        pumping.value = False
    else:
        print('pressed')
        led.value = True
        chiller.value = True
        pump.value = True
        time.sleep(chillTime)

    time.sleep(0.01)  # debounce delay
