"""
'potentiometer_plotter.py'.

=================================================
using Mu-Editor v1.0.0b15+ to plot potentiometer values
"""
import time
import analogio
import board
from simpleio import map_range

pote = analogio.AnalogIn(board.A0)

sensor_val = 0

while True:
    sensor_val = pote.value
    sensor_val = map_range(sensor_val, 0, 65296, -1000, 1000)
    tup = (sensor_val,)
    print(tup)
    time.sleep(1)
