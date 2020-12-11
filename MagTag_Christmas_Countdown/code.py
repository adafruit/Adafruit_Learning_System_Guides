import time
import displayio
from adafruit_magtag.magtag import MagTag
from adafruit_display_shapes.circle import Circle

#  create MagTag and connect to network
magtag = MagTag()
magtag.network.connect()

#  displayio groups
group = displayio.Group(max_size=30)
tree_group = displayio.Group(max_size=30)
circle_group = displayio.Group(max_size=30)

#  import tree bitmap
tree = displayio.OnDiskBitmap(open("/atree.bmp", "rb"))

tree_grid = displayio.TileGrid(tree, pixel_shader=displayio.ColorConverter())

#  add bitmap to its group
tree_group.append(tree_grid)
#  add tree group to the main group
group.append(tree_group)

#  list of circle positions
spots = (
    (246, 53),
    (246, 75),
    (206, 42),
    (206, 64),
    (206, 86),
    (176, 31),
    (176, 53),
    (176, 75),
    (176, 97),
    (136, 42),
    (136, 64),
    (136, 86),
    (106, 31),
    (106, 53),
    (106, 75),
    (106, 97),
    (66, 31),
    (66, 53),
    (66, 75),
    (66, 97),
    (36, 20),
    (36, 42),
    (36, 64),
    (36, 86),
    (36, 108)
    )

#  circles to cover-up bitmap's number ornaments

#  creating the circles & pulling in positions from spots
for spot in spots:
    circle = Circle(x0=spot[0], y0=spot[1],
                    r=11,
                    fill=0xFF00FF)
	#  adding circles to their display group
    circle_group.append(circle)

#  adding circles group to main display group
group.append(circle_group)

#  grabs time from network
magtag.get_local_time()
#  parses time into month, date, etc
now = time.localtime()
month = now[1]
day = now[2]
print("day is", day)

#  sets colors of circles to transparent to reveal dates that have passed & current date
for i in range(day):
    circle_group[i].fill = None
    time.sleep(0.1)

#  updates display with bitmap and current circle colors
magtag.display.show(group)
magtag.display.refresh()
time.sleep(5)

#  goes into deep sleep for 12 hours
print("entering deep sleep")
magtag.exit_and_deep_sleep(43200)

#  entire code will run again after deep sleep cycle
#  similar to hitting the reset button
