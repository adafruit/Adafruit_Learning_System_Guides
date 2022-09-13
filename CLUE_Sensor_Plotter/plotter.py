# SPDX-FileCopyrightText: 2020 Kevin J Walters for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# MIT License

# Copyright (c) 2020 Kevin J. Walters

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
`plotter`
================================================================================
CircuitPython library for the clue-plotter application's plotting facilties.
Internally this holds some values in a circular buffer to enable redrawing
and has some basic statistics on data.
Not intended to be a truly general purpose plotter but perhaps could be
developed into one.

* Author(s): Kevin J. Walters

Implementation Notes
--------------------
**Hardware:**
* Adafruit CLUE <https://www.adafruit.com/product/4500>
**Software and Dependencies:**
* Adafruit's CLUE library: https://github.com/adafruit/Adafruit_CircuitPython_CLUE
"""

import time
import array

import displayio
import terminalio

from adafruit_display_text.bitmap_label import Label


def mapf(value, in_min, in_max, out_min, out_max):
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


# This creates ('{:.0f}', '{:.1f}', '{:.2f}', etc
_FMT_DEC_PLACES = tuple("{:." + str(x) + "f}" for x in range(10))


def format_width(nchars, value):
    """Simple attempt to generate a value within nchars characters.
    Return value can be too long, e.g. for nchars=5, bad things happen
    with values > 99999 or < -9999 or < -99.9."""
    neg_format = _FMT_DEC_PLACES[nchars - 3]
    pos_format = _FMT_DEC_PLACES[nchars - 2]
    if value <= -10.0:
        text_value = neg_format.format(value)  # may overflow width
    elif value < 0.0:
        text_value = neg_format.format(value)
    elif value >= 10.0:
        text_value = pos_format.format(value)  # may overflow width
    else:
        text_value = pos_format.format(value)  # 0.0 to 9.99999
    return text_value


class Plotter:
    _DEFAULT_SCALE_MODE = {"lines": "onscroll", "dots": "screen"}

    # Palette for plotting, first one is set transparent
    TRANSPARENT_IDX = 0
    # Removed one colour to get number down to 8 for more efficient
    # bit-packing in displayio's Bitmap
    _PLOT_COLORS = (
        0x000000,
        0x0000FF,
        0x00FF00,
        0x00FFFF,
        0xFF0000,
        # 0xff00ff,
        0xFFFF00,
        0xFFFFFF,
        0xFF0080,
    )

    POS_INF = float("inf")
    NEG_INF = float("-inf")

    # Approximate number of seconds to review data for zooming in
    # and how often to do that check
    ZOOM_IN_TIME = 8
    ZOOM_IN_CHECK_TIME_NS = 5 * 1e9
    # 20% headroom either side on zoom in/out
    ZOOM_HEADROOM = 20 / 100

    GRID_COLOR = 0x308030
    GRID_DOT_SPACING = 8

    _GRAPH_TOP = 30  # y position for the graph placement

    INFO_FG_COLOR = 0x000080
    INFO_BG_COLOR = 0xC0C000
    LABEL_COLOR = 0xC0C0C0

    def _display_manual(self):
        """Intention was to disable auto_refresh here but this needs a
        simple displayio refresh to work well."""
        self._output.auto_refresh = True

    def _display_auto(self):
        self._output.auto_refresh = True

    def _display_refresh(self):
        """Intention was to call self._output.refresh() but this does not work well
        as current implementation is designed with a fixed frame rate in mind."""
        if self._output.auto_refresh:
            return True
        else:
            return True

    def __init__(
        self,
        output,
        style="lines",
        mode="scroll",
        scale_mode=None,
        screen_width=240,
        screen_height=240,
        plot_width=192,
        plot_height=201,
        x_divs=4,
        y_divs=4,
        scroll_px=50,
        max_channels=3,
        est_rate=50,
        title="",
        max_title_len=20,
        mu_output=False,
        debug=0,
    ):
        """scroll_px of greater than 1 gives a jump scroll."""
        # pylint: disable=too-many-locals,too-many-statements
        self._output = output
        self.change_stylemode(style, mode, scale_mode=scale_mode, clear=False)
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._plot_width = plot_width
        self._plot_height = plot_height
        self._plot_height_m1 = plot_height - 1
        self._x_divs = x_divs
        self._y_divs = y_divs
        self._scroll_px = scroll_px
        self._max_channels = max_channels
        self._est_rate = est_rate
        self._title = title
        self._max_title_len = max_title_len

        # These arrays are used to provide a circular buffer
        # with _data_values valid values - this needs to be sized
        # one larger than screen width to retrieve prior y position
        # for line undrawing in wrap mode
        self._data_size = self._plot_width + 1
        self._data_y_pos = []
        self._data_value = []
        for _ in range(self._max_channels):
            # 'i' is 32 bit signed integer
            self._data_y_pos.append(array.array("i", [0] * self._data_size))
            self._data_value.append(array.array("f", [0.0] * self._data_size))

        # begin-keep-pylint-happy
        self._data_mins = None
        self._data_maxs = None
        self._data_stats_maxlen = None
        self._data_stats = None
        self._values = None
        self._data_values = None
        self._x_pos = None
        self._data_idx = None
        self._plot_lastzoom_ns = None
        # end-keep-pylint-happy
        self._init_data()

        self._mu_output = mu_output
        self._debug = debug

        self._channels = None
        self._channel_colidx = []

        # The range the data source generates within
        self._abs_min = None
        self._abs_max = None

        # The current plot min/max
        self._plot_min = None
        self._plot_max = None
        self._plot_min_range = None  # Used partly to prevent div by zero
        self._plot_range_lock = False
        self._plot_dirty = False  # flag indicate some data has been plotted

        self._font = terminalio.FONT
        self._y_axis_lab = ""
        self._y_lab_width = 6  # maximum characters for y axis label
        self._y_lab_color = self.LABEL_COLOR

        self._displayio_graph = None
        self._displayio_plot = None
        self._displayio_title = None
        self._displayio_info = None
        self._displayio_y_labs = None
        self._displayio_y_axis_lab = None
        self._last_manual_refresh = None

    def _init_data(self, ranges=True):
        # Allocate arrays for each possible channel with plot_width elements
        self._data_mins = [self.POS_INF]
        self._data_maxs = [self.NEG_INF]
        self._data_start_ns = [time.monotonic_ns()]
        self._data_stats_maxlen = 10

        # When in use the arrays in here are variable length
        self._data_stats = [[] * self._max_channels]

        self._values = 0  # total data processed
        self._data_values = 0  # valid elements in data_y_pos and data_value
        self._x_pos = 0
        self._data_idx = 0

        self._plot_lastzoom_ns = 0  # monotonic_ns() for last zoom in
        if ranges:
            self._plot_min = None
            self._plot_max = None
            self._plot_min_range = None  # Used partly to prevent div by zero
        self._plot_dirty = False  # flag indicate some data has been plotted

    def _recalc_y_pos(self):
        """Recalculates _data_y_pos based on _data_value for changes in y scale."""
        # Check if nothing to do - important since _plot_min _plot_max not yet set
        if self._data_values == 0:
            return

        for ch_idx in range(self._channels):
            # intentional use of negative array indexing
            for data_idx in range(
                self._data_idx - 1, self._data_idx - 1 - self._data_values, -1
            ):
                self._data_y_pos[ch_idx][data_idx] = round(
                    mapf(
                        self._data_value[ch_idx][data_idx],
                        self._plot_min,
                        self._plot_max,
                        self._plot_height_m1,
                        0,
                    )
                )

    def get_colors(self):
        return self._PLOT_COLORS

    def clear_all(self, ranges=True):
        if self._values != 0:
            self._undraw_bitmap()
        self._init_data(ranges=ranges)

    # Simple implementation here is to clear the screen on change...
    def change_stylemode(self, style, mode, scale_mode=None, clear=True):
        if style not in ("lines", "dots"):
            raise ValueError("style not lines or dots")
        if mode not in ("scroll", "wrap"):
            raise ValueError("mode not scroll or wrap")
        if scale_mode is None:
            scale_mode = self._DEFAULT_SCALE_MODE[style]
        elif scale_mode not in ("pixel", "onscroll", "screen", "time"):
            raise ValueError("scale_mode not pixel, onscroll, screen or time")

        # Clearing everything on screen and everything stored in variables
        # apart from plot ranges is simplest approach here - clearing
        # involves undrawing which uses the self._style so must not change
        # that beforehand
        if clear:
            self.clear_all(ranges=False)

        self._style = style
        self._mode = mode
        self._scale_mode = scale_mode

        if self._mode == "wrap":
            self._display_auto()
        elif self._mode == "scroll":
            self._display_manual()

    def _make_empty_tg_plot_bitmap(self):
        plot_bitmap = displayio.Bitmap(
            self._plot_width, self._plot_height, len(self._PLOT_COLORS)
        )
        # Create a colour palette for plot dots/lines
        plot_palette = displayio.Palette(len(self._PLOT_COLORS))

        for idx in range(len(self._PLOT_COLORS)):
            plot_palette[idx] = self._PLOT_COLORS[idx]
        plot_palette.make_transparent(0)
        tg_plot_data = displayio.TileGrid(plot_bitmap, pixel_shader=plot_palette)
        tg_plot_data.x = self._screen_width - self._plot_width - 1
        tg_plot_data.y = self._GRAPH_TOP
        return (tg_plot_data, plot_bitmap)

    def _make_tg_grid(self):
        # pylint: disable=too-many-locals
        grid_width = self._plot_width
        grid_height = self._plot_height_m1
        div_width = self._plot_width // self._x_divs
        div_height = self._plot_height // self._y_divs
        a_plot_grid = displayio.Bitmap(div_width, div_height, 2)

        # Grid colours
        grid_palette = displayio.Palette(2)
        grid_palette.make_transparent(0)
        grid_palette[0] = 0x000000
        grid_palette[1] = self.GRID_COLOR

        # Horizontal line on grid rectangle
        for x in range(0, div_width, self.GRID_DOT_SPACING):
            a_plot_grid[x, 0] = 1

        # Vertical line on grid rectangle
        for y in range(0, div_height, self.GRID_DOT_SPACING):
            a_plot_grid[0, y] = 1

        right_line = displayio.Bitmap(1, grid_height, 2)
        tg_right_line = displayio.TileGrid(right_line, pixel_shader=grid_palette)
        for y in range(0, grid_height, self.GRID_DOT_SPACING):
            right_line[0, y] = 1

        bottom_line = displayio.Bitmap(grid_width + 1, 1, 2)
        tg_bottom_line = displayio.TileGrid(bottom_line, pixel_shader=grid_palette)
        for x in range(0, grid_width + 1, self.GRID_DOT_SPACING):
            bottom_line[x, 0] = 1

        # Create a TileGrid using the Bitmap and Palette
        # and tiling it based on number of divisions required
        tg_plot_grid = displayio.TileGrid(
            a_plot_grid,
            pixel_shader=grid_palette,
            width=self._x_divs,
            height=self._y_divs,
            default_tile=0,
        )
        tg_plot_grid.x = self._screen_width - self._plot_width - 1
        tg_plot_grid.y = self._GRAPH_TOP
        tg_right_line.x = tg_plot_grid.x + grid_width
        tg_right_line.y = tg_plot_grid.y
        tg_bottom_line.x = tg_plot_grid.x
        tg_bottom_line.y = tg_plot_grid.y + grid_height

        g_plot_grid = displayio.Group()
        g_plot_grid.append(tg_plot_grid)
        g_plot_grid.append(tg_right_line)
        g_plot_grid.append(tg_bottom_line)

        return g_plot_grid

    def _make_empty_graph(self, tg_and_plot=None):
        font_w, font_h = self._font.get_bounding_box()

        self._displayio_title = Label(
            self._font,
            text=self._title,
            scale=2,
            line_spacing=1,
            color=self._y_lab_color,
        )
        self._displayio_title.x = self._screen_width - self._plot_width
        self._displayio_title.y = font_h // 1

        self._displayio_y_axis_lab = Label(
            self._font, text=self._y_axis_lab, line_spacing=1, color=self._y_lab_color
        )
        self._displayio_y_axis_lab.x = 0  # 0 works here because text is ""
        self._displayio_y_axis_lab.y = font_h // 1

        plot_y_labels = []
        # y increases top to bottom of screen
        for y_div in range(self._y_divs + 1):
            plot_y_labels.append(
                Label(
                    self._font,
                    text=" " * self._y_lab_width,
                    line_spacing=1,
                    color=self._y_lab_color,
                )
            )
            plot_y_labels[-1].x = (
                self._screen_width - self._plot_width - self._y_lab_width * font_w - 5
            )
            plot_y_labels[-1].y = (
                round(y_div * self._plot_height / self._y_divs) + self._GRAPH_TOP - 1
            )
        self._displayio_y_labs = plot_y_labels

        # Three items (grid, axis label, title) plus the y tick labels
        g_background = displayio.Group()
        g_background.append(self._make_tg_grid())
        for label in self._displayio_y_labs:
            g_background.append(label)
        g_background.append(self._displayio_y_axis_lab)
        g_background.append(self._displayio_title)

        if tg_and_plot is not None:
            (tg_plot, plot) = tg_and_plot
        else:
            (tg_plot, plot) = self._make_empty_tg_plot_bitmap()

        self._displayio_plot = plot

        # Create the main Group for display with one spare slot for
        # popup informational text
        main_group = displayio.Group()
        main_group.append(g_background)
        main_group.append(tg_plot)
        self._displayio_info = None

        return main_group

    def set_y_axis_tick_labels(self, y_min, y_max):
        px_per_div = (y_max - y_min) / self._y_divs
        for idx, tick_label in enumerate(self._displayio_y_labs):
            value = y_max - idx * px_per_div
            text_value = format_width(self._y_lab_width, value)
            tick_label.text = text_value[: self._y_lab_width]

    def display_on(self, tg_and_plot=None):
        if self._displayio_graph is None:
            self._displayio_graph = self._make_empty_graph(tg_and_plot=tg_and_plot)

        self._output.show(self._displayio_graph)

    def display_off(self):
        pass

    def _draw_vline(self, x1, y1, y2, colidx):
        """Draw a clipped vertical line at x1 from pixel one along from y1 to y2."""
        if y2 == y1:
            if 0 <= y2 <= self._plot_height_m1:
                self._displayio_plot[x1, y2] = colidx
            return

        # For y2 above y1, on screen this translates to being below
        step = 1 if y2 > y1 else -1

        for line_y_pos in range(
            max(0, min(y1 + step, self._plot_height_m1)),
            max(0, min(y2, self._plot_height_m1)) + step,
            step,
        ):
            self._displayio_plot[x1, line_y_pos] = colidx

    # def _clear_plot_bitmap(self):  ### woz here

    def _redraw_all_col_idx(self, col_idx_list):
        x_cols = min(self._data_values, self._plot_width)
        wrapMode = self._mode == "wrap"
        if wrapMode:
            x_data_idx = (self._data_idx - self._x_pos) % self._data_size
        else:
            x_data_idx = (self._data_idx - x_cols) % self._data_size

        for ch_idx in range(self._channels):
            col_idx = col_idx_list[ch_idx]
            data_idx = x_data_idx
            for x_pos in range(x_cols):
                # "jump" the gap in the circular buffer for wrap mode
                if wrapMode and x_pos == self._x_pos:
                    data_idx = (
                        data_idx + self._data_size - self._plot_width
                    ) % self._data_size
                    # ideally this should inhibit lines between wrapped data

                y_pos = self._data_y_pos[ch_idx][data_idx]
                if self._style == "lines" and x_pos != 0:
                    # Python supports negative array index
                    prev_y_pos = self._data_y_pos[ch_idx][data_idx - 1]
                    self._draw_vline(x_pos, prev_y_pos, y_pos, col_idx)
                else:
                    if 0 <= y_pos <= self._plot_height_m1:
                        self._displayio_plot[x_pos, y_pos] = col_idx
                data_idx += 1
                if data_idx >= self._data_size:
                    data_idx = 0

    # This is almost always going to be quicker
    # than the slow _clear_plot_bitmap implemented on 5.0.0 displayio
    def _undraw_bitmap(self):
        if not self._plot_dirty:
            return

        self._redraw_all_col_idx([self.TRANSPARENT_IDX] * self._channels)
        self._plot_dirty = False

    def _redraw_all(self):
        self._redraw_all_col_idx(self._channel_colidx)
        self._plot_dirty = True

    def _undraw_column(self, x_pos, data_idx):
        """Undraw a single column at x_pos based on data from data_idx."""
        colidx = self.TRANSPARENT_IDX
        for ch_idx in range(self._channels):
            y_pos = self._data_y_pos[ch_idx][data_idx]
            if self._style == "lines" and x_pos != 0:
                # Python supports negative array index
                prev_y_pos = self._data_y_pos[ch_idx][data_idx - 1]
                self._draw_vline(x_pos, prev_y_pos, y_pos, colidx)
            else:
                if 0 <= y_pos <= self._plot_height_m1:
                    self._displayio_plot[x_pos, y_pos] = colidx

    # very similar code to _undraw_bitmap although that is now
    # more sophisticated as it supports wrap mode
    def _redraw_for_scroll(self, x1, x2, x1_data_idx):
        """Redraw data from x1 to x2 inclusive for scroll mode only."""
        for ch_idx in range(self._channels):
            colidx = self._channel_colidx[ch_idx]
            data_idx = x1_data_idx
            for x_pos in range(x1, x2 + 1):
                y_pos = self._data_y_pos[ch_idx][data_idx]
                if self._style == "lines" and x_pos != 0:
                    # Python supports negative array index
                    prev_y_pos = self._data_y_pos[ch_idx][data_idx - 1]
                    self._draw_vline(x_pos, prev_y_pos, y_pos, colidx)
                else:
                    if 0 <= y_pos <= self._plot_height_m1:
                        self._displayio_plot[x_pos, y_pos] = colidx
                data_idx += 1
                if data_idx >= self._data_size:
                    data_idx = 0

        self._plot_dirty = True

    def _update_stats(self, values):
        """Update the statistics for minimum and maximum."""
        for idx, value in enumerate(values):
            # Occasionally check if we need to add a new bucket to stats
            if idx == 0 and self._values & 0xF == 0:
                now_ns = time.monotonic_ns()
                if now_ns - self._data_start_ns[-1] > 1e9:
                    self._data_start_ns.append(now_ns)
                    self._data_mins.append(value)
                    self._data_maxs.append(value)
                    # Remove the first elements if too long
                    if len(self._data_start_ns) > self._data_stats_maxlen:
                        self._data_start_ns.pop(0)
                        self._data_mins.pop(0)
                        self._data_maxs.pop(0)
                    continue

            if value < self._data_mins[-1]:
                self._data_mins[-1] = value
            if value > self._data_maxs[-1]:
                self._data_maxs[-1] = value

    def _data_store(self, values):
        """Store the data values in the circular buffer."""
        for ch_idx, value in enumerate(values):
            self._data_value[ch_idx][self._data_idx] = value

        # Increment the data index for circular buffer
        self._data_idx += 1
        if self._data_idx >= self._data_size:
            self._data_idx = 0

    def _data_draw(self, values, x_pos, data_idx):
        offscale = False

        for ch_idx, value in enumerate(values):
            # Last two parameters appear "swapped" - this deals with the
            # displayio screen y coordinate increasing downwards
            y_pos = round(
                mapf(value, self._plot_min, self._plot_max, self._plot_height_m1, 0)
            )

            if y_pos < 0 or y_pos >= self._plot_height:
                offscale = True

            self._data_y_pos[ch_idx][data_idx] = y_pos

            if self._style == "lines" and self._x_pos != 0:
                # Python supports negative array index
                prev_y_pos = self._data_y_pos[ch_idx][data_idx - 1]
                self._draw_vline(x_pos, prev_y_pos, y_pos, self._channel_colidx[ch_idx])
                self._plot_dirty = True  # bit wrong if whole line is off screen
            else:
                if not offscale:
                    self._displayio_plot[x_pos, y_pos] = self._channel_colidx[ch_idx]
                    self._plot_dirty = True

    def _check_zoom_in(self):
        """Check if recent data warrants zooming in on y axis scale based on checking
        minimum and maximum times which are recorded in approximate 1 second buckets.
        Returns two element tuple with (min, max) or empty tuple for no zoom required.
        Caution is required with min == max."""
        start_idx = len(self._data_start_ns) - self.ZOOM_IN_TIME
        if start_idx < 0:
            return ()

        now_ns = time.monotonic_ns()
        if now_ns < self._plot_lastzoom_ns + self.ZOOM_IN_CHECK_TIME_NS:
            return ()

        recent_min = min(self._data_mins[start_idx:])
        recent_max = max(self._data_maxs[start_idx:])
        recent_range = recent_max - recent_min
        headroom = recent_range * self.ZOOM_HEADROOM

        # No zoom if the range of data is near the plot range
        if (
            self._plot_min > recent_min - headroom
            and self._plot_max < recent_max + headroom
        ):
            return ()

        new_plot_min = max(recent_min - headroom, self._abs_min)
        new_plot_max = min(recent_max + headroom, self._abs_max)
        return (new_plot_min, new_plot_max)

    def _auto_plot_range(self, redraw_plot=True):
        """Check if we need to zoom out or in based on checking historical
        data values unless y_range_lock has been set.
        """
        if self._plot_range_lock:
            return False
        zoom_in = False
        zoom_out = False

        # Calcuate some new min/max values based on recentish data
        # and add some headroom
        y_min = min(self._data_mins)
        y_max = max(self._data_maxs)
        y_range = y_max - y_min
        headroom = y_range * self.ZOOM_HEADROOM
        new_plot_min = max(y_min - headroom, self._abs_min)
        new_plot_max = min(y_max + headroom, self._abs_max)

        # set new range if the data does not fit on the screen
        # this will also redo y tick labels if necessary
        if new_plot_min < self._plot_min or new_plot_max > self._plot_max:
            if self._debug >= 2:
                print("Zoom out")
            self._change_y_range(new_plot_min, new_plot_max, redraw_plot=redraw_plot)
            zoom_out = True

        else:  # otherwise check if zoom in is warranted
            rescale_zoom_range = self._check_zoom_in()
            if rescale_zoom_range:
                if self._debug >= 2:
                    print("Zoom in")
                self._change_y_range(
                    rescale_zoom_range[0],
                    rescale_zoom_range[1],
                    redraw_plot=redraw_plot,
                )
                zoom_in = True

        if zoom_in or zoom_out:
            self._plot_lastzoom_ns = time.monotonic_ns()
            return True
        return False

    def data_add(self, values):
        # pylint: disable=too-many-branches
        changed = False
        data_idx = self._data_idx
        x_pos = self._x_pos

        self._update_stats(values)

        if self._mode == "wrap":
            if self._x_pos == 0 or self._scale_mode == "pixel":
                changed = self._auto_plot_range(redraw_plot=False)

            # Undraw any previous data at current x position
            if (
                not changed
                and self._data_values >= self._plot_width
                and self._values >= self._plot_width
            ):
                self._undraw_column(self._x_pos, data_idx - self._plot_width)

        elif self._mode == "scroll":
            if x_pos >= self._plot_width:  # Fallen off x axis range?
                changed = self._auto_plot_range(redraw_plot=False)
                if not changed:
                    self._undraw_bitmap()  # Need to cls for the scroll

                sc_data_idx = (
                    data_idx + self._scroll_px - self._plot_width
                ) % self._data_size
                self._data_values -= self._scroll_px
                self._redraw_for_scroll(
                    0, self._plot_width - 1 - self._scroll_px, sc_data_idx
                )
                x_pos = self._plot_width - self._scroll_px

            elif self._scale_mode == "pixel":
                changed = self._auto_plot_range(redraw_plot=True)

        # Draw the new data
        self._data_draw(values, x_pos, data_idx)

        # Store the new values in circular buffer
        self._data_store(values)

        # increment x position dealing with wrap/scroll
        new_x_pos = x_pos + 1
        if new_x_pos >= self._plot_width:
            # fallen off edge so wrap or leave position
            # on last column for scroll
            if self._mode == "wrap":
                self._x_pos = 0
            else:
                self._x_pos = new_x_pos  # this is off screen
        else:
            self._x_pos = new_x_pos

        if self._data_values < self._data_size:
            self._data_values += 1

        self._values += 1

        if self._mu_output:
            print(values)

        # scrolling mode has automatic refresh in background turned off
        if self._mode == "scroll":
            self._display_refresh()

    def _change_y_range(self, new_plot_min, new_plot_max, redraw_plot=True):
        y_min = new_plot_min
        y_max = new_plot_max
        if self._debug >= 2:
            print("Change Y range", new_plot_min, new_plot_max, redraw_plot)

        # if values reduce range below the minimum then widen the range
        # but keep it within the absolute min/max values
        if self._plot_min_range is not None:
            range_extend = self._plot_min_range - (y_max - y_min)
            if range_extend > 0:
                y_max += range_extend / 2
                y_min -= range_extend / 2
                if y_min < self._abs_min:
                    y_min = self._abs_min
                    y_max = y_min + self._plot_min_range
                elif y_max > self._abs_max:
                    y_max = self._abs_max
                    y_min = y_max - self._plot_min_range

        self._plot_min = y_min
        self._plot_max = y_max
        self.set_y_axis_tick_labels(self._plot_min, self._plot_max)

        if self._values:
            self._undraw_bitmap()
            self._recalc_y_pos()  ## calculates new y positions
            if redraw_plot:
                self._redraw_all()

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        self._title = value[: self._max_title_len]  # does not show truncation
        self._displayio_title.text = self._title

    @property
    def info(self):
        if self._displayio_info is None:
            return None
        return self._displayio_info.text

    @info.setter
    def info(self, value):
        """Place some text on the screen.
        Multiple lines are supported with newline character.
        Font will be 3x standard terminalio font or 2x if that does not fit."""
        if self._displayio_info is not None:
            self._displayio_graph.pop()

        if value is not None and value != "":
            font_scale = 2
            line_spacing = 1

            font_w, font_h = self._font.get_bounding_box()
            text_lines = value.split("\n")
            max_word_chars = max([len(word) for word in text_lines])
            # If too large reduce the scale
            if (
                max_word_chars * font_scale * font_w > self._screen_width
                or len(text_lines) * font_scale * font_h * line_spacing
                > self._screen_height
            ):
                font_scale -= 1

            self._displayio_info = Label(
                self._font,
                text=value,
                line_spacing=line_spacing,
                scale=font_scale,
                background_color=self.INFO_FG_COLOR,
                color=self.INFO_BG_COLOR,
            )
            # centre the (left justified) text
            self._displayio_info.x = (
                self._screen_width - font_scale * font_w * max_word_chars
            ) // 2
            self._displayio_info.y = self._screen_height // 3
            self._displayio_graph.append(self._displayio_info)

        else:
            self._displayio_info = None

        if self._mode == "scroll":
            self._display_refresh()

    @property
    def channels(self):
        return self._channels

    @channels.setter
    def channels(self, value):
        if value > self._max_channels:
            raise ValueError("Exceeds max_channels")
        self._channels = value

    @property
    def y_range(self):
        return (self._plot_min, self._plot_max)

    @y_range.setter
    def y_range(self, minmax):
        if minmax[0] != self._plot_min or minmax[1] != self._plot_max:
            self._change_y_range(minmax[0], minmax[1], redraw_plot=True)

    @property
    def y_full_range(self):
        return (self._plot_min, self._plot_max)

    @y_full_range.setter
    def y_full_range(self, minmax):
        self._abs_min = minmax[0]
        self._abs_max = minmax[1]

    @property
    def y_min_range(self):
        return self._plot_min_range

    @y_min_range.setter
    def y_min_range(self, value):
        self._plot_min_range = value

    @property
    def y_axis_lab(self):
        return self._y_axis_lab

    @y_axis_lab.setter
    def y_axis_lab(self, text):
        self._y_axis_lab = text[: self._y_lab_width]
        font_w, _ = self._font.get_bounding_box()
        x_pos = (40 - font_w * len(self._y_axis_lab)) // 2
        # max() used to prevent negative (off-screen) values
        self._displayio_y_axis_lab.x = max(0, x_pos)
        self._displayio_y_axis_lab.text = self._y_axis_lab

    @property
    def channel_colidx(self):
        return self._channel_colidx

    @channel_colidx.setter
    def channel_colidx(self, value):
        # tuple() ensures object has a local / read-only copy of data
        self._channel_colidx = tuple(value)

    @property
    def mu_output(self):
        return self._mu_output

    @mu_output.setter
    def mu_output(self, value):
        self._mu_output = value

    @property
    def y_range_lock(self):
        return self._plot_range_lock

    @y_range_lock.setter
    def y_range_lock(self, value):
        self._plot_range_lock = value
