import time
import random
import displayio
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_clue import clue

#--| User Config |-------------------------------
BACKGROUND_COLOR = 0xCFBC17
HEXAGRAM_COLOR   = 0xBB0000
FONT_COLOR       = 0x005500
SHAKE_THRESHOLD  = 20
MELODY = ( (1000, 0.1),  # (freq, duration)
           (1200, 0.1),
           (1400, 0.1),
           (1600, 0.2))
#--| User Config |-------------------------------

# Defined in order treating each hexagram as a 6 bit value.
HEXAGRAMS = (
    "EARTH", "RETURN", "THE ARMY", "PREVAILING", "MODESTY", "  CRYING\nPHEASANT",
    "ASCENDANCE", "PEACE", "WEARINESS", "THUNDER", "LETTING\n LOOSE",
    "MARRYING\n MAIDEN", " SMALL\nEXCESS", "ABUNDANCE", "STEADFASTNESS",
    " GREAT\nINJURY", "SUPPORT", "RETRENCHMENT", "WATER", "FRUGALITY",
    "ADMONISHMENT", "FULFILLMENT", "THE WELL", "WAITING", "ILLNESS",
    "THE CHASE", "TRAPPED", "LAKE", "CUTTING", "REVOLUTION", " GREAT\nEXCESS",
    "STRIDE", "LOSS", "THE CHEEKS", "BLINDNESS", "DECREASE", "MOUNTAIN",
    "DECORATION", "WORK", "   BIG\nCATTLE", "ADVANCE", "BITING", "UNFULFILLMENT",
    "ABANDONED", "TRAVELER", "FIRE", "    THE\nCAULDRON", " GREAT\nHARVEST",
    "VIEW", "INCREASE", "FLOWING", "SINCERITY", "PROGRESS", "FAMILY", "WIND",
    " SMALL\nCATTLE", "OBSTRUCTION", "PROPRIETY", "THE COURT", "TREADING",
    "LITTLE\n  PIG", "GATHERING", "RENDEZVOUS", "HEAVEN",
)

# Grab the CLUE's display
display = clue.display

# Background fill
bg_bitmap = displayio.Bitmap(display.width, display.height, 1)
bg_palette = displayio.Palette(1)
bg_palette[0] = BACKGROUND_COLOR
background = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette)

# Hexagram setup
sprite_sheet = displayio.Bitmap(11, 4, 2)
palette = displayio.Palette(2)
palette.make_transparent(0)
palette[0] = 0x000000
palette[1] = HEXAGRAM_COLOR

for x in range(11):
    sprite_sheet[x, 0] = 1 # - - 0 YIN
    sprite_sheet[x, 1] = 0
    sprite_sheet[x, 2] = 1 # --- 1 YANG
    sprite_sheet[x, 3] = 0
sprite_sheet[5, 0] = 0

tile_grid = displayio.TileGrid(sprite_sheet, pixel_shader=palette,
                               width = 1,
                               height = 6,
                               tile_width = 11,
                               tile_height = 2)

hexagram = displayio.Group(max_size=1, x=60, y=15, scale=10)
hexagram.append(tile_grid)

# Hexagram name label
# font credit: https://www.instagram.com/cove703/
font = bitmap_font.load_font("/christopher_done_24.bdf")
font.load_glyphs(b'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
hexname = label.Label(font, text=" "*40, color=FONT_COLOR)
# this will initially hold the "shake for reading" message
hexname.text = " SHAKE\n   FOR\nREADING"
hexname.anchor_point = (0.5, 0.0)
hexname.anchored_position = (120, 120)

# Set up main display group (splash)
splash = displayio.Group()
display.show(splash)

# Add background and text label
splash.append(background)
splash.append(hexname)

def show_hexagram(number):
    for i in range(6):
        tile_grid[5-i] = (number >> i) & 0x01

def show_name(number):
    hexname.text = HEXAGRAMS[number]
    hexname.anchored_position = (120, 180)

#===================================
# MAIN CODE
#===================================
print("shake")
# wait for shake
while not clue.shake(shake_threshold=SHAKE_THRESHOLD):
    pass

# calibrate the mystic universe
x, y, z = clue.acceleration
random.seed(int(time.monotonic() + abs(x) + abs(y) + abs(z)))

# cast a reading
reading = random.randrange(64)
print("reading = ", reading, HEXAGRAMS[reading])

# play a melody
for note, duration in MELODY:
    clue.play_tone(note, duration)

# prompt to show
display.auto_refresh = False
hexname.text = "      GOT IT\n\nPRESS BUTTON\n       TO SEE"
hexname.anchored_position = (120, 120)
display.auto_refresh = True
while not clue.button_a and not clue.button_b:
    pass

# and then show it
display.auto_refresh = False
splash.append(hexagram)
show_hexagram(reading)
show_name(reading)
display.auto_refresh = True

# hold here until reset
while True:
    pass
