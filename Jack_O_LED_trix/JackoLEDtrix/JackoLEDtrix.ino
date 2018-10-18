/*  This is the FastLED library NoisePlusPalette example code incorporating a momentary 
    push button to cycle between modes for the Jack-o-LED-trix project. 
    
    You should wire a momentary push button to connect from ground to a digital IO pin. 
    In this example, wire the button to ground and pin 11.
    
    FastLED has a number of built in "palettes" to choose from: 
      RainbowColors_p       is all the colors of the rainbow
      PartyColors_p         is all the colors of the rainbow minus greens
      RainbowStripeColors_p is all the colors of the rainbow divided into stripes
      HeatColors_p          is reds and yellows, white, and black
      LavaColors_p          is more reds and orangey colors
      ForestColors_p        is greens and yellows
      OceanColors_p         is lots of blues and aqua colors
      CloudColors_p         is blues and white
    FastLED also provides a number of easy ways to create you own personalized palettes,
    see the "HalloweenPalette_p" to personalize your own colors.
      
    There are also ways to create other palettes using functions, 
    see "SetupCandyCornPalette()" & "SetupBlackAndWhiteStripedPalette()" to personalize 
    your own colors.  
*/

#include <FastLED.h>
#include "colorutils.h"
#include "colorpalettes.h"

#define BRIGHTNESS  128 

//Define the type of pixels you are using on the next line here. 
//If you are using a strand or two of WS2801 pixels from Adafruit, update the chipset type to WS2801.
#define LED_TYPE       WS2811

//You may need to adjust your color order to "GRB" instead of "RGB" below. 
#define COLOR_ORDER   RGB

//If you are using 4-pin LEDs, you will need to uncomment and define the CLOCK_PIN 
#define DATA_PIN      6
//#define CLOCK_PIN   #

#define BUTTON_PIN   11   // button is connected to pin 11 and GND
#define UPDATES_PER_SECOND 100

//This sketch is set up for a matrix of 8 pixels wide and 6 pixels high. Update to match your matrix.
const uint8_t kMatrixWidth  = 8;
const uint8_t kMatrixHeight = 6;
const bool    kMatrixSerpentineLayout = true;

#define NUM_LEDS (kMatrixWidth * kMatrixHeight)   //no need to define the number of LEDS - here's the math!
#define MAX_DIMENSION ((kMatrixWidth>kMatrixHeight) ? kMatrixWidth : kMatrixHeight)

// The leds
CRGB leds[kMatrixWidth * kMatrixHeight];

uint8_t gHue = 0; // rotating "base color" used by many of the patterns
int ledMode = 0;

// The 16 bit version of our coordinates
static uint16_t x;
static uint16_t y;
static uint16_t z;

// We're using the x/y dimensions to map to the x/y pixels on the matrix.  We'll
// use the z-axis for "time".  speed determines how fast time moves forward.  Try
// 1 for a very slow moving effect, or 60 for something that ends up looking like
// water.
uint16_t speed = 10; // speed is set dynamically once we've started up

// Scale determines how far apart the pixels in our noise matrix are.  Try
// changing these values around to see how it affects the motion of the display.  The
// higher the value of scale, the more "zoomed out" the noise will be.  A value
// of 1 will be so zoomed in, you'll mostly see solid colors.
uint16_t scale = 50; // scale is set dynamically once we've started up

// This is the array that we keep our computed noise values in
uint8_t noise[MAX_DIMENSION][MAX_DIMENSION];

CRGBPalette16 currentPalette( RainbowColors_p );
uint8_t       colorLoop = 0;

TBlendType    currentBlending;

const TProgmemPalette16 HalloweenPalette_p PROGMEM =
{
  CRGB:: OrangeRed,
  CRGB:: Gold,
  CRGB:: Purple,
  CRGB:: Gold,
  
  CRGB:: OrangeRed,
  CRGB:: Gold,
  CRGB:: Purple,
  CRGB:: OrangeRed,
  
  CRGB:: Gold,    
  CRGB:: Purple,
  CRGB:: Gold,
  CRGB:: OrangeRed,
  
  CRGB:: Gold,
  CRGB:: Purple,
  CRGB:: Gold,
  CRGB:: OrangeRed,
};


unsigned long keyPrevMillis = 0;
const unsigned long keySampleIntervalMs = 25;
byte longKeyPressCountMax = 80;    // 80 * 25 = 2000 ms
byte longKeyPressCount = 0;

byte prevKeyState = HIGH;         // button is active low

void setup() {
  delay(3000);

//If you are using 3-pin LEDs, uncomment the next line:
  FastLED.addLeds<LED_TYPE, DATA_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection(TypicalLEDStrip);
  
//If you are using 4-pin LEDs, uncomment the next line:
  //FastLED.addLeds<LED_TYPE, DATA_PIN, CLOCK_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection(TypicalLEDStrip);

  FastLED.setBrightness(BRIGHTNESS);
  currentBlending;
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  // Initialize our coordinates to some random values
  x = random16();
  y = random16();
  z = random16();
}

// Fill the x/y array of 8-bit noise values using the inoise8 function.
void fillnoise8() {
  // If we're runing at a low "speed", some 8-bit artifacts become visible
  // from frame-to-frame.  In order to reduce this, we can do some fast data-smoothing.
  // The amount of data smoothing we're doing depends on "speed".
  uint8_t dataSmoothing = 0;
  if( speed < 50) {
    dataSmoothing = 200 - (speed * 4);
  }
  
  for(int i = 0; i < MAX_DIMENSION; i++) {
    int ioffset = scale * i;
    for(int j = 0; j < MAX_DIMENSION; j++) {
      int joffset = scale * j;
      
      uint8_t data = inoise8(x + ioffset,y + joffset,z);

      // The range of the inoise8 function is roughly 16-238.
      // These two operations expand those values out to roughly 0..255
      // You can comment them out if you want the raw noise data.
      data = qsub8(data,16);
      data = qadd8(data,scale8(data,39));

      if( dataSmoothing ) {
        uint8_t olddata = noise[i][j];
        uint8_t newdata = scale8( olddata, dataSmoothing) + scale8( data, 256 - dataSmoothing);
        data = newdata;
      }
      
      noise[i][j] = data;
    }
  }
  
  z += speed;
  
  // apply slow drift to X and Y, just for visual variation.
  x += speed / 8;
  y -= speed / 16;
}

void mapNoiseToLEDsUsingPalette()
{
  static uint8_t ihue=0;
  
  for(int i = 0; i < kMatrixWidth; i++) {
    for(int j = 0; j < kMatrixHeight; j++) {
      // We use the value at the (i,j) coordinate in the noise
      // array for our brightness, and the flipped value from (j,i)
      // for our pixel's index into the color palette.

      uint8_t index = noise[j][i];
      uint8_t bri =   noise[i][j];

      // if this palette is a 'loop', add a slowly-changing base value
      if( colorLoop) { 
        index += ihue;
      }

      // brighten up, as the color palette itself often contains the 
      // light/dark dynamic range desired
      if( bri > 127 ) {
        bri = 255;
      } else {
        bri = dim8_raw( bri * 2);
      }

      CRGB color = ColorFromPalette( currentPalette, index, bri);
      leds[XY(i,j)] = color;
    }
  }
  
  ihue+=1;
}

void loop() {  
  
  byte currKeyState = digitalRead(BUTTON_PIN);

  if ((prevKeyState == LOW) && (currKeyState == HIGH)) {
    shortKeyPress();
  }
  prevKeyState = currKeyState;

  static uint8_t startIndex = 0;
  startIndex = startIndex + 1; /* motion speed */

  // generate noise data
  fillnoise8();
  
  //The group of colors in a palette are sent through a strip of LEDS in speed and step increments youve chosen
  //You can change the SPEED and STEPS to make things look exactly how you want
  //SPEED refers to how fast the colors move.  
  //Try 1 for a very slow moving effect, or 60 for something that ends up looking like water.
  //SCALE refers to how zoomed in we are.  
  //Try changing these values around to see how it affects the motion of the display.  
  //The higher the value of scale, the more "zoomed out" the noise will be.  
  //A value of 1 will be so zoomed in, you'll mostly see solid colors.
  
  // convert the noise data to colors in the LED array using the current palette
  mapNoiseToLEDsUsingPalette();

  switch (ledMode)  {
  case 0:
  {currentPalette = RainbowColors_p;        speed = 25; scale = 25; colorLoop = 0; }
  break;
  
  case 1: 
  {currentPalette = HeatColors_p;           speed = 20; scale = 50; colorLoop = 2; }
  break;
  
  case 2:
  {SetupBlackAndWhiteStripedPalette();      speed = 20; scale = 100; colorLoop = 1; }
  break;
  
  case 3: 
  {currentPalette = LavaColors_p;           speed = 10; scale = 25; colorLoop = 0; }  
  break;
  
  case 4:
  {currentPalette = HalloweenPalette_p;     speed = 20; scale = 20; colorLoop = 1; }
  break;
  
  case 5: 
  {SetupCandyCornPalette();                 speed = 15; scale = 30; colorLoop = 1; }
  break;
  } 

  //FillLEDsFromPaletteColors( startIndex);
  LEDS.show();
  delay(1000/speed);
}

void shortKeyPress() {
  ledMode++;
  if (ledMode > 5) {
    ledMode=0; 
  }  
}

// This function sets up a palette of black and white stripes,
// using code.  Since the palette is effectively an array of
// sixteen CRGB colors, the various fill_* functions can be used
// to set them up.
void SetupBlackAndWhiteStripedPalette()
{
  // 'black out' all 16 palette entries...
  fill_solid( currentPalette, 16, CRGB::Black);
  // and set every fourth one to White or Gray.
  currentPalette[0] = CRGB::White;
  currentPalette[4] = CRGB::Gray;
  currentPalette[8] = CRGB::White;
  currentPalette[12] = CRGB::Gray;

}

// This function sets up a palette of candy corn colors
void SetupCandyCornPalette()
{
    fill_solid( currentPalette, 16, CRGB::Black);
    // set half of the LEDs to the colors selected here. This palette incorporates a lot of black
    currentPalette[0] = CRGB::Orange;
    currentPalette[1] = CRGB::Yellow;
    currentPalette[2] = CRGB::Red;
    currentPalette[3] = CRGB::OrangeRed;

    currentPalette[8] = CRGB::Yellow;
    currentPalette[9] = CRGB::OrangeRed;
    currentPalette[10] = CRGB::Orange;
    currentPalette[11] = CRGB::Red;

}

// Mark's xy coordinate mapping code.  See the XYMatrix for more information on it.
//
uint16_t XY( uint8_t x, uint8_t y)
{
  uint16_t i;
  if( kMatrixSerpentineLayout == false) {
    i = (y * kMatrixWidth) + x;
  }
  if( kMatrixSerpentineLayout == true) {
    if( y & 0x01) {
      // Odd rows run backwards
      uint8_t reverseX = (kMatrixWidth - 1) - x;
      i = (y * kMatrixWidth) + reverseX;
    } else {
      // Even rows run forwards
      i = (y * kMatrixWidth) + x;
    }
  }
  return i;
}
