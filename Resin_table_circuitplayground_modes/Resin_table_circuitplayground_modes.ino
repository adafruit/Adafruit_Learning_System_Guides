// Code by Erin St Blaine for Adafruit.com, based on FastLED animations by Mark Kriegsman

#include <Adafruit_CircuitPlayground.h>
#include <FastLED.h>

// tell FastLED all about the Circuit Playground's layout

#define DATA_PIN     A1    //LED data on pin A1
#define NUM_LEDS    200   // total number of LEDs in your strip
#define COLOR_ORDER GRB  //  color order -- change this if your colors are coming out wrong

uint8_t brightness = 150;  // Set brightness level

int STEPS = 6;  //makes the rainbow colors more or less spread out
int NUM_MODES = 5;  // change this number if you add or subtract modes
int CYCLETIME = 60;  // number of seconds on each mode, for mode cycling

CRGB leds[NUM_LEDS];      // set up an LED array

CRGBPalette16 currentPalette;
TBlendType    currentBlending;

int ledMode = 0;       //Initial mode 
bool leftButtonPressed;
bool rightButtonPressed;


// SETUP -----------------------------------------------------
void setup() {
  Serial.begin(57600);
  CircuitPlayground.begin();
  FastLED.addLeds<WS2812B, DATA_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection( TypicalLEDStrip ); // Use this line if using neopixels
  currentBlending = LINEARBLEND;
  set_max_power_in_volts_and_milliamps(5, 5000);               // FastLED 2.1 Power management set at 5V, 5000mA

  
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
    if (rightButtonPressed) {  // on off button
    ledMode=99;
  
    }
  
 switch (ledMode) {
       case 0: modeCycle(); break;
       case 1: currentPalette = RainbowColors_p; rainbow(); break;
       case 2: currentPalette = OceanColors_p; rainbow(); break;                    
       case 3: currentPalette = LavaColors_p; rainbow(); break;   
       case 4: currentPalette = ForestColors_p; rainbow(); break;
       case 5: currentPalette = PartyColors_p; rainbow(); break;
       case 99: clearpixels(); break;
       
}
}
void clearpixels()
{
  CircuitPlayground.clearPixels();
   for( int i = 0; i < NUM_LEDS; i++) {
   leds[i]= CRGB::Black;
    }
   FastLED.show();
}

void rainbow()
{
  
  static uint8_t startIndex = 0;
  startIndex = startIndex + 1; /* motion speed */

  FillLEDsFromPaletteColors( startIndex);

  FastLED.show();
  FastLED.delay(20);
  
  }

//this bit is in every palette mode, needs to be in there just once
void FillLEDsFromPaletteColors( uint8_t colorIndex)
{ 
  for( int i = 0; i < NUM_LEDS; i++) {
    leds[i] = ColorFromPalette( currentPalette, colorIndex, brightness, currentBlending);
    colorIndex += STEPS;
  }
}


int cycleMode=0;

void modeCycle()
{
   switch (cycleMode) {
       case 0: currentPalette = RainbowColors_p; rainbow(); break;
       case 1: currentPalette = OceanColors_p; rainbow(); break;                    
       case 2: currentPalette = LavaColors_p; rainbow(); break;   
       case 3: currentPalette = ForestColors_p; rainbow(); break;
       case 4: currentPalette = PartyColors_p; rainbow(); break;
       case 5: cycleMode=0; break;
}

   EVERY_N_SECONDS(CYCLETIME) {
    cycleMode++;
   }
   
}
