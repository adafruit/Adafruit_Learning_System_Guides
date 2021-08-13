# Chilled Drinkibot

import time

import board
from digitalio import DigitalInOut, Direction, Pull

led = DigitalInOut(board.D2)  # Button LED
led.direction = Direction.OUTPUT

button = DigitalInOut(board.D0)
button.direction = Direction.INPUT
button.pull = Pull.UP

chiller = DigitalInOut(board.D3)  # Pin to control the chiller and fan
chiller.direction = Direction.OUTPUT

pump = DigitalInOut(board.D4)  # Pin to control the pump
pump.direction = Direction.OUTPUT

chillTime = 5  # How many _minutes_ of cooling

pumpTime = 35  # How many seconds of pumping

while True:
    # we could also just do "led.value = not button.value" !
    if button.value:
        print('not')
        led.value = False  # turn OFF LED
        chiller.value = False  # turn OFF chiller
        pump.value = False  # turn OFF pump
    else:
        print('pressed')
        led.value = True  # turn ON LED
        chiller.value = True  # turn ON chiller
        time.sleep(chillTime * 60)  # wait chiller time (in seconds)
        chiller.value = False  # turn OFF chiller
        pump.value = True  # turn ON pump
        time.sleep(pumpTime)  # wait pump time
        pump.value = False  # turn OFF pump
        led.value = False  # turn OFF LED

    time.sleep(0.01)  # debounce delay
