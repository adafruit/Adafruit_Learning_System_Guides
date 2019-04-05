# Talking A, B, Cs Soundboards: Animal ABCs and "E is for Electronics" ABCs

import time
import board
import audioio
import adafruit_fancyled.adafruit_fancyled as fancy
import adafruit_trellism4

# Custom colors for keys
RED = 0xFF0000
MAROON = 0xFF0044
ORANGE = 0xFF6600
YELLOW = 0xFFFF00
BROWN = 0x8B4513
GREEN = 0x008000
AQUA = 0x33ff33
TEAL = 0x66ffff
BLUE = 0x0000FF
NAVY = 0x24248f
PURPLE = 0x660066
PINK = 0xFF66B3
WHITE = 0xFFFFFF
EXTRA = 0x888888

# Select the folder for the ABC files, only define one,
#   the other line should have a # to comment it out
#SAMPLE_FOLDER = "/animals/"
SAMPLE_FOLDER = "/electronics/"

# This soundboard can select up to *32* sound clips! each one has a filename
# which will be inside the SAMPLE_FOLDER above, and a *color* in a tuple ()
SAMPLES = [("A.wav", RED),
           ("B.wav", MAROON),
           ("C.wav", ORANGE),
           ("D.wav", YELLOW),
           ("E.wav", BROWN),
           ("F.wav", GREEN),
           ("G.wav", AQUA),
           ("H.wav", TEAL),
           ("I.wav", BLUE),
           ("J.wav", NAVY),
           ("K.wav", PURPLE),
           ("L.wav", PINK),
           ("M.wav", RED),
           ("N.wav", MAROON),
           ("O.wav", ORANGE),
           ("P.wav", YELLOW),
           ("Q.wav", BROWN),
           ("R.wav", GREEN),
           ("S.wav", AQUA),
           ("T.wav", TEAL),
           ("U.wav", BLUE),
           ("V.wav", NAVY),
           ("W.wav", PURPLE),
           ("X.wav", PINK),
           ("Y.wav", RED),
           ("Z.wav", MAROON),
           ("01.wav", EXTRA),  # Keys beyond the 26 alphabetic keys
           ("02.wav", EXTRA),
           ("03.wav", EXTRA),
           ("04.wav", EXTRA),
           ("05.wav", EXTRA),
           ("06.wav", EXTRA)]

# For the intro, pick any number of colors to make a fancy gradient!
INTRO_SWIRL = [RED, GREEN, BLUE]
# The color for the pressed key
SELECTED_COLOR = 0x333300

PLAY_SAMPLES_ON_START = False  # Will not play all the sounds on start

# Our keypad + NeoPixel driver
trellis = adafruit_trellism4.TrellisM4Express(rotation=0)

# Play the welcome wav (if its there)
with audioio.AudioOut(board.A1, right_channel=board.A0) as audio:
    try:
        f = open(SAMPLE_FOLDER+SAMPLES[27][0], "rb")  # Use 02.wav as welcome
        wave = audioio.WaveFile(f)
        audio.play(wave)
        swirl = 0  # we'll swirl through the colors in the gradient
        while audio.playing:
            for i in range(32):
                palette_index = ((swirl+i) % 32) / 32
                color = fancy.palette_lookup(INTRO_SWIRL, palette_index)
                # display it!
                trellis.pixels[(i%8, i//8)] = color.pack()
            swirl += 1
            time.sleep(0.005)
        f.close()
        # just hold a moment
        time.sleep(0.5)
    except OSError:
        # no biggie, they could have deleted it
        pass

# Parse the first file to figure out what format it's in
channel_count = None
bits_per_sample = None
sample_rate = None
with open(SAMPLE_FOLDER+SAMPLES[0][0], "rb") as f:
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

# Turn on, maybe play all of the buttons
for i, v in enumerate(SAMPLES):
    filename = SAMPLE_FOLDER+v[0]
    try:
        with open(filename, "rb") as f:
            wav = audioio.WaveFile(f)
            print(filename,
                  "%d channels, %d bits per sample, %d Hz sample rate " %
                  (wav.channel_count, wav.bits_per_sample, wav.sample_rate))
            if wav.channel_count != channel_count:
                pass
            if wav.bits_per_sample != bits_per_sample:
                pass
            if wav.sample_rate != sample_rate:
                pass
            trellis.pixels[(i%8, i//8)] = v[1]
            if PLAY_SAMPLES_ON_START:
                audio.play(wav)
                while audio.playing:
                    pass
    except OSError:
        # File not found! skip to next
        pass

def stop_playing_sample(playback_details):
    print("playing: ", playback_details)
    audio.stop()
    trellis.pixels[playback_details['neopixel_location']] = playback_details['neopixel_color']
    playback_details['file'].close()
    playback_details['voice'] = None

current_press = set()
currently_playing = {'voice' : None}
last_samplenum = None
while True:
    pressed = set(trellis.pressed_keys)
    # if pressed:
    #    print("Pressed:", pressed)

    just_pressed = pressed - current_press
    just_released = current_press - pressed

    # if just_pressed:
    #    print("Just pressed", just_pressed)
    for down in just_pressed:
        sample_num = down[1]*8 + down[0]
        print(sample_num)
        try:
            filename = SAMPLE_FOLDER+SAMPLES[sample_num][0]
            f = open(filename, "rb")
            wav = audioio.WaveFile(f)

            # is something else playing? interrupt it!
            if currently_playing['voice'] != None:
                print("Interrupt")
                stop_playing_sample(currently_playing)

            trellis.pixels[down] = SELECTED_COLOR
            audio.play(wav)
            # voice, neopixel tuple, color, and sample, file handle
            currently_playing = {
                'voice': 0,
                'neopixel_location': down,
                'neopixel_color': SAMPLES[sample_num][1],
                'sample_num': sample_num,
                'file': f}
        except OSError:
            pass # File not found! skip to next

    # check if any samples are done
    if not audio.playing and currently_playing['voice'] != None:
        stop_playing_sample(currently_playing)

    time.sleep(0.01)  # a little delay here helps avoid debounce annoyances
    current_press = pressed
