from adafruit_circuitplayground.express import cpx

while True:
    if cpx.touch_A1:
        print('Touched 1!')
