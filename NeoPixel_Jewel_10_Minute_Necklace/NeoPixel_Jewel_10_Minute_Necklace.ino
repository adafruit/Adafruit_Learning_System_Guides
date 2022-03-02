// SPDX-FileCopyrightText: 2017 Mikey Sklar for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>

#define PIN 1

Adafruit_NeoPixel pixels = Adafruit_NeoPixel(40, PIN);

uint8_t  mode   = 0, // Current animation effect
         offset = 0;
uint32_t color  = 0X00A4B3; // Starting color
uint32_t prevTime; 

void setup() {
  pixels.begin();
  pixels.setBrightness(40); // 1/3 brightness
  prevTime = millis();
}

void loop() {
  uint8_t  i;
  uint32_t t;

  switch(mode) {
    
   case 0: //rainbow hold
    rainbowHold(20);
    delay(500);
    break;
    
   case 1: //rainbow cycle slow
    rainbowCycleslow(20);
    delay(50);
    break;
       
   case 2: //rainbow cycle fast 
    rainbowCycle(5);
    delay(50);
    break;
  }

  t = millis();
  if((t - prevTime) > 8000) {      // Every 8 seconds...
    mode++;                        // Next mode
    if(mode > 3) {                 // End of modes?
      mode = 0;                    // Start modes over
      color >>= 8;                 // Next color R->G->B
      if(!color) color = 0xB300A4; // Reset color
    }
    for(i=0; i<32; i++) pixels.setPixelColor(i, 0);
    prevTime = t;
    
  }

  
}
void rainbow(uint8_t wait) {
  uint16_t i, j;

  for(j=0; j<256; j++) {
    for(i=0; i<pixels.numPixels(); i++) {
      pixels.setPixelColor(i, Wheel((i+j) & 255));
    }
    pixels.show();
    delay(wait);
  }
}

void rainbowCycle(uint8_t wait) {
  uint16_t r, j;

  for(j=0; j<256*6; j++) { // 6 cycles of all colors on wheel
    for(r=0; r< pixels.numPixels(); r++) {
      pixels.setPixelColor(r, Wheel(((r * 256 / pixels.numPixels()) + j) & 255));
    }
    pixels.show();
    delay(wait);
  }
}
void rainbowCycleslow(uint8_t wait) {
  uint16_t r, j;

  for(j=0; j<256*3; j++) { // 3 cycles of all colors on wheel
    for(r=0; r< pixels.numPixels(); r++) {
      pixels.setPixelColor(r, Wheel(((r * 256 / pixels.numPixels()) + j) & 255));
    }
    pixels.show();
    delay(wait);
  }
}
void rainbowHold(uint8_t wait) {
  uint16_t r, j;

  for(j=0; j<256*1; j++) { // 3 cycles of all colors on wheel
    for(r=0; r< pixels.numPixels(); r++) {
      pixels.setPixelColor(r, Wheel(((r * 256 / pixels.numPixels()) + j) & 255));
    }
    pixels.show();
    delay(wait);
  }
}

// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  if(WheelPos < 85) {
   return pixels.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
  } else if(WheelPos < 170) {
   WheelPos -= 85;
   return pixels.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  } else {
   WheelPos -= 170;
   return pixels.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
}

