# SPDX-FileCopyrightText: 2019 Dan Cogliano for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import json
import array
import math
import gc
import board
import busio
import audioio
import audiocore
import displayio
import digitalio
import os
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text import bitmap_label as label
from adafruit_display_shapes.circle import Circle
from adafruit_button import Button
import adafruit_touchscreen
from adafruit_mcp9600 import MCP9600

TITLE = "EZ Make Oven Controller"
VERSION = "1.3.3"

print(TITLE, "version ", VERSION)
time.sleep(2)

PROFILE_SIZE = 2  # plot thickness
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

ts = adafruit_touchscreen.Touchscreen(
    board.TOUCH_XL,
    board.TOUCH_XR,
    board.TOUCH_YD,
    board.TOUCH_YU,
    calibration=((5200, 59000), (5800, 57000)),
    size=(WIDTH, HEIGHT),
)


class Beep(object):
    def __init__(self):
        self.duration = 0
        self.start = 0
        tone_volume = 1  # volume is from 0.0 to 1.0
        frequency = 440  # Set this to the Hz of the tone you want to generate.
        length = 4000 // frequency
        sine_wave = array.array("H", [0] * length)
        for i in range(length):
            sine_wave[i] = int(
                (1 + math.sin(math.pi * 2 * i / length)) * tone_volume * (2 ** 15 - 1)
            )
        self.sine_wave_sample = audiocore.RawSample(sine_wave)

        self._speaker_enable = digitalio.DigitalInOut(board.SPEAKER_ENABLE)
        self._speaker_enable.switch_to_output(False)

        if hasattr(board, "AUDIO_OUT"):
            self.audio = audioio.AudioOut(board.AUDIO_OUT)
        elif hasattr(board, "SPEAKER"):
            self.audio = audioio.AudioOut(board.SPEAKER)
        else:
            raise AttributeError("Board does not have a builtin speaker!")

    # pylint: disable=protected-access
    def play(self, duration=0.1):
        if not self._speaker_enable.value:
            self._speaker_enable.value = True
            self.audio.play(self.sine_wave_sample, loop=True)
            self.start = time.monotonic()
            self.duration = duration
            if duration <= 0.5:
                # for beeps less than .5 sec, sleep here,
                # otherwise, use refresh() in loop to turn off long beep
                time.sleep(duration)
                self.stop()

    def stop(self):
        if self._speaker_enable.value:
            self.duration = 0
            self.audio.stop()
            self._speaker_enable.value = False

    def refresh(self):
        if time.monotonic() - self.start >= self.duration:
            self.stop()


class ReflowOvenControl(object):
    global message, timediff, sgraph, timer_data

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
        self.control = False
        self.reset()
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
        self.reflow_start = 0

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
            if temp < 35:
                self.set_state("ready")
                oven.reset()
                draw_profile(sgraph, oven.sprofile)
                timer_data.text = format_time(0)

        if self.state == "ready":
            self.enable(False)
        if self.state == "start" and temp >= 50:
            self.set_state("preheat")
        if self.state == "start":
            message.text = "Starting"
            self.enable(True)
        if self.state == "preheat" and temp >= self.sprofile["stages"]["soak"][1]:
            self.set_state("soak")
        if self.state == "preheat":
            message.text = "Preheat"
        if self.state == "soak" and temp >= self.sprofile["stages"]["reflow"][1]:
            self.set_state("reflow")
        if self.state == "soak":
            message.text = "Soak"
        if (
            self.state == "reflow"
            and temp >= self.sprofile["stages"]["cool"][1]
            and self.reflow_start > 0
            and (
                time.monotonic() - self.reflow_start
                >= self.sprofile["stages"]["cool"][0]
                - self.sprofile["stages"]["reflow"][0]
            )
        ):
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
                self.beep.play(0.1)
            # oven temp control here
            # check range of calibration to catch any humps in the graph
            checktime = 0
            checktimemax = self.config["calibrate_seconds"]
            checkoven = False
            if not self.control:
                checktimemax = max(
                    0,
                    self.config["calibrate_seconds"]
                    - (time.monotonic() - self.offtime),
                )
            while checktime <= checktimemax:
                check_temp = self.get_profile_temp(int(timediff + checktime))
                if (
                    temp + self.config["calibrate_temp"] * checktime / checktimemax
                    < check_temp
                ):
                    checkoven = True
                    break
                checktime += 5
            if not checkoven:
                # hold oven temperature
                if (
                    self.state in ("start", "preheat", "soak")
                    and self.offtemp > self.sensor.temperature
                ):
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
        x1p = self.xstart + self.width * (x1 - self.xmin) // (self.xmax - self.xmin)
        y1p = self.ystart + int(
            self.height * (y1 - self.ymin) / (self.ymax - self.ymin)
        )
        x2p = self.xstart + self.width * (x2 - self.xmin) // (self.xmax - self.xmin)
        y2p = self.ystart + int(
            self.height * (y2 - self.ymin) / (self.ymax - self.ymin)
        )
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
        xx = self.xstart + self.width * (x - self.xmin) // (self.xmax - self.xmin)
        yy = self.ystart + int(self.height * (y - self.ymin) / (self.ymax - self.ymin))
        print("graph point:", x, y, xx, yy)
        self.draw_point(xx, max(0 + size, yy), size, color)

    def draw_point(self, x, y, size=PROFILE_SIZE, color=1):
        """Draw data point on to the plot bitmap at (x,y)."""
        if y is None:
            return
        offset = size // 2
        for xx in range(x - offset, x + offset + 1):
            if xx in range(self.xstart, self.xstart + self.width):
                for yy in range(y - offset, y + offset + 1):
                    if yy in range(self.ystart, self.ystart + self.height):
                        try:
                            yy = GHEIGHT - yy
                            plot[xx, yy] = color
                        except IndexError:
                            pass


def draw_profile(graph, profile):
    global label_reflow

    """Update the display with current info."""
    for i in range(GWIDTH * GHEIGHT):
        plot[i] = 0

    # draw stage lines
    # preheat
    graph.draw_line(
        profile["stages"]["preheat"][0],
        profile["temp_range"][0],
        profile["stages"]["preheat"][0],
        profile["temp_range"][1] * 1.1,
        GRID_SIZE,
        GRID_COLOR,
        GRID_STYLE,
    )
    graph.draw_line(
        profile["time_range"][0],
        profile["stages"]["preheat"][1],
        profile["time_range"][1],
        profile["stages"]["preheat"][1],
        GRID_SIZE,
        GRID_COLOR,
        GRID_STYLE,
    )
    # soak
    graph.draw_line(
        profile["stages"]["soak"][0],
        profile["temp_range"][0],
        profile["stages"]["soak"][0],
        profile["temp_range"][1] * 1.1,
        GRID_SIZE,
        GRID_COLOR,
        GRID_STYLE,
    )
    graph.draw_line(
        profile["time_range"][0],
        profile["stages"]["soak"][1],
        profile["time_range"][1],
        profile["stages"]["soak"][1],
        GRID_SIZE,
        GRID_COLOR,
        GRID_STYLE,
    )
    # reflow
    graph.draw_line(
        profile["stages"]["reflow"][0],
        profile["temp_range"][0],
        profile["stages"]["reflow"][0],
        profile["temp_range"][1] * 1.1,
        GRID_SIZE,
        GRID_COLOR,
        GRID_STYLE,
    )
    graph.draw_line(
        profile["time_range"][0],
        profile["stages"]["reflow"][1],
        profile["time_range"][1],
        profile["stages"]["reflow"][1],
        GRID_SIZE,
        GRID_COLOR,
        GRID_STYLE,
    )
    # cool
    graph.draw_line(
        profile["stages"]["cool"][0],
        profile["temp_range"][0],
        profile["stages"]["cool"][0],
        profile["temp_range"][1] * 1.1,
        GRID_SIZE,
        GRID_COLOR,
        GRID_STYLE,
    )
    graph.draw_line(
        profile["time_range"][0],
        profile["stages"]["cool"][1],
        profile["time_range"][1],
        profile["stages"]["cool"][1],
        GRID_SIZE,
        GRID_COLOR,
        GRID_STYLE,
    )

    # draw labels
    x = profile["time_range"][0]
    y = profile["stages"]["reflow"][1]
    xp = int(GXSTART + graph.width * (x - graph.xmin) // (graph.xmax - graph.xmin))
    yp = int(GHEIGHT * (y - graph.ymin) // (graph.ymax - graph.ymin))

    label_reflow.x = xp + 10
    label_reflow.y = HEIGHT - yp
    label_reflow.text = str(profile["stages"]["reflow"][1])
    print("reflow temp:", str(profile["stages"]["reflow"][1]))
    print("graph point: ", x, y, "->", xp, yp)

    x = profile["stages"]["reflow"][0]
    y = profile["stages"]["reflow"][1]

    # draw time line (horizontal)
    graph.draw_line(
        graph.xmin, graph.ymin + 1, graph.xmax, graph.ymin + 1, AXIS_SIZE, AXIS_COLOR, 1
    )
    graph.draw_line(
        graph.xmin, graph.ymax, graph.xmax, graph.ymax, AXIS_SIZE, AXIS_COLOR, 1
    )
    # draw time ticks
    tick = graph.xmin
    while tick < (graph.xmax - graph.xmin):
        graph.draw_line(
            tick, graph.ymin, tick, graph.ymin + 10, AXIS_SIZE, AXIS_COLOR, 1
        )
        graph.draw_line(
            tick,
            graph.ymax,
            tick,
            graph.ymax - 10 - AXIS_SIZE,
            AXIS_SIZE,
            AXIS_COLOR,
            1,
        )
        tick += 60

    # draw temperature line (vertical)
    graph.draw_line(
        graph.xmin, graph.ymin, graph.xmin, graph.ymax, AXIS_SIZE, AXIS_COLOR, 1
    )
    graph.draw_line(
        graph.xmax - AXIS_SIZE + 1,
        graph.ymin,
        graph.xmax - AXIS_SIZE + 1,
        graph.ymax,
        AXIS_SIZE,
        AXIS_COLOR,
        1,
    )
    # draw temperature ticks
    tick = graph.ymin
    while tick < (graph.ymax - graph.ymin) * 1.1:
        graph.draw_line(
            graph.xmin, tick, graph.xmin + 10, tick, AXIS_SIZE, AXIS_COLOR, 1
        )
        graph.draw_line(
            graph.xmax,
            tick,
            graph.xmax - 10 - AXIS_SIZE,
            tick,
            AXIS_SIZE,
            AXIS_COLOR,
            1,
        )
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


def check_buttons_press_location(p, button_details):
    """
    Function to easily check a button press within a list of Buttons
    """
    for button in button_details:
        if button.contains(p):
            return button
    return None


def change_profile(oven):
    """
    Function added to render the available profile selections to screen and then load into memory

    Limitations: Only the first 6 profiles will be displayed to honor to the size format of the screen
    """
    selected_file = None

    display_group = displayio.Group()
    gc.collect()

    title_label = label.Label(font3, text=TITLE)
    title_label.x = 5
    title_label.y = 14
    display_group.append(title_label)
    profile_label = label.Label(font2, text="Profile Change")
    profile_label.x = 5
    profile_label.y = 45
    display_group.append(profile_label)

    selected_label_default_text = "Selected Profile: "
    selected_label = label.Label(font1, text=selected_label_default_text)
    selected_label.x = 5
    selected_label.y = HEIGHT - 20
    display_group.append(selected_label)

    buttons = []
    button_details = {}
    button_x = 20
    button_y = 60
    button_y_start = 60
    button_height = 30
    button_width = 120
    spacing = 10
    profile_limit = 6
    count = 0
    dir_list = os.listdir("/profiles/")
    for f in dir_list:
        f = f.split('.')[0]
        button = Button(
            x=button_x, y=button_y, width=button_width, height=button_height, label=f, label_font=font1
        )
        button_details[f] = [button_x, button_y, button_width, button_height]
        buttons.append(button)
        button_y += button_height + spacing

        count+=1

        if count == 3:
            button_x += button_width + spacing
            button_y = button_y_start

        if count >= 6:
            break

    save_button = Button(x=WIDTH-70, y=HEIGHT-50, width=60, height=40, label="Save", label_font=font2)
    button_details["Save"] = [WIDTH-70, HEIGHT-50, 60, 40]
    buttons.append(save_button)

    for b in buttons:
        display_group.append(b)

    board.DISPLAY.show(display_group)

    try:
        board.DISPLAY.refresh(target_frames_per_second=60)
    except AttributeError:
        board.DISPLAY.refresh_soon()
    print("Profile change display complete")

    while True:
        gc.collect()
        try:
            board.DISPLAY.refresh(target_frames_per_second=60)
        except AttributeError:
            board.DISPLAY.refresh_soon()

        p = ts.touch_point

        if p:
            button_pressed = check_buttons_press_location(p, buttons)
            if button_pressed:
                print(f"{button_pressed.label} button pressed")
                if button_pressed.label == "Save":
                    with open("/profiles/" + selected_file + ".json", mode="r") as fpr:
                        oven.sprofile = json.load(fpr)
                        fpr.close()
                        oven.reset()
                    return
                else:
                    selected_file = button_pressed.label
                    print(f"Profile selected: {selected_file}")
                    selected_label.text = selected_label_default_text + " " + button_pressed.label

                time.sleep(1)  # for debounce


def default_view():
    """
    The below code was wrapped into this fucntion to give execution back and forth between this the default view
    of the EZ Make Oven and the alternative profile selection view.

    As such there were numerous global variables that have been declared as needed in the various other functions
    that use them.
    """

    global label_reflow, oven, message, timediff, plot, sgraph, timer_data

    display_group = displayio.Group()
    board.DISPLAY.show(display_group)

    plot = displayio.Bitmap(GWIDTH, GHEIGHT, 4)

    display_group.append(
        displayio.TileGrid(plot, pixel_shader=palette, x=GXSTART, y=GYSTART)
    )

    timediff = 0

    print("melting point: ", oven.sprofile["melting_point"])

    label_reflow = label.Label(font1, text="", color=0xFFFFFF, line_spacing=0)
    label_reflow.x = 0
    label_reflow.y = -20
    display_group.append(label_reflow)
    title_label = label.Label(font3, text=TITLE)
    title_label.x = 5
    title_label.y = 14
    display_group.append(title_label)
    # version_label = label.Label(font1, text=VERSION, color=0xAAAAAA)
    # version_label.x = 300
    # version_label.y = 40
    # display_group.append(version_label)
    message = label.Label(font2, text="Wait")
    message.x = 100
    message.y = 40
    display_group.append(message)
    alloy_label = label.Label(font1, text="Alloy:", color=0xAAAAAA)
    alloy_label.x = 5
    alloy_label.y = 40
    display_group.append(alloy_label)
    alloy_data = label.Label(font1, text=str(oven.sprofile["alloy"]))
    alloy_data.x = 10
    alloy_data.y = 60
    display_group.append(alloy_data)
    profile_label = label.Label(font1, text="Profile:", color=0xAAAAAA)
    profile_label.x = 5
    profile_label.y = 80
    display_group.append(profile_label)
    profile_data = label.Label(font1, text=oven.sprofile["title"])
    profile_data.x = 10
    profile_data.y = 100
    display_group.append(profile_data)
    timer_label = label.Label(font1, text="Time:", color=0xAAAAAA)
    timer_label.x = 5
    timer_label.y = 120
    display_group.append(timer_label)
    timer_data = label.Label(font3, text=format_time(timediff))
    timer_data.x = 10
    timer_data.y = 140
    display_group.append(timer_data)
    temp_label = label.Label(font1, text="Temp(C):", color=0xAAAAAA)
    temp_label.x = 5
    temp_label.y = 160
    display_group.append(temp_label)
    temp_data = label.Label(font3, text="--")
    temp_data.x = 10
    temp_data.y = 180
    display_group.append(temp_data)
    circle = Circle(308, 12, 8, fill=0)
    display_group.append(circle)

    sgraph = Graph()

    # sgraph.xstart = 100
    # sgraph.ystart = 4
    sgraph.xstart = 0
    sgraph.ystart = 0
    # sgraph.width = WIDTH - sgraph.xstart - 4  # 216 for standard PyPortal
    # sgraph.height = HEIGHT - 80  # 160 for standard PyPortal
    sgraph.width = GWIDTH  # 216 for standard PyPortal
    sgraph.height = GHEIGHT  # 160 for standard PyPortal
    sgraph.xmin = oven.sprofile["time_range"][0]
    sgraph.xmax = oven.sprofile["time_range"][1]
    sgraph.ymin = oven.sprofile["temp_range"][0]
    sgraph.ymax = oven.sprofile["temp_range"][1] * 1.1
    print("x range:", sgraph.xmin, sgraph.xmax)
    print("y range:", sgraph.ymin, sgraph.ymax)
    draw_profile(sgraph, oven.sprofile)
    buttons = []
    if oven.sensor_status:
        button = Button(
            x=0, y=HEIGHT - 40, width=80, height=40, label="Start", label_font=font2
        )
        buttons.append(button)
        profile_button = Button(
            x=WIDTH - 100, y=40, width=100, height=30, label="Profile Change", label_font=font1
        )
        buttons.append(profile_button)

    for b in buttons:
        display_group.append(b)

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

    display_profile_button = True
    is_Running = True
    while is_Running:
        gc.collect()
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
            if button.contains(p):
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

            elif profile_button.contains(p):
                if message.text == "Ready":  # only allow profile change when NOT running
                    print("Profile change button pressed")
                    is_Running = False
                    change_profile(oven)

        if oven.sensor_status:
            if oven.state == "ready":
                status = "Ready"
                display_profile_button = True
                if last_state != "ready":
                    oven.beep.refresh()
                    oven.reset()
                    draw_profile(sgraph, oven.sprofile)
                    timer_data.text = format_time(0)
                if button.label != "Start":
                    button.label = "Start"
            if oven.state == "start":
                status = "Starting"
                display_profile_button = False
                if last_state != "start":
                    timer = time.monotonic()
            if oven.state == "preheat":
                if last_state != "preheat":
                    timer = time.monotonic()  # reset timer when preheat starts
                status = "Preheat"
                display_profile_button = False
            if oven.state == "soak":
                status = "Soak"
                display_profile_button = False
            if oven.state == "reflow":
                status = "Reflow"
                display_profile_button = False
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
                    sgraph.draw_graph_point(
                        int(timediff), oven_temp, size=TEMP_SIZE, color=TEMP_COLOR
                    )

            last_state = oven.state

        # Manage whether the Profile Button should be displayed or not
        if display_profile_button == True:
            try:
                display_group.append(profile_button)
            except ValueError:
                # profile_button already in the display_group
                pass
        else:
            try:
                display_group.remove(profile_button)
            except ValueError:
                # profile_button is missing, handle gracefully
                pass

# Global variables that are used in numerous of the supporting functions
font1 = bitmap_font.load_font("/fonts/OpenSans-9.bdf")
font2 = bitmap_font.load_font("/fonts/OpenSans-12.bdf")
font3 = bitmap_font.load_font("/fonts/OpenSans-16.bdf")
label_reflow = None
oven = ReflowOvenControl(board.D4)
message = None
timediff = 0
plot = None
sgraph = None
timer_data = None

# Essentially the main function of the entire codebase
while True:
    default_view()