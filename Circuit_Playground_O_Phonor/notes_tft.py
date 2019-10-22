import time
import array
import board
import busio
import audiobusio
import displayio
from adafruit_st7789 import ST7789
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label

#---| User Configuration |---------------------------
SAMPLERATE = 16000
SAMPLES = 1024
THRESHOLD = 100
MIN_DELTAS = 5
DELAY = 0.2

#        octave = 1    2    3    4    5     6     7     8
NOTES = { "C" : (33,  65, 131, 262, 523, 1047, 2093, 4186),
          "D" : (37,  73, 147, 294, 587, 1175, 2349, 4699),
          "E" : (41,  82, 165, 330, 659, 1319, 2637, 5274),
          "F" : (44,  87, 175, 349, 698, 1397, 2794, 5588),
          "G" : (49,  98, 196, 392, 785, 1568, 3136, 6272),
          "A" : (55, 110, 220, 440, 880, 1760, 3520, 7040),
          "B" : (62, 123, 247, 494, 988, 1976, 3951, 7902)}
#----------------------------------------------------

# Create a buffer to record into
samples = array.array('H', [0] * SAMPLES)

# Setup the mic input
mic = audiobusio.PDMIn(board.MICROPHONE_CLOCK,
                       board.MICROPHONE_DATA,
                       sample_rate=SAMPLERATE,
                       bit_depth=16)

# Setup TFT Gizmo
displayio.release_displays()

spi = busio.SPI(board.SCL, MOSI=board.SDA)
tft_cs = board.RX
tft_dc = board.TX
tft_backlight = board.A3

display_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs)

display = ST7789(display_bus, width=240, height=240, rowstart=80,
                 backlight_pin=tft_backlight, rotation=180)

# Setup the various text labels
note_font = bitmap_font.load_font("/monoMMM_5_90.bdf")
note_text = label.Label(note_font, text="A", color=0xFFFFFF)
note_text.x = 90
note_text.y = 100

oct_font = bitmap_font.load_font("/monoMMM_5_24.bdf")
oct_text = label.Label(oct_font, text=" ", color=0x00FFFF)
oct_text.x = 180
oct_text.y = 150

freq_font = oct_font
freq_text = label.Label(freq_font, text="f = 1234.5", color=0xFFFF00)
freq_text.x = 20
freq_text.y = 220

# Add everything to the display group
splash = displayio.Group()
splash.append(note_text)
splash.append(oct_text)
splash.append(freq_text)
display.show(splash)

while True:
    # Get raw mic data
    mic.record(samples, SAMPLES)

    # Compute DC offset (mean) and threshold level
    mean = int(sum(samples) / len(samples) + 0.5)
    threshold = mean + THRESHOLD

    # Compute deltas between mean crossing points
    # (this bit by Dan Halbert)
    deltas = []
    last_xing_point = None
    crossed_threshold = False
    for i in range(SAMPLES-1):
        sample = samples[i]
        if sample > threshold:
            crossed_threshold = True
        if crossed_threshold and sample < mean:
            if last_xing_point:
                deltas.append(i - last_xing_point)
            last_xing_point = i
            crossed_threshold = False

    # Try again if not enough deltas
    if len(deltas) < MIN_DELTAS:
        continue

    # Average the deltas
    mean = sum(deltas) / len(deltas)

    # Compute frequency
    freq = SAMPLERATE / mean

    print("crossings: {}  mean: {}  freq: {} ".format(len(deltas), mean, freq))
    freq_text.text = "f = {:6.1f}".format(freq)

    # Find corresponding note
    for note in NOTES:
        for octave, note_freq in enumerate(NOTES[note]):
            if note_freq * 0.97 <= freq <= note_freq * 1.03:
                print("Note: {}{}".format(note, octave + 1))
                note_text.text = note
                oct_text.text = "{}".format(octave + 1)

    time.sleep(DELAY)
