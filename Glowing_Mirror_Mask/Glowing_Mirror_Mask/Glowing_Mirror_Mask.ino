// Glowing Mirror Mask using the Adafruit Hallowing
// Full tutorial available on the Adafruit Learning System.
// Code by Phil Burgess & Erin St. Blaine for Adafruit Industries.  


#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <Adafruit_NeoPixel.h>
#include <FastLED.h>

// Enable ONE of these lines to select an animation,
// others MUST be commented out!

//#include "fire.h"
#include "butterfly.h"

#define TFT_CS       39
#define TFT_RST      37
#define TFT_DC       38
#define TFT_BACKLIGHT 7

#define LED_PIN     4  // Hallowing's neopixel port is on pin 4
#define NUM_LEDS    30 // Change this to reflect how many LEDs you have
#define LED_TYPE    WS2812 // Neopixels
#define COLOR_ORDER GRB  
CRGB leds[NUM_LEDS];

int indexinc = 1;
uint8_t brightness = 150;
uint8_t updates_per_second = 30;

CRGBPalette16 currentPalette;
TBlendType    currentBlending;

Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS,  TFT_DC, TFT_RST);

void setup(void) {
  tft.initR(INITR_144GREENTAB);
  tft.setRotation(2);  // change between 0-3 to set the rotation of the image on the screen 
  tft.fillScreen(0);  // screen background brightness

  pinMode(TFT_BACKLIGHT, OUTPUT);
  digitalWrite(TFT_BACKLIGHT, HIGH);
 
FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);             // WS2812B
FastLED.setBrightness(brightness);
  
  currentPalette = RainbowColors_p;    //Uncomment ONE of these lines to choose your Neopixel color palette
  //currentPalette = HeatColors_p;
  //currentPalette = PartyColors_p;
  //currentPalette = CloudColors_p;
  //currentPalette = RainbowStripeColors_p;
  //currentPalette = ForestColors_p;
  //currentPalette = OceanColors_p;
}

uint8_t frameNum = 0;

void loop() {
    tft.startWrite();
  tft.setAddrWindow(
    (tft.width()  - IMG_WIDTH ) / 2,
    (tft.height() - IMG_HEIGHT) / 2,
    IMG_WIDTH, IMG_HEIGHT);
  tft.writePixels((uint16_t *)frames[frameNum], IMG_WIDTH * IMG_HEIGHT);
  tft.endWrite();
  delay(IMG_DELAY);
  if(++frameNum >= IMG_FRAMES) frameNum = 0;

  colorwaves( leds, NUM_LEDS, currentPalette);

  FastLED.show();
}


void FillLEDsFromPaletteColors(uint8_t colorIndex) {
  for (int i = 0; i < NUM_LEDS; i++) {
    leds[i] = ColorFromPalette( currentPalette, colorIndex, brightness, currentBlending);
    colorIndex += indexinc;
  }
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
  uint8_t msmultiplier = beatsin88(147, 23, 60);

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
