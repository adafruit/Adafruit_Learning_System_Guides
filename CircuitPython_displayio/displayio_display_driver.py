import board
import displayio
import adafruit_ili9341

# Release any previously configured displays
displayio.release_displays()

# Setup SPI bus
spi_bus = board.SPI()

# Digital pins to use
tft_cs = board.D10
tft_dc = board.D9

# Setup the display bus
display_bus = displayio.FourWire(spi_bus, command=tft_dc, chip_select=tft_cs)

# Setup the Display
display = adafruit_ili9341.ILI9341(display_bus, width=320, height=240)

#
# DONE - now you can use the display however you want
#

bitmap = displayio.Bitmap(320, 240, 2)

palette = displayio.Palette(2)
palette[0] = 0
palette[1] = 0xFFFFFF

for x in range(10, 20):
    for y in range(10, 20):
        bitmap[x, y] = 1

tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)

group = displayio.Group()
group.append(tile_grid)
display.show(group)
display.refresh_soon()
