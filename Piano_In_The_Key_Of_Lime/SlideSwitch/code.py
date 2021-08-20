from adafruit_circuitplayground.express import cpx

while True:
    if cpx.switch:
        print("Slide switch off!")
    else:
        print("Slide switch on!")
