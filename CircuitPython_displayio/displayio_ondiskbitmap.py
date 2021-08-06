import board
import displayio

display = board.DISPLAY

# Current method valid for CircuitPython 6 & 7

# Open the file
with open("/purple.bmp", "rb") as bitmap_file:

    # Setup the file as the bitmap data source
    bitmap = displayio.OnDiskBitmap(bitmap_file)

    # Create a TileGrid to hold the bitmap
    tile_grid = displayio.TileGrid(
        bitmap,
        pixel_shader=getattr(bitmap, 'pixel_shader', displayio.ColorConverter())
    )

    # Create a Group to hold the TileGrid
    group = displayio.Group()

    # Add the TileGrid to the Group
    group.append(tile_grid)

    # Add the Group to the Display
    display.show(group)

    # Loop forever so you can enjoy your image
    while True:
        pass


# Future method for CircuitPython 7 onwards

# Setup the file as the bitmap data source
bitmap = displayio.OnDiskBitmap("/purple.bmp")

# Create a TileGrid to hold the bitmap
tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)

# Create a Group to hold the TileGrid
group = displayio.Group()

# Add the TileGrid to the Group
group.append(tile_grid)

# Add the Group to the Display
display.show(group)

# Loop forever so you can enjoy your image
while True:
    pass
