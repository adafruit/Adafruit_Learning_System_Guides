# SPDX-FileCopyrightText: Copyright (c) 2023 Scott Shawcroft for Adafruit Industries
#
# SPDX-License-Identifier: MIT

import time
import board
import digitalio
import usb.core
import usb_host

import adafruit_usb_host_descriptors

# power up usb host
usb_power = digitalio.DigitalInOut(board.USB_HOST_POWER)
usb_power.switch_to_output(value=True)

# init the usb host port
usb_host.Port(board.USB_HOST_DP, board.USB_HOST_DM)

time.sleep(1) # delay for enumeration

DIR_IN = 0x80 # USB direction bit in endpoint address

while True:
    print("searching for devices")
    for device in usb.core.find(find_all=True):
        print("pid", hex(device.idProduct))
        print("vid", hex(device.idVendor))
        print("man", device.manufacturer)
        print("product", device.product)
        print("serial", device.serial_number)
        print("config[0]:")
        config_descriptor = adafruit_usb_host_descriptors.get_configuration_descriptor(device, 0)

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
                print(f"  class {interface_class:02x} subclass {interface_subclass:02x}")
            elif descriptor_type == adafruit_usb_host_descriptors.DESC_ENDPOINT:
                endpoint_address = config_descriptor[i + 2]
                if endpoint_address & DIR_IN:
                    print(f"  IN {endpoint_address:02x}")
                else:
                    print(f"  OUT {endpoint_address:02x}")
            i += descriptor_len
        print()
    time.sleep(5)
