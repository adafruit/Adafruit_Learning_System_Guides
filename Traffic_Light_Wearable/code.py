import time
import board
import alarm
from digitalio import DigitalInOut, Direction, Pull
#  setup pins for the traffic light LEDs
red_light = DigitalInOut(board.A1)
yellow_light = DigitalInOut(board.SCL1)
green_light = DigitalInOut(board.A2)
#  array of LEDs
lights = [red_light, yellow_light, green_light]
#  the traffic light is common anode
#  the pins will need to be pulled down to ground
#  to turn on the LEDs. they are setup as inputs
#  so that the pull can be toggled
#  Pull.UP turns the LEDs off to start
for light in lights:
    light.direction = Direction.INPUT
    light.pull = Pull.UP
#  button pin setup
pin_alarm = alarm.pin.PinAlarm(pin=board.SDA1, value=False, pull=True)
#  count to track which light is on
count = 2
#  tracks the last light
last_count = 1
while True:
    #  increase count by 1, loop through 0-2
    count = (count+1) % 3
    #  turn off the last LED
    lights[last_count].pull = Pull.UP
    #  turn on the current LED
    lights[count].pull = Pull.DOWN
    #  print(count)
    #  delay to keep count
    time.sleep(1)
    #  reset last LED for next loop
    last_count = count
    #  go into light sleep mode until button is pressed again
    alarm.light_sleep_until_alarms(pin_alarm)
