# CircuitPython code for the Gyroscopic Marble Maze
# Adafruit Industries, 2019. MIT License
import time
import board
import pulseio
from adafruit_motor import servo
import simpleio
from adafruit_circuitplayground.express import cpx

# create a PWMOut object on Pin A2.
pwm1 = pulseio.PWMOut(board.A1, duty_cycle=2 ** 15, frequency=50)
pwm2 = pulseio.PWMOut(board.A2, duty_cycle=2 ** 15, frequency=50)

# Create a servo object, my_servo.
my_servo1 = servo.Servo(pwm1)
my_servo2 = servo.Servo(pwm2)

NUM_READINGS = 8
roll_readings = [90] * NUM_READINGS
pitch_readings = [90] * NUM_READINGS

def Average(lst):
    return sum(lst) / len(lst)

while True:
    x, y, z = cpx.acceleration  # x = green
    print((x, y, z))

    roll = simpleio.map_range(x, -9.8, 9.8, 0, 180)
    roll_readings = roll_readings[1:]
    roll_readings.append(roll)
    roll = Average(roll_readings)

    print(roll)

    my_servo1.angle = roll

    pitch = simpleio.map_range(y, -9.8, 9.8, 0, 180)
    pitch_readings = pitch_readings[1:]
    pitch_readings.append(pitch)
    pitch = Average(pitch_readings)

    print(pitch)

    my_servo2.angle = pitch

    time.sleep(0.05)
