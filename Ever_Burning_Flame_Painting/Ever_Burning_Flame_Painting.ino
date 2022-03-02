// SPDX-FileCopyrightText: 2018 Erin St Blaine for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_CircuitPlayground.h>  
#include <FastLED.h> // add FastLED library AFTER Circuit Playground library to avoid issues

#define STRIP1_DATA_PIN 9  // define data pins for all 3 LED strips
#define STRIP2_DATA_PIN 12
#define STRIP3_DATA_PIN 6

#define COLOR_ORDER GRB

#define NUM_LEDS    80     // how many LEDs in each strip
#define NUM_LEDS_2   52
#define NUM_LEDS_3  69

#define CAP_THRESHOLD   50       //Change capacitive touch sensitivitiy here
#define FRAMES_PER_SECOND 35    // faster or slower burning fire

#define COOLING  55  // Less cooling = taller flames. Default 55, suggested range 20-100
#define SPARKING 50 //Higher chance = more roaring fire.  Default 120, suggested range 50-200
#define BRIGHTNESS 125  // set global brightness here.  0-255
#define FADE 40  //How slowly the LEDs fade to off

CRGB leds[NUM_LEDS];       //separate LED arrays for all 3 strips
CRGB leds2[NUM_LEDS_2];
CRGB leds3[NUM_LEDS_3];

static byte heat[NUM_LEDS];    // separate heat arrays for all 3 strips
static byte heat2[NUM_LEDS_2];
static byte heat3[NUM_LEDS_3];

CRGBPalette16 currentPalette;
TBlendType    currentBlending;
CRGBPalette16 gPal;


//BUTTON SETUP STUFF
byte prevKeyState = HIGH;       

//FIRST ACTIVE MODE
#define NUM_MODES 1     // actually 2 modes, mode 0 (off) and mode 1 (on)
int ledMode = 1;       // change to 0 to make the LEDs dark on startup

//READ CAP TOUCH BUTTON STATE
boolean capButton(uint8_t pad) {
  if (CircuitPlayground.readCap(pad) > CAP_THRESHOLD) {
    return true;  
  } else {
    return false;
  }
}

//--------------------------------------------------
void setup() {
  // Initialize serial.
  Serial.begin(9600); 
  
  // Initialize Circuit Playground library.
  CircuitPlayground.begin();
  
  // Add all 3 LED strips for FastLED library
  FastLED.addLeds<WS2812B, STRIP1_DATA_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection( TypicalLEDStrip );
  FastLED.addLeds<WS2812B, STRIP2_DATA_PIN, COLOR_ORDER>(leds2, NUM_LEDS_2).setCorrection( TypicalLEDStrip );
  FastLED.addLeds<WS2812B, STRIP3_DATA_PIN, COLOR_ORDER>(leds3, NUM_LEDS_3).setCorrection( TypicalLEDStrip );

  //Set global brightness
  FastLED.setBrightness(BRIGHTNESS);
  currentBlending = LINEARBLEND;
  // Choose your color Palette
  gPal = HeatColors_p;
  //gpal = LavaColors_p;
  //gpal = RainbowColors_p;
  //gpal = CloudColors_p;
  //gpal = ForestColors_p;
  //gpal = PartyColors_p;
  //gpal = RainbowStripeColors_p;

}

//-----------------------------------------------------
void loop() {
    switch (ledMode) {
       case 0: fire(); break; 
       case 1: alloff(); break; 
    }
      // READ THE BUTTON
        byte currKeyState = capButton(10);
        Serial.println (capButton(10));
        if ((prevKeyState == true) && (currKeyState == false)) {
            keyRelease();
        }
        
        prevKeyState = currKeyState;
   
}


//BUTTON CONTROL
void keyRelease() {
    Serial.println("short");
    
    ledMode++;
    if (ledMode > NUM_MODES){
    ledMode=0; }
}

 
 void fire()
{
  
  currentPalette = HeatColors_p;
  Fire2012WithPalette(); // run simulation frame, using palette colors
  Fire2012WithPalette2();
  Fire2012WithPalette3();
  FastLED.show(); // display this frame
  FastLED.delay(1000 / FRAMES_PER_SECOND);  
  
}


void Fire2012WithPalette()
{
  random16_add_entropy( random());
  
    for( int i = 0; i < NUM_LEDS; i++) {
      heat[i] = qsub8( heat[i],  random8(0, ((COOLING * 10) / NUM_LEDS) + 2));
    }
    for( int k= NUM_LEDS - 3; k > 0; k--) {
      heat[k] = (heat[k - 1] + heat[k - 2] + heat[k - 2] ) / 3;
    }
    if( random8() < SPARKING ) {
      int y = random8(7);
      heat[y] = qadd8( heat[y], random8(160,255) );
    }
    for( int j = 0; j < NUM_LEDS; j++) {
      byte colorindex = scale8( heat[j], 240);
      leds[j] = ColorFromPalette( currentPalette, colorindex);

    }
} 

void Fire2012WithPalette2()
{
  random16_add_entropy( random());
  static byte heat2[NUM_LEDS_2];
    for( int i = 0; i < NUM_LEDS_2; i++) {
      heat2[i] = qsub8( heat[i],  random8(0, ((COOLING * 10) / NUM_LEDS_2) + 2));
    }
    for( int k= NUM_LEDS_2 - 3; k > 0; k--) {
      heat2[k] = (heat2[k - 1] + heat2[k - 2] + heat2[k - 2] ) / 3;
    }
    if( random8() < SPARKING ) {
      int y = random8(7);
      heat2[y] = qadd8( heat2[y], random8(160,255) );
    }
    for( int j = 0; j < NUM_LEDS_2; j++) {
      byte colorindex = scale8( heat2[j], 240);
      leds2[j] = ColorFromPalette( currentPalette, colorindex);

    }
} 
void Fire2012WithPalette3()
{
  random16_add_entropy( random());
    for( int i = 0; i < NUM_LEDS_3; i++) {
      heat3[i] = qsub8( heat3[i],  random8(0, ((COOLING * 10) / NUM_LEDS_3) + 2));
    }
    for( int k= NUM_LEDS_3 - 3; k > 0; k--) {
      heat3[k] = (heat3[k - 1] + heat3[k - 2] + heat3[k - 2] ) / 3;
    }
    if( random8() < SPARKING ) {
      int y = random8(7);
      heat3[y] = qadd8( heat3[y], random8(160,255) );
    }
    for( int j = 0; j < NUM_LEDS_3; j++) {
      byte colorindex = scale8( heat3[j], 240);
      leds3[j] = ColorFromPalette( currentPalette, colorindex);

    }
} 


void alloff() {  // Fade all LEDs slowly to black
  for (int i = 0; i < NUM_LEDS; i++){
    leds[i].fadeToBlackBy( FADE );
    leds2[i].fadeToBlackBy( FADE );
    leds3[i].fadeToBlackBy( FADE );
  }
    for(int i = 0; i < NUM_LEDS; i++) {
  heat[i] = 0;
}
  for(int i = 0; i < NUM_LEDS; i++) {
  heat2[i] = 0;
}
  for(int i = 0; i < NUM_LEDS; i++) {
  heat3[i] = 0;
}

  FastLED.show();
  delay(20);
}
