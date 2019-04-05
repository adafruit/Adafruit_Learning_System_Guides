"""
Self balancing 2 wheeled bot using a PID controller.
See https://en.wikipedia.org/wiki/PID_controller

Adafruit invests time and resources providing this open source code.
Please support Adafruit and open source hardware by purchasing
products from Adafruit!

Written by Dave Astels for Adafruit Industries
Copyright (c) 2018 Adafruit Industries
Licensed under the MIT license.

All text above must be included in any redistribution.
"""


import time
import array
import math
import busio
import board
from adafruit_seesaw.seesaw import Seesaw
from adafruit_seesaw.pwmout import PWMOut
from adafruit_motor import servo
from digitalio import DigitalInOut, Direction
import adafruit_lsm9ds0

# Parameters
SAMPLE_INTERVAL = 0.02
ACCEL_ZERO_ADJUST = 0.25

SERVO1_ZERO_ADJUST = -0.015
SERVO2_ZERO_ADJUST = -0.015

# Tilt signal LED
led = DigitalInOut(board.D13)
led.direction = Direction.OUTPUT
led.value = False

# i@c: accelerometer and CRICKIT
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_lsm9ds0.LSM9DS0_I2C(i2c)
seesaw = Seesaw(i2c)

# UART
uart = busio.UART(board.TX, board.RX, baudrate=115200)

# Servos
pwm1 = PWMOut(seesaw, 17)
pwm1.frequency = 50
servo1 = servo.ContinuousServo(pwm1, min_pulse=500, max_pulse=2500)

pwm2 = PWMOut(seesaw, 16)
pwm2.frequency = 50
servo2 = servo.ContinuousServo(pwm2, min_pulse=500, max_pulse=2500)

# Stop the servos
servo1.throttle = SERVO1_ZERO_ADJUST
servo2.throttle = SERVO2_ZERO_ADJUST


def adjust(original, op, value):
    """Return an adjusted value based on the original, the operation,
       and the supplied value"""
    if op == 61:                          # =
        return value
    elif op == 43:                        # +
        return original + value
    else:
        return original - value


def report(kp, ki, kd):
    """Inner function to write the constants to the UART"""
    uart.write("KP: {0: 0.3f}  KI: {1: 0.3f}  KD: {2: 0.3f}\r\n".format(kp, ki, kd))

# A line was received via the UART, process it

def process_command(cmd, kp, ki, kd):
    """Process a command line from the UART.
    cmd is the list of bytes received via the UART
    kp, ki, and kd are the current constant values
    Returns new constant values (unchanged in the cases of an error)
    """

    print(cmd[0])
    if cmd[0] == 63:                      # ?
        report(kp, ki, kd)
    elif cmd[0] not in [112, 105, 100]:   # p/i/d
        uart.write("Bad parameter\r\n")
    elif len(cmd) > 1:
        var = cmd[0]
        op = cmd[1]
        if op not in [61, 43, 45]:        # =/+/-
            uart.write("Bad operation\r\n")
            return (kp, ki, kd)

        value = 0.0
        try:
            value = float(cmd[2:])                   # the value to adjust by
        except ValueError:
            uart.write("Bad value\r\n")
            return (kp, ki, kd)

        if var == 112:                    # p
            kp = adjust(kp, op, value)
        elif var == 105:                  # i
            ki = adjust(ki, op, value)
        else:                             # d
            kd = adjust(kd, op, value)
        report(kp, ki, kd)
    else:
        uart.write("Bad command\r\n")

    return (kp, ki, kd)


def limit(x):
    """Limit the argument to the range -1.0 to 1.0"""
    return max([-1.0, min([1.0, x])])

Kp = 1.000
Ki = 0.100
Kd = 0.000

iterm = 0.0
dterm = 0.0

extreme_z_count = 0
error = 0.0
previous_error = 0.0
previous_time = 0.0
output = 0.0
cmd_buffer = array.array("B", [0] * 8)
cmd_buffer_index = 0

while True:
    loop_start_time = time.monotonic()

    # Process UART input and process complete lines
    if uart.in_waiting > 0:
        ch = uart.read(1)
        if cmd_buffer_index > 7:
            cmd_buffer_index = 0
            uart.write("command too long.. ignored\r\n")
        else:
            uart.write(ch)
            if ch == 13:                  # \r
                if cmd_buffer_index > 0:
                    Kp, Ki, Kd = process_command(cmd_buffer[0:cmd_buffer_index], Kp, Ki, Kd)
                cmd_buffer_index = 0
            else:
                cmd_buffer[cmd_buffer_index] = ch[0]
                cmd_buffer_index += 1
        continue


    _, _, z = sensor.accelerometer
    # print("z: {0: 0.3f}, adj: {1: 0.3f}".format(z, z + ACCEL_ZERO_ADJUST))

    # Check if the bot fell over: a high Z value for a second.
    # If so stop the servos and blink the tilt LED
    # When it's righted, continue
    if math.fabs(z) >= 6.0:
        extreme_z_count += 1
        if extreme_z_count > 50:
            servo1.throttle = 0.0
            servo2.throttle = 0.0
            while math.fabs(z) >= 6.0:
                led.value = True
                time.sleep(0.2)
                led.value = False
                time.sleep(0.2)
                _, _, z = sensor.accelerometer
                # print("z: {0: 03f}".format(z))
            extreme_z_count = 0
            previous_error = 0.0
            iterm = 0.0
            previous_time = loop_start_time
            error = 0.0
            continue
    else:
        extreme_z_count = 0

    # process the error
    error = (z + ACCEL_ZERO_ADJUST) / 10.0

    delta_time = loop_start_time - previous_time
    delta_error = error - previous_error

    if previous_time > 0.0:
        iterm += error * delta_time
        dterm = 0.0
        if delta_time > 0:
            dterm = delta_error / delta_time

        output = limit((Kp * error) + (Ki * iterm) + (Kd * dterm))
        servo1.throttle = limit(output + SERVO1_ZERO_ADJUST)
        servo2.throttle = limit((-1 * output) + SERVO2_ZERO_ADJUST)

    previous_error = error
    previous_time = loop_start_time

    time.sleep(max([0.0, SAMPLE_INTERVAL - (time.monotonic() - loop_start_time)]))
