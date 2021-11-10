from adafruit_circuitplayground import cp

while True:
    if cp.switch:
        print("Slide switch off!")
    else:
        print("Slide switch on!")
