from adafruit_circuitplayground import cp

while True:
    if cp.switch:
        print("Slide switch off!")
        cp.pixels.fill((0, 0, 0))
        cp.stop_tone()
        continue
    if cp.touch_A4:
        print('Touched A4!')
        cp.pixels.fill((15, 0, 0))
        cp.start_tone(262)
    elif cp.touch_A5:
        print('Touched A5!')
        cp.pixels.fill((15, 5, 0))
        cp.start_tone(294)
    elif cp.touch_A6:
        print('Touched A6!')
        cp.pixels.fill((15, 15, 0))
        cp.start_tone(330)
    elif cp.touch_A7:
        print('Touched A7!')
        cp.pixels.fill((0, 15, 0))
        cp.start_tone(349)
    elif cp.touch_A1:
        print('Touched A1!')
        cp.pixels.fill((0, 15, 15))
        cp.start_tone(392)
    elif cp.touch_A2 and not cp.touch_A3:
        print('Touched A2!')
        cp.pixels.fill((0, 0, 15))
        cp.start_tone(440)
    elif cp.touch_A3 and not cp.touch_A2:
        print('Touched A3!')
        cp.pixels.fill((5, 0, 15))
        cp.start_tone(494)
    elif cp.touch_A2 and cp.touch_A3:
        print('Touched "8"!')
        cp.pixels.fill((15, 0, 15))
        cp.start_tone(523)
    else:
        cp.pixels.fill((0, 0, 0))
        cp.stop_tone()
