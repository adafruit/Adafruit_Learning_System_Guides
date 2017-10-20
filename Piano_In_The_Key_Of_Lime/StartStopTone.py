from adafruit_circuitplayground.express import cpx

while True:
    if cpx.touch_A1:
        cpx.start_tone(262)
    elif cpx.touch_A2:
        cpx.start_tone(294)
    else:
        cpx.stop_tone()
