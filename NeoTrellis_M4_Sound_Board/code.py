import time
import board
import busio
import audioio
import adafruit_fancyled.adafruit_fancyled as fancy
import adafruit_trellism4
import adafruit_adxl34x
from color_names import *

SAMPLE_FOLDER = "/samples/"  # the name of the folder containing the samples
# This soundboard can select up to *32* sound clips! each one has a filename
# which will be inside the SAMPLE_FOLDER above, and a *color* in a tuple ()
VOICES = [("01.wav", RED),
          ("02.wav", ORANGE),
          ("03.wav", YELLOW),
          ("04.wav", GREEN),
          ("05.wav", TEAL),
          ("06.wav", BLUE),
          ("07.wav", PURPLE),
          ("08.wav", PINK),
          ("09.wav", RED),
          ("10.wav", ORANGE),
          ("11.wav", YELLOW),
          ("12.wav", GREEN),
          ("13.wav", TEAL),
          ("14.wav", BLUE),
          ("15.wav", PURPLE),
          ("16.wav", PINK),
          ("17.wav", RED),
          ("18.wav", ORANGE),
          ("19.wav", YELLOW),
          ("20.wav", GREEN),
          ("21.wav", TEAL),
          ("22.wav", BLUE),
          ("23.wav", PURPLE),
          ("24.wav", PINK),
          ("25.wav", RED),
          ("26.wav", ORANGE),
          ("27.wav", YELLOW),
          ("28.wav", GREEN),
          ("29.wav", TEAL),
          ("30.wav", BLUE),
          ("31.wav", PURPLE),
          ("32.wav", PINK)]

# For the intro, pick any number of colors to make a fancy gradient!
INTRO_SWIRL = [PINK, TEAL, YELLOW]
# the color for the selected sample
SELECTED_COLOR = WHITE

# Our keypad + neopixel driver
trellis = adafruit_trellism4.TrellisM4Express(rotation=270)

# Play the welcome wav (if its there)
with audioio.AudioOut(board.A1, right_channel=board.A0) as audio:
    try:
        f = open("welcome.wav", "rb")
        wave = audioio.WaveFile(f)
        audio.play(wave)
        swirl = 0  # we'll swirl through the colors in the gradient
        while audio.playing:
            for i in range(32):
                palette_index = ((swirl+i) % 32) / 32
                color = fancy.palette_lookup(INTRO_SWIRL, palette_index)
                # display it!
                trellis.pixels[(i//8, i%8)] = color.pack()
            swirl += 1
            time.sleep(0.005)
        f.close()
        # Clear all pixels
        trellis.pixels.fill(0)
        # just hold a moment
        time.sleep(0.5)
    except OSError:
        # no biggie, they probably deleted it
        pass


# Parse the first file to figure out what format its in
with open(SAMPLE_FOLDER+VOICES[0][0], "rb") as f:
    wav = audioio.WaveFile(f)
    print("%d channels, %d bits per sample, %d Hz sample rate " %
          (wav.channel_count, wav.bits_per_sample, wav.sample_rate))

    # Audio playback object - we'll go with either mono or stereo depending on
    # what we see in the first file
    if wav.channel_count == 1:
        audio = audioio.AudioOut(board.A1)
    elif wav.channel_count == 2:
        audio = audioio.AudioOut(board.A1, right_channel=board.A0)
    else:
        raise RuntimeError("Must be mono or stereo waves!")

# Clear all pixels
trellis.pixels.fill(0)

current_press = set()

while True:
    pressed = set(trellis.pressed_keys)
    #print(pressed)
    for down in pressed - current_press:
        print("Pressed down", down)
        current_press = pressed
        button_num = down[0]*8 + down[1] + 1
        print(button_num)

    time.sleep(0.01)  # a little delay here helps avoid debounce annoyances
