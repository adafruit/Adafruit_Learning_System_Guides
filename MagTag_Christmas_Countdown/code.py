import time
import displayio
from adafruit_magtag.magtag import MagTag
from adafruit_display_shapes.circle import Circle

#  create MagTag and connect to network
try:
    magtag = MagTag()
    magtag.network.connect()
except (ConnectionError, ValueError, RuntimeError) as e:
    print("*** MagTag(), Some error occured, retrying! -", e)
    # Exit program and restart in 1 seconds.
    magtag.exit_and_deep_sleep(1)



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

ball_color = [0x555555, 0xaaaaaa, 0xFFFFFF] # All colors except black (0x000000)
ball_index = 0

#  creating the circles & pulling in positions from spots
for spot in spots:
    circle = Circle(x0=spot[0], y0=spot[1], r=11, fill=ball_color[ball_index]) # Each ball has a color
    ball_index += 1
    ball_index %= len(ball_color)

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
(hour, minutes, seconds) = now[3:6]
seconds_since_midnight = 60 * (hour*60 + minutes)+seconds
print( f"day is {day}, ({seconds_since_midnight} seconds since midnight)")


#  sets colors of circles to transparent to reveal dates that have passed & current date
for i in range(day):
    circle_group[i].fill = None
    time.sleep(0.1)

#  updates display with bitmap and current circle colors
magtag.display.show(group)
magtag.display.refresh()
time.sleep(5)

#  goes into deep sleep till a 'stroke' past midnight
print("entering deep sleep")
seconds_to_sleep = 24*60*60 - seconds_since_midnight + 10
print( f"sleeping for {seconds_to_sleep} seconds")
magtag.exit_and_deep_sleep(seconds_to_sleep)

#  entire code will run again after deep sleep cycle
#  similar to hitting the reset button
