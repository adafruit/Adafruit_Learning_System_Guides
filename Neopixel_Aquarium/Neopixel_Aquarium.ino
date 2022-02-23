// SPDX-FileCopyrightText: 2018 Erin St Blaine for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Code by Erin St. Blaine for Adafruit Industries
// NeoPixel Aquarium Tutorial: https://learn.adafruit.com/neopixel-aquarium-with-submersible-lights/
// For QT Py board

#include "Adafruit_FreeTouch.h"
#include "FastLED.h"

#define CAPTOUCH_PIN A2  //A2 capacitive touch pin
#define CAPTOUCH_PIN2 A3  //A3 capacitive touch pin
#define NEOPIXEL_PIN A1  //A1 neopixel pin
#define NUM_LEDS    164  //how many pixels total

#define LED_TYPE    WS2812
#define COLOR_ORDER GRB
CRGB leds[NUM_LEDS];   //LED array 

// These variables will affect the way the gradient animation looks.  Feel free to mess with them.
int SPEEDO = 10;          
int STEPS = 50;         
int HUE = 0;            
int SATURATION = 255;  
int COLORCHANGE = 50;        
int BRIGHTNESS = 200;     
int onBright = 200;

// Calibrating your capacitive touch sensitivity: Change this variable to something between your capacitive touch serial readouts for on and off
int touch = 500;    

long oldState = 0;
long offState = 0;

// set up capacitive touch button using the FreeTouch library
Adafruit_FreeTouch qt_1 = Adafruit_FreeTouch(CAPTOUCH_PIN, OVERSAMPLE_4, RESISTOR_50K, FREQ_MODE_NONE);
Adafruit_FreeTouch qt_2 = Adafruit_FreeTouch(CAPTOUCH_PIN2, OVERSAMPLE_4, RESISTOR_50K, FREQ_MODE_NONE);

TBlendType    currentBlending;
CRGBPalette16 currentPalette;


void setup() {
  Serial.begin(115200);

  if (! qt_1.begin())  
   Serial.println("Failed to begin qt on pin A2");
  if (! qt_2.begin())  
   Serial.println("Failed to begin qt on pin A3");
   FastLED.addLeds<WS2812, NEOPIXEL_PIN, COLOR_ORDER>(leds, NUM_LEDS);  // Set up neopixels with FastLED
   FastLED.setBrightness(BRIGHTNESS); // set global brightness
   FastLED.setMaxPowerInVoltsAndMilliamps(3,350);  //Constrain FastLED's power usage
}

void loop() {
  
  Serial.print(qt_1.measure());
  Serial.write(' ');
  checkpress();   //check to see if the button's been pressed
  delay(20);
}

void checkpress() {

// Get current button state.
 
    long newState =  qt_1.measure(); 
    long switchState = qt_2.measure(); 
    Serial.println(qt_1.measure());
    Serial.println(qt_2.measure());
   if (newState > touch && oldState < touch) {
    // Short delay to debounce button.
    delay(500);
    // Check if button is still low after debounce.
    long newState =  qt_1.measure(); 
    long switchState = qt_2.measure();
    }
    if (switchState > touch && offState < touch) {
    // Short delay to debounce button.
    delay(500);
    // Check if button is still low after debounce.
    long newState =  qt_1.measure(); 
    }

 
  if (newState > touch ) {  
     BRIGHTNESS = onBright;
     HUE=HUE+COLORCHANGE;  // change the hue by a specified amount each time the cap touch pad is activated
  if (HUE > 255){
    HUE=0;}
   Gradient();
    }
//  if (HUE==250) {
//    dark();
//  }
    else {
      Gradient();
      
    }
   if (switchState > touch) {
      if (BRIGHTNESS == onBright){
        dark();
        switchState = 0;
        BRIGHTNESS = 0;
      }
      else {
        BRIGHTNESS = onBright;
      }
   }

   
    
  // Set the last button state to the old state.
  oldState = newState;
  offState = switchState;

} 



// GRADIENT --------------------------------------------------------------
void Gradient()
{
  SetupGradientPalette();

  static uint8_t startIndex = 0;
  startIndex = startIndex - 1;  // motion speed

  FillLEDsFromPaletteColors( startIndex);
  FastLED.show();
  FastLED.delay(SPEEDO);
}

// adjust hue, saturation and brightness values here to make a pleasing gradient

void SetupGradientPalette()
{
  CRGB light = CHSV( HUE + 25, SATURATION - 20, BRIGHTNESS);
  CRGB lightmed = CHSV (HUE + 15, SATURATION - 10, BRIGHTNESS-50);
  CRGB medium = CHSV ( HUE + 10, SATURATION - 15, BRIGHTNESS);
  CRGB dark  = CHSV( HUE, SATURATION, BRIGHTNESS);
  CRGB black = CHSV (HUE, SATURATION, 0);
  
  currentPalette = CRGBPalette16( 
    black,  light,  light,  light,
    lightmed, lightmed, lightmed,  medium,
    medium,  medium,  medium,  dark,
    dark, dark, dark,  black );
}

void FillLEDsFromPaletteColors( uint8_t colorIndex)
{
  uint8_t brightness = BRIGHTNESS;
  
  for( int i = 0; i < NUM_LEDS; i++) {
    leds[i] = ColorFromPalette( currentPalette, colorIndex, brightness, currentBlending);
    colorIndex += STEPS;
  }
}

void dark()
{ 
  for(int i = 0; i < NUM_LEDS; i++) { 
  leds[i] = CRGB::Black; 
  FastLED.show();
  delay(20);
}
}
