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
