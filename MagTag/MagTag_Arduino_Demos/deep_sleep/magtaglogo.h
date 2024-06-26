// SPDX-FileCopyrightText: 2020 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#define MAGTAGLOGO_WIDTH 297
#define MAGTAGLOGO_HEIGHT 52

const uint8_t magtaglogo_mono[] = {
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0xf0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0xff, 0xc0, 0x00, 0x00, 
0xff, 0xf8, 0x00, 0x00, 0x1f, 0xff, 0x00, 0x1f, 0xff, 0xff, 0xff, 0x00, 0x00, 0x00, 0x0f, 0xff, 0xff, 0x00, 0x01, 0xff, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x00, 0x3f, 0xff, 0xff, 0xfe, 0x00, 0x00, 0x00, 0x1f, 0xff, 0xfe, 0x00, 0x00, 
0xff, 0xfc, 0x00, 0x00, 0x3f, 0xff, 0x00, 0x7f, 0xff, 0xff, 0xff, 0xc0, 0x00, 0x00, 0x3f, 0xff, 0xff, 0xe0, 0x01, 0xff, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x01, 0xff, 0xff, 0xff, 0xff, 0x80, 0x00, 0x00, 0xff, 0xff, 0xff, 0x80, 0x00, 
0xff, 0xfc, 0x00, 0x00, 0x3f, 0xff, 0x00, 0xff, 0xff, 0xff, 0xff, 0xf0, 0x00, 0x00, 0xff, 0xff, 0xff, 0xf8, 0x01, 0xff, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x03, 0xff, 0xff, 0xff, 0xff, 0xc0, 0x00, 0x03, 0xff, 0xff, 0xff, 0xe0, 0x00, 
0xff, 0xfe, 0x00, 0x00, 0x7f, 0xff, 0x01, 0xff, 0xff, 0xff, 0xff, 0xf8, 0x00, 0x03, 0xff, 0xff, 0xff, 0xfc, 0x01, 0xff, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x07, 0xff, 0xff, 0xff, 0xff, 0xe0, 0x00, 0x07, 0xff, 0xff, 0xff, 0xf8, 0x00, 
0xff, 0xfe, 0x00, 0x00, 0x7f, 0xff, 0x03, 0xff, 0xff, 0xff, 0xff, 0xf8, 0x00, 0x07, 0xff, 0xff, 0xff, 0xff, 0x01, 0xff, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x0f, 0xff, 0xff, 0xff, 0xff, 0xf0, 0x00, 0x1f, 0xff, 0xff, 0xff, 0xfc, 0x00, 
0xff, 0xff, 0x00, 0x00, 0xff, 0xff, 0x07, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x00, 0x0f, 0xff, 0xff, 0xff, 0xff, 0x81, 0xff, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x0f, 0xff, 0xff, 0xff, 0xff, 0xf8, 0x00, 0x3f, 0xff, 0xff, 0xff, 0xfe, 0x00, 
0xff, 0xff, 0x80, 0x00, 0xff, 0xff, 0x07, 0xff, 0xff, 0xff, 0xff, 0xfe, 0x00, 0x1f, 0xff, 0xff, 0xff, 0xff, 0x81, 0xff, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x1f, 0xff, 0xff, 0xff, 0xff, 0xf8, 0x00, 0x7f, 0xff, 0xff, 0xff, 0xff, 0x00, 
0xff, 0xff, 0x80, 0x01, 0xff, 0xff, 0x0f, 0xff, 0xff, 0xff, 0xff, 0xfe, 0x00, 0x3f, 0xff, 0xff, 0xff, 0xff, 0x81, 0xff, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x1f, 0xff, 0xff, 0xff, 0xff, 0xf8, 0x00, 0xff, 0xff, 0xff, 0xff, 0xfe, 0x00, 
0xff, 0xff, 0xc0, 0x03, 0xff, 0xff, 0x0f, 0xff, 0xff, 0xff, 0xff, 0xfe, 0x00, 0x7f, 0xff, 0xff, 0xff, 0xff, 0x01, 0xff, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x3f, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x01, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x00, 
0xff, 0xff, 0xc0, 0x03, 0xff, 0xff, 0x0f, 0xff, 0xff, 0xff, 0xff, 0xfe, 0x00, 0xff, 0xff, 0xff, 0xff, 0xfe, 0x01, 0xff, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x3f, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x03, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x00, 
0xff, 0xff, 0xe0, 0x07, 0xff, 0xff, 0x0f, 0xff, 0xff, 0xff, 0xff, 0xfe, 0x01, 0xff, 0xff, 0xc0, 0x7f, 0xfc, 0x01, 0xff, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x3f, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x03, 0xff, 0xff, 0x81, 0xff, 0xf8, 0x00, 
0xff, 0xff, 0xe0, 0x07, 0xff, 0xff, 0x0f, 0xff, 0xff, 0xff, 0xff, 0xfe, 0x01, 0xff, 0xff, 0x00, 0x0f, 0xf8, 0x00, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x07, 0xff, 0xfc, 0x00, 0x1f, 0xf0, 0x00, 
0xff, 0xff, 0xf0, 0x0f, 0xff, 0xff, 0x0f, 0xff, 0x80, 0x00, 0x3f, 0xfe, 0x03, 0xff, 0xfc, 0x00, 0x03, 0xf8, 0x00, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xff, 0x00, 0x00, 0x7f, 0xfc, 0x07, 0xff, 0xf0, 0x00, 0x0f, 0xe0, 0x00, 
0xff, 0xff, 0xf0, 0x0f, 0xff, 0xff, 0x0f, 0xff, 0x00, 0x00, 0x1f, 0xfe, 0x03, 0xff, 0xf8, 0x00, 0x01, 0xf0, 0x00, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfe, 0x00, 0x00, 0x3f, 0xfc, 0x0f, 0xff, 0xe0, 0x00, 0x03, 0xc0, 0x00, 
0xff, 0xff, 0xf8, 0x1f, 0xff, 0xff, 0x0f, 0xff, 0x00, 0x00, 0x1f, 0xfe, 0x07, 0xff, 0xf0, 0x00, 0x00, 0x60, 0x00, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0x3f, 0xfc, 0x0f, 0xff, 0xc0, 0x00, 0x01, 0x80, 0x00, 
0xff, 0xff, 0xfc, 0x1f, 0xff, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x07, 0xff, 0xe0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0x3f, 0xfc, 0x1f, 0xff, 0x80, 0x00, 0x00, 0x00, 0x00, 
0xff, 0xff, 0xfc, 0x3f, 0xff, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x0f, 0xff, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xbf, 0xfc, 0x1f, 0xff, 0x80, 0x00, 0x00, 0x00, 0x00, 
0xff, 0xff, 0xfe, 0x7f, 0xff, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x0f, 0xff, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xbf, 0xfc, 0x1f, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 
0xff, 0xff, 0xfe, 0x7f, 0xff, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x0f, 0xff, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xbf, 0xfc, 0x3f, 0xfe, 0x00, 0x00, 0x00, 0x00, 0x00, 
0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x0f, 0xff, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xbf, 0xfc, 0x3f, 0xfe, 0x00, 0x00, 0x00, 0x00, 0x00, 
0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x1f, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xbf, 0xfc, 0x3f, 0xfe, 0x00, 0x00, 0x00, 0x00, 0x00, 
0xff, 0xf7, 0xff, 0xff, 0xef, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x1f, 0xff, 0x00, 0x07, 0xff, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xbf, 0xfc, 0x3f, 0xfc, 0x00, 0x1f, 0xff, 0xff, 0x80, 
0xff, 0xf7, 0xff, 0xff, 0xef, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x1f, 0xff, 0x00, 0x07, 0xff, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0x3f, 0xfc, 0x3f, 0xfc, 0x00, 0x1f, 0xff, 0xff, 0x80, 
0xff, 0xf3, 0xff, 0xff, 0xcf, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x1f, 0xff, 0x00, 0x07, 0xff, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0x3f, 0xfc, 0x3f, 0xfc, 0x00, 0x1f, 0xff, 0xff, 0x80, 
0xff, 0xf1, 0xff, 0xff, 0x8f, 0xff, 0x0f, 0xfe, 0x7f, 0xff, 0xcf, 0xfe, 0x1f, 0xfe, 0x00, 0x07, 0xff, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x3f, 0xfc, 0x00, 0x1f, 0xff, 0xff, 0x80, 
0xff, 0xf1, 0xff, 0xff, 0x8f, 0xff, 0x0f, 0xfe, 0x7f, 0xff, 0xcf, 0xfe, 0x1f, 0xfe, 0x00, 0x07, 0xff, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x3f, 0xfc, 0x00, 0x1f, 0xff, 0xff, 0x80, 
0xff, 0xf0, 0xff, 0xff, 0x0f, 0xff, 0x0f, 0xfe, 0x7f, 0xff, 0xcf, 0xfe, 0x1f, 0xff, 0x00, 0x07, 0xff, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x3f, 0xfc, 0x00, 0x1f, 0xff, 0xff, 0x80, 
0xff, 0xf0, 0xff, 0xff, 0x0f, 0xff, 0x0f, 0xfe, 0x7f, 0xff, 0xcf, 0xfe, 0x1f, 0xff, 0x00, 0x07, 0xff, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xff, 0xff, 0xff, 0xff, 0xfc, 0x3f, 0xfc, 0x00, 0x1f, 0xff, 0xff, 0x80, 
0xff, 0xf0, 0x7f, 0xfe, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x1f, 0xff, 0x00, 0x07, 0xff, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0x3f, 0xfc, 0x3f, 0xfc, 0x00, 0x1f, 0xff, 0xff, 0x80, 
0xff, 0xf0, 0x3f, 0xfc, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x1f, 0xff, 0x00, 0x07, 0xff, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x01, 0x3f, 0xfc, 0x3f, 0xfe, 0x00, 0x1f, 0xff, 0xff, 0x80, 
0xff, 0xf0, 0x3f, 0xfc, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x0f, 0xff, 0x00, 0x07, 0xff, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xbf, 0xfc, 0x3f, 0xfe, 0x00, 0x1f, 0xff, 0xff, 0x80, 
0xff, 0xf0, 0x1f, 0xf8, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x0f, 0xff, 0x80, 0x00, 0x00, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xbf, 0xfc, 0x3f, 0xfe, 0x00, 0x00, 0x03, 0xff, 0x80, 
0xff, 0xf0, 0x0f, 0xf0, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x0f, 0xff, 0x80, 0x00, 0x00, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xbf, 0xfc, 0x1f, 0xff, 0x00, 0x00, 0x03, 0xff, 0x80, 
0xff, 0xf0, 0x0f, 0xf0, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x0f, 0xff, 0xc0, 0x00, 0x00, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xbf, 0xfc, 0x1f, 0xff, 0x00, 0x00, 0x03, 0xff, 0x80, 
0xff, 0xf0, 0x07, 0xe0, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x07, 0xff, 0xe0, 0x00, 0x00, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xbf, 0xfc, 0x1f, 0xff, 0x80, 0x00, 0x03, 0xff, 0x80, 
0xff, 0xf0, 0x07, 0xe0, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x07, 0xff, 0xe0, 0x00, 0x00, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xbf, 0xfc, 0x1f, 0xff, 0xc0, 0x00, 0x03, 0xff, 0x80, 
0xff, 0xf0, 0x03, 0xc0, 0x0f, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x07, 0xff, 0xf8, 0x00, 0x00, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xbf, 0xfc, 0x0f, 0xff, 0xe0, 0x00, 0x03, 0xff, 0x80, 
0xff, 0xf0, 0x01, 0x80, 0x0f, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0xff, 0xfc, 0x00, 0x01, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xbf, 0xfc, 0x0f, 0xff, 0xf0, 0x00, 0x07, 0xff, 0x80, 
0xff, 0xf0, 0x01, 0x80, 0x0f, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0xff, 0xfe, 0x00, 0x07, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xbf, 0xfc, 0x07, 0xff, 0xfc, 0x00, 0x0f, 0xff, 0x80, 
0xff, 0xf0, 0x00, 0x00, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x01, 0xff, 0xff, 0xc0, 0x3f, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xbf, 0xfc, 0x07, 0xff, 0xff, 0x80, 0x7f, 0xff, 0x80, 
0xff, 0xf0, 0x00, 0x00, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0x3f, 0xfc, 0x03, 0xff, 0xff, 0xff, 0xff, 0xff, 0x80, 
0xff, 0xf0, 0x00, 0x00, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0x3f, 0xfc, 0x01, 0xff, 0xff, 0xff, 0xff, 0xff, 0x80, 
0xff, 0xf0, 0x00, 0x00, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x00, 0x7f, 0xff, 0xff, 0xff, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0x80, 
0xff, 0xf0, 0x00, 0x00, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x00, 0x3f, 0xff, 0xff, 0xff, 0xff, 0xe0, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x7f, 0xff, 0xff, 0xff, 0xff, 0x80, 
0xff, 0xf0, 0x00, 0x00, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x00, 0x1f, 0xff, 0xff, 0xff, 0xff, 0x80, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x3f, 0xff, 0xff, 0xff, 0xff, 0x00, 
0xff, 0xf0, 0x00, 0x00, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x00, 0x0f, 0xff, 0xff, 0xff, 0xff, 0x00, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x1f, 0xff, 0xff, 0xff, 0xfc, 0x00, 
0xff, 0xf0, 0x00, 0x00, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x00, 0x03, 0xff, 0xff, 0xff, 0xfc, 0x00, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x0f, 0xff, 0xff, 0xff, 0xf8, 0x00, 
0xff, 0xf0, 0x00, 0x00, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x00, 0x01, 0xff, 0xff, 0xff, 0xf0, 0x00, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x03, 0xff, 0xff, 0xff, 0xe0, 0x00, 
0xff, 0xf0, 0x00, 0x00, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x00, 0x00, 0x7f, 0xff, 0xff, 0xc0, 0x00, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0xff, 0xff, 0xff, 0x80, 0x00, 
0xff, 0xf0, 0x00, 0x00, 0x0f, 0xff, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xfe, 0x00, 0x00, 0x0f, 0xff, 0xfe, 0x00, 0x00, 0x00, 0x00, 0x7f, 0xf0, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0x3f, 0xfc, 0x00, 0x00, 0x3f, 0xff, 0xfc, 0x00, 0x00, 
0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0xe0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0xff, 0xc0, 0x00, 0x00
};
