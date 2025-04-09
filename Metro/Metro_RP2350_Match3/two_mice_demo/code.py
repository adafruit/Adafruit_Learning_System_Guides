# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import array
import supervisor
import terminalio
import usb.core
from adafruit_display_text.bitmap_label import Label
from displayio import Group, OnDiskBitmap, TileGrid, Palette, ColorConverter

import adafruit_usb_host_descriptors

# use the default built-in display,
# the HSTX / PicoDVI display for the Metro RP2350
display = supervisor.runtime.display

# a group to hold all other visual elements
main_group = Group()

# set the main group to show on the display
display.root_group = main_group

# load the cursor bitmap file
mouse_bmp = OnDiskBitmap("mouse_cursor.bmp")

# lists for labels, mouse tilegrids, and palettes.
# each mouse will get 1 of each item. All lists
# will end up with length 2.
output_lbls = []
mouse_tgs = []
palettes = []

# the different colors to use for each mouse cursor
# and labels
colors = [0xFF00FF, 0x00FF00]

for i in range(2):
    # create a palette for this mouse
    mouse_palette = Palette(3)
    # index zero is used for transparency
    mouse_palette.make_transparent(0)
    # add the palette to the list of palettes
    palettes.append(mouse_palette)

    # copy the first two colors from mouse palette
    for palette_color_index in range(2):
        mouse_palette[palette_color_index] = mouse_bmp.pixel_shader[palette_color_index]

    # replace the last color with different color for each mouse
    mouse_palette[2] = colors[i]

    # create a TileGrid for this mouse cursor.
    # use the palette created above
    mouse_tg = TileGrid(mouse_bmp, pixel_shader=mouse_palette)

    # move the mouse tilegrid to near the center of the display
    mouse_tg.x = display.width // 2 - (i * 12)
    mouse_tg.y = display.height // 2

    # add this mouse tilegrid to the list of mouse tilegrids
    mouse_tgs.append(mouse_tg)

    # add this mouse tilegrid to the main group so it will show
    # on the display
    main_group.append(mouse_tg)

    # create a label for this mouse
    output_lbl = Label(terminalio.FONT, text=f"{mouse_tg.x},{mouse_tg.y}", color=colors[i], scale=1)
    # anchored to the top left corner of the label
    output_lbl.anchor_point = (0, 0)

    # move to op left corner of the display, moving
    # down by a static amount to static the two labels
    # one below the other
    output_lbl.anchored_position = (1, 1 + i * 13)

    # add the label to the list of labels
    output_lbls.append(output_lbl)

    # add the label to the main group so it will show
    # on the display
    main_group.append(output_lbl)

# lists for mouse interface indexes, endpoint addresses, and USB Device instances
# each of these will end up with length 2 once we find both mice
mouse_interface_indexes = []
mouse_endpoint_addresses = []
mice = []

# scan for connected USB devices
for device in usb.core.find(find_all=True):
    # check for boot mouse endpoints on this device
    mouse_interface_index, mouse_endpoint_address = (
        adafruit_usb_host_descriptors.find_boot_mouse_endpoint(device)
    )
    # if a boot mouse interface index and endpoint address were found
    if mouse_interface_index is not None and mouse_endpoint_address is not None:
        # add the interface index to the list of indexes
        mouse_interface_indexes.append(mouse_interface_index)
        # add the endpoint address to the list of addresses
        mouse_endpoint_addresses.append(mouse_endpoint_address)
        # add the device instance to the list of mice
        mice.append(device)

        # print details to the console
        print(f"mouse interface: {mouse_interface_index} ", end="")
        print(f"endpoint_address: {hex(mouse_endpoint_address)}")

        # detach device from kernel if needed
        if device.is_kernel_driver_active(0):
            device.detach_kernel_driver(0)

        # set the mouse configuration so it can be used
        device.set_configuration()

# This is ordered by bit position.
BUTTONS = ["left", "right", "middle"]

# list of buffers, will hold one buffer for each mouse
mouse_bufs = []
for i in range(2):
    # Buffer to hold data read from the mouse
    mouse_bufs.append(array.array("b", [0] * 8))


def get_mouse_deltas(buffer, read_count):
    """
    Given a buffer and read_count return the x and y delta values
    :param buffer: A buffer containing data read from the mouse
    :param read_count: How many bytes of data were read from the mouse
    :return: tuple x,y delta values
    """
    if read_count == 4:
        delta_x = buffer[1]
        delta_y = buffer[2]
    elif read_count == 8:
        delta_x = buffer[2]
        delta_y = buffer[4]
    else:
        raise ValueError(f"Unsupported mouse packet size: {read_count}, must be 4 or 8")
    return delta_x, delta_y

# main loop
while True:
    # for each mouse instance
    for mouse_index, mouse in enumerate(mice):
        # try to read data from the mouse
        try:
            count = mouse.read(
                mouse_endpoint_addresses[mouse_index], mouse_bufs[mouse_index], timeout=10
            )

        # if there is no data it will raise USBTimeoutError
        except usb.core.USBTimeoutError:
            # Nothing to do if there is no data for this mouse
            continue

        # there was mouse data, so get the delta x and y values from it
        mouse_deltas = get_mouse_deltas(mouse_bufs[mouse_index], count)

        # update the x position of this mouse cursor using the delta value
        # clamped to the display size
        mouse_tgs[mouse_index].x = max(
            0, min(display.width - 1, mouse_tgs[mouse_index].x + mouse_deltas[0])
        )
        # update the y position of this mouse cursor using the delta value
        # clamped to the display size
        mouse_tgs[mouse_index].y = max(
            0, min(display.height - 1, mouse_tgs[mouse_index].y + mouse_deltas[1])
        )

        # output string with the new cursor position
        out_str = f"{mouse_tgs[mouse_index].x},{mouse_tgs[mouse_index].y}"

        # loop over possible button bit indexes
        for i, button in enumerate(BUTTONS):
            # check each bit index to determin if the button was pressed
            if mouse_bufs[mouse_index][0] & (1 << i) != 0:
                # if it was pressed, add the button to the output string
                out_str += f" {button}"

        # set the output string into text of the label
        # to show it on the display
        output_lbls[mouse_index].text = out_str