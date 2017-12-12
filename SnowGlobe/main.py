# Snow Globe
# for Adafruit Circuit Playground express
# with CircuitPython

from adafruit_circuitplayground.express import cpx
import math
import time

ROLL_THRESHOLD = 30  # Total acceleration
cpx.pixels.brightness = 0.1  # set brightness value

WHITE = (65, 65, 65)
RED = (220, 0, 0)
GREEN = (0, 220, 0)
BLUE = (0, 0, 220)
SKYBLUE = (0, 20, 200)
BLACK = (0, 0, 0)

# Initialize the global states
new_roll = False
rolling = False


def pixelFade(fadeColor):  # pick from colors defined above, e.g., RED, GREEN, BLUE, WHITE, etc.
    # fade up
    for j in range(25):
        pixelBright = (j * 0.01)
        cpx.pixels.brightness = pixelBright
        for i in range(10):
            cpx.pixels[i] = fadeColor

    # fade down
    for k in range(25):
        pixelBright = (0.25 - (k * 0.01))
        cpx.pixels.brightness = pixelBright
        for i in range(10):
            cpx.pixels[i] = fadeColor

# fade in the pixels
pixelFade(GREEN)


def playSong(song):
    # 1: Jingle bells
    # 2: Let It Snow

    # set up time signature
    whole_note = 1.5  # adjust this to change tempo of everything
    # these notes are fractions of the whole note
    half_note = whole_note / 2
    quarter_note = whole_note / 4
    dotted_quarter_note = quarter_note * 1.5
    eighth_note = whole_note / 8

    # set up note values
    A3 = 220
    Bb3 = 233
    B3 = 247
    C4 = 262
    Db4 = 277
    D4 = 294
    Eb4 = 311
    E4 = 330
    F4 = 349
    Gb4 = 370
    G4 = 392
    Ab4 = 415
    A4 = 440
    Bb4 = 466
    B4 = 494

    if(song == 1):
        # jingle bells
        jingleBellsSong = [[E4, quarter_note], [E4, quarter_note],
        [E4, half_note], [E4, quarter_note], [E4, quarter_note],
        [E4, half_note], [E4, quarter_note], [G4, quarter_note],
        [C4, dotted_quarter_note], [D4, eighth_note], [E4, whole_note]]

        for n in range(len(jingleBellsSong)):
            cpx.start_tone(jingleBellsSong[n][0])
            time.sleep(jingleBellsSong[n][1])
            cpx.stop_tone()


    if(song == 2):
        # Let It Snow
        letItSnowSong = [[B4, dotted_quarter_note], [A4, eighth_note],
        [G4, quarter_note], [G4, dotted_quarter_note], [F4, eighth_note],
        [E4, quarter_note], [E4, dotted_quarter_note], [D4, eighth_note],
        [C4, whole_note]]

        for n in range(len(letItSnowSong)):
            cpx.start_tone(letItSnowSong[n][0])
            time.sleep(letItSnowSong[n][1])
            cpx.stop_tone()

playSong(1)  # play music on start


# Loop forever
while True:
    # check for shaking
    # Compute total acceleration
    x_total = 0
    y_total = 0
    z_total = 0
    for count in range(10):
        x, y, z = cpx.acceleration
        x_total = x_total + x
        y_total = y_total + y
        z_total = z_total + z
        time.sleep(0.001)
    x_total = x_total / 10
    y_total = y_total / 10
    z_total = z_total / 10

    total_accel = math.sqrt(x_total*x_total + y_total*y_total + z_total*z_total)

    # Check for rolling
    if total_accel > ROLL_THRESHOLD:
        roll_start_time = time.monotonic()
        new_roll = True
        rolling = True
        print('shaken')

    # Rolling momentum
    # Keep rolling for a period of time even after shaking stops
    if new_roll:
        if time.monotonic() - roll_start_time > 2:  # seconds to run
                rolling = False

    # Light show
    if rolling:
        pixelFade(SKYBLUE)
        pixelFade(WHITE)
        cpx.pixels.brightness = 0.8
        cpx.pixels.fill(WHITE)

    elif new_roll:
        new_roll = False
        # play a song!
        playSong(2)
        #return to resting color
        pixelFade(GREEN)
        cpx.pixels.brightness = 0.05
        cpx.pixels.fill(GREEN)
