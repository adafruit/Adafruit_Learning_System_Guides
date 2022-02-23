// SPDX-FileCopyrightText: 2017 John Edgar Park for Adafruit Industries
//
// SPDX-License-Identifier: MIT

//  NeoPixie Dust Bag by John Edgar Park jpixl.net
//   
//     No fairy costume is complete without a glowing pixie dust bag. 
//     This one uses a touch sensor to cycle through colors on the beautifully twinkling NeoPixel rings, 
//     controlled by the tiny Adafruit GEMMA microcontroller.
//
//     Build instructions: learn.adafruit.com/neopixel-pixie-dust-bag/overview
//
//  Some code based upon Adafruit GEMMA earring code and Adafruit NeoPixel buttoncycler code

#include <Adafruit_NeoPixel.h>  //Include the NeoPixel library

#define NEO_PIN 0        // DIGITAL IO pin for NeoPixel OUTPUT from GEMMA
#define TOUCH_PIN 2      // DIGITAL IO pin for momentary touch sensor INPUT to GEMMA
#define PIXEL_COUNT 30   // Number of NeoPixels connected to GEMMA
#define DELAY_MILLIS 10  // delay between blinks, smaller numbers are faster 
#define DELAY_MULT 8     // Randomization multiplier on the delay speed of the effect
#define BRIGHT 100        // Brightness of the pixels, max is 255

// Parameter 1 = number of pixels in strip
// Parameter 2 = pin number on Arduino (most are valid)
// Parameter 3 = pixel type flags, add together as needed:
//   NEO_RGB     Pixels are wired for RGB bitstream (v1 FLORA pixels, not v2)
//   NEO_GRB     Pixels are wired for GRB bitstream, correct for neopixel stick (most NeoPixel products)
//   NEO_KHZ400  400 KHz bitstream (e.g. FLORA pixels)
//   NEO_KHZ800  800 KHz bitstream (e.g. High Density LED strip), correct for neopixel stick
Adafruit_NeoPixel pixels = Adafruit_NeoPixel(PIXEL_COUNT, NEO_PIN, NEO_GRB + NEO_KHZ800);

bool oldState = HIGH; //sets the initial variable for counting touch sensor button pushes
int showColor = 0;    //color mode for cycling

void setup() {
  pinMode(TOUCH_PIN, INPUT);    //Initialize touch sensor pin as input using external pull-up resistor
  pixels.begin();
  pixels.setBrightness(BRIGHT);
  pixels.show();                //Set all pixels to "off"
}


void loop() {
  int RColor = 100; //color (0-255) values to be set by cylcing touch switch, initially GOLD
  int GColor = 0 ;
  int BColor = 0 ;
  
       if (showColor==0) {//Garden PINK
         RColor = 242;
         GColor = 90;
         BColor = 255; 
       }
       if (showColor==1) {//Pixie GOLD
         RColor = 255;
         GColor = 222;
         BColor = 30; 
       }
       if (showColor==2) {//Alchemy BLUE
         RColor = 50;
         GColor = 255;
         BColor = 255; 
       }
       if (showColor==3) {//Animal ORANGE
         RColor = 255;
         GColor = 100;
         BColor = 0; 
       }
       if (showColor==4) {//Tinker GREEN
         RColor = 0;
         GColor = 255;
         BColor = 40; 
       }
  
  //sparkling
  int p = random(PIXEL_COUNT); //select a random pixel
  pixels.setPixelColor(p,RColor,GColor,BColor); //color value comes from cycling state of momentary switch
  pixels.show();
  delay(DELAY_MILLIS * random(DELAY_MULT) ); //delay value randomized to up to DELAY_MULT times longer
  pixels.setPixelColor(p, RColor/10, GColor/10, BColor/10); //set to a dimmed version of the state color
  pixels.show();
  pixels.setPixelColor(p+1, RColor/15, GColor/15, BColor/15); //set a neighbor pixel to an even dimmer value
  pixels.show();
  
  //button check to cycle through color value sets
  bool newState = digitalRead(TOUCH_PIN); //Get the current button state
  // Check if state changed from high to low (button press).
  if (newState == LOW && oldState == HIGH) {
    // Short delay to debounce button.
    delay(20);
    // Check if button is still low after debounce.
    newState = digitalRead(TOUCH_PIN);
    if (newState == LOW) {
      showColor++;
      if (showColor > 4)
        showColor=0;
       }   
  }
  // Set the last button state to the old state.
  oldState = newState;  
  
}
