import time
import board
from rainbowio import colorwheel
import adafruit_hcsr04
from adafruit_circuitplayground.express import cpx

# This line creates the distance sensor as an object.
sonar = adafruit_hcsr04.HCSR04(trigger_pin=board.D9, echo_pin=board.D6, timeout=0.1)
pixels = cpx.pixels
pitchMultiplier = 300   # Change this value to modify the pitch of the theremin.

while True:
    try:
        handDistance = int(sonar.distance)
        print("Distance:", handDistance)
    except RuntimeError:
        print("retrying!")
    time.sleep(.00001)

    pitch = handDistance*pitchMultiplier

    # Limits on the distances that trigger sound/light to between 3 and 25 cm.
    if (handDistance >= 3) & (handDistance < 25):
        cpx.play_tone(pitch, 0.1)
        pixels.fill(colorwheel(handDistance*10))
        pixels.show()
        time.sleep(.00001)
        print(pitch)
    else:
        cpx.stop_tone()
        pixels.fill((0, 0, 0))
        pixels.show()
