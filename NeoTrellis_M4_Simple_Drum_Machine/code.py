import time
import board
import busio
import audioio
import adafruit_fancyled.adafruit_fancyled as fancy
import adafruit_trellism4
import adafruit_adxl34x

tempo = 180  # Starting BPM

# You can use the accelerometer to speed/slow down tempo by tilting!
ENABLE_TILT_TEMPO = True
MIN_TEMPO = 100
MAX_TEMPO = 300

SAMPLE_FOLDER = "/samples/"  # the name of the folder containing the samples
# You get 4 voices, they must all have the same sample rate and must
# all be mono or stereo (no mix-n-match!)
VOICES = [SAMPLE_FOLDER+"voice01.wav",
          SAMPLE_FOLDER+"voice02.wav",
          SAMPLE_FOLDER+"voice03.wav",
          SAMPLE_FOLDER+"voice04.wav"]

# four colors for the 4 voices, using 0 or 255 only will reduce buzz
DRUM_COLOR = ((0, 255, 255),
              (0, 255, 0),
              (255, 255, 0),
              (255, 0, 0))
# For the intro, pick any number of colors to make a fancy gradient!
INTRO_SWIRL = [fancy.CRGB(255, 0, 0),  # red
               fancy.CRGB(0, 255, 0),  # green
               fancy.CRGB(0, 0, 255)]  # blue
# the color for the sweeping ticker bar
TICKER_COLOR = (255, 255, 255)

# Our keypad + neopixel driver
trellis = adafruit_trellism4.TrellisM4Express(rotation=90)

# Our accelerometer
i2c = busio.I2C(board.ACCELEROMETER_SCL, board.ACCELEROMETER_SDA)
accelerometer = adafruit_adxl34x.ADXL345(i2c)

def wheel(pos): # Input a value 0 to 255 to get a color value.
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    elif pos < 85:
        return(int(pos * 3), int(255 - pos*3), 0)
    elif pos < 170:
        pos -= 85
        return(int(255 - pos*3), 0, int(pos * 3))
    else:
        pos -= 170
        return(0, int(pos * 3), int(255 - pos*3))

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
with open(VOICES[0], "rb") as f:
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
    mixer = audioio.Mixer(voice_count=4,
                          sample_rate=wav.sample_rate,
                          channel_count=wav.channel_count,
                          bits_per_sample=wav.bits_per_sample,
                          samples_signed=True)
    audio.play(mixer)

samples = []
# Read the 4 wave files, convert to stereo samples, and store
# (show load status on neopixels and play audio once loaded too!)
for v in range(4):
    trellis.pixels[(v, 0)] = DRUM_COLOR[v]
    wave_file = open(VOICES[v], "rb")
    # OK we managed to open the wave OK
    for x in range(1, 4):
        trellis.pixels[(v, x)] = DRUM_COLOR[v]
    sample = audioio.WaveFile(wave_file)
    # debug play back on load!
    mixer.play(sample, voice=0)
    for x in range(4, 7):
        trellis.pixels[(v, x)] = DRUM_COLOR[v]
    while mixer.playing:
        pass
    trellis.pixels[(v, 7)] = DRUM_COLOR[v]
    samples.append(sample)

# Clear all pixels
trellis.pixels.fill(0)

# Our global state
current_step = 7 # we actually start on the last step since we increment first
# the state of the sequencer
beatset = [[False] * 8, [False] * 8, [False] * 8, [False] * 8]
# currently pressed buttons
current_press = set()

while True:
    stamp = time.monotonic()
    # redraw the last step to remove the ticker bar (e.g. 'normal' view)
    for y in range(4):
        color = 0
        if beatset[y][current_step]:
            color = DRUM_COLOR[y]
        trellis.pixels[(y, current_step)] = color

    # next beat!
    current_step = (current_step + 1) % 8

    # draw the vertical ticker bar, with selected voices highlighted
    for y in range(4):
        if beatset[y][current_step]:
            r, g, b = DRUM_COLOR[y]
            color = (r//2, g//2, b//2)  # this voice is enabled
            #print("Playing: ", VOICES[y])
            mixer.play(samples[y], voice=y)
        else:
            color = TICKER_COLOR     # no voice on
        trellis.pixels[(y, current_step)] = color

    # handle button presses while we're waiting for the next tempo beat
    # also check the accelerometer if we're using it, to adjust tempo
    while time.monotonic() - stamp < 60/tempo:
        # Check for pressed buttons
        pressed = set(trellis.pressed_keys)
        #print(pressed)
        for down in pressed - current_press:
            print("Pressed down", down)
            y = down[0]
            x = down[1]
            beatset[y][x] = not beatset[y][x] # enable the voice
            if beatset[y][x]:
                color = DRUM_COLOR[y]
            else:
                color = 0
            trellis.pixels[down] = color
        current_press = pressed

        if ENABLE_TILT_TEMPO:
            # Check accelerometer tilt!
            tilt = accelerometer.acceleration[1]
            #print("%0.1f" % tilt)
            new_tempo = tempo
            if tilt < -9:
                new_tempo = tempo + 5
            elif tilt < -6:
                new_tempo = tempo + 1
            elif tilt > 9:
                new_tempo = tempo - 5
            elif tilt > 6:
                new_tempo = tempo - 1
            if new_tempo != tempo:
                tempo = max(min(new_tempo, MAX_TEMPO), MIN_TEMPO)
                print("Tempo: %d BPM" % tempo)
                time.sleep(0.05)  # dont update tempo too fast!
        time.sleep(0.01)  # a little delay here helps avoid debounce annoyances
