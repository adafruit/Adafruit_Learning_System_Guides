# Adafruit Grand Central Robot Xylophone Demo Program
# Dano Wall and Mike Barela for Adafruit Industries
# MIT License

import time
import board
from digitalio import DigitalInOut, Direction

solenoid_count = 8  # Set the total number of solenoids used
start_pin = 2       # Start at pin D2

# Create the input objects list for solenoids
solenoid = []
for k in range(start_pin, solenoid_count + start_pin + 1):
    # get pin # attribute, use string formatting
    this_solenoid = DigitalInOut(getattr(board, "D{}".format(k)))
    this_solenoid.direction = Direction.OUTPUT
    solenoid.append(this_solenoid)

STRIKE_TIME = 0.01  # Time between initiating a strike and turning it off
TIME_BETWEEN = 0.5  # Time between actions in seconds

song = [3, 4, 5, 4, 3, 3, 3, 4, 4, 4, 3, 3, 3, 3, 4, 5, 4, 3, 3, 3, 2, 2, 3, 4, 5]

def play(key, time_to_strike):
    solenoid[key].value = True
    time.sleep(time_to_strike)
    solenoid[key].value = False

def rest(time_to_wait):
    time.sleep(time_to_wait)

while True:
    # Play each of the bars
    for bar in range(solenoid_count):
        play(bar, STRIKE_TIME)
        rest(TIME_BETWEEN)

    time.sleep(1.0)  # Wait a bit before playing the song

    # Play the notes defined in song
    # simple example does not vary time between notes
    for bar in range(len(song)):
        play(song[bar], STRIKE_TIME)
        rest(TIME_BETWEEN)

    time.sleep(1.0)
