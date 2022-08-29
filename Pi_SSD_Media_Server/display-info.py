# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import subprocess
import board
import displayio
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
from adafruit_st7789 import ST7789

BORDER_WIDTH = 4
TEXT_SCALE = 1

font = bitmap_font.load_font("/home/pi/fonts/Arial-18.bdf")
font_small = bitmap_font.load_font("/home/pi/fonts/Arial-14.bdf")
font_bold = bitmap_font.load_font("/home/pi/fonts/Arial-Bold-24.bdf")

# Release any resources currently in use for the displays
displayio.release_displays()

spi = board.SPI()
tft_cs = board.CE0
tft_dc = board.D25
tft_rst = board.D24

display_bus = displayio.FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=tft_rst)

display = ST7789(display_bus, width=320, height=170, colstart=35, rotation=270)

# Make the display context
splash = displayio.Group()
display.show(splash)

color_bitmap = displayio.Bitmap(display.width, display.height, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0xAA0088  # Purple
bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
splash.append(bg_sprite)

# Draw a smaller inner rectangle
inner_bitmap = displayio.Bitmap(
    display.width - (BORDER_WIDTH * 2), display.height - (BORDER_WIDTH * 2), 1
)
inner_palette = displayio.Palette(1)
inner_palette[0] = 0x222222  # Dark Gray
inner_sprite = displayio.TileGrid(
    inner_bitmap, pixel_shader=inner_palette, x=BORDER_WIDTH, y=BORDER_WIDTH
)
splash.append(inner_sprite)

# display ip, cpu and memory usage
cmd = "hostname -I | cut -d' ' -f1"
IP = subprocess.check_output(cmd, shell=True).decode("utf-8")
cmd = 'cut -f 1 -d " " /proc/loadavg'
CPU = subprocess.check_output(cmd, shell=True).decode("utf-8")
cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%s MB  %.2f%%\", $3,$2,$3*100/$2 }'"
MemUsage = subprocess.check_output(cmd, shell=True).decode("utf-8")
cmd =  "vcgencmd measure_temp | grep -o -E '[[:digit:]].*'"
cpu_temp = subprocess.check_output(cmd, shell=True).decode("utf-8")

# Draw a label
text_ip = label.Label(
    font_bold,
    text="IP: " + IP,
    color=0x1BF702,
    scale=TEXT_SCALE,
)
text_cpu = label.Label(
    font,
    text="CPU: " + cpu_temp,
    color=0xFFFFFF,
    scale=TEXT_SCALE,
)
text_mem = label.Label(
    font_small,
    text=MemUsage,
    color=0xCCCCCC,
    scale=TEXT_SCALE,
)
text_ip.x = 12
text_cpu.x = 12
text_mem.x = 12

text_ip.y = 30
text_cpu.y = 70
text_mem.y = 150

splash.append(text_ip)
splash.append(text_cpu)
splash.append(text_mem)

while True:
    text_ip.text = "IP: " + IP
    text_cpu.text = "CPU:" + cpu_temp
    text_mem.text = MemUsage
    display.refresh()
