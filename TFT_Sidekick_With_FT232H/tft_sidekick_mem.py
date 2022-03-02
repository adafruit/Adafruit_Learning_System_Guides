# SPDX-FileCopyrightText: 2019 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
from collections import deque
import psutil
# Blinka CircuitPython
import board
import digitalio
import adafruit_rgb_display.ili9341 as ili9341
# Matplotlib
import matplotlib.pyplot as plt
# Python Imaging Library
from PIL import Image

#pylint: disable=bad-continuation
#==| User Config |========================================================
REFRESH_RATE = 1
HIST_SIZE = 61
PLOT_CONFIG = (
    #--------------------
    # PLOT 1 (upper plot)
    #--------------------
    {
    'title' : 'VIRTUAL',
    'ylim' : (0, psutil.virtual_memory().total / 1e9),
    'line_config' : (
        {'color' : '#00FFFF', 'width' : 2}, # free
        {'color' : '#FF00FF', 'width' : 2}, # used
        )
    },
    #--------------------
    # PLOT 2 (lower plot)
    #--------------------
    {
    'title' : 'SWAP',
    'ylim' : (0, psutil.swap_memory().total / 1e9),
    'line_config' : (
        {'color' : '#00FF00', 'width' : 2}, # free
        {'color' : '#FF0000', 'width' : 2}, # used
        )
    }
)

def update_data():
    ''' Do whatever to update your data here. General form is:
           y_data[plot][line].append(new_data_point)
    '''
    vir_mem = psutil.virtual_memory()
    y_data[0][0].append(vir_mem.free / 1e9)
    y_data[0][1].append(vir_mem.used / 1e9)

    swp_mem = psutil.swap_memory()
    y_data[1][0].append(swp_mem.free / 1e9)
    y_data[1][1].append(swp_mem.used / 1e9)

#==| User Config |========================================================
#pylint: enable=bad-continuation

# Setup X data storage
x_time = [x * REFRESH_RATE for x in range(HIST_SIZE)]
x_time.reverse()

# Setup Y data storage
y_data = [ [deque([None] * HIST_SIZE, maxlen=HIST_SIZE) for _ in plot['line_config']]
           for plot in PLOT_CONFIG
         ]

# Setup display
disp = ili9341.ILI9341(board.SPI(), baudrate = 24000000,
                       cs  = digitalio.DigitalInOut(board.D4),
                       dc  = digitalio.DigitalInOut(board.D5),
                       rst = digitalio.DigitalInOut(board.D6))

# Setup plot figure
plt.style.use('dark_background')
fig, ax = plt.subplots(2, 1, figsize=(disp.width / 100, disp.height / 100))

# Setup plot axis
ax[0].xaxis.set_ticklabels([])
for plot, a in enumerate(ax):
    # add grid to all plots
    a.grid(True, linestyle=':')
    # limit and invert x time axis
    a.set_xlim(min(x_time), max(x_time))
    a.invert_xaxis()
    # custom settings
    if 'title' in PLOT_CONFIG[plot]:
        a.set_title(PLOT_CONFIG[plot]['title'], position=(0.5, 0.8))
    if 'ylim' in PLOT_CONFIG[plot]:
        a.set_ylim(PLOT_CONFIG[plot]['ylim'])

# Setup plot lines
#pylint: disable=redefined-outer-name
plot_lines = []
for plot, config in enumerate(PLOT_CONFIG):
    lines = []
    for index, line_config in enumerate(config['line_config']):
        # create line
        line, = ax[plot].plot(x_time, y_data[plot][index])
        # custom settings
        if 'color' in line_config:
            line.set_color(line_config['color'])
        if 'width' in line_config:
            line.set_linewidth(line_config['width'])
        if 'style' in line_config:
            line.set_linestyle(line_config['style'])
        # add line to list
        lines.append(line)
    plot_lines.append(lines)

def update_plot():
    # update lines with latest data
    for plot, lines in enumerate(plot_lines):
        for index, line in enumerate(lines):
            line.set_ydata(y_data[plot][index])
        # autoscale if not specified
        if 'ylim' not in PLOT_CONFIG[plot].keys():
            ax[plot].relim()
            ax[plot].autoscale_view()
    # draw the plots
    canvas = plt.get_current_fig_manager().canvas
    plt.tight_layout()
    canvas.draw()
    # transfer into PIL image and display
    image = Image.frombytes('RGB', canvas.get_width_height(),
                            canvas.tostring_rgb())
    disp.image(image)

print("looping")
while True:
    update_data()
    update_plot()
    time.sleep(REFRESH_RATE)
