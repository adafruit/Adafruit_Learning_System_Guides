import time

import board
import pwmio

piezo = pwmio.PWMOut(board.D2, duty_cycle=0,
                       frequency=440, variable_frequency=True)

while True:
    for f in (262, 294, 330, 349, 392, 440, 494, 523):
        piezo.frequency = f
        piezo.duty_cycle = 65536 // 2  # on 50%
        time.sleep(0.25)  # on for 1/4 second
        piezo.duty_cycle = 0  # off
        time.sleep(0.05)  # pause between notes
    time.sleep(0.5)
