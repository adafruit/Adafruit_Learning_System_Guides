// SPDX-FileCopyrightText: 2018 Erin St. Blaine for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include "Adafruit_FreeTouch.h"
#include "FastLED.h"

#define CAPTOUCH_PIN A1
#define NEOPIXEL_PIN 1
#define LED_PIN 0
#define NUM_LEDS    12

#define LED_TYPE    WS2812
#define COLOR_ORDER GRB
CRGB leds[NUM_LEDS];

int BRIGHTNESS=150;
int touch = 500;    // Change this variable to something between your capacitive touch serial readouts for on and off

long oldState = 0;
int gHue=0;

Adafruit_FreeTouch qt_1 = Adafruit_FreeTouch(CAPTOUCH_PIN, OVERSAMPLE_4, RESISTOR_50K, FREQ_MODE_NONE);
//Adafruit_FreeTouch qt_2 = Adafruit_FreeTouch(A2, OVERSAMPLE_4, RESISTOR_50K, FREQ_MODE_NONE);



void setup() {
  Serial.begin(115200);

  if (! qt_1.begin())  
    Serial.println("Failed to begin qt on pin A1");
  
   pinMode(LED_PIN, OUTPUT);  //initialize the LED pin

   FastLED.addLeds<WS2812, NEOPIXEL_PIN, COLOR_ORDER>(leds, NUM_LEDS);  // Set up neopixels with FastLED
   FastLED.setBrightness(BRIGHTNESS);
   FastLED.setMaxPowerInVoltsAndMilliamps(3,350);  //Constrain FastLED's power usage
}

void loop() {
  
  Serial.print(qt_1.measure());
  Serial.write(' ');
  checkpress();
  delay(20);
}

void checkpress() {

// Get current button state.
 
    long newState =  qt_1.measure();  
    Serial.println(qt_1.measure());
   if (newState > touch && oldState < touch) {
    // Short delay to debounce button.
    delay(20);
    // Check if button is still low after debounce.
    long newState =  qt_1.measure(); }

 
  if (newState > touch ) {  
     dark();
     digitalWrite(LED_PIN, HIGH);
     delay(20);
    }

    else {
      rainbow();
      digitalWrite(LED_PIN, LOW);
      delay(20);
    }

   
    
  // Set the last button state to the old state.
  oldState = newState;

  // do some periodic updates
  EVERY_N_MILLISECONDS( 20 ) { gHue++; } // slowly cycle the "base color" through the rainbow
} 

void rainbow() 
{
  // FastLED's built-in rainbow generator
  fill_rainbow( leds, NUM_LEDS, gHue, 7);
  FastLED.show();
  delay(20);
  
}

void dark()
{ 
  for(int i = 0; i < NUM_LEDS; i++) { 
  leds[i] = CRGB::Black; 
  FastLED.show();
  delay(20);
}
}

