import time
import board
import displayio
import adafruit_sgp30
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
import adafruit_imageload
from adafruit_clue import clue

# --| User Config |-------------------------
TVOC_LEVELS = (80, 120)  # set two TVOC levels
MESSAGES = ("GOOD", "SUS?", "BAD!")  # set three messages (4 char max)
# ------------------------------------------

# setup UI
cow_bmp, cow_pal = adafruit_imageload.load("bmps/milk_bg.bmp")
background = displayio.TileGrid(cow_bmp, pixel_shader=cow_pal)

mouth_bmp, mouth_pal = adafruit_imageload.load("bmps/mouth_sheet.bmp")
mouth = displayio.TileGrid(
    mouth_bmp,
    pixel_shader=mouth_pal,
    tile_width=40,
    tile_height=20,
    width=1,
    height=1,
    x=35,
    y=110,
)

msg_font = bitmap_font.load_font("fonts/Alphakind_28.bdf")
msg_font.load_glyphs("".join(MESSAGES))
message = label.Label(msg_font, text="WAIT", color=0x000000)
message.anchor_point = (0.5, 0.5)
message.anchored_position = (172, 38)

data_font = bitmap_font.load_font("fonts/F25_Bank_Printer_Bold_12.bdf")
data_font.load_glyphs("eTVOC=12345?")
tvoc = label.Label(data_font, text="TVOC=?????", color=0x000000)
tvoc.anchor_point = (0, 1)
tvoc.anchored_position = (5, 235)

eco2 = label.Label(data_font, text="eCO2=?????", color=0x000000)
eco2.anchor_point = (0, 1)
eco2.anchored_position = (130, 235)

splash = displayio.Group()
splash.append(background)
splash.append(mouth)
splash.append(message)
splash.append(tvoc)
splash.append(eco2)
clue.display.show(splash)

# setup SGP30 and wait for initial warm up
sgp30 = adafruit_sgp30.Adafruit_SGP30(board.I2C())
time.sleep(15)

# loop forever
while True:
    eCO2, TVOC = sgp30.iaq_measure()

    tvoc.text = "TVOC={:5d}".format(TVOC)
    eco2.text = "eCO2={:5d}".format(eCO2)

    level = 0
    for thresh in TVOC_LEVELS:
        if TVOC <= thresh:
            break
        level += 1

    if level <= len(TVOC_LEVELS):
        message.text = MESSAGES[level]
        mouth[0] = level
    else:
        message.text = "????"

    time.sleep(1)
