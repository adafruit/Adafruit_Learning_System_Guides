import time
import board
from adafruit_circuitplayground import cp
import neopixel

# Constants
NUM_PIXELS_STRIP = 20
NUM_PIXELS_FACE = 10  # Number of NeoPixels on the face
PIXEL_PIN_STRIP = board.A1
SOUND_THRESHOLD = 50  # Adjust this threshold based on your environment

# Variables
DELAY_AFTER_LIGHT_UP = 2.0
COLOR = (255, 100, 0)  # Warm yellow color
SPEED = 0.2  # Animation speed (adjust as needed, higher number moves more slowly)

# Initialize NeoPixels on face
pixels_face = cp.pixels
pixels_face.brightness = 0.5

# Initialize NeoPixels on strip (A1)
pixels_strip = neopixel.NeoPixel(PIXEL_PIN_STRIP, NUM_PIXELS_STRIP, brightness=0.5)

# Main loop
while True:
    # Read sound level
    sound_level = cp.sound_level

    # Debugging: Print sound level to the serial monitor
    print("Sound Level:", sound_level)

    # Check if sound threshold is reached
    if sound_level > SOUND_THRESHOLD:
        # Sequentially light up NeoPixels on the face
        for i in range(NUM_PIXELS_FACE):
            if i < len(pixels_face):
                pixels_face[i] = COLOR
                time.sleep(SPEED)  # Adjust speed if needed
        pixels_face.show()  # Show all pixels at once

        # Sequentially light up NeoPixels on strip (A1)
        for i in range(NUM_PIXELS_STRIP):
            if i < len(pixels_strip):
                pixels_strip[i] = COLOR
                time.sleep(SPEED)  # Adjust speed if needed
        pixels_strip.show()  # Show all pixels at once

        # Delay for the specified duration after lighting up all pixels
        time.sleep(DELAY_AFTER_LIGHT_UP)

        # Turn off all pixels on strip
        pixels_strip.fill((0, 0, 0))
        pixels_strip.show()

        # Turn off all pixels on face
        pixels_face.fill((0, 0, 0))
        pixels_face.show()

    # Add a delay to avoid rapid detection
    time.sleep(0.1)
