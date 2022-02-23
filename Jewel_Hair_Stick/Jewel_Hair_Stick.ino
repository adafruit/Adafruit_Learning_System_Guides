// SPDX-FileCopyrightText: 2017 Leslie Birch for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/* 
Jewel Hairstick by Leslie Birch for Adafruit Industries
Based on NeoPixel Library by Adafruit
*/
 
// This section is NeoPixel Variables
 
#include <Adafruit_NeoPixel.h>
 
#define PIN 1
 
// Parameter 1 = number of pixels in strip
// Parameter 2 = pin number (most are valid)
// Parameter 3 = pixel type flags, add together as needed:
//   NEO_KHZ800  800 KHz bitstream (most NeoPixel products w/WS2812 LEDs)
//   NEO_KHZ400  400 KHz (classic 'v1' (not v2) FLORA pixels, WS2811 drivers)
//   NEO_GRB     Pixels are wired for GRB bitstream (most NeoPixel products)
//   NEO_RGB     Pixels are wired for RGB bitstream (v1 FLORA pixels, not v2)
Adafruit_NeoPixel strip = Adafruit_NeoPixel(7, 1, NEO_GRB + NEO_KHZ800);

//You can have fun here changing the colors for the code
uint32_t color1 = strip.Color(236, 79, 100); //Salmon Pink
uint32_t color2 = strip.Color(246, 216, 180); //Cream
uint32_t color3 = strip.Color(174, 113, 208); //Lavendar
uint32_t color4 = strip.Color(182, 31, 40); //Red
uint32_t color5 = strip.Color(91, 44, 86); //Purple


  
void setup() {
   //This is for Neopixel Setup
  strip.begin();
  strip.show(); // Initialize all pixels to 'off'
}
 
void loop() 
{
  
    
  strip.setBrightness(30);
  // the first number is the pixel number for Jewel. O is the center one 
  strip.setPixelColor(1, color1); 
  strip.setPixelColor(2, color1); 
  strip.setPixelColor(3, color1); 
  strip.setPixelColor(4, color1); 
  strip.setPixelColor(5, color1); 
  strip.setPixelColor(6, color1); 
  strip.setPixelColor(0, color2); 
  
  strip.show();
  delay(3000);
  
  
  strip.setPixelColor(1, color2); 
  strip.setPixelColor(2, color2); 
  strip.setPixelColor(3, color2); 
  strip.setPixelColor(4, color2); 
  strip.setPixelColor(5, color2); 
  strip.setPixelColor(6, color2); 
  strip.setPixelColor(0, color3); 
  
  strip.show();
  delay(3000);
  
  strip.setPixelColor(1, color3); 
  strip.setPixelColor(2, color3); 
  strip.setPixelColor(3, color3);
  strip.setPixelColor(4, color3); 
  strip.setPixelColor(5, color3); 
  strip.setPixelColor(6, color3); 
  strip.setPixelColor(0, color4); 
  
  strip.show();
  delay(3000);
  
  strip.setPixelColor(1, color4); 
  strip.setPixelColor(2, color4); 
  strip.setPixelColor(3, color4); 
  strip.setPixelColor(4, color4); 
  strip.setPixelColor(5, color4); 
  strip.setPixelColor(6, color4); 
  strip.setPixelColor(0, color5); 
  
  strip.show();
  delay(3000);
  
  strip.setPixelColor(1, color5); 
  strip.setPixelColor(2, color5); 
  strip.setPixelColor(3, color5);
  strip.setPixelColor(4, color5); 
  strip.setPixelColor(5, color5); 
  strip.setPixelColor(6, color5); 
  strip.setPixelColor(0, color1); 
  
  strip.show();
  delay(3000);
  
}
