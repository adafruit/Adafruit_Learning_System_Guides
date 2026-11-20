# SPDX-FileCopyrightText: Copyright (c) 2026 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Tiles for the home dashboard: each tile is one rounded rectangle on a page
code.py decides where tiles go (from config.json) and feeds them data
"""

import binascii
import math
import time
import bitmaptools
import board
import displayio
import jpegio
import mipicsi
import vectorio
import videocore
import adafruit_ov5647
from adafruit_display_text import label
from adafruit_display_shapes.multisparkline import MultiSparkline
from adafruit_display_shapes.roundrect import RoundRect
from adafruit_displayio_layout.widgets.switch_round import SwitchRound
from font_league_gothic_regular_30_latin1 import FONT as SMALL
from font_league_gothic_regular_48_latin1 import FONT as MEDIUM
from font_league_gothic_regular_72_latin1 import FONT as LARGE

# The dashboard's own colors. Colors for data (gauge bands, graph lines) come
# from the palette in config.json
WHITE = 0xFFFFFF       # text
GREY = 0x8E8E93        # captions, and the dimmer when the light is off
TRACK = 0x3A3A3C       # empty part of gauge rings, graph grid lines
TILE_COLOR = 0x1C1C1E  # tile backgrounds
GREEN = 0x30D158       # light switch when on, connection dot when online
YELLOW = 0xFFD60A      # dimmer fill when the light is on
ORANGE = 0xFF9F0A      # forecast line, clock center
RED = 0xFF453A         # connection dot when offline
BLUE = 0x0A84FF        # gauges that have no bands
TEMP_SCALE = 3  # text scale for large temperatures

def text(string, font, color, anchor, pos, *, scale=1):
    """Make a label."""
    cap = font.get_glyph(ord("M")).height * scale
    return label.Label(font, text=string, color=color, scale=scale, base_alignment=True,
                       anchor_point=(anchor[0], 0),
                       anchored_position=(pos[0], pos[1] - round(anchor[1] * cap)))

def format_time(now):
    """A time as text, like "2:30 PM"."""
    ampm = "PM" if now.tm_hour >= 12 else "AM"
    return f"{now.tm_hour % 12 or 12}:{now.tm_min:02d} {ampm}"

def circle(radius, x, y, color):
    palette = displayio.Palette(1)
    palette[0] = color
    return vectorio.Circle(pixel_shader=palette, radius=radius, x=x, y=y)

def mix(color1, color2, t):
    """Blend two 0xRRGGBB colors; t=0 gives color1, t=1 gives color2."""
    return sum(round(((color1 >> s) & 0xFF) * (1 - t) + ((color2 >> s) & 0xFF) * t) << s
               for s in (16, 8, 0))

def gradient(width, height, start, end, steps=256):
    """Full-screen diagonal gradient from start (top left) to end (bottom right)."""
    palette = displayio.Palette(steps, dither=True)
    for i in range(steps):
        palette[i] = mix(start, end, i / (steps - 1))
    strip = displayio.Bitmap(width + height, 1, steps)
    for x in range(width + height):
        strip[x, 0] = x * (steps - 1) // (width + height - 1)
    bitmap = displayio.Bitmap(width, height, steps)
    for y in range(height):
        bitmaptools.blit(bitmap, strip, 0, y, x1=y, y1=0, x2=y + width, y2=1)
    return displayio.TileGrid(bitmap, pixel_shader=palette)

def band(value, bands):
    """(status, color) of the first band whose upper limit the value is under."""
    for limit, status, color in bands:
        if value <= limit:
            return status, color
    return bands[-1][1], bands[-1][2]

def make_ring(r, thickness, segments):
    """Bitmap of a 270° ring, open at the bottom."""
    ring = displayio.Bitmap(2 * r + 1, 2 * r + 1, segments + 1)
    for y in range(2 * r + 1):
        for x in range(2 * r + 1):
            if (r - thickness) ** 2 <= (x - r) ** 2 + (y - r) ** 2 <= r * r:
                angle = (math.degrees(math.atan2(y - r, x - r)) - 135) % 360
                if angle <= 270:
                    ring[x, y] = min(int(angle / 270 * segments), segments - 1) + 1
    return ring

class Tile(displayio.Group):
    """A rounded, tappable tile. GridLayout calls resize() to set its size."""

    SHOW_NAME = True  # draw the name in the top left corner

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.width = self.height = 0
        self.drag_area = (0, 0, 0, 0)

    def resize(self, width, height):
        self.width, self.height = width, height
        self.append(RoundRect(0, 0, width, height, 28, fill=TILE_COLOR))
        if self.SHOW_NAME:
            self.append(text(self.name, SMALL, WHITE, (0, 0), (24, 24)))

    def press(self, point):
        """Finger down. Returns True if it's in the drag area, which makes the touch
        a drag: drag() then follows the finger, and release() ends it."""
        left, top, width, height = self.drag_area
        return left <= point[0] < left + width and top <= point[1] < top + height

    def release(self, point):
        """Finger lifted after a tap (or a drag, if press returned True)."""
        print("Tapped", self.name, "at", point)

class BigTemp(displayio.Group):
    """A large temperature like "72°F", centered on (cx, cy) at the given text
    scale."""

    def __init__(self, cx, cy, scale):
        super().__init__()
        s = scale
        top = cy - LARGE.get_glyph(ord("M")).height * s // 2  # top of the digits
        self.number = text("--", LARGE, WHITE, (1.0, 0.5), (cx + 2 * s, cy), scale=s)
        self.append(self.number)
        self.append(circle(7 * s, cx + 13 * s, top + 7 * s, WHITE))
        self.append(circle(3 * s, cx + 13 * s, top + 7 * s, TILE_COLOR))
        self.append(text("F", LARGE, WHITE, (0, 0.5), (cx + 22 * s, cy), scale=s))

    @property
    def text(self):
        return self.number.text

    @text.setter
    def text(self, value):
        self.number.text = value

class TempTile(Tile):
    """A temperature as large text, with its status (from bands) underneath."""

    def __init__(self, name, bands):
        super().__init__(name)
        self.bands = bands
        self.temp = self.status = None  # made by resize()

    def resize(self, width, height):
        super().resize(width, height)
        self.temp = BigTemp(width // 2, height // 2 + 5, 2)
        self.status = text("", SMALL, GREY, (0.5, 0.5), (width // 2, height - 32))
        self.append(self.temp)
        self.append(self.status)

    def set(self, value):
        self.temp.text = f"{value:.0f}"
        self.status.text, self.status.color = band(value, self.bands)

    def receive(self, value):
        self.set(float(value))

class ConditionTile(Tile):
    """The weather condition in words"""

    def __init__(self, name):
        super().__init__(name)
        self.center, self.max_width = (0, 0), 0  # set by resize()
        self.top_line = self.bottom_line = None  # made by resize()

    def resize(self, width, height):
        super().resize(width, height)
        self.center = (width // 2, height // 2 + 10)
        self.max_width = width - 48
        self.top_line = text("--", MEDIUM, WHITE, (0.5, 0.5), self.center)
        self.bottom_line = text("", MEDIUM, WHITE, (0.5, 0.5), self.center)
        self.append(self.top_line)
        self.append(self.bottom_line)

    def set(self, condition):
        top, bottom = self.top_line, self.bottom_line
        top.text, bottom.text = condition, ""
        words = condition.split(" ")
        if top.bounding_box[2] > self.max_width and len(words) > 1:
            half = (len(words) + 1) // 2
            top.text, bottom.text = " ".join(words[:half]), " ".join(words[half:])
        cx, cy = self.center
        cap = MEDIUM.get_glyph(ord("M")).height
        spread = 28 if bottom.text else 0  # two lines sit above and below the center
        top.anchored_position = (cx, cy - spread - cap // 2)
        bottom.anchored_position = (cx, cy + spread - cap // 2)

    def show_weather(self, weather):
        self.set(weather["condition"])

class Reading:
    """One sensor reading on a WeatherTile as a value label that its feed updates."""

    def __init__(self, caption, feed, fmt):
        self.caption, self.feed, self.fmt = caption, feed, fmt
        self.label = None  # made by WeatherTile.resize()

    def receive(self, value):
        self.label.text = self.fmt.format(float(value))

class WeatherTile(Tile):
    """Big temperature and the condition from the weather, then up to three sensor
    readings, then sunrise and sunset."""

    def __init__(self, name, readings):
        super().__init__(name)
        self.readings = [Reading(reading["label"], reading["feed"],
                                 reading.get("format", "{:.0f}")) for reading in readings]
        self.temp = self.condition = None  # made by resize()
        self.sun = {}  # "sunrise" and "sunset" -> their value labels

    def resize(self, width, height):
        super().resize(width, height)
        self.temp = BigTemp(width // 2, int(height * 0.30), TEMP_SCALE)
        self.condition = text("--", SMALL, GREY, (1.0, 0), (width - 24, 24))
        self.append(self.temp)
        self.append(self.condition)
        count = len(self.readings)
        for i, reading in enumerate(self.readings):
            reading.label = self.add_value(reading.caption, width * (2 * i + 1) // (2 * count),
                                           int(height * 0.58))
        for i, (key, caption) in enumerate((("sunrise", "Sunrise"), ("sunset", "Sunset"))):
            self.sun[key] = self.add_value(caption, width * (2 * i + 1) // 4, int(height * 0.80))

    def add_value(self, caption, x, y):
        """A value label with its caption underneath, centered on x. Returns the
        value label."""
        value = text("--", MEDIUM, WHITE, (0.5, 0.5), (x, y))
        self.append(value)
        self.append(text(caption, SMALL, GREY, (0.5, 0.5), (x, y + 45)))
        return value

    def show_weather(self, weather):
        self.temp.text = f"{weather['temp']:.0f}"
        self.condition.text = weather["condition"]
        for key, value_label in self.sun.items():
            if weather.get(key):
                value_label.text = weather[key]

class Gauge(Tile):
    """Tile with a 270° ring gauge"""

    SEGMENTS = 54  # how finely the ring fills
    rings = {}     # ring bitmaps by radius, shared between gauges

    def __init__(self, name, lo, hi, fmt, bands):
        super().__init__(name)
        self.lo, self.hi, self.fmt, self.bands = lo, hi, fmt, bands
        self.palette = self.value_label = self.status_label = None  # made by resize()

    def resize(self, width, height):
        super().resize(width, height)
        r = min(width, height) // 3
        if r not in Gauge.rings:
            Gauge.rings[r] = make_ring(r, r // 5, self.SEGMENTS)
        self.palette = displayio.Palette(self.SEGMENTS + 1)
        self.palette.make_transparent(0)
        for i in range(self.SEGMENTS):  # an empty ring until the first reading
            self.palette[i + 1] = TRACK
        cx, cy = width // 2, 60 + r
        self.append(displayio.TileGrid(Gauge.rings[r], pixel_shader=self.palette,
                                       x=cx - r, y=cy - r))
        self.value_label = text("--", MEDIUM, WHITE, (0.5, 0.5), (cx, cy))
        self.status_label = text("", SMALL, GREY, (0.5, 0.5), (cx, height - 32))
        self.append(self.value_label)
        self.append(self.status_label)

    def set(self, value):
        status, color = band(value, self.bands)
        fraction = max(0, min(1, (value - self.lo) / (self.hi - self.lo)))
        filled = round(fraction * self.SEGMENTS)
        for i in range(self.SEGMENTS):
            self.palette[i + 1] = color if i < filled else TRACK
        self.value_label.text = self.fmt.format(value)
        self.status_label.text = status
        self.status_label.color = color

    def receive(self, value):
        self.set(float(value))


class GraphTile(Tile):
    """Line graph of one or two series of evenly spaced values, drawn by the
    display_shapes MultiSparkline"""

    INSET = 40

    def __init__(self, name, legend, x_labels, series):
        super().__init__(name)
        self.legend, self.x_labels, self.series = legend, x_labels, series
        self.values = [[] for _ in series]
        self.plot = (0, 0, 0, 0)  # x, y, width, height of the graph area, set by resize()
        self.spark = None
        self.y_labels = []  # [series][top, middle, bottom]

    def resize(self, width, height):
        super().resize(width, height)
        right = 70 if len(self.series) > 1 else 30  # room for a right-hand axis
        self.plot = (70, 72, width - 70 - right, height - 136)
        self.add_legend(width)
        self.add_grid()
        plot_x, plot_y, plot_w, plot_h = self.plot
        self.spark = MultiSparkline(plot_w - 2 * self.INSET, plot_h, 100,
                                    [color for color, _ in self.series],
                                    x=plot_x + self.INSET, y=plot_y)
        self.append(self.spark)
        self.add_axis_labels()
        self.redraw()

    def add_legend(self, width):
        x = width - 24
        for caption, color in reversed(self.legend):  # right to left
            item = text(caption, SMALL, color, (1.0, 0), (x, 24))
            self.append(item)
            x -= item.bounding_box[2] + 20

    def add_grid(self):
        plot_x, plot_y, plot_w, plot_h = self.plot
        palette = displayio.Palette(1)
        palette[0] = TRACK
        for j in range(3):  # top, middle and bottom grid lines
            self.append(vectorio.Rectangle(pixel_shader=palette, width=plot_w, height=1,
                                           x=plot_x, y=plot_y + j * (plot_h - 1) // 2))

    def add_axis_labels(self):
        """Value labels for each series (first on the left, second on the right),
        and the x labels along the bottom."""
        plot_x, plot_y, plot_w, plot_h = self.plot
        for i, (color, _) in enumerate(self.series):
            side = (1.0, plot_x - 14) if i == 0 else (0.0, plot_x + plot_w + 14)
            labels = [text("--", SMALL, color, (side[0], 0.5),
                           (side[1], plot_y + j * (plot_h - 1) // 2)) for j in range(3)]
            for item in labels:
                self.append(item)
            self.y_labels.append(labels)
        line_w = plot_w - 2 * self.INSET
        for x, caption in self.x_labels:
            self.append(text(caption, SMALL, GREY, (0.5, 0),
                             (plot_x + self.INSET + round(x * (line_w - 1)),
                              plot_y + plot_h + 16)))

    def set_series(self, index, values):
        """values: the series' numbers, oldest first, spread evenly across the graph."""
        self.values[index] = values[-100:]  # the sparkline holds up to 100 values
        self.redraw()

    def redraw(self):
        spark = self.spark
        spark.clear_values()
        for s, values in enumerate(self.values):
            if not values:
                continue
            pad = max((max(values) - min(values)) * 0.1, abs(max(values)) * 0.05, 0.1)
            lo, hi = min(values) - pad, max(values) + pad  # keep the line off the edges
            if min(values) >= 0:
                lo = max(lo, 0)  # no negative axis labels for things that can't go below 0
            # A fixed range per line, so the axis labels match the line
            spark.y_mins[s] = spark.y_bottoms[s] = lo
            spark.y_maxs[s] = spark.y_tops[s] = hi
            for i, item in enumerate(self.y_labels[s]):
                item.text = self.series[s][1].format(hi - i * (hi - lo) / 2)
        # One value per line per step; None leaves that line out
        for step in range(max([len(values) for values in self.values] + [0])):
            spark.add_values([values[step] if step < len(values) else None
                              for values in self.values], update=False)
        spark.update_line()

class ForecastTile(GraphTile):
    """Temperature now and over the next few hours, from the weather"""

    def __init__(self, name, hours):
        half = hours // 2
        super().__init__(name, legend=((f"Next {hours} hours", GREY),),
                         x_labels=((0, "Now"), (0.5, f"In {half} hours"),
                                   (1, f"In {hours} hours")),
                         series=((ORANGE, "{:.0f}"),))

    def show_weather(self, weather):
        forecast = [temp for _, temp in sorted(weather["forecast"].items())]
        self.set_series(0, [weather["temp"]] + forecast)

class HistoryTile(GraphTile):
    """The last 24 hours of one or two feeds"""

    def __init__(self, name, lines):
        self.feeds = [feed for _, feed, _, _ in lines]
        super().__init__(name, legend=[(label, color) for label, _, color, _ in lines],
                         x_labels=((0, "24h ago"), (0.5, "12h ago"), (1, "Now")),
                         series=[(color, fmt) for _, _, color, fmt in lines])

class LightTile(Tile):
    """On/off switch and dimmer for a light whose feed takes "#RRGGBB" values."""

    SLIDER_Y = 180  # vertical center of the dimmer

    def __init__(self, name, feed, on_change):
        """on_change(feed, "#RRGGBB") is called when the user changes the light."""
        super().__init__(name)
        self.feed = feed
        self.on_change = on_change
        self.on = False
        self.level = None  # 0-255 once known; remembered while the light is off
        self.dragging = False
        # Made by resize():
        self.switch = self.fill_color = self.fill = self.knob = None
        self.percent = self.hex = None
        self.left = self.right = 0  # travel of the dimmer knob's center

    def resize(self, width, height):
        super().resize(width, height)
        y = self.SLIDER_Y
        self.switch = SwitchRound(width - 112, 14, height=44, display_button_text=False,
                                  animation_time=0.15, fill_color_off=WHITE,
                                  fill_color_on=WHITE, outline_color_off=WHITE,
                                  outline_color_on=WHITE, background_color_off=TRACK,
                                  background_color_on=GREEN,
                                  background_outline_color_off=TRACK,
                                  background_outline_color_on=GREEN)
        self.append(self.switch)
        self.drag_area = (0, y - 40, width, 80)
        # Dimmer: grey track, colored fill up to the knob, white knob
        self.append(RoundRect(24, y - 8, width - 48, 16, 8, fill=TRACK))
        self.fill_color = displayio.Palette(1)
        self.append(vectorio.Circle(pixel_shader=self.fill_color, radius=8, x=32, y=y))
        self.fill = vectorio.Rectangle(pixel_shader=self.fill_color, width=1, height=16,
                                       x=32, y=y - 8)
        self.append(self.fill)
        self.left, self.right = 42, width - 42
        self.knob = circle(18, self.left, y, WHITE)
        self.append(self.knob)
        self.percent = text("--", MEDIUM, WHITE, (0.5, 0.5), (width // 2, 110))
        self.hex = text("--", SMALL, GREY, (0.5, 0.5), (width // 2, height - 32))
        self.append(self.percent)
        self.append(self.hex)
        self.show()

    def color(self):
        level = self.level if self.on else 0
        return f"#{level:02X}{level:02X}{level:02X}"

    def show(self):
        """Redraw everything from self.on and self.level."""
        if self.switch.value != self.on:
            self.switch.value = self.on  # animates the switch
        level = self.level or 0
        self.knob.x = self.left + (self.right - self.left) * level // 255
        self.fill.width = max(1, self.knob.x - 32)
        self.fill_color[0] = YELLOW if self.on else GREY
        if self.level is None:  # haven't heard from the feed yet
            self.percent.text = self.hex.text = "--"
        else:
            self.percent.text = f"{round(level * 100 / 255)}%" if self.on else "Off"
            self.hex.text = self.color()

    def set_color(self, payload):
        """Show a value that came from the feed, e.g. "#BFBFBF"."""
        rgb = int(str(payload).lstrip("#"), 16)
        level = max(rgb >> 16, (rgb >> 8) & 0xFF, rgb & 0xFF)
        self.on = level > 0
        if self.on or self.level is None:  # while off, keep the remembered level
            self.level = level
        self.show()

    def receive(self, value):
        self.set_color(value)

    def press(self, point):
        self.dragging = super().press(point)
        return self.dragging

    def drag(self, point):
        """The dimmer follows the finger."""
        position = point[0] - self.left
        self.level = max(0, min(255, position * 255 // (self.right - self.left)))
        self.on = self.level > 0
        self.show()

    def release(self, point):
        x, y = point
        if self.dragging:
            self.dragging = False
        elif x >= self.switch.x - 20 and y < self.switch.y + self.switch.height + 20:
            self.on = not self.on  # tapped the switch
            if self.on and not self.level:
                self.level = 255
        else:
            super().release(point)
            return
        self.show()
        self.on_change(self.feed, self.color())

class PhotoTile(Tile):
    """The latest JPEG photo from a feed (sent as base64 text)"""

    def __init__(self, name):
        super().__init__(name)
        self.decoder = jpegio.JpegDecoder()
        self.status = self.photo = None  # made by resize()
        self.area = (0, 0, 0, 0)  # x, y, width, height for the photo, set by resize()

    def resize(self, width, height):
        super().resize(width, height)
        self.status = text("Waiting for a photo...", SMALL, GREY, (1.0, 0), (width - 24, 24))
        self.append(self.status)
        self.photo = displayio.Group()  # holds the current photo
        self.append(self.photo)
        self.area = (16, 60, width - 32, height - 76)

    def show_photo(self, base64_text):
        jpeg = binascii.a2b_base64(base64_text)
        width, height = self.decoder.open(jpeg)
        area_x, area_y, area_w, area_h = self.area
        # jpegio can shrink by 2, 4 or 8 while decoding; shrink until the photo fits
        shrink = 0
        while shrink < 3 and (width >> shrink > area_w or height >> shrink > area_h):
            shrink += 1
        width = (width + (1 << shrink) - 1) >> shrink  # round up so the bitmap is big enough
        height = (height + (1 << shrink) - 1) >> shrink
        if self.photo:
            self.photo.pop()  # free the old photo first
        bitmap = displayio.Bitmap(width, height, 65535)
        self.decoder.decode(bitmap, scale=shrink)
        zoom = max(1, min(area_w // width, area_h // height))  # enlarge small photos
        self.photo.scale = zoom
        self.photo.x = area_x + (area_w - width * zoom) // 2
        self.photo.y = area_y + (area_h - height * zoom) // 2
        self.photo.append(displayio.TileGrid(bitmap, pixel_shader=displayio.ColorConverter(
            input_colorspace=displayio.Colorspace.RGB565_SWAPPED)))
        self.status.text = "Updated " + format_time(time.localtime())

    def receive(self, value):
        self.show_photo(value)

def spoke(angle, start, end, width):
    """Polygon points for a straight spoke pointing at angle"""
    a = math.radians(angle)
    dx, dy = math.sin(a), -math.cos(a)        # along the spoke
    px, py = -dy * width / 2, dx * width / 2  # across the spoke
    return [(round(dx * start + px), round(dy * start + py)),
            (round(dx * end + px), round(dy * end + py)),
            (round(dx * end - px), round(dy * end - py)),
            (round(dx * start - px), round(dy * start - py))]

class ClockTile(Tile):
    """Analog clock face with hour marks and hour and minute hands."""

    SHOW_NAME = False

    def __init__(self, name):
        super().__init__(name)
        self.r = 0  # face radius, set by resize()
        self.hands = self.hour_hand = self.minute_hand = None  # made by resize()

    def resize(self, width, height):
        super().resize(width, height)
        cx, cy = width // 2, height // 2
        r = min(width, height) // 2 - 20
        self.r = r
        self.append(circle(r, cx, cy, 0x2C2C2E))  # face
        white = displayio.Palette(1)
        white[0] = WHITE
        for hour in range(12):  # hour marks, longer at 12, 3, 6 and 9
            quarter = hour % 3 == 0
            self.append(vectorio.Polygon(pixel_shader=white, x=cx, y=cy, points=spoke(
                hour * 30, r - (24 if quarter else 16), r - 8, 6 if quarter else 3)))
        self.hands = displayio.Group()  # hidden until the clock has been synced
        self.hands.hidden = True
        self.hour_hand = vectorio.Polygon(pixel_shader=white, x=cx, y=cy,
                                          points=spoke(0, -12, r * 0.5, 9))
        self.minute_hand = vectorio.Polygon(pixel_shader=white, x=cx, y=cy,
                                            points=spoke(0, -12, r * 0.8, 5))
        self.hands.append(self.hour_hand)
        self.hands.append(self.minute_hand)
        self.hands.append(circle(7, cx, cy, ORANGE))  # center cap
        self.append(self.hands)

    def set_time(self, now):
        minutes = now.tm_hour % 12 * 60 + now.tm_min  # minutes since 12 o'clock
        self.hour_hand.points = spoke(minutes / 2, -12, self.r * 0.5, 9)  # 360° per 720 min
        self.minute_hand.points = spoke(now.tm_min * 6, -12, self.r * 0.8, 5)
        self.hands.hidden = False

class LiveTile(Tile):
    """Live video from the camera."""

    def __init__(self, name, i2c):
        super().__init__(name)
        self.sensor = adafruit_ov5647.OV5647(i2c, reset_pin=board.CAMERA_RESET)
        self.sensor.mode = adafruit_ov5647.Mode.R640X480
        self.camera = mipicsi.Camera(self.sensor, output_format=mipicsi.PixelFormat.RGB565)
        self.frame = bytearray(self.sensor.width * self.sensor.height * 2)  # 2 bytes a pixel
        self.video = videocore.VideoBuffer(self.frame)
        self.video_offset = (0, 0)  # set by resize()

    def resize(self, width, height):
        super().resize(width, height)
        video_w, video_h = self.sensor.width, self.sensor.height
        # Where the video goes, relative to this tile's top left corner
        self.video_offset = ((width - video_w) // 2, 60 + (height - 76 - video_h) // 2)

    def start(self, layer, tile_x, tile_y):
        """Show the video on layer (the top-level Group). tile_x and tile_y are
        this tile's position on the screen."""
        if not self.video.playing:
            self.video.play(self.camera)
            self.video.x = tile_x + self.video_offset[0]
            self.video.y = tile_y + self.video_offset[1]
            layer.append(self.video)

    def stop(self, layer):
        if self.video.playing:
            self.video.stop()
            layer.remove(self.video)
