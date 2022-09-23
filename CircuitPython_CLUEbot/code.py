import board
import neopixel
from robot import Robot

# Ring:bit Pins
UNDERLIGHT_PIXELS = board.D0
LEFT_MOTOR = board.D1
RIGHT_MOTOR = board.D2

# Set up the hardware
underlight_neopixels = neopixel.NeoPixel(UNDERLIGHT_PIXELS, 2)
robot = Robot(LEFT_MOTOR, RIGHT_MOTOR, underlight_neopixels)

while True:
    robot.wait_for_connection()
    while robot.is_connected():
        robot.check_for_packets()
