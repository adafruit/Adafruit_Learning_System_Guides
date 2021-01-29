"""
'potentiometer.py'.

=================================================
control a LED's brightness using a potentiometer
"""
import time
import digitalio
import analogio
import board

LED = digitalio.DigitalInOut(board.D13)
LED.switch_to_output()
POT = analogio.AnalogIn(board.A0)

SENSOR_VAL = 0

while True:
    # potentiometer value/max potentiometer value
    SENSOR_VAL = POT.value / 65536
    print(SENSOR_VAL)
    LED.value = True
    time.sleep(SENSOR_VAL)
    LED.value = False
    time.sleep(SENSOR_VAL)
