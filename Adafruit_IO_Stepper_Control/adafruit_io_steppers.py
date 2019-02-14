"""
'adafruit_io_steppers.py'
==================================
Example of using CircuitPython and
Adafruit IO to control two stepper
motors over the internet.

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

# import Adafruit IO REST client.
from Adafruit_IO import Client, RequestError

# Import CircuitPython Libraries
from adafruit_motor import stepper as STEPPER
from adafruit_motorkit import MotorKit

# Set to your Adafruit IO key.
# Remember, your key is a secret,
# so make sure not to publish it when you publish this code!
ADAFRUIT_IO_KEY = 'YOUR_IO_KEY'

# Set to your Adafruit IO username.
# (go to https://accounts.adafruit.com to find your username)
ADAFRUIT_IO_USERNAME = 'YOUR_IO_USERNAME'

# Create an instance of the REST client.
aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)

# Delay between checking for `go` button press on Adafruit IO, in seconds
ADAFRUIT_IO_DELAY = 1

# Stepper 1 Adafruit IO Feeds
feed_step_1_steps = aio.feeds('stepper1steps')
feed_step_1_direction = aio.feeds('stepper1direction')
feed_step_1_step_size = aio.feeds('stepper1stepsize')
# Stepper 2 Adafruit Feeds
feed_step_2_steps = aio.feeds('stepper2steps')
feed_step_2_direction = aio.feeds('stepper2direction')
feed_step_2_step_size = aio.feeds('stepper2stepsize')
# Steppers start button
feed_steppers_status = aio.feeds('stepperstart')

# create a default object, no changes to I2C address or frequency
kit = MotorKit()

# create empty threads (these will hold the stepper 1 and 2 threads)
# pylint: disable=bad-thread-instantiation
st1 = threading.Thread()
st2 = threading.Thread()

# recommended for auto-disabling motors on shutdown!
def turnOffMotors():
    kit.stepper1.release()
    kit.stepper2.release()

atexit.register(turnOffMotors)
stepstyles = [STEPPER.SINGLE, STEPPER.DOUBLE, STEPPER.INTERLEAVE, STEPPER.MICROSTEP]

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
            time.sleep(0.5)
    print("{0} Done Stepping".format(stepper_name))
    # Reset slider on dashboard
    if stepper_name == "Stepper 1":
        aio.send(feed_step_1_steps.key, 0)
    elif stepper_name == "Stepper 2":
        aio.send(feed_step_2_steps.key, 0)


while True:
    try: # attempt to poll the stepper status feed
        print('checking for GO button press...')
        stepper_start = aio.receive(feed_steppers_status.key)
    except RequestError.ThrottlingError:
        print('Exceeded the limit of Adafruit IO requests, delaying 30 seconds...')
        time.sleep(30)

    # Stepper 1
    if not st1.isAlive() and int(stepper_start.value):
        stepper_1_steps = aio.receive(feed_step_1_steps.key)
        stepper_1_steps = int(stepper_1_steps.value)
        if stepper_1_steps > 0: # stepper slider is set
            # Get stepper configuration from io feeds
            stepper_1_direction = aio.receive(feed_step_1_direction.key)
            stepper_1_step_size = aio.receive(feed_step_1_step_size.key)
            print('Stepper 1 Configuration')
            print('\t%d steps' % stepper_1_steps)
            print('\tStep Size: ', stepper_1_step_size.value)
            print('\tStepper Direction: ', stepper_1_direction.value)

            # Set Stepper Direction
            if stepper_1_direction.value == 'Forward':
                move_dir = STEPPER.FORWARD
            elif stepper_1_direction.value == 'Backward':
                move_dir = STEPPER.BACKWARD
            # Stepper 1 Thread
            st1 = threading.Thread(target=stepper_worker, args=(kit.stepper1,
                                                                stepper_1_steps,
                                                                move_dir,
                                                                "Stepper 1",
                                                                stepstyles[STEPPER.SINGLE],))
            st1.start()

    # Stepper 2
    if not st2.isAlive() and int(stepper_start.value):
        stepper_2_steps = aio.receive(feed_step_2_steps.key)
        stepper_2_steps = int(stepper_2_steps.value)
        if stepper_2_steps > 0: # stepper slider is set
            # Get stepper configuration from io feeds
            stepper_2_direction = aio.receive(feed_step_2_direction.key)
            stepper_2_step_size = aio.receive(feed_step_2_step_size.key)
            print('Stepper 2 Configuration')
            print('\t%d steps' % stepper_2_steps)
            print('\tStep Size: ', stepper_2_step_size.value)
            print('\tStepper Direction: ', stepper_2_direction.value)
            # Set Stepper Direction
            if stepper_2_direction.value == 'Forward':
                move_dir = STEPPER.FORWARD
            elif stepper_2_direction.value == 'Backward':
                move_dir = STEPPER.BACKWARD
            # Stepper 2 Thread
            st2 = threading.Thread(target=stepper_worker, args=(kit.stepper2,
                                                                stepper_2_steps,
                                                                move_dir,
                                                                "Stepper 2",
                                                                stepstyles[STEPPER.SINGLE],))
            st2.start()

    # delay polling the `go button` to avoid Adafruit IO timeouts
    print('Delaying for {0} seconds...'.format(ADAFRUIT_IO_DELAY))
    time.sleep(ADAFRUIT_IO_DELAY)
