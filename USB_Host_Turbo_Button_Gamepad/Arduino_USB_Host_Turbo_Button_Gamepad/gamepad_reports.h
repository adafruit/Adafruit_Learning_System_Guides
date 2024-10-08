// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// HID reports for Logitech Gamepad F310
// Update defines and combo_report for your gamepad and/or combo!

uint8_t combo_report[] = { 0x80, 0x7F, 0x80, 0x7F, 0x28, 0x03, 0x00, 0xFF };

// Byte indices for the gamepad report
#define BYTE_LEFT_STICK_X    0   // Left analog stick X-axis
#define BYTE_LEFT_STICK_Y    1   // Left analog stick Y-axis
#define BYTE_RIGHT_STICK_X   2   // Right analog stick X-axis
#define BYTE_RIGHT_STICK_Y   3   // Right analog stick Y-axis
#define BYTE_DPAD_BUTTONS    4   // D-Pad and face buttons
#define BYTE_MISC_BUTTONS    5   // Miscellaneous buttons (triggers, paddles, start, back)
#define BYTE_UNUSED          6   // Unused
#define BYTE_STATUS          7   // Status byte (usually constant)

// Button masks for Byte[4] (DPAD and face buttons)
#define DPAD_MASK            0x07  // Bits 0-2 for D-Pad direction
#define DPAD_NEUTRAL         0x08  // Bit 3 set when D-Pad is neutral

// D-Pad directions (use when DPAD_NEUTRAL is not set)
#define DPAD_UP              0x00  // 0000
#define DPAD_UP_RIGHT        0x01  // 0001
#define DPAD_RIGHT           0x02  // 0010
#define DPAD_DOWN_RIGHT      0x03  // 0011
#define DPAD_DOWN            0x04  // 0100
#define DPAD_DOWN_LEFT       0x05  // 0101
#define DPAD_LEFT            0x06  // 0110
#define DPAD_UP_LEFT         0x07  // 0111

// Face buttons (Byte[4] bits 4-7)
#define BUTTON_X             0x18
#define BUTTON_A             0x28
#define BUTTON_B             0x48
#define BUTTON_Y             0x88

// Button masks for Byte[5] (MISC buttons)
#define MISC_NEUTRAL         0x00

// Miscellaneous buttons (Byte[5])
#define BUTTON_LEFT_PADDLE   0x01
#define BUTTON_RIGHT_PADDLE  0x02
#define BUTTON_LEFT_TRIGGER  0x04
#define BUTTON_RIGHT_TRIGGER 0x08
#define BUTTON_BACK          0x10
#define BUTTON_START         0x20

#define LEFT_STICK_X_NEUTRAL   0x80
#define LEFT_STICK_Y_NEUTRAL   0x7F
#define RIGHT_STICK_X_NEUTRAL   0x80
#define RIGHT_STICK_Y_NEUTRAL   0x7F
