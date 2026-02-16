"""
Circuit Playground Express shake trigger.

Reads accelerometer magnitude and, when it exceeds SHAKE_THRESHOLD,
pulses pin A1 HIGH for TRIGGER_DURATION seconds, then enforces a cooldown.

Also sets a fixed NeoPixel pattern at startup.
"""

import math
import time

import board
import digitalio
from adafruit_circuitplayground.express import cpx

SHAKE_THRESHOLD = 11.0
TRIGGER_DURATION = 3.0  # seconds
COOLDOWN = 1.0  # seconds to wait after trigger
LOOP_DELAY = 0.01  # seconds


def setup_a1_output() -> digitalio.DigitalInOut:
    """Configure A1 as a digital output, default LOW."""
    a1_output = digitalio.DigitalInOut(board.A1)
    a1_output.direction = digitalio.Direction.OUTPUT
    a1_output.value = False
    return a1_output


def set_pixel_pattern() -> None:
    """Set the NeoPixel ring to a red/green pattern."""
    red = (255, 0, 0)
    green = (0, 255, 0)

    pattern = (
        red, red, red,        # 0-2
        green, green,         # 3-4
        red, red, red,        # 5-7
        green, green,         # 8-9
    )

    cpx.pixels.auto_write = False
    # Adjust to taste; helps battery + brightness.
    cpx.pixels.brightness = 0.2

    for index, color in enumerate(pattern):
        cpx.pixels[index] = color

    cpx.pixels.show()


def acceleration_magnitude() -> float:
    """Return the magnitude of the CPX acceleration vector."""
    accel_x, accel_y, accel_z = cpx.acceleration
    return math.sqrt((accel_x ** 2) + (accel_y ** 2) + (accel_z ** 2))


def pulse(output: digitalio.DigitalInOut, duration_s: float) -> None:
    """Set output HIGH for duration_s seconds, then LOW."""
    output.value = True
    time.sleep(duration_s)
    output.value = False


def main() -> None:
    """Main loop."""
    a1_pin = setup_a1_output()
    set_pixel_pattern()

    while True:
        magnitude = acceleration_magnitude()

        print(
            f"Magnitude: {magnitude:.2f} | "
            f"Threshold: {SHAKE_THRESHOLD:.2f} | "
            f"A1 value: {a1_pin.value}"
        )

        if magnitude > SHAKE_THRESHOLD:
            print(">>> SHAKE DETECTED! Pulsing A1 HIGH")
            a1_pin.value = True
            print(f"A1 is now: {a1_pin.value}")
            time.sleep(TRIGGER_DURATION)
            a1_pin.value = False
            print(f"A1 is now: {a1_pin.value}")
            time.sleep(COOLDOWN)

        time.sleep(LOOP_DELAY)


main()
