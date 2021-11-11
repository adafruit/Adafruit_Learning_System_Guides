// SPDX-FileCopyrightText: 2021 Irete Hamdani for Adafruit Industries
//
// SPDX-License-Identifier: MIT
//
#include <FastLED.h>
#include <Wire.h>
#include "Adafruit_TCS34725.h"

#define DATA_PIN   1
#define LED_TYPE    WS2812B
#define COLOR_ORDER GRB
#define NUM_LEDS    180     // Change this to reflect the number of LEDs you have
#define BRIGHTNESS  255     // Set Brightness here 255

CRGB leds[NUM_LEDS];
 
// color sensor
// our RGB -> eye-recognized gamma color
byte gammatable[256];
//used to store color sensor received color
uint16_t clear, red, green, blue;

// color sensor
Adafruit_TCS34725 tcs = Adafruit_TCS34725(TCS34725_INTEGRATIONTIME_50MS, TCS34725_GAIN_4X);

void setup() {
  delay(3000); // 3 second delay for recovery

  // tell FastLED about the LED strip configuration
  FastLED.addLeds<LED_TYPE,DATA_PIN, COLOR_ORDER>(leds, NUM_LEDS)
    .setCorrection(TypicalLEDStrip) // cpt-city palettes have different color balance
    .setDither(BRIGHTNESS < 255);
 
  // set master brightness control
  FastLED.setBrightness(BRIGHTNESS);

  tcs.begin();

  // helps convert RGB colors to what humans see
  for (int i=0; i<256; i++) {
    float x = i;
    x /= 255;
    x = pow(x, 2.5);
    x *= 255;
      
    gammatable[i] = x;      
  }

  for (int i=0; i<3; i++){ //this sequence flashes the first pixel three times none/white as a countdown to the color reading.
    leds[16] = CRGB::Black; 
    FastLED.show(); 
    delay(1000);
    leds[16] = CRGB::White; 
    FastLED.show(); 
    delay(500);
  }

  // turn on LED
  tcs.setInterrupt(false);        
  delay(60);  // takes 50ms to read 
  
  tcs.getRawData(&red, &green, &blue, &clear);

  tcs.setInterrupt(true);  // turn off LED
}

void loop()
{
  // Figure out some basic hex code for visualization
  uint32_t sum = red;
  sum += green;
  sum += blue;
  //sum += clear; // clear contains RGB already so no need to re-add it
  
  float r, g, b;
  r = red; r /= sum;
  g = green; g /= sum;
  b = blue; b /= sum;
  r *= 256; g *= 256; b *= 256;
  
  CRGBPalette16 gTargetPalette (
   CRGB (gammatable[(int)r], gammatable[(int)g], gammatable[(int)b]));
  
  colorwaves( leds, NUM_LEDS, gTargetPalette);//gCurrentPalette);
 
  FastLED.show();
  FastLED.delay(20);
}
 
// This function draws color waves with an ever-changing,
// widely-varying set of parameters, using a color palette.
void colorwaves( CRGB* ledarray, uint16_t numleds, CRGBPalette16& palette) 
{
  static uint16_t sPseudotime = 0;
  static uint16_t sLastMillis = 0;
  static uint16_t sHue16 = 0;
 
  uint8_t sat8 = beatsin88( 87, 220, 250);
  uint8_t brightdepth = beatsin88( 341, 96, 224);
  uint16_t brightnessthetainc16 = beatsin88( 203, (25 * 256), (40 * 256));
  uint8_t msmultiplier = beat8(147); //beatsin88(147, 23, 60); - creates a more dynamic pattern [IH]
 
  uint16_t hue16 = sHue16;//gHue * 256;
  uint16_t hueinc16 = beatsin88(113, 300, 1500);
  
  uint16_t ms = millis();
  uint16_t deltams = ms - sLastMillis ;
  sLastMillis  = ms;
  sPseudotime += deltams * msmultiplier;
  sHue16 += deltams * beatsin88( 400, 5,9);
  uint16_t brightnesstheta16 = sPseudotime;
  
  for( uint16_t i = 0 ; i < numleds; i++) {
    hue16 += hueinc16;
    uint8_t hue8 = hue16 / 256;
    uint16_t h16_128 = hue16 >> 7;
    if( h16_128 & 0x100) {
      hue8 = 255 - (h16_128 >> 1);
    } else {
      hue8 = h16_128 >> 1;
    }
 
    brightnesstheta16  += brightnessthetainc16;
    uint16_t b16 = sin16( brightnesstheta16  ) + 32768;
 
    uint16_t bri16 = (uint32_t)((uint32_t)b16 * (uint32_t)b16) / 65536;
    uint8_t bri8 = (uint32_t)(((uint32_t)bri16) * brightdepth) / 65536;
    bri8 += (255 - brightdepth);
    
    uint8_t index = hue8;
    //index = triwave8( index);
    index = scale8( index, 240);
 
    CRGB newcolor = ColorFromPalette( palette, index, bri8);
 
    uint16_t pixelnumber = i;
    pixelnumber = (numleds-1) - pixelnumber;
    
    nblend( ledarray[pixelnumber], newcolor, 128);
  }
}
