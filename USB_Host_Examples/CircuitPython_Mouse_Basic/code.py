# SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
# SPDX-License-Identifier: MIT
"""
This example is made for a basic mouse with
two buttons and a wheel that can be pressed.

It assumes there is a single mouse connected to USB Host.
"""
import array
import usb.core
import adafruit_usb_host_descriptors

# button names
# This is ordered by bit position.
BUTTONS = ["left", "right", "middle"]

# scan for connected USB device and loop over any found
for device in usb.core.find(find_all=True):
    # print device info
    print(f"{device.idVendor:04x}:{device.idProduct:04x}")
    print(device.manufacturer, device.product)
    print(device.serial_number)

    # try to find mouse endpoint on the current device.
    mouse_interface_index, mouse_endpoint_address = (
        adafruit_usb_host_descriptors.find_boot_mouse_endpoint(device)
    )
    if mouse_interface_index is not None and mouse_endpoint_address is not None:
        mouse = device
        print(
            f"mouse interface: {mouse_interface_index} "
            + f"endpoint_address: {hex(mouse_endpoint_address)}"
        )

        # detach the kernel driver if needed
        if mouse.is_kernel_driver_active(0):
            mouse.detach_kernel_driver(0)

        # set configuration on the mouse so we can use it
        mouse.set_configuration()

        break

# buffer to hold mouse data
buf = array.array("b", [0] * 8)

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

    # string with delta x, y values to print
    out_str = f"{buf[1]},{buf[2]}"

    # loop over the button names
    for i, button in enumerate(BUTTONS):
        # check if each button is pressed using bitwise AND shifted
        # to the appropriate index for this button
        if buf[0] & (1 << i) != 0:
            # append the button name to the string to show if
            # it is being clicked.
            out_str += f" {button}"

    print(out_str)
