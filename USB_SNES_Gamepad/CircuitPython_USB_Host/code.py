# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import array
import time
import usb.core
import adafruit_usb_host_descriptors

# Set to true to print detailed information about all devices found
VERBOSE_SCAN = True

BTN_DPAD_UPDOWN_INDEX = 1
BTN_DPAD_RIGHTLEFT_INDEX = 0
BTN_ABXY_INDEX = 5
BTN_OTHER_INDEX = 6

DIR_IN = 0x80
controller = None

if VERBOSE_SCAN:
    for device in usb.core.find(find_all=True):
        controller = device
        print("pid", hex(device.idProduct))
        print("vid", hex(device.idVendor))
        print("man", device.manufacturer)
        print("product", device.product)
        print("serial", device.serial_number)
        print("config[0]:")
        config_descriptor = adafruit_usb_host_descriptors.get_configuration_descriptor(
            device, 0
        )

        i = 0
        while i < len(config_descriptor):
            descriptor_len = config_descriptor[i]
            descriptor_type = config_descriptor[i + 1]
            if descriptor_type == adafruit_usb_host_descriptors.DESC_CONFIGURATION:
                config_value = config_descriptor[i + 5]
                print(f" value {config_value:d}")
            elif descriptor_type == adafruit_usb_host_descriptors.DESC_INTERFACE:
                interface_number = config_descriptor[i + 2]
                interface_class = config_descriptor[i + 5]
                interface_subclass = config_descriptor[i + 6]
                print(f" interface[{interface_number:d}]")
                print(
                    f"  class {interface_class:02x} subclass {interface_subclass:02x}"
                )
            elif descriptor_type == adafruit_usb_host_descriptors.DESC_ENDPOINT:
                endpoint_address = config_descriptor[i + 2]
                if endpoint_address & DIR_IN:
                    print(f"  IN {endpoint_address:02x}")
                else:
                    print(f"  OUT {endpoint_address:02x}")
            i += descriptor_len

# get the first device found
device = None
while device is None:
    for d in usb.core.find(find_all=True):
        device = d
        break
    time.sleep(0.1)

# set configuration so we can read data from it
device.set_configuration()
print(
    f"configuration set for {device.manufacturer}, {device.product}, {device.serial_number}"
)

# Test to see if the kernel is using the device and detach it.
if device.is_kernel_driver_active(0):
    device.detach_kernel_driver(0)

# buffer to hold 64 bytes
buf = array.array("B", [0] * 64)


def print_array(arr, max_index=None, fmt="hex"):
    """
    Print the values of an array
    :param arr: The array to print
    :param max_index: The maximum index to print. None means print all.
    :param fmt: The format to use, either "hex" or "bin"
    :return: None
    """
    out_str = ""
    if max_index is None or max_index >= len(arr):
        length = len(arr)
    else:
        length = max_index

    for _ in range(length):
        if fmt == "hex":
            out_str += f"{int(arr[_]):02x} "
        elif fmt == "bin":
            out_str += f"{int(arr[_]):08b} "
    print(out_str)


def reports_equal(report_a, report_b, check_length=None):
    """
    Test if two reports are equal. Accounting for any IGNORE_INDEXES

    :param report_a: First report data
    :param report_b: Second report data
    :return: True if the reports are equal, otherwise False.
    """
    if (
        report_a is None
        and report_b is not None
        or report_b is None
        and report_a is not None
    ):
        return False

    length = len(report_a) if check_length is None else check_length
    for _ in range(length):
        if report_a[_] != report_b[_]:
            return False
    return True


idle_state = None
prev_state = None

while True:
    try:
        count = device.read(0x81, buf)
        # print(f"read size: {count}")
    except usb.core.USBTimeoutError:
        continue

    if idle_state is None:
        idle_state = buf[:]
        print("Idle state:")
        print_array(idle_state[:8], max_index=count)
        print()

    if not reports_equal(buf, prev_state, 8) and not reports_equal(buf, idle_state, 8):
        if buf[BTN_DPAD_UPDOWN_INDEX] == 0x0:
            print("D-Pad UP pressed")
        elif buf[BTN_DPAD_UPDOWN_INDEX] == 0xFF:
            print("D-Pad DOWN pressed")

        if buf[BTN_DPAD_RIGHTLEFT_INDEX] == 0:
            print("D-Pad LEFT pressed")
        elif buf[BTN_DPAD_RIGHTLEFT_INDEX] == 0xFF:
            print("D-Pad RIGHT pressed")

        if buf[BTN_ABXY_INDEX] == 0x2F:
            print("A pressed")
        elif buf[BTN_ABXY_INDEX] == 0x4F:
            print("B pressed")
        elif buf[BTN_ABXY_INDEX] == 0x1F:
            print("X pressed")
        elif buf[BTN_ABXY_INDEX] == 0x8F:
            print("Y pressed")

        if buf[BTN_OTHER_INDEX] == 0x01:
            print("L shoulder pressed")
        elif buf[BTN_OTHER_INDEX] == 0x02:
            print("R shoulder pressed")
        elif buf[BTN_OTHER_INDEX] == 0x10:
            print("SELECT pressed")
        elif buf[BTN_OTHER_INDEX] == 0x20:
            print("START pressed")

        # print_array(buf[:8])

    prev_state = buf[:]
