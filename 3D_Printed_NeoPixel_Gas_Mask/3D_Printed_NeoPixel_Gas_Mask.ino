# SPDX-FileCopyrightText: 2017 Phil Burgess for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
#include <Adafruit_NeoPixel.h>

#define PIN       0
#define NUM_LEDS 24

Adafruit_NeoPixel pixels = Adafruit_NeoPixel(NUM_LEDS, PIN);

uint8_t  mode   = 0,        // Current animation effect
         offset = 0;        // Position of spinner animation
uint32_t color  = 0xFF0000; // Starting color = red
uint32_t prevTime;          // Time of last animation mode switch

void setup() {
  pixels.begin();
  pixels.setBrightness(85); // 1/3 brightness
  prevTime = millis();      // Starting time
}

void loop() {
  uint8_t  i;
  uint32_t t;

  switch(mode) {

   case 0: // Random sparkles - just one LED on at a time!
    i = random(NUM_LEDS);           // Choose a random pixel
    pixels.setPixelColor(i, color); // Set it to current color
    pixels.show();                  // Refresh LED states
    // Set same pixel to "off" color now but DON'T refresh...
    // it stays on for now...both this and the next random
    // pixel will be refreshed on the next pass.
    pixels.setPixelColor(i, 0);
    delay(10);                      // 10 millisecond delay
    break;
 
   case 1: // Spinny wheel
    // A little trick here: pixels are processed in groups of 8
    // (with 2 of 8 on at a time), NeoPixel rings are 24 pixels
    // (8*3) and 16 pixels (8*2), so we can issue the same data
    // to both rings and it appears correct and contiguous
    // (also, the pixel order is different between the two ring
    // types, so we get the reversed motion on #2 for free).
    for(i=0; i<NUM_LEDS; i++) {    // For each LED...
      uint32_t c = 0;              // Assume pixel will be "off" color
      if(((offset + i) & 7) < 2) { // For each 8 pixels, 2 will be...
        c = color;                 // ...assigned the current color
      }
      pixels.setPixelColor(i, c);  // Set color of pixel 'i'
    }
    pixels.show();                 // Refresh LED states
    delay(50);                     // 50 millisecond delay
    offset++;                      // Shift animation by 1 pixel on next frame
    if(offset >= 8) offset = 0;    // Reset offset every 8 pixels
    break;

    // More animation modes could be added here!
  }

  t = millis();                    // Current time in milliseconds
  if((t - prevTime) > 8000) {      // Every 8 seconds...
    mode++;                        // Advance to next animation mode
    if(mode > 1) {                 // End of modes?
      mode = 0;                    // Start over from beginning
      color >>= 8;                 // Next color R->G->B
      if(!color) color = 0xFF0000; // Preiodically reset to red
    }
    pixels.clear();                // Set all pixels to 'off' state
    prevTime = t;                  // Record the time of the last mode change
  }
}
