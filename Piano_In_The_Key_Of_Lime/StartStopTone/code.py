from adafruit_circuitplayground import cp

while True:
    if cp.touch_A1:
        cp.start_tone(262)
    elif cp.touch_A2:
        cp.start_tone(294)
    else:
        cp.stop_tone()
