// SPDX-FileCopyrightText: 2017 Erin St Blaine for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Code by Erin St Blaine for Adafruit.com
// Full tutorial at https://learn.adafruit.com/glowing-beehive-hairdo-wig/

#include <Adafruit_CircuitPlayground.h>  // add this before the FastLED library to avoid issues
#include <FastLED.h>

#define LED_PIN     6    //led strand is soldered to pin 6
#define CP_PIN      17   //circuit playground's neopixels live on pin 17
#define NUM_LEDS    12   // number of LEDs in my strand
#define NUM_CP      10   // number of neopixels on the circuit playground

// I have purposefully mixed up the color order on the Neopixel strip to 
// quickly and easily add color variety to this code -- This way the strip will always
// show a different color from the light pipe. 

#define COLOR_ORDER GRB   
#define COLOR_ORDER_STRIP  RBG 

uint8_t brightness = 255;  //led strand brightness control
uint8_t cpbrightness = 255;  //circuit playground brightness control

int STEPS = 25;  //makes the rainbow colors more or less spread out
int NUM_MODES = 4;  // change this number if you add or subtract modes

CRGB leds[NUM_LEDS];  //I've set up different arrays for the neopixel strand and the circuit playground
CRGB cp[NUM_CP];      // so that we can control the brightness separately

CRGBPalette16 currentPalette;
TBlendType    currentBlending;

int ledMode = 0;       //Initial mode 
bool leftButtonPressed;
bool rightButtonPressed;

// SOUND REACTIVE SETUP --------------

#define MIC_PIN         A4                                    // Analog port for microphone
#define DC_OFFSET  0                                          // DC offset in mic signal - if unusure, leave 0
                                                              // I calculated this value by serialprintln lots of mic values
#define NOISE     200                                         // Noise/hum/interference in mic signal and increased value until it went quiet
#define SAMPLES   60                                          // Length of buffer for dynamic level adjustment
#define TOP (NUM_LEDS + 2)                                    // Allow dot to go slightly off scale
#define PEAK_FALL 10                                          // Rate of peak falling dot
 
byte
  peak      = 0,                                              // Used for falling dot
  dotCount  = 0,                                              // Frame counter for delaying dot-falling speed
  volCount  = 0;                                              // Frame counter for storing past volume data
int
  vol[SAMPLES],                                               // Collection of prior volume samples
  lvl       = 10,                                             // Current audio level, change this number to adjust sensitivity
  minLvlAvg = 0,                                              // For dynamic adjustment of graph low & high
  maxLvlAvg = 512;


// SETUP -------------------

void setup() {
  Serial.begin(57600);
  CircuitPlayground.begin();
  FastLED.addLeds<WS2812B, LED_PIN, COLOR_ORDER_STRIP>(leds, NUM_LEDS).setCorrection( TypicalLEDStrip );
  FastLED.addLeds<WS2812B, CP_PIN, COLOR_ORDER>(cp, 10).setCorrection( TypicalLEDStrip );
  currentBlending = LINEARBLEND;
  set_max_power_in_volts_and_milliamps(5, 500);               // FastLED 2.1 Power management set at 5V, 500mA

  
}

void loop()  {

  leftButtonPressed = CircuitPlayground.leftButton();
  rightButtonPressed = CircuitPlayground.rightButton();

  if (leftButtonPressed) {  //left button cycles through modes
    clearpixels(); 
    ledMode=ledMode+1;
    delay(300);
    if (ledMode > NUM_MODES){
    ledMode=0;
     }
  }
    if (rightButtonPressed) {   // right button turns all leds off
    ledMode=99;
  
    }
  
 switch (ledMode) {
       case 0: currentPalette = RainbowColors_p; rainbow(); break; 
       case 1: soundreactive(); break; 
       case 2: currentPalette = OceanColors_p; rainbow(); break;                    
       case 3: currentPalette = LavaColors_p; rainbow(); break; 
       case 4: currentPalette = RainbowStripeColors_p; rainbow(); break;    
       case 99: clearpixels(); break;
       
}
}

void clearpixels()
{
  CircuitPlayground.clearPixels();
  for (int i = 0; i < NUM_LEDS; i++) leds[i] = CRGB::Black; 
  for (int i = 0; i < NUM_CP; i++) cp[i] = CRGB::Black;
  FastLED.show();
}

void rainbow()
{
  
  static uint8_t startIndex = 0;
  startIndex = startIndex + 1; /* motion speed */

  FillLEDsFromPaletteColors( startIndex);

  FastLED.show();
  FastLED.delay(20);}

//this bit is in every palette mode, needs to be in there just once
void FillLEDsFromPaletteColors( uint8_t colorIndex)
{ 
  for (int i = 0; i < NUM_LEDS; i++) leds[i] = ColorFromPalette( currentPalette, colorIndex, brightness, currentBlending);
  for (int i = 0; i < NUM_CP; i++) cp[i] = ColorFromPalette( currentPalette, colorIndex, cpbrightness, currentBlending);
    colorIndex += 25;
  
}


void soundreactive() {

  uint8_t  i;
  uint16_t minLvl, maxLvl;
  int      n, height;
   
  n = analogRead(MIC_PIN);                                    // Raw reading from mic
  n = abs(n - 512 - DC_OFFSET);                               // Center on zero
  
  n = (n <= NOISE) ? 0 : (n - NOISE);                         // Remove noise/hum
  lvl = ((lvl * 7) + n) >> 3;                                 // "Dampened" reading (else looks twitchy)
 
  // Calculate bar height based on dynamic min/max levels (fixed point):
  height = TOP * (lvl - minLvlAvg) / (long)(maxLvlAvg - minLvlAvg);
 
  if (height < 0L)       height = 0;                          // Clip output
  else if (height > TOP) height = TOP;
  if (height > peak)     peak   = height;                     // Keep 'peak' dot at top
 
 
  // Color pixels based on rainbow gradient -- led strand
  for (i=0; i<NUM_LEDS; i++) {
    if (i >= height)   leds[i].setRGB( 0, 0,0);
    else leds[i] = CHSV(map(i,0,NUM_LEDS-1,0,255), 255, brightness);  //constrain colors here by changing HSV values
  }
 
  // Draw peak dot  -- led strand
  if (peak > 0 && peak <= NUM_LEDS-1) leds[peak] = CHSV(map(peak,0,NUM_LEDS-1,0,255), 255, brightness);

  // Color pixels based on rainbow gradient  -- circuit playground
  for (i=0; i<NUM_CP; i++) {
    if (i >= height)   cp[i].setRGB( 0, 0,0);
    else cp[i] = CHSV(map(i,0,NUM_CP-1,0,255), 255, cpbrightness);  //constrain colors here by changing HSV values
  }
 
  // Draw peak dot  -- circuit playground
  if (peak > 0 && peak <= NUM_CP-1) cp[peak] = CHSV(map(peak,0,NUM_LEDS-1,0,255), 255, cpbrightness);

// Every few frames, make the peak pixel drop by 1:
 
    if (++dotCount >= PEAK_FALL) {                            // fall rate 
      if(peak > 0) peak--;
      dotCount = 0;
    }
  
  vol[volCount] = n;                                          // Save sample for dynamic leveling
  if (++volCount >= SAMPLES) volCount = 0;                    // Advance/rollover sample counter
 
  // Get volume range of prior frames
  minLvl = maxLvl = vol[0];
  for (i=1; i<SAMPLES; i++) {
    if (vol[i] < minLvl)      minLvl = vol[i];
    else if (vol[i] > maxLvl) maxLvl = vol[i];
  }
  // minLvl and maxLvl indicate the volume range over prior frames, used
  // for vertically scaling the output graph (so it looks interesting
  // regardless of volume level).  If they're too close together though
  // (e.g. at very low volume levels) the graph becomes super coarse
  // and 'jumpy'...so keep some minimum distance between them (this
  // also lets the graph go to zero when no sound is playing):
  if((maxLvl - minLvl) < TOP) maxLvl = minLvl + TOP;
  minLvlAvg = (minLvlAvg * 63 + minLvl) >> 6;                 // Dampen min/max levels
  maxLvlAvg = (maxLvlAvg * 63 + maxLvl) >> 6;                 // (fake rolling average)


show_at_max_brightness_for_power();                         // Power managed FastLED display
  Serial.println(LEDS.getFPS()); 
} 
