from adafruit_circuitplayground.express import cpx

while True:
    if cpx.shake():
        print("Shake detected!")
