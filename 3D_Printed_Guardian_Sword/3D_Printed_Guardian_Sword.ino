S# SPDX-FileCopyrightText: 2017 Mikey Sklar for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
#include <Adafruit_NeoPixel.h>
#ifdef __AVR__
  #include <avr/power.h>
#endif

// Which pin on the Arduino is connected to the NeoPixels?
// On a Trinket or Gemma we suggest changing this to 1
#define PIN            4

// Color Segments
#define APIXELS      14 // number of first orange pixels 
#define BPIXELS      84 // number of blue pixels
#define CPIXELS      93 // second orange pixels

// When we setup the NeoPixel library, we tell it how many pixels, and which pin to use to send signals.
// Note that for older NeoPixel strips you might need to change the third parameter--see the strandtest
// example for more information on possible values.
Adafruit_NeoPixel pixels = Adafruit_NeoPixel(93, PIN, NEO_GRB + NEO_KHZ800);

int delayval = 10; // delay for half a second

void setup() {
  // This is for Trinket 5V 16MHz, you can remove these three lines if you are not using a Trinket
#if defined (__AVR_ATtiny85__)
  if (F_CPU == 16000000) clock_prescale_set(clock_div_1);
#endif
  // End of trinket special code

  pixels.begin(); // This initializes the NeoPixel library.
}

void loop() {

  // For the first 14 pixels, make them orange, starting from pixel number 0.
  for(int i=0;i<APIXELS;i++){
    pixels.setPixelColor(i, pixels.Color(255,50,0)); // Set Pixels to Orange Color
    pixels.show(); // This sends the updated pixel color to the hardware.
    delay(delayval); // Delay for a period of time (in milliseconds).
  }

  // Fill up 84 pixels with blue, starting with pixel number 14.
  for(int i=14;i<BPIXELS;i++){
    pixels.setPixelColor(i, pixels.Color(0,250,200)); // Set Pixels to Blue Color
    pixels.show(); // This sends the updated pixel color to the hardware.
    delay(delayval); // Delay for a period of time (in milliseconds).

  }
  
  // Fill up 9 pixels with orange, starting from pixel number 84.
  for(int i=84;i<CPIXELS;i++){
    pixels.setPixelColor(i, pixels.Color(250,50,0)); //Set Pixels to Orange Color
    pixels.show(); // This sends the updated pixel color to the hardware.
    delay(delayval); // Delay for a period of time (in milliseconds).
  }
}
