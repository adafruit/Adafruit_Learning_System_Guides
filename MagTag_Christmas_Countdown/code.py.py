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

#  circles to cover-up bitmap's number ornaments
c_1 = Circle(246, 53, 11, fill = 0xFF00FF)
c_2 = Circle(246, 75, 11, fill = 0xFF00FF)
c_3 = Circle(206, 42, 11, fill = 0xFF00FF)
c_4 = Circle(206, 64, 11, fill = 0xFF00FF)
c_5 = Circle(206, 86, 11, fill = 0xFF00FF)
c_6 = Circle(176, 31, 11, fill = 0xFF00FF)
c_7 = Circle(176, 53, 11, fill = 0xFF00FF)
c_8 = Circle(176, 75, 11, fill = 0xFF00FF)
c_9 = Circle(176, 97, 11, fill = 0xFF00FF)
c_10 = Circle(136, 42, 11, fill = 0xFF00FF)
c_11 = Circle(136, 64, 11, fill = 0xFF00FF)
c_12 = Circle(136, 86, 11, fill = 0xFF00FF)
c_13 = Circle(106, 31, 11, fill = 0xFF00FF)
c_14 = Circle(106, 53, 11, fill = 0xFF00FF)
c_15 = Circle(106, 75, 11, fill = 0xFF00FF)
c_16 = Circle(106, 97, 11, fill = 0xFF00FF)
c_17 = Circle(66, 31, 11, fill = 0xFF00FF)
c_18 = Circle(66, 53, 11, fill = 0xFF00FF)
c_19 = Circle(66, 75, 11, fill = 0xFF00FF)
c_20 = Circle(66, 97, 11, fill = 0xFF00FF)
c_21 = Circle(36, 20, 11, fill = 0xFF00FF)
c_22 = Circle(36, 42, 11, fill = 0xFF00FF)
c_23 = Circle(36, 64, 11, fill = 0xFF00FF)
c_24 = Circle(36, 86, 11, fill = 0xFF00FF)
c_25 = Circle(36, 108, 11, fill = 0xFF00FF)

#  adding bitmap and circles to group
group.append(tree_grid)
group.append(c_1)
group.append(c_2)
group.append(c_3)
group.append(c_4)
group.append(c_5)
group.append(c_6)
group.append(c_7)
group.append(c_8)
group.append(c_9)
group.append(c_10)
group.append(c_11)
group.append(c_12)
group.append(c_13)
group.append(c_14)
group.append(c_15)
group.append(c_16)
group.append(c_17)
group.append(c_18)
group.append(c_19)
group.append(c_20)
group.append(c_21)
group.append(c_22)
group.append(c_23)
group.append(c_24)
group.append(c_25)

#  array of circles
balls = [c_1, c_2, c_3, c_4, c_5, c_6, c_7, c_8, c_9, c_10,
         c_11, c_12, c_13, c_14, c_15, c_16, c_17, c_18, c_19,
         c_20, c_21, c_22, c_23, c_24, c_25]

#  grabs time from network
magtag.get_local_time()
#  parses time into month, date, etc
now = time.localtime()
month = now[1]
day = now[2]
print("day is", day)

#  sets colors of circles to transparent to reveal dates that have passed & current date
for i in range(day):
    balls[i].fill = None
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
