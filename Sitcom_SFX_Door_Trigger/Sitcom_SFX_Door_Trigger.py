import time
import board
from digitalio import DigitalInOut, Direction
import pygame.mixer

# setup inputs
door_switch_pin = board.D23
motion_sensor_pin = board.D24

door = DigitalInOut(door_switch_pin)
door.direction = Direction.INPUT

motion = DigitalInOut(motion_sensor_pin)
motion.direction = Direction.INPUT

# setup output LED indicators
motion_led_pin = board.D18
door_led_pin = board.D25

door_led = DigitalInOut(door_led_pin)
door_led.direction = Direction.OUTPUT
door_led.value = False

motion_led = DigitalInOut(motion_led_pin)
motion_led.direction = Direction.OUTPUT
motion_led.value = False

prev_door = False

# audio settings
pygame.mixer.init(44100, -16, 2, 1024)

# sound files expect to be in the same directory as script
enter_sound = pygame.mixer.Sound("./enter.wav")
exit_sound = pygame.mixer.Sound("./exit.wav")

while True:

    # toggle door LED based on door sensor
    if door.value:
        door_led.value = True
    else:
        door_led.value = False

    # toggle motion LED based on motion (PIR) sensor
    if motion.value:
        motion_led.value = True
    else:
        motion_led.value = False

    # When the door is opened, if there is movement outside,
    # It means that someone is entering.
    # If not, someone is exiting.
    if door.value and not prev_door:
        if motion.value:
            enter_sound.play()
        else:
            exit_sound.play()

    prev_door = door.value
    time.sleep(0.01)
