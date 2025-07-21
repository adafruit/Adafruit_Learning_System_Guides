# SPDX-FileCopyrightText: Copyright (c) 2025 Anne Barela for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Display the EDID monitor resolutions for a connected HDMI/DVI display
#
import sys
import board
import busio

def parse_established_timings(edid):
    # pylint: disable=redefined-outer-name
    # pylint: disable=too-many-branches
    """Parse established timings from EDID bytes 35-37"""
    modes = []

    # Byte 35 (established timings I)
    if edid[35] & 0x80:
        modes.append("720x400 @70Hz")
    if edid[35] & 0x40:
        modes.append("720x400 @88Hz")
    if edid[35] & 0x20:
        modes.append("640x480 @60Hz")
    if edid[35] & 0x10:
        modes.append("640x480 @67Hz")
    if edid[35] & 0x08:
        modes.append("640x480 @72Hz")
    if edid[35] & 0x04:
        modes.append("640x480 @75Hz")
    if edid[35] & 0x02:
        modes.append("800x600 @56Hz")
    if edid[35] & 0x01:
        modes.append("800x600 @60Hz")

    # Byte 36 (established timings II)
    if edid[36] & 0x80:
        modes.append("800x600 @72Hz")
    if edid[36] & 0x40:
        modes.append("800x600 @75Hz")
    if edid[36] & 0x20:
        modes.append("832x624 @75Hz")
    if edid[36] & 0x10:
        modes.append("1024x768 @87Hz")
    if edid[36] & 0x08:
        modes.append("1024x768 @60Hz")
    if edid[36] & 0x04:
        modes.append("1024x768 @70Hz")
    if edid[36] & 0x02:
        modes.append("1024x768 @75Hz")
    if edid[36] & 0x01:
        modes.append("1280x1024 @75Hz")

    # Byte 37 (manufacturer timings)
    if edid[37] & 0x80:
        modes.append("1152x870 @75Hz")

    return modes

def parse_standard_timings(edid):
    # pylint: disable=redefined-outer-name
    """Parse standard timings from EDID bytes 38-53"""
    modes = []

    for i in range(38, 54, 2):  # 8 standard timing descriptors, 2 bytes each
        if edid[i] == 0x01 and edid[i+1] == 0x01:
            continue  # Unused timing

        if edid[i] == 0x00:
            continue  # Invalid timing

        # Calculate horizontal resolution
        h_res = (edid[i] + 31) * 8

        # Calculate aspect ratio and vertical resolution
        aspect_ratio = (edid[i+1] & 0xC0) >> 6
        refresh_rate = (edid[i+1] & 0x3F) + 60

        if aspect_ratio == 0:    # 16:10
            aspect = "16:10"
            v_res = (h_res * 10) // 16
        elif aspect_ratio == 1:  # 4:3
            aspect = "4:3"
            v_res = (h_res * 3) // 4
        elif aspect_ratio == 2:  # 5:4
            aspect = "5:4"
            v_res = (h_res * 4) // 5
        else:  # aspect_ratio == 3, 16:9
            aspect = "16:9"
            v_res = (h_res * 9) // 16

        modes.append(f"{h_res}x{v_res} @{refresh_rate}Hz, Aspect: {aspect}")

    return modes

def parse_detailed_timings(edid):
    # pylint: disable=redefined-outer-name
    # pylint: disable=unused-variable
    # pylint: disable=too-many-locals

    """Parse detailed timing descriptors from EDID bytes 54-125"""
    modes = []

    for i in range(54, 126, 18):  # 4 detailed timing descriptors, 18 bytes each
        # Check if this is a timing descriptor (pixel clock != 0)
        pixel_clock = edid[i] | (edid[i+1] << 8)
        if pixel_clock == 0:
            continue  # Not a timing descriptor

        # Parse horizontal resolution
        h_active_low = edid[i+2]
        h_active_high = (edid[i+4] & 0xF0) >> 4
        h_active = h_active_low | (h_active_high << 8)

        # Parse vertical resolution
        v_active_low = edid[i+5]
        v_active_high = (edid[i+7] & 0xF0) >> 4
        v_active = v_active_low | (v_active_high << 8)

        # Parse horizontal sync
        h_sync_offset_low = edid[i+8]
        h_sync_width_low = edid[i+9]
        h_sync_high = (edid[i+11] & 0xC0) >> 6
        h_sync_offset = h_sync_offset_low | ((h_sync_high & 0x3) << 8)
        h_sync_width = h_sync_width_low | ((h_sync_high & 0xC) << 6)

        # Parse vertical sync
        v_sync_offset_low = (edid[i+10] & 0xF0) >> 4
        v_sync_width_low = edid[i+10] & 0x0F
        v_sync_high = (edid[i+11] & 0x0C) >> 2
        v_sync_offset = v_sync_offset_low | ((v_sync_high & 0x3) << 4)
        v_sync_width = v_sync_width_low | ((v_sync_high & 0xC) << 2)

        # Calculate refresh rate (approximate)
        h_blank_low = edid[i+3]
        h_blank_high = edid[i+4] & 0x0F
        h_blank = h_blank_low | (h_blank_high << 8)
        h_total = h_active + h_blank

        v_blank_low = edid[i+6]
        v_blank_high = edid[i+7] & 0x0F
        v_blank = v_blank_low | (v_blank_high << 8)
        v_total = v_active + v_blank

        if h_total > 0 and v_total > 0:
            refresh_rate = (pixel_clock * 10000) // (h_total * v_total)
            modes.append(f"{h_active}x{v_active} @{refresh_rate}Hz")

    return modes

# Main EDID reading code
i2c = busio.I2C(board.SCL, board.SDA)
if not i2c:
    print("Board doesn't have I2C")
    sys.exit(1)
if not i2c.try_lock():
    print("Cannot lock I2C")
    sys.exit(1)

print("\nI2C Present")

devices = i2c.scan()
if not 0x50 in devices:
    print("No device found at EDID address 0x50, is the monitor plugged in " +
          "& board power cycled?")
    sys.exit(1)

print("Device 0x50 found!")
device = 0x50
edid = bytearray(128)
out = bytearray([0])
i2c.writeto_then_readfrom(device, out, edid)
# pylint: disable=too-many-boolean-expressions
if edid[0] != 0x00 or edid[1] != 0xFF or edid[2] != 0xFF or \
   edid[3] != 0xFF or edid[4] != 0xFF or edid[5] != 0xFF or \
   edid[6] != 0xFF or edid[7] != 0x00:
    print("EDID signature not recognized")
    sys.exit(1)

print("Valid EDID signature!")

# Verify checksum
checksum = sum(edid) & 0xFF
if checksum != 0:
    print("Bad EDID checksum detected")
    sys.exit(1)

print("Good EDID checksum!")

# Parse all supported modes
supported_modes = []

# Get established timings
established_modes = parse_established_timings(edid)
supported_modes.extend(established_modes)

# Get standard timings
standard_modes = parse_standard_timings(edid)
supported_modes.extend(standard_modes)

# Get detailed timings
detailed_modes = parse_detailed_timings(edid)
supported_modes.extend(detailed_modes)

# Remove duplicates while preserving order
unique_modes = []
for mode in supported_modes:
    if mode not in unique_modes:
        unique_modes.append(mode)

# Display results
print(f"\nSupported Display Modes ({len(unique_modes)} found):")
print("=" * 50)
for mode in unique_modes:
    print(f"  {mode}")

# Original default resolution logic
established_timings = edid[35]
if (established_timings & 0xa0) == 0:
    print("\nWarning: 720x400@70Hz and 640x480@60Hz not supported")
    default_width = 640
    default_height = 480
else:
    offset = 54
    preferred_pixel_clock = edid[offset] | (edid[offset + 1] << 8)
    if preferred_pixel_clock != 0:
        preferred_width = ((edid[offset + 4] & 0xf0) << 4) | edid[offset + 2]
        preferred_height = ((edid[offset + 7] & 0xf0) << 4) | edid[offset + 5]
        if (established_timings & 0x80) != 0 and \
           preferred_width % 1920 == 0 and \
           preferred_height % 1080 == 0:
            default_width = 720
            default_height = 400
        else:
            default_width = 640
            default_height = 480
    else:
        default_width = 640
        default_height = 480

print(f"\nDefault resolution: {default_width}x{default_height}")
print(f"Preferred resolution: {preferred_width}x{preferred_height}")

i2c.unlock()
print("\nDone!")
