# main.py - code to test the Adafruit CRICKIT board with
# the BBC micro:bit and MicroPython (NOT CircuitPython)
# MIT License by Limor Fried and Mike Barela, 2019
# This code requires the seesaw.py module as a driver
import time
import seesaw

seesaw.init()
while True:
    # Touch test - check with the Mu plotter!
    print("Touch: \n(", end="")
    for i in range(1, 5):
        print(seesaw.read_touch(i), end=", \t")
    print(")")

    # analog read signal test - assumes analog input pin 8
    print("Analog signal:\n(", end="")
    print(seesaw.analog_read(8), end=", \t")
    print(")")

    seesaw.write_digital(2, 0)  # Assumes LED on Signal pin 2
    time.sleep(0.1)
    seesaw.write_digital(2, 1)
    time.sleep(0.1)

    if seesaw.read_digital(7):  # Assumes button on Signal pin 7
        print("pin high")
    else:
        print("pin low")

    # Servo test - assumes servo on Servo position 1 on CRICKIT
    seesaw.servo(1, 0, min=0.5, max=2.5)
    time.sleep(0.5)
    seesaw.servo(1, 90, min=0.5, max=2.5)
    time.sleep(0.5)
    seesaw.servo(1, 180, min=0.5, max=2.5)
    time.sleep(0.5)

    # Drive test
    # seesaw.drive(1, 0.2)
    # seesaw.drive(2, 0.4)
    # seesaw.drive(3, 0.6)
    # seesaw.drive(4, 0.8)

    # motor test - assumes a DC motor on CRICKIT Motor 1 terminals
    seesaw.motor(1, 1)
    time.sleep(0.5)
    seesaw.motor(1, 0)
    time.sleep(0.5)
    seesaw.motor(1, -1)
    time.sleep(0.5)
    seesaw.motor(1, 0)

    time.sleep(0.1)
