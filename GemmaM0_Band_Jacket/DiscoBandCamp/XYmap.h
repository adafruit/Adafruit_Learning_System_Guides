// SPDX-FileCopyrightText: 2019 Anne Barela for Adafruit Industries
//
// SPDX-License-Identifier: MIT

//  Helper functions for a two-dimensional XY matrix of pixels.
//  Special credit to Mark Kriegsman for RGB Shades Kickstarter 2014-10-18
//  https://www.kickstarter.com/projects/macetech/rgb-led-shades
//
//  This special 'XY' code lets you program as a plain matrix.
//
//  Writing to and reading from the 'holes' in the layout is 
//  also allowed; holes retain their data, it's just not displayed.
//
//  You can also test to see if you're on or off the layout
//  like this
//  if( XY(x,y) > LAST_VISIBLE_LED ) { ...off the layout...}
//
//  X and Y bounds checking is also included, so it is safe
//  to just do this without checking x or y in your code:
//  leds[ XY(x,y) ] == CRGB::Red;
//  All out of bounds coordinates map to the first hidden pixel.
//
//  XY(x,y) takes x and y coordinates and returns an LED index number,
//  for use like this:  leds[ XY(x,y) ] == CRGB::Red;

#ifndef XYMAP_H
#define XYMAP_H

#include <FastLED.h>

// Parameters for width and height
const uint8_t kMatrixWidth = 24;
const uint8_t kMatrixHeight = 8;
const uint8_t kBorderWidth = 2; //for swirly

#define NUM_LEDS (kMatrixWidth * kMatrixHeight)
extern CRGB leds[ NUM_LEDS ];

// This function will return the right 'led index number' for 
// a given set of X and Y coordinates on DiscoBandCamp
// This code, plus the supporting 80-byte table is much smaller 
// and much faster than trying to calculate the pixel ID with code.
#define LAST_VISIBLE_LED 119
uint16_t XY(uint16_t x, uint16_t y, uint16_t width, uint16_t height);
extern XYMap myXYMap;
#endif
