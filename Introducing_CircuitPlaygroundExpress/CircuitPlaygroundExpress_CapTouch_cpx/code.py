from adafruit_circuitplayground.express import cpx

while True:
    if cpx.touch_A1:
        print('Touched 1!')
    elif cpx.touch_A2:
        print('Touched 2!')
    elif cpx.touch_A3:
        print('Touched 3!')
    elif cpx.touch_A4:
        print('Touched 4!')
    elif cpx.touch_A5:
        print('Touched 5!')
    elif cpx.touch_A6:
        print('Touched 6!')
    elif cpx.touch_A7:
        print('Touched 7!')
