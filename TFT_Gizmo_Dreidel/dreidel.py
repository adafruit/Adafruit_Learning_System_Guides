import time
import random
import displayio
import adafruit_imageload
from adafruit_circuitplayground.bluefruit import cpb
from adafruit_gizmo import tft_gizmo

SHAKE_THRESHOLD = 20

#pylint: disable=bad-continuation
# define melody to play while spinning (freq, duration)
melody = (
#      oh       drei       del      drei      del
    (330, 8), (392, 8), (330, 8), (392, 8), (330, 8),
#     drei       del         I       made      it
    (392, 8), (330, 16), (330, 8), (392, 8), (392, 8),
#     out        of       clay
    (349, 8), (330, 8), (294, 16), (0, 8),
#      oh       drei       del      drei      del
    (294, 8), (349, 8), (294, 8), (349, 8), (294, 8),
#     drei        del      then      drei      del
    (349, 8), (294, 16), (294, 8), (392, 8), (349, 8),
#       I       shall      play
    (330, 8), (294, 8), (262, 16),
)
melody_tempo = 0.02
#pylint: enable=bad-continuation

# setup TFT Gizmo and main display group (splash)
display = tft_gizmo.TFT_Gizmo()
splash = displayio.Group()
display.show(splash)

# load dreidel background image
dreidel_bmp, dreidel_pal = adafruit_imageload.load("/dreidel_background.bmp",
                                                   bitmap=displayio.Bitmap,
                                                   palette=displayio.Palette)
dreidel_tg = displayio.TileGrid(dreidel_bmp, pixel_shader=dreidel_pal)
splash.append(dreidel_tg)

# load dreidel symbols (sprite sheet)
symbols_bmp, symbols_pal = adafruit_imageload.load("/dreidel_sheet.bmp",
                                                   bitmap=displayio.Bitmap,
                                                   palette=displayio.Palette)
for index, color in enumerate(symbols_pal):
    if color == 0xFFFF01:
        symbols_pal.make_transparent(index)
symbols_tg = displayio.TileGrid(symbols_bmp, pixel_shader=symbols_pal,
                                width = 1,
                                height = 1,
                                tile_width = 60,
                                tile_height = 60)
symbols_group = displayio.Group(scale=2, x=60, y=70)
symbols_group.append(symbols_tg)
splash.append(symbols_group)

# dreidel time!
tile = 0
while True:
    # wait for shake
    while not cpb.shake(shake_threshold=SHAKE_THRESHOLD):
        pass
    # play melody while "spinning" the symbols
    for note, duration in melody:
        symbols_tg[0] = tile % 4
        tile += 1
        cpb.play_tone(note, duration * melody_tempo)
    # land on a random symbol
    symbols_tg[0] = random.randint(0, 3)
    # prevent immediate re-shake
    time.sleep(2)
