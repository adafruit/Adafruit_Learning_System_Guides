# SPDX-FileCopyrightText: 2020 Kevin J Walters for Adafruit Industries
#
# SPDX-License-Identifier: MIT

# clue-plotter v1.14
# Sensor and input plotter for Adafruit CLUE in CircuitPython
# This plots the sensors and three of the analogue inputs on
# the LCD display either with scrolling or wrap mode which
# approximates a slow timebase oscilloscope, left button selects
# next source or with long press changes palette or longer press
# turns on output for Mu plotting, right button changes plot style

# Tested with an Adafruit CLUE (Alpha) and CircuitPython and 5.0.0

# copy this file to CLUE board as code.py
# needs companion plot_sensor.py and plotter.py files

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

import time

import gc
import board

from plotter import Plotter
from plot_source import PlotSource, TemperaturePlotSource, PressurePlotSource, \
                        HumidityPlotSource, ColorPlotSource, ProximityPlotSource, \
                        IlluminatedColorPlotSource, VolumePlotSource, \
                        AccelerometerPlotSource, GyroPlotSource, \
                        MagnetometerPlotSource, PinPlotSource
from adafruit_clue import clue


debug = 1


# A list of all the data sources for plotting
sources = [TemperaturePlotSource(clue, mode="Celsius"),
           TemperaturePlotSource(clue, mode="Fahrenheit"),
           PressurePlotSource(clue, mode="Metric"),
           PressurePlotSource(clue, mode="Imperial"),
           HumidityPlotSource(clue),
           ColorPlotSource(clue),
           ProximityPlotSource(clue),
           IlluminatedColorPlotSource(clue, mode="Red"),
           IlluminatedColorPlotSource(clue, mode="Green"),
           IlluminatedColorPlotSource(clue, mode="Blue"),
           IlluminatedColorPlotSource(clue, mode="Clear"),
           VolumePlotSource(clue),
           AccelerometerPlotSource(clue),
           GyroPlotSource(clue),
           MagnetometerPlotSource(clue),
           PinPlotSource([board.P0, board.P1, board.P2])
          ]
# The first source to select when plotting starts
current_source_idx = 0

# The various plotting styles - scroll is currently a jump scroll
stylemodes = (("lines", "scroll"),  # draws lines between points
              ("lines", "wrap"),
              ("dots", "scroll"),   # just points - slightly quicker
              ("dots", "wrap")
             )
current_sm_idx = 0


def d_print(level, *args, **kwargs):
    """A simple conditional print for debugging based on global debug level."""
    if not isinstance(level, int):
        print(level, *args, **kwargs)
    elif debug >= level:
        print(*args, **kwargs)


def select_colors(plttr, src, def_palette):
    """Choose the colours based on the particular PlotSource
       or forcing use of default palette."""
    # otherwise use defaults
    channel_colidx = []
    palette = plttr.get_colors()
    colors = PlotSource.DEFAULT_COLORS if def_palette else src.colors()
    for col in colors:
        try:
            channel_colidx.append(palette.index(col))
        except ValueError:
            channel_colidx.append(PlotSource.DEFAULT_COLORS.index(col))
    return channel_colidx


def ready_plot_source(plttr, srcs, def_palette, index=0):
    """Select the plot source by index from srcs list and then setup the
       plot parameters by retrieving meta-data from the PlotSource object."""
    src = srcs[index]
    # Put the description of the source on screen at the top
    source_name = str(src)
    d_print(1, "Selecting source:", source_name)
    plttr.clear_all()
    plttr.title = source_name
    plttr.y_axis_lab = src.units()
    # The range on graph will start at this value
    plttr.y_range = (src.initial_min(), src.initial_max())
    plttr.y_min_range = src.range_min()
    # Sensor/data source is expected to produce data between these values
    plttr.y_full_range = (src.min(), src.max())
    channels_from_src = src.values()
    plttr.channels = channels_from_src  # Can be between 1 and 3
    plttr.channel_colidx = select_colors(plttr, src, def_palette)

    src.start()
    return (src, channels_from_src)


def wait_release(func, menu):
    """Calls func repeatedly waiting for it to return a false value
       and goes through menu list as time passes.

       The menu is a list of menu entries where each entry is a
       two element list of time passed in seconds and text to display
       for that period.
       The entries must be in ascending time order."""

    start_t_ns = time.monotonic_ns()
    menu_option = None
    selected = False

    for menu_option, menu_entry in enumerate(menu):
        menu_time_ns = start_t_ns + int(menu_entry[0] * 1e9)
        menu_text = menu_entry[1]
        if menu_text:
            plotter.info = menu_text
        while time.monotonic_ns() < menu_time_ns:
            if not func():
                selected = True
                break
        if menu_text:
            plotter.info = ""
        if selected:
            break

    return (menu_option, (time.monotonic_ns() - start_t_ns) * 1e-9)


def popup_text(plttr, text, duration=1.0):
    """Place some text on the screen using info property of Plotter object
       for duration seconds."""
    plttr.info = text
    time.sleep(duration)
    plttr.info = None


mu_plotter_output = False
range_lock = False

initial_title = "CLUE Plotter"
# displayio has some static limits on text - pre-calculate the maximum
# length of all of the different PlotSource objects
max_title_len = max(len(initial_title), max([len(str(so)) for so in sources]))
plotter = Plotter(board.DISPLAY,
                  style=stylemodes[current_sm_idx][0],
                  mode=stylemodes[current_sm_idx][1],
                  title=initial_title,
                  max_title_len=max_title_len,
                  mu_output=mu_plotter_output,
                  debug=debug)

# If set to true this forces use of colour blindness friendly colours
use_def_pal = False

clue.pixel[0] = clue.BLACK  # turn off the NeoPixel on the back of CLUE board

plotter.display_on()
# Using left and right here in case the CLUE is cased hiding A/B labels
popup_text(plotter,
           "\n".join(["Button Guide",
                      "Left: next source",
                      "  2secs: palette",
                      "  4s: Mu plot",
                      "  6s: range lock",
                      "Right: style change"]), duration=10)

count = 0

while True:
    # Set the source and start items
    (source, channels) = ready_plot_source(plotter, sources,
                                           use_def_pal,
                                           current_source_idx)

    while True:
        # Read data from sensor or voltage from pad
        all_data = source.data()

        # Check for left (A) and right (B) buttons
        if clue.button_a:
            # Wait for button release with time-based menu
            opt, _ = wait_release(lambda: clue.button_a,
                                  [(2, "Next\nsource"),
                                   (4,
                                    ("Source" if use_def_pal else "Default")
                                    + "\npalette"),
                                   (6,
                                    "Mu output "
                                    + ("off" if mu_plotter_output else "on")),
                                   (8,
                                    "Range lock\n" + ("off" if range_lock else "on"))
                                  ])
            if opt == 0:  # change plot source
                current_source_idx = (current_source_idx + 1) % len(sources)
                break  # to leave inner while and select the new source

            elif opt == 1:  # toggle palette
                use_def_pal = not use_def_pal
                plotter.channel_colidx = select_colors(plotter, source,
                                                       use_def_pal)

            elif opt == 2:  # toggle Mu output
                mu_plotter_output = not mu_plotter_output
                plotter.mu_output = mu_plotter_output

            else:  # toggle range lock
                range_lock = not range_lock
                plotter.y_range_lock = range_lock

        if clue.button_b:  # change plot style and mode
            current_sm_idx = (current_sm_idx + 1) % len(stylemodes)
            (new_style, new_mode) = stylemodes[current_sm_idx]
            wait_release(lambda: clue.button_b,
                         [(2, new_style + "\n" + new_mode)])
            d_print(1, "Graph change", new_style, new_mode)
            plotter.change_stylemode(new_style, new_mode)

        # Display it
        if channels == 1:
            plotter.data_add((all_data,))
        else:
            plotter.data_add(all_data)

        # An occasional print of free heap
        if debug >=3 and count % 15 == 0:
            gc.collect()  # must collect() first to measure free memory
            print("Free memory:", gc.mem_free())

        count += 1

    source.stop()

plotter.display_off()
