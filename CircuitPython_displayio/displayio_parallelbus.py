import board
import displayio

# Release any previously configured displays
displayio.release_displays()

# Setup the display bus
# Tested with a Metro M4 Express
display_bus = displayio.ParallelBus(data0=board.D13,
                                    command=board.D6,
                                    chip_select=board.D7,
                                    write=board.D5,
                                    read=board.D4)

# Setup the initialization sequence
# stolen from adafruit_ili9341.py
INIT_SEQUENCE = (
    b"\x01\x80\x80"            # Software reset then delay 0x80 (128ms)
    b"\xEF\x03\x03\x80\x02"
    b"\xCF\x03\x00\xC1\x30"
    b"\xED\x04\x64\x03\x12\x81"
    b"\xE8\x03\x85\x00\x78"
    b"\xCB\x05\x39\x2C\x00\x34\x02"
    b"\xF7\x01\x20"
    b"\xEA\x02\x00\x00"
    b"\xc0\x01\x23"            # Power control VRH[5:0]
    b"\xc1\x01\x10"            # Power control SAP[2:0];BT[3:0]
    b"\xc5\x02\x3e\x28"        # VCM control
    b"\xc7\x01\x86"            # VCM control2
    b"\x36\x01\x38"            # Memory Access Control
    b"\x37\x01\x00"            # Vertical scroll zero
    b"\x3a\x01\x55"            # COLMOD: Pixel Format Set
    b"\xb1\x02\x00\x18"        # Frame Rate Control (In Normal Mode/Full Colors)
    b"\xb6\x03\x08\x82\x27"    # Display Function Control
    b"\xF2\x01\x00"            # 3Gamma Function Disable
    b"\x26\x01\x01"            # Gamma curve selected
    b"\xe0\x0f\x0F\x31\x2B\x0C\x0E\x08\x4E\xF1\x37\x07\x10\x03\x0E\x09\x00" # Set Gamma
    b"\xe1\x0f\x00\x0E\x14\x03\x11\x07\x31\xC1\x48\x08\x0F\x0C\x31\x36\x0F" # Set Gamma
    b"\x11\x80\x78"            # Exit Sleep then delay 0x78 (120ms)
    b"\x29\x80\x78"            # Display on then delay 0x78 (120ms)
)

# Setup the Display
display = displayio.Display(display_bus, INIT_SEQUENCE, width=320, height=240)

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
