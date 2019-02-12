"""
'adafruit_io_stepper.py'
==================================
Example of using CircuitPython and
Adafruit IO to perform real-time
control of stepper motors over the
internet.

Dependencies:
    - Adafruit_Blinka
        (https://github.com/adafruit/Adafruit_Blinka)
    - Adafruit_CircuitPython_MotorKit
        (https://github.com/adafruit/Adafruit_CircuitPython_MotorKit)
    - Adafruit_IO_Python
        (https://github.com/adafruit/Adafruit_IO_Python)
"""
# Import Python Libraries
import time
import atexit
import threading
import random

# import Adafruit IO REST client.
from Adafruit_IO import Client, Feed, RequestError

# Import CircuitPython Libraries
from adafruit_motor import stepper as STEPPER
from adafruit_motorkit import MotorKit

# Set to your Adafruit IO key.
# Remember, your key is a secret,
# so make sure not to publish it when you publish this code!
ADAFRUIT_IO_KEY = ''

# Set to your Adafruit IO username.
# (go to https://accounts.adafruit.com to find your username)
ADAFRUIT_IO_USERNAME = ''

# Create an instance of the REST client.
aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)

# Stepper 1 Speed Feed
feed_step_1_steps = aio.feeds('stepper1steps')
feed_step_1_direction = aio.feeds('stepper1direction')
feed_step_1_step_size = aio.feeds('stepper1stepsize')

# create a default object, no changes to I2C address or frequency
kit = MotorKit()

# create empty threads (these will hold the stepper 1 and 2 threads)
st1 = threading.Thread()
st2 = threading.Thread()

# recommended for auto-disabling motors on shutdown!
def turnOffMotors():
    kit.stepper1.release()
    kit.stepper2.release()

atexit.register(turnOffMotors)
stepstyles = [STEPPER.SINGLE, STEPPER.DOUBLE, STEPPER.INTERLEAVE, STEPPER.MICROSTEP]

#TODO: Save previous state of stepper1/stepper2 IO RX's

# TODO: Fetch this data every 30sec
# Get stepper 1 configuration from IO
stepper1_steps = aio.receive(feed_step_1_steps.key)
stepper1_steps = int(stepper1_steps.value)
stepper_1_direction = aio.receive(feed_step_1_direction.key)
stepper1_step_size = aio.receive(feed_step_1_step_size.key)
print('Stepper 1 Configuration (from IO)')
print("%d steps" % stepper1_steps)
print('Step Size: ', stepper1_step_size.value)
print('Stepper Direction: ', stepper_1_direction.value)


def stepper_worker(stepper, numsteps, direction, stepper_name, style, show_steps=False):
    print("Steppin!")
    stepper_steps = numsteps
    print(stepper_steps)
    for _ in range(numsteps):
        stepper.onestep(direction=direction, style=style)
        if show_steps: # print out the steps and send to IO stepper slider
            stepper_steps -= 1
            print('Steps: ', stepper_steps)
            aio.send(feed_step_1_steps.key, stepper_steps)
            time.sleep(0.30)
    print("Done using ", stepper_name)

while True:
    # Stepper 1 Adafruit IO Configuration
    if not st1.isAlive(): # if thread is killed
        print('Retrieving Stepper 1 Config from IO...')
        stepper1_steps = aio.receive(feed_step_1_steps.key)
        stepper1_steps = int(stepper1_steps.value)
        if stepper1_steps is not 0: # check against if the feed value is 0
            stepper_1_direction = aio.receive(feed_step_1_direction.key)
            stepper1_step_size = aio.receive(feed_step_1_step_size.key)
            print('Stepper 1 Configuration (from IO)')
            print("%d steps" % stepper1_steps)
            print('Step Size: ', stepper1_step_size.value)
            print('Stepper Direction: ', stepper_1_direction.value)
            stepper_name = "Stepper 1"
            # Set Stepper Direction
            if stepper_1_direction.value == 'Forward':
                move_dir = STEPPER.FORWARD
                print("forward")
            elif stepper_1_direction.value == 'Backward':
                move_dir = STEPPER.BACKWARD
                print("backward")
            # Stepper 1 Thread
            st1 = threading.Thread(target=stepper_worker, args=(kit.stepper1,
                                                                stepper1_steps,
                                                                move_dir,
                                                                stepper_name,
                                                                stepstyles[STEPPER.SINGLE],))
            st1.start()
    # poll for new data every 30sec to avoid Adafruit IO Timeouts
    print('delaying...')
    time.sleep(30)

