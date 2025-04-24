// SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// HID reports for standard boot mouse

// Byte indices for the gamepad report
#define BYTE_BUTTONS    0   // Left, right, middle click buttons
#define BYTE_DELTA_X    1   // Mouse movement horizontal
#define BYTE_DELTA_Y    2   // Mouse movement vertical

#define BUTTON_NEUTRAL      0x00
#define BUTTON_LEFT         0x01
#define BUTTON_RIGHT        0x02
#define BUTTON_MIDDLE       0x04
