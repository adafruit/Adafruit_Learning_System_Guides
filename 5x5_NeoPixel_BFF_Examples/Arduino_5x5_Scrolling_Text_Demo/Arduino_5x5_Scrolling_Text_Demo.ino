// SPDX-FileCopyrightText: 2022 Phil B. for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Example for 5x5 NeoBFF - scrolls a message across the LED matrix.
// Requires Adafruit_GFX, Adafruit_NeoPixel and Adafruit_NeoMatrix libraries.

#include <Adafruit_GFX.h>       // Graphics library
#include <Adafruit_NeoPixel.h>  // NeoPixel library
#include <Adafruit_NeoMatrix.h> // Bridges GFX and NeoPixel
#include <Fonts/TomThumb.h>     // A tiny 3x5 font incl. w/GFX

#define PIN A3

// NeoMatrix declaration for BFF with the power and
// Neo pins at the top (same edge as QT Py USB port):
Adafruit_NeoMatrix matrix(5, 5, PIN,
  NEO_MATRIX_TOP  + NEO_MATRIX_RIGHT +
  NEO_MATRIX_ROWS + NEO_MATRIX_PROGRESSIVE,
  NEO_GRB         + NEO_KHZ800);

// Message to display, and a set of colors to cycle through. Because
// the matrix is only 5 pixels tall, characters with descenders (e.g.
// lowercase p or y) are best avoided. There are even smaller fonts
// but these get progressively less legible. ALL CAPS helps!
const char message[] = "HELLO BFF";
const uint16_t colors[] = {
  matrix.Color(255, 0, 0), matrix.Color(0, 255, 0), matrix.Color(0, 0, 255) };
uint16_t message_width; // Computed in setup() below

void setup() {
  matrix.begin();
  matrix.setBrightness(40);       // Turn down brightness to about 15%
  matrix.setFont(&TomThumb);      // Use custom font
  matrix.setTextWrap(false);      // Allows text to scroll off edges
  matrix.setTextColor(colors[0]); // Start with first color in list
  // To determine when the message has fully scrolled off the left side,
  // get the bounding rectangle of the text. As we only need the width
  // value, a couple of throwaway variables are passed to the bounds
  // function for the other values:
  int16_t  d1;
  uint16_t d2;
  matrix.getTextBounds(message, 0, 0, &d1, &d1, &message_width, &d2);
}

int x = matrix.width();  // Start with message off right edge
int y = matrix.height(); // With custom fonts, y is the baseline, not top
int pass = 0;            // Counts through the colors[] array

void loop() {
  matrix.fillScreen(0);       // Erase message in old position.
  matrix.setCursor(x, y);     // Set new cursor position,
  matrix.print(message);      // draw the message
  matrix.show();              // and update the matrix.
  if(--x < -message_width) {  // Move 1 pixel left. Then, if scrolled off left...
    x = matrix.width();       // reset position off right edge and
    if(++pass >= 3) pass = 0; // increment color in list, rolling over if needed.
    matrix.setTextColor(colors[pass]);
  }
  delay(100); // 1/10 sec pause
}
