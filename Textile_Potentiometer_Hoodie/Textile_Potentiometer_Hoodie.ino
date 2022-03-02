// SPDX-FileCopyrightText: 2017 Mikey Sklar for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>

#define PIN 1
// Parameter 1 = number of pixels in strip
// Parameter 2 = Arduino pin number (most are valid)
// Parameter 3 = pixel type flags, add together as needed:
//   NEO_KHZ800  800 KHz bitstream (most NeoPixel products w/WS2812 LEDs)
//   NEO_KHZ400  400 KHz (classic 'v1' (not v2) FLORA pixels, WS2811 drivers)
//   NEO_GRB     Pixels are wired for GRB bitstream (most NeoPixel products)
//   NEO_RGB     Pixels are wired for RGB bitstream (v1 FLORA pixels, not v2)
Adafruit_NeoPixel strip = Adafruit_NeoPixel(8, PIN, NEO_GRB + NEO_KHZ800);

int sensorPin = 1;    // select the input pin for the potentiometer (analog 1 is digital 2)
int sensorValue = 0;  // variable to store the value coming from the sensor
int colorValue = 0;

void setup() {
  // Set internal pullup resistor for sensor pin (analog 1 is digital 2)
  pinMode(2, INPUT_PULLUP); 
  strip.begin();
  strip.setBrightness(40); //adjust brightness here
  strip.show(); // Initialize all pixels to 'off'
}

void loop() {
  // read the value from the sensor:
  sensorValue = analogRead(sensorPin);
  colorValue = map(sensorValue, 0, 1024, 0, 255); //map sensor values from 0-124 to 0-255
  for (int i = 0; i<strip.numPixels(); i++){
    strip.setPixelColor(i, Wheel(colorValue)); //use Wheel function to set color
  }
  strip.show();                
}

// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  if(WheelPos < 85) {
   return strip.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
  } else if(WheelPos < 170) {
   WheelPos -= 85;
   return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  } else {
   WheelPos -= 170;
   return strip.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
}
