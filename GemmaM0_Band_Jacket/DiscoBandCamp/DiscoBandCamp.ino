// SPDX-FileCopyrightText: 2019 Amelia T
//
// SPDX-License-Identifier: MIT

//    Sketch for "DiscoBandCamp" by Amelia T, 2019
//    See Adafruit guide & XYmap.h for pixel map for more information
//    Use Adafruit Gemma M0: 60 pixels to D0, 60 pixels to D1, & button to D2 & GND
//
//    This sketch shows mapping pixels on an irregular matrix and provides 
//    various examples from RGB Shades Demo Code & the FastLED demo library.
//    Can easily incorporate other examples or create your own!
//    
//    To use:
//    Press the button to cycle through available effects shown on the functions list
//    Press and hold the button (>one second) to cycle through five brightness levels
//   
//    Special credit to RGB Shades Demo Code Copyright (c) 2015 macetech LLC
//    This software is provided under the MIT License (see license.txt)
//    Special credit to Mark Kriegsman for XY mapping code


//  Pins on Adafruit Gemma M0
#define LEFT_PIN    1     // Visual Left (LEDs on the wearers right) connected to D1
#define NUM_LEFT    60    // number of LEDs connected on the Left
#define RIGHT_PIN   0     // Visual Right (LEDs on the wearers left) connected to D0
#define NUM_RIGHT   60    // number of LEDs connected on the Right

//  Color order (Green/Red/Blue)
#define COLOR_ORDER GRB
#define CHIPSET     WS2812B

//  Global maximum brightness value, maximum 255
#define MAXBRIGHTNESS 100
#define STARTBRIGHTNESS 32

//  Hue time (milliseconds between hue increments)
#define hueTime 30

// Include FastLED library and other useful files
#include <FastLED.h>
#include "XYmap.h"
#include "utils.h"
#include "effects.h"
#include "buttons.h"
extern XYMap myXYMap;

CRGB leds[ NUM_LEDS ];

uint16_t XY(uint16_t x, uint16_t y, uint16_t width, uint16_t height)
{
  (void)width;
  (void)height;
  // any out of bounds address maps to the first hidden pixel
  if( (x >= kMatrixWidth) || (y >= kMatrixHeight) ) {
    return (LAST_VISIBLE_LED + 1);
  }

//   On the visual left of DiscoBandCamp, wearers right
//     +------------------------------------------ 
//   | 10   9   8   7   6   5   4   3   2   1   0
//   | .    20  19  18  17  16  15  14  13  12  11
//   | .    .   29  28  27  26  25  24  23  22  21
//   | .    .   .   37  36  35  34  33  32  31  30  
//   | .    .   .   .   44  43  42  41  40  39  38
//   | .    .   .   .   .   50  49  48  47  46  45
//   | .    .   .   .   .   .   55  54  53  52  51  
//   | .    .   .   .   .   .   .   59  58  57  56

//this is how DiscoBandCamp works
  const uint8_t JacketTable[] = {
10, 9,  8,  7,  6,  5,  4,  3,  2,  1,  0,  145,
153,60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 
120,11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 146,  
154,80, 79, 78, 77, 76, 75, 74, 73, 72, 71, 182, 
121,127,21, 22, 23, 24, 25, 26, 27, 28, 29, 147, 
155,89, 88, 87, 86, 85, 84, 83, 82, 81, 176,183, 
122,128,133,30, 31, 32, 33, 34, 35, 36, 37, 148,  
156,97, 96, 95, 94, 93, 92, 91, 90, 171,177,184, 
123,129,134,135,38, 39, 40, 41, 42, 43, 44, 149,  
157,104,103,102,101,100,99, 98, 167,172,178,185, 
124,130,134,136,139,45, 46, 47, 48, 49, 50, 150,  
158,110,109,108,107,106,105,164,168,173,179,186, 
125,131,134,137,140,142,51, 52, 53, 54, 55, 151,  
159,115,114,113,112,111,162,165,169,174,180,187, 
126,132,134,138,141,143,144,56, 57, 58, 59, 152,  
160,119,118,117,116,161,163,166,170,175,181,188,
  };

  uint8_t i = (y * kMatrixWidth) + x;
  uint8_t j = JacketTable[i];
  return j;
}
// Instantiate an XYMap object
XYMap myXYMap = XYMap::constructWithUserFunction(kMatrixWidth, kMatrixHeight, XY);

// list of Functions:
functionList effectList[] = {SolidRed,    //all pixels solid red
                             swirly,      //glittery swirly patterns
                             NoisePlusPalette,   //NoisePlusPalette fastLED example sketch
                             confetti,    //confetti with a random FastLED palette
                             threeSine,   //Triple Sine Waves
                             colorFill,   // Fills saturated colors into the array from alternating directions
                             plasma,      //pretty rainbow plasma animation
                             rider,       //Scanning pattern left/right, using global hue cycle
                             myConfetti,  //confetti in with my pink/orange palette
                             slantBars,   //slanted bars
                             sideRain,    // Random pixels scroll sideways, using current hue
                             SolidWhite,  //all pixels solid white, great for portopotty visits!       
                            };

const byte numEffects = (sizeof(effectList)/sizeof(effectList[0]));

// Runs one time at the start of the program (power up or reset)
void setup() {

//Add the onboard Strip on the Right and Left to create a single array
  FastLED.addLeds<CHIPSET, LEFT_PIN, COLOR_ORDER>(leds, 0, NUM_LEFT);
  FastLED.addLeds<CHIPSET, RIGHT_PIN, COLOR_ORDER>(leds, NUM_LEFT, NUM_RIGHT);

  // set global brightness value
  FastLED.setBrightness( scale8(currentBrightness, MAXBRIGHTNESS) );

  // configure input buttons
  pinMode(MODEBUTTON, INPUT_PULLUP);
}


// Runs over and over until power off or reset
void loop()
{
  currentMillis = millis(); // save the current timer value
  updateButtons();          // read, debounce, and process the buttons
  doButtons();              // perform actions based on button state

  // increment the global hue value every hueTime milliseconds
  if (currentMillis - hueMillis > hueTime) {
    hueMillis = currentMillis;
    hueCycle(1); // increment the global hue value
  }

  // run the currently selected effect every effectDelay milliseconds
  if (currentMillis - effectMillis > effectDelay) {
    effectMillis = currentMillis;
    effectList[currentEffect](); // run the selected effect function
    random16_add_entropy(1); // make the random values a bit more random-ish
  }

  // run a fade effect too if the confetti or myConfetti is running:
  if (effectList[currentEffect] == confetti or myConfetti) fadeAll(1);

  FastLED.show(); // send the contents of the led memory to the LEDs
}
