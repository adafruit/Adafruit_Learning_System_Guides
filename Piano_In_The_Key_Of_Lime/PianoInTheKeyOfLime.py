from adafruit_circuitplayground.express import cpx

while True:
    if cpx.switch:
        print("Slide switch off!")
        cpx.pixels.fill((0, 0, 0))
        cpx.stop_tone()
        continue
    if cpx.touch_A4:
        print('Touched A4!')
        cpx.pixels.fill((15, 0, 0))
        cpx.start_tone(262)
    elif cpx.touch_A5:
        print('Touched A5!')
        cpx.pixels.fill((15, 5, 0))
        cpx.start_tone(294)
    elif cpx.touch_A6:
        print('Touched A6!')
        cpx.pixels.fill((15, 15, 0))
        cpx.start_tone(330)
    elif cpx.touch_A7:
        print('Touched A7!')
        cpx.pixels.fill((0, 15, 0))
        cpx.start_tone(349)
    elif cpx.touch_A1:
        print('Touched A1!')
        cpx.pixels.fill((0, 15, 15))
        cpx.start_tone(392)
    elif cpx.touch_A2 and not cpx.touch_A3:
        print('Touched A2!')
        cpx.pixels.fill((0, 0, 15))
        cpx.start_tone(440)
    elif cpx.touch_A3 and not cpx.touch_A2:
        print('Touched A3!')
        cpx.pixels.fill((5, 0, 15))
        cpx.start_tone(494)
    elif cpx.touch_A2 and cpx.touch_A3:
        print('Touched "8"!')
        cpx.pixels.fill((15, 0, 15))
        cpx.start_tone(523)
    else:
        cpx.pixels.fill((0, 0, 0))
        cpx.stop_tone()
