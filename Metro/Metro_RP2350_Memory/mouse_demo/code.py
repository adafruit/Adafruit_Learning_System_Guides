# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
This example is made for a basic Microsoft optical mouse with
two buttons and a wheel that can be pressed.

It assumes there is a single mouse connected to USB Host,
and no other devices connected.
"""
import array
from displayio import Group, OnDiskBitmap, TileGrid
from adafruit_display_text.bitmap_label import Label
import supervisor
import terminalio
import usb.core

# pylint: disable=ungrouped-imports
if hasattr(supervisor.runtime, "display") and supervisor.runtime.display is not None:
    # use the built-in HSTX display for Metro RP2350
    display = supervisor.runtime.display
else:
    # pylint: disable=ungrouped-imports
    from displayio import release_displays
    import picodvi
    import board
    import framebufferio

    # initialize display
    release_displays()

    fb = picodvi.Framebuffer(
        320,
        240,
        clk_dp=board.CKP,
        clk_dn=board.CKN,
        red_dp=board.D0P,
        red_dn=board.D0N,
        green_dp=board.D1P,
        green_dn=board.D1N,
        blue_dp=board.D2P,
        blue_dn=board.D2N,
        color_depth=16,
    )
    display = framebufferio.FramebufferDisplay(fb)

# group to hold visual elements
main_group = Group()

# make the group visible on the display
display.root_group = main_group

# load the mouse cursor bitmap
mouse_bmp = OnDiskBitmap("mouse_cursor.bmp")

# make the background pink pixels transparent
mouse_bmp.pixel_shader.make_transparent(0)

# create a TileGrid for the mouse, using its bitmap and pixel_shader
mouse_tg = TileGrid(mouse_bmp, pixel_shader=mouse_bmp.pixel_shader)

# move it to the center of the display
mouse_tg.x = display.width // 2
mouse_tg.y = display.height // 2

# text label to show the x, y coordinates on the screen
output_lbl = Label(
    terminalio.FONT, text=f"{mouse_tg.x},{mouse_tg.y}", color=0xFFFFFF, scale=1
)

# move it to the upper left corner
output_lbl.anchor_point = (0, 0)
output_lbl.anchored_position = (1, 1)

# add it to the main group
main_group.append(output_lbl)

# add the mouse tile grid to the main group
main_group.append(mouse_tg)

# button names
# This is ordered by bit position.
BUTTONS = ["left", "right", "middle"]

# scan for connected USB device and loop over any found
for device in usb.core.find(find_all=True):
    # print device info
    print(f"{device.idVendor:04x}:{device.idProduct:04x}")
    print(device.manufacturer, device.product)
    print(device.serial_number)
    # assume the device is the mouse
    mouse = device

# detach the kernel driver if needed
if mouse.is_kernel_driver_active(0):
    mouse.detach_kernel_driver(0)

# set configuration on the mouse so we can use it
mouse.set_configuration()

# buffer to hold mouse data
# Boot mice have 4 byte reports
buf = array.array("b", [0] * 4)

# main loop
while True:
    try:
        # attempt to read data from the mouse
        # 10ms timeout, so we don't block long if there
        # is no data
        count = mouse.read(0x81, buf, timeout=10)
    except usb.core.USBTimeoutError:
        # skip the rest of the loop if there is no data
        continue

    # update the mouse tilegrid x and y coordinates
    # based on the delta values read from the mouse
    mouse_tg.x = max(0, min(display.width - 1, mouse_tg.x + buf[1]))
    mouse_tg.y = max(0, min(display.height - 1, mouse_tg.y + buf[2]))

    # string with updated coordinates for the text label
    out_str = f"{mouse_tg.x},{mouse_tg.y}"

    # loop over the button names
    for i, button in enumerate(BUTTONS):
        # check if each button is pressed using bitwise AND shifted
        # to the appropriate index for this button
        if buf[0] & (1 << i) != 0:
            # append the button name to the string to show if
            # it is being clicked.
            out_str += f" {button}"

    # update the text label with the new coordinates
    # and buttons being pressed
    output_lbl.text = out_str
