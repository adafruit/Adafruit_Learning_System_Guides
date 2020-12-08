import time
import board
import displayio
from adafruit_magtag.magtag import MagTag
import adafruit_il0373
from adafruit_display_shapes.circle import Circle

#  create MagTag and connect to network
magtag = MagTag()
magtag.network.connect()

#  setup display for use with displayio
displayio.release_displays()
display_bus = displayio.FourWire(board.SPI(), command=board.EPD_DC,
                                 chip_select=board.EPD_CS,
                                 reset=board.EPD_RESET, baudrate=1000000)
time.sleep(1)
display = adafruit_il0373.IL0373(
    display_bus,
    width=296,
    height=128,
    rotation=270,
    black_bits_inverted=False,
    color_bits_inverted=False,
    grayscale=True,
    refresh_time=1,
    seconds_per_frame=1
)

#  displayio group
group = displayio.Group(max_size=30)

#  import tree bitmap
tree = displayio.OnDiskBitmap(open("/atree.bmp", "rb"))

tree_grid = displayio.TileGrid(tree, pixel_shader=displayio.ColorConverter())

#  add bitmap to group
group.append(tree_grid)

#  list of circle positions
spots = [
    {'pos': (246, 53)},
    {'pos': (246, 75)},
    {'pos': (206, 42)},
    {'pos': (206, 64)},
    {'pos': (206, 86)},
    {'pos': (176, 31)},
    {'pos': (176, 53)},
    {'pos': (176, 75)},
    {'pos': (176, 97)},
    {'pos': (136, 42)},
    {'pos': (136, 64)},
    {'pos': (136, 86)},
    {'pos': (106, 31)},
    {'pos': (106, 53)},
    {'pos': (106, 75)},
    {'pos': (106, 97)},
    {'pos': (66, 31)},
    {'pos': (66, 53)},
    {'pos': (66, 75)},
    {'pos': (66, 97)},
    {'pos': (36, 20)},
    {'pos': (36, 42)},
    {'pos': (36, 64)},
    {'pos': (36, 86)},
    {'pos': (36, 108)}
    ]

#  circles to cover-up bitmap's number ornaments

#  array of the circles
circles = []
#  creating the circles & pulling in positions from spots
for spot in spots:
    circle = Circle(x0=spot['pos'][0], y0=spot['pos'][1],
                    r=11,
                    fill=0xFF00FF)
	#  adding circles to group
    group.append(circle)
	#  adding circles to circles array
    circles.append(circle)

#  grabs time from network
magtag.get_local_time()
#  parses time into month, date, etc
now = time.localtime()
month = now[1]
day = now[2]
print("day is", day)

#  sets colors of circles to transparent to reveal dates that have passed & current date
for i in range(day):
    circles[i].fill = None
    time.sleep(0.1)

#  updates display with bitmap and current circle colors
display.show(group)
display.refresh()
time.sleep(5)

#  goes into deep sleep for 12 hours
print("entering deep sleep")
magtag.exit_and_deep_sleep(43200)

#  entire code will run again after deep sleep cycle
#  similar to hitting the reset button
