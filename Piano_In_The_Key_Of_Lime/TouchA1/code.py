from adafruit_circuitplayground import cp

while True:
    if cp.touch_A1:
        print('Touched 1!')
