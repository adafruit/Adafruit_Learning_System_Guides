from adafruit_circuitplayground.express import cpx

while True:
    if cpx.shake(shake_threshold=20):
        print("Shake detected!")
        cpx.red_led = True
