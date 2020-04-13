import time
import json
import array
import math
import board
import busio
import audioio
import displayio
import digitalio
from adafruit_pyportal import PyPortal
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import label
from adafruit_display_shapes.circle import Circle
from adafruit_button import Button
import adafruit_touchscreen
from adafruit_mcp9600 import MCP9600

TITLE = "EZ Make Oven Controller"
VERSION = "1.2.0"

print(TITLE, "version ", VERSION)
time.sleep(2)

display_group = displayio.Group(max_size=20)
board.DISPLAY.show(display_group)

PROFILE_SIZE = 2            # plot thickness
GRID_SIZE = 2
GRID_STYLE = 3
TEMP_SIZE = 2
AXIS_SIZE = 2

BLACK = 0x0
BLUE = 0x2020FF
GREEN = 0x00FF55
RED = 0xFF0000
YELLOW = 0xFFFF00

WIDTH = board.DISPLAY.width
HEIGHT = board.DISPLAY.height

pyportal = PyPortal()

palette = displayio.Palette(5)
palette[0] = BLACK
palette[1] = GREEN
palette[2] = BLUE
palette[3] = RED
palette[4] = YELLOW

palette.make_transparent(0)

BACKGROUND_COLOR = 0
PROFILE_COLOR = 1
GRID_COLOR = 2
TEMP_COLOR = 3
AXIS_COLOR = 2

GXSTART = 100
GYSTART = 80
GWIDTH = WIDTH - GXSTART
GHEIGHT = HEIGHT - GYSTART
plot = displayio.Bitmap(GWIDTH, GHEIGHT, 4)

pyportal.splash.append(displayio.TileGrid(plot, pixel_shader=palette, x=GXSTART, y=GYSTART))

ts = adafruit_touchscreen.Touchscreen(board.TOUCH_XL, board.TOUCH_XR,
                                      board.TOUCH_YD, board.TOUCH_YU,
                                      calibration=(
                                          (5200, 59000),
                                          (5800, 57000)
                                          ),
                                      size=(WIDTH, HEIGHT))

class Beep(object):
    def __init__(self):
        self.duration = 0
        self.start = 0
        tone_volume = 1  # volume is from 0.0 to 1.0
        frequency = 440  # Set this to the Hz of the tone you want to generate.
        length = 4000 // frequency
        sine_wave = array.array("H", [0] * length)
        for i in range(length):
            sine_wave[i] = int((1 + math.sin(math.pi * 2 * i / length))
                               * tone_volume * (2 ** 15 - 1))
        self.sine_wave_sample = audioio.RawSample(sine_wave)

    # pylint: disable=protected-access
    def play(self, duration=0.1):
        if not pyportal._speaker_enable.value:
            pyportal._speaker_enable.value = True
            pyportal.audio.play(self.sine_wave_sample, loop=True)
            self.start = time.monotonic()
            self.duration = duration
            if duration <= .5:
                # for beeps less than .5 sec, sleep here,
                # otherwise, use refresh() in loop to turn off long beep
                time.sleep(duration)
                self.stop()

    def stop(self):
        if pyportal._speaker_enable.value:
            self.duration = 0
            pyportal.audio.stop()
            pyportal._speaker_enable.value = False

    def refresh(self):
        if time.monotonic() - self.start >= self.duration:
            self.stop()

class ReflowOvenControl(object):
    states = ("wait", "ready", "start", "preheat", "soak", "reflow", "cool")

    def __init__(self, pin):
        self.oven = digitalio.DigitalInOut(pin)
        self.oven.direction = digitalio.Direction.OUTPUT
        with open("/config.json", mode="r") as fpr:
            self.config = json.load(fpr)
            fpr.close()
        self.sensor_status = False
        with open("/profiles/" + self.config["profile"] + ".json", mode="r") as fpr:
            self.sprofile = json.load(fpr)
            fpr.close()
        i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
        try:
            self.sensor = MCP9600(i2c, self.config["sensor_address"], "K")
            self.ontemp = self.sensor.temperature
            self.offtemp = self.ontemp
            self.sensor_status = True
        except ValueError:
            print("temperature sensor not available")
        self.ontime = 0
        self.offtime = 0
        self.control = False
        self.reset()
        self.reflow_start = 0
        self.beep = Beep()
        self.set_state("ready")
        if self.sensor_status:
            if self.sensor.temperature >= 50:
                self.last_state = "wait"
                self.set_state("wait")

    def reset(self):
        self.ontime = 0
        self.offtime = 0
        self.enable(False)

    def get_profile_temp(self, seconds):
        x1 = self.sprofile["profile"][0][0]
        y1 = self.sprofile["profile"][0][1]
        for point in self.sprofile["profile"]:
            x2 = point[0]
            y2 = point[1]
            if x1 <= seconds < x2:
                temp = y1 + (y2 - y1) * (seconds - x1) // (x2 - x1)
                return temp
            x1 = x2
            y1 = y2
        return 0

    def set_state(self, state):
        self.state = state
        self.check_state()
        self.last_state = state

    # pylint: disable=too-many-branches, too-many-statements
    def check_state(self):
        try:
            temp = self.sensor.temperature
        except AttributeError:
            temp = 32  # sensor not available, use 32 for testing
            self.sensor_status = False
            # message.text = "Temperature sensor missing"
        self.beep.refresh()
        if self.state == "wait":
            self.enable(False)
            if self.state != self.last_state:
                # change in status, time for a beep!
                self.beep.play(0.1)
            if temp < 50:
                self.set_state("ready")
        if self.state == "ready":
            self.enable(False)
        if self.state == "start" and temp >= 50:
            self.set_state("preheat")
        if self.state == "start":
            message.text = "Starting"
            self.enable(True)
        if (self.state == "preheat" and temp >=
                self.sprofile["stages"]["soak"][1]):
            self.set_state("soak")
        if self.state == "preheat":
            message.text = "Preheat"
        if (self.state == "soak" and temp >=
                self.sprofile["stages"]["reflow"][1]):
            self.set_state("reflow")
        if self.state == "soak":
            message.text = "Soak"
        if (self.state == "reflow"
                and temp >= self.sprofile["stages"]["cool"][1]
                and self.reflow_start > 0
                and (time.monotonic() - self.reflow_start >=
                     self.sprofile["stages"]["cool"][0]
                     - self.sprofile["stages"]["reflow"][0])):
            self.set_state("cool")
            self.beep.play(5)
        if self.state == "reflow":
            message.text = "Reflow"
            if self.last_state != "reflow":
                self.reflow_start = time.monotonic()
        if self.state == "cool":
            self.enable(False)
            message.text = "Cool Down, Open Door"

        if self.state in ("start", "preheat", "soak", "reflow"):
            if self.state != self.last_state:
                # change in status, time for a beep!
                self.beep.play(.1)
            # oven temp control here
            # check range of calibration to catch any humps in the graph
            checktime = 0
            checktimemax = self.config["calibrate_seconds"]
            checkoven = False
            if not self.control:
                checktimemax = max(0, self.config["calibrate_seconds"] -
                                   (time.monotonic() - self.offtime))
            while checktime <= checktimemax:
                check_temp = self.get_profile_temp(int(timediff + checktime))
                if (temp + self.config["calibrate_temp"]*checktime/checktimemax
                        < check_temp):
                    checkoven = True
                    break
                checktime += 5
            if not checkoven:
                # hold oven temperature
                if (self.state in ("start", "preheat", "soak") and
                        self.offtemp > self.sensor.temperature):
                    checkoven = True
            self.enable(checkoven)

    # turn oven on or off
    def enable(self, enable):
        try:
            self.oven.value = enable
            self.control = enable
            if enable:
                self.offtime = 0
                self.ontime = time.monotonic()
                self.ontemp = self.sensor.temperature
                print("oven on")
            else:
                self.offtime = time.monotonic()
                self.ontime = 0
                self.offtemp = self.sensor.temperature
                print("oven off")
        except AttributeError:
            # bad sensor
            pass

class Graph(object):
    def __init__(self):
        self.xmin = 0
        self.xmax = 720  # graph up to 12 minutes
        self.ymin = 0
        self.ymax = 240
        self.xstart = 0
        self.ystart = 0
        self.width = GWIDTH
        self.height = GHEIGHT

    # pylint: disable=too-many-branches
    def draw_line(self, x1, y1, x2, y2, size=PROFILE_SIZE, color=1, style=1):
        # print("draw_line:", x1, y1, x2, y2)
        # convert graph coords to screen coords
        x1p = (self.xstart + self.width * (x1 - self.xmin)
               // (self.xmax - self.xmin))
        y1p = (self.ystart + int(self.height * (y1 - self.ymin)
                                 / (self.ymax - self.ymin)))
        x2p = (self.xstart + self.width * (x2 - self.xmin) //
               (self.xmax - self.xmin))
        y2p = (self.ystart + int(self.height * (y2 - self.ymin) /
                                 (self.ymax - self.ymin)))
        # print("screen coords:", x1p, y1p, x2p, y2p)

        if (max(x1p, x2p) - min(x1p, x2p)) > (max(y1p, y2p) - min(y1p, y2p)):
            for xx in range(min(x1p, x2p), max(x1p, x2p)):
                if x2p != x1p:
                    yy = y1p + (y2p - y1p) * (xx - x1p) // (x2p - x1p)
                    if style == 2:
                        if xx % 2 == 0:
                            self.draw_point(xx, yy, size, color)
                    elif style == 3:
                        if xx % 8 == 0:
                            self.draw_point(xx, yy, size, color)
                    elif style == 4:
                        if xx % 12 == 0:
                            self.draw_point(xx, yy, size, color)
                    else:
                        self.draw_point(xx, yy, size, color)
        else:
            for yy in range(min(y1p, y2p), max(y1p, y2p)):
                if y2p != y1p:
                    xx = x1p + (x2p - x1p) * (yy - y1p) // (y2p - y1p)
                    if style == 2:
                        if yy % 2 == 0:
                            self.draw_point(xx, yy, size, color)
                    elif style == 3:
                        if yy % 8 == 0:
                            self.draw_point(xx, yy, size, color)
                    elif style == 4:
                        if yy % 12 == 0:
                            self.draw_point(xx, yy, size, color)
                    else:
                        self.draw_point(xx, yy, size, color)

    def draw_graph_point(self, x, y, size=PROFILE_SIZE, color=1):
        """ draw point using graph coordinates """

        # wrap around graph point when x goes out of bounds
        x = (x - self.xmin) % (self.xmax - self.xmin) + self.xmin
        xx = (self.xstart + self.width * (x - self.xmin)
              // (self.xmax - self.xmin))
        yy = (self.ystart + int(self.height * (y - self.ymin)
                                / (self.ymax - self.ymin)))
        print("graph point:", x, y, xx, yy)
        self.draw_point(xx, max(0 + size, yy), size, color)

    def draw_point(self, x, y, size=PROFILE_SIZE, color=1):
        """Draw data point on to the plot bitmap at (x,y)."""
        if y is None:
            return
        offset = size // 2
        for xx in range(x-offset, x+offset+1):
            if xx in range(self.xstart, self.xstart + self.width):
                for yy in range(y-offset, y+offset+1):
                    if yy in range(self.ystart, self.ystart + self.height):
                        try:
                            yy = GHEIGHT - yy
                            plot[xx, yy] = color
                        except IndexError:
                            pass

def draw_profile(graph, profile):
    """Update the display with current info."""
    for i in range(GWIDTH * GHEIGHT):
        plot[i] = 0

    # draw stage lines
    # preheat
    graph.draw_line(profile["stages"]["preheat"][0], profile["temp_range"][0],
                    profile["stages"]["preheat"][0], profile["temp_range"][1]
                    * 1.1,
                    GRID_SIZE, GRID_COLOR, GRID_STYLE)
    graph.draw_line(profile["time_range"][0], profile["stages"]["preheat"][1],
                    profile["time_range"][1], profile["stages"]["preheat"][1],
                    GRID_SIZE, GRID_COLOR, GRID_STYLE)
    # soak
    graph.draw_line(profile["stages"]["soak"][0], profile["temp_range"][0],
                    profile["stages"]["soak"][0], profile["temp_range"][1]*1.1,
                    GRID_SIZE, GRID_COLOR, GRID_STYLE)
    graph.draw_line(profile["time_range"][0], profile["stages"]["soak"][1],
                    profile["time_range"][1], profile["stages"]["soak"][1],
                    GRID_SIZE, GRID_COLOR, GRID_STYLE)
    # reflow
    graph.draw_line(profile["stages"]["reflow"][0], profile["temp_range"][0],
                    profile["stages"]["reflow"][0], profile["temp_range"][1]
                    * 1.1,
                    GRID_SIZE, GRID_COLOR, GRID_STYLE)
    graph.draw_line(profile["time_range"][0], profile["stages"]["reflow"][1],
                    profile["time_range"][1], profile["stages"]["reflow"][1],
                    GRID_SIZE, GRID_COLOR, GRID_STYLE)
    # cool
    graph.draw_line(profile["stages"]["cool"][0], profile["temp_range"][0],
                    profile["stages"]["cool"][0], profile["temp_range"][1]*1.1,
                    GRID_SIZE, GRID_COLOR, GRID_STYLE)
    graph.draw_line(profile["time_range"][0], profile["stages"]["cool"][1],
                    profile["time_range"][1], profile["stages"]["cool"][1],
                    GRID_SIZE, GRID_COLOR, GRID_STYLE)

    # draw labels
    x = profile["time_range"][0]
    y = profile["stages"]["reflow"][1]
    xp = int(GXSTART + graph.width * (x - graph.xmin)
             // (graph.xmax - graph.xmin))
    yp = int(GHEIGHT * (y - graph.ymin)
             // (graph.ymax - graph.ymin))

    label_reflow.x = xp + 10
    label_reflow.y = HEIGHT - yp
    label_reflow.text = str(profile["stages"]["reflow"][1])
    print("reflow temp:", str(profile["stages"]["reflow"][1]))
    print("graph point: ", x, y, "->", xp, yp)

    x = profile["stages"]["reflow"][0]
    y = profile["stages"]["reflow"][1]

    # draw time line (horizontal)
    graph.draw_line(graph.xmin, graph.ymin + 1, graph.xmax,
                    graph.ymin + 1, AXIS_SIZE, AXIS_COLOR, 1)
    graph.draw_line(graph.xmin, graph.ymax, graph.xmax, graph.ymax,
                    AXIS_SIZE, AXIS_COLOR, 1)
    # draw time ticks
    tick = graph.xmin
    while tick < (graph.xmax - graph.xmin):
        graph.draw_line(tick, graph.ymin, tick, graph.ymin + 10,
                        AXIS_SIZE, AXIS_COLOR, 1)
        graph.draw_line(tick, graph.ymax, tick, graph.ymax - 10 - AXIS_SIZE,
                        AXIS_SIZE, AXIS_COLOR, 1)
        tick += 60

    # draw temperature line (vertical)
    graph.draw_line(graph.xmin, graph.ymin, graph.xmin,
                    graph.ymax, AXIS_SIZE, AXIS_COLOR, 1)
    graph.draw_line(graph.xmax - AXIS_SIZE + 1, graph.ymin,
                    graph.xmax - AXIS_SIZE + 1,
                    graph.ymax, AXIS_SIZE, AXIS_COLOR, 1)
    # draw temperature ticks
    tick = graph.ymin
    while tick < (graph.ymax - graph.ymin)*1.1:
        graph.draw_line(graph.xmin, tick, graph.xmin + 10, tick,
                        AXIS_SIZE, AXIS_COLOR, 1)
        graph.draw_line(graph.xmax, tick, graph.xmax - 10 - AXIS_SIZE,
                        tick, AXIS_SIZE, AXIS_COLOR, 1)
        tick += 50

    # draw profile
    x1 = profile["profile"][0][0]
    y1 = profile["profile"][0][1]
    for point in profile["profile"]:
        x2 = point[0]
        y2 = point[1]
        graph.draw_line(x1, y1, x2, y2, PROFILE_SIZE, PROFILE_COLOR, 1)
        # print(point)
        x1 = x2
        y1 = y2

def format_time(seconds):
    minutes = seconds // 60
    seconds = int(seconds) % 60
    return "{:02d}:{:02d}".format(minutes, seconds, width=2)

timediff = 0
oven = ReflowOvenControl(board.D4)
print("melting point: ", oven.sprofile["melting_point"])
font1 = bitmap_font.load_font("/fonts/OpenSans-9.bdf")
font1.load_glyphs(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789/:')
font2 = bitmap_font.load_font("/fonts/OpenSans-12.bdf")
font2.load_glyphs(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789/:')
font3 = bitmap_font.load_font("/fonts/OpenSans-16.bdf")
font3.load_glyphs(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789/:')


label_reflow = label.Label(font1, text="", max_glyphs=10,
                           color=0xFFFFFF, line_spacing=0)
label_reflow.x = 0
label_reflow.y = -20
pyportal.splash.append(label_reflow)
title_label = label.Label(font3, text=TITLE)
title_label.x = 5
title_label.y = 14
pyportal.splash.append(title_label)
# version_label = label.Label(font1, text=VERSION, color=0xAAAAAA)
# version_label.x = 300
# version_label.y = 40
# pyportal.splash.append(version_label)
message = label.Label(font2, text="Wait", max_glyphs=30)
message.x = 100
message.y = 40
pyportal.splash.append(message)
alloy_label = label.Label(font1, text="Alloy:", color=0xAAAAAA)
alloy_label.x = 5
alloy_label.y = 40
pyportal.splash.append(alloy_label)
alloy_data = label.Label(font1, text=str(oven.sprofile["alloy"]))
alloy_data.x = 10
alloy_data.y = 60
pyportal.splash.append(alloy_data)
profile_label = label.Label(font1, text="Profile:", color=0xAAAAAA)
profile_label.x = 5
profile_label.y = 80
pyportal.splash.append(profile_label)
profile_data = label.Label(font1, text=oven.sprofile["title"])
profile_data.x = 10
profile_data.y = 100
pyportal.splash.append(profile_data)
timer_label = label.Label(font1, text="Time:", color=0xAAAAAA)
timer_label.x = 5
timer_label.y = 120
pyportal.splash.append(timer_label)
timer_data = label.Label(font3, text=format_time(timediff), max_glyphs=10)
timer_data.x = 10
timer_data.y = 140
pyportal.splash.append(timer_data)
temp_label = label.Label(font1, text="Temp(C):", color=0xAAAAAA)
temp_label.x = 5
temp_label.y = 160
pyportal.splash.append(temp_label)
temp_data = label.Label(font3, text="--", max_glyphs=10)
temp_data.x = 10
temp_data.y = 180
pyportal.splash.append(temp_data)
circle = Circle(308, 12, 8, fill=0)
pyportal.splash.append(circle)

sgraph = Graph()

#sgraph.xstart = 100
#sgraph.ystart = 4
sgraph.xstart = 0
sgraph.ystart = 0
#sgraph.width = WIDTH - sgraph.xstart - 4  # 216 for standard PyPortal
#sgraph.height = HEIGHT - 80  # 160 for standard PyPortal
sgraph.width = GWIDTH  # 216 for standard PyPortal
sgraph.height = GHEIGHT  # 160 for standard PyPortal
sgraph.xmin = oven.sprofile["time_range"][0]
sgraph.xmax = oven.sprofile["time_range"][1]
sgraph.ymin = oven.sprofile["temp_range"][0]
sgraph.ymax = oven.sprofile["temp_range"][1]*1.1
print("x range:", sgraph.xmin, sgraph.xmax)
print("y range:", sgraph.ymin, sgraph.ymax)
draw_profile(sgraph, oven.sprofile)
buttons = []
if oven.sensor_status:
    button = Button(x=0, y=HEIGHT-40, width=80, height=40,
                    label="Start", label_font=font2)
    buttons.append(button)

for b in buttons:
    pyportal.splash.append(b.group)

try:
    board.DISPLAY.refresh(target_frames_per_second=60)
except AttributeError:
    board.DISPLAY.refresh_soon()
print("display complete")
last_temp = 0
last_state = "ready"
last_control = False
second_timer = time.monotonic()
timer = time.monotonic()
while True:
    try:
        board.DISPLAY.refresh(target_frames_per_second=60)
    except AttributeError:
        board.DISPLAY.refresh_soon()
    oven.beep.refresh()  # this allows beeps less than one second in length
    try:
        oven_temp = int(oven.sensor.temperature)
    except AttributeError:
        oven_temp = 32  # testing
        oven.sensor_status = False
        message.text = "Bad/missing temp sensor"
    if oven.control != last_control:
        last_control = oven.control
        if oven.control:
            circle.fill = 0xFF0000
        else:
            circle.fill = 0x0
    p = ts.touch_point
    status = ""
    last_status = ""

    if p:
        if p[0] >= 0 and p[0] <= 80 and p[1] >= HEIGHT - 40 and p[1] <= HEIGHT:
            print("touch!")
            if oven.state == "ready":
                button.label = "Stop"
                oven.set_state("start")
            else:
                # cancel operation
                message.text = "Wait"
                button.label = "Wait"
                oven.set_state("wait")
            time.sleep(1)  # for debounce
    if oven.sensor_status:
        if oven.state == "ready":
            status = "Ready"
            if last_state != "ready":
                oven.beep.refresh()
                draw_profile(sgraph, oven.sprofile)
                timer_data.text = format_time(0)
            if button.label != "Start":
                button.label = "Start"
        if oven.state == "start":
            status = "Starting"
            if last_state != "start":
                timer = time.monotonic()
        if oven.state == "preheat":
            if last_state != "preheat":
                timer = time.monotonic()  # reset timer when preheat starts
            status = "Preheat"
        if oven.state == "soak":
            status = "Soak"
        if oven.state == "reflow":
            status = "Reflow"
        if oven.state == "cool" or oven.state == "wait":
            status = "Cool Down, Open Door"
        if last_status != status:
            message.text = status
            last_status = status

        if oven_temp != last_temp and oven.sensor_status:
            last_temp = oven_temp
            temp_data.text = str(oven_temp)
        # update once per second when oven is active
        if oven.state != "ready" and time.monotonic() - second_timer >= 1.0:
            second_timer = time.monotonic()
            oven.check_state()
            if oven.state == "preheat" and last_state != "preheat":
                timer = time.monotonic()  # reset timer at start of preheat
            timediff = int(time.monotonic() - timer)
            timer_data.text = format_time(timediff)
            print(oven.state)
            if oven_temp >= 50:
                sgraph.draw_graph_point(int(timediff), oven_temp,
                                        size=TEMP_SIZE, color=TEMP_COLOR)

        last_state = oven.state
