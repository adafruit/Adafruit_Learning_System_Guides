import time
from adafruit_circuitplayground.express import cpx

while True:
    if cpx.touch_A1:
        print("Touched A1!")
    if cpx.touch_A2:
        print("Touched A2!")
    if cpx.touch_A3:
        print("Touched A3!")
    if cpx.touch_A4:
        print("Touched A4!")
    if cpx.touch_A5:
        print("Touched A5!")
    if cpx.touch_A6:
        print("Touched A6!")
    if cpx.touch_A7:
        print("Touched A7!")
    time.sleep(0.1)
