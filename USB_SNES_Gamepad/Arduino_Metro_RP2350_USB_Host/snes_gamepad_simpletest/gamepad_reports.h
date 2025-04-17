// SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// HID reports for USB SNES-like controller

// Byte indices for the gamepad report
#define BYTE_DPAD_LEFT_RIGHT 0   // D-Pad left and right
#define BYTE_DPAD_UP_DOWN    1   // D-Pad up and down
// bytes 2,3,4 unused
#define BYTE_ABXY_BUTTONS    5   // A, B, X, Y
#define BYTE_OTHER_BUTTONS   6   // Shoulders, start, and select


#define DPAD_NEUTRAL         0x7F
// D-Pad directions
#define DPAD_UP              0x00
#define DPAD_RIGHT           0xFF
#define DPAD_DOWN            0xFF
#define DPAD_LEFT            0x00


// Face buttons (Byte[5])
#define BUTTON_NEUTRAL       0x0F
#define BUTTON_X             0x1F
#define BUTTON_A             0x2F
#define BUTTON_B             0x4F
#define BUTTON_Y             0x8F


// Miscellaneous buttons (Byte[6])
#define BUTTON_MISC_NEUTRAL   0x00
#define BUTTON_LEFT_SHOULDER  0x01
#define BUTTON_RIGHT_SHOULDER 0x02
#define BUTTON_SELECT         0x10
#define BUTTON_START          0x20
