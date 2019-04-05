// Techno-Tiki RGB LED Torch with IR Remote Control for Circuit Playground Express
// This version ONLY works with Circuit Playground Express boards:
//   https://www.adafruit.com/product/3333
// Created by Tony DiCola
//
// See guide at: https://learn.adafruit.com/techno-tiki-rgb-led-torch/overview
//
// Released under a MIT license: http://opensource.org/licenses/MIT
#include <Adafruit_CircuitPlayground.h> 

#if !defined(ARDUINO_SAMD_CIRCUITPLAYGROUND_EXPRESS)
  #error "This sketch requires Circuit Playground Express, it doesn't work with the Classic version or other boards!"
#endif

#define BRIGHTNESS 255  // Brightness of the neopixels, set to 255 for max or lower for less bright.

// Adafruit IR Remote Codes:
#define ADAF_MINI_VOLUME_DOWN   0xfd00ff
#define ADAF_MINI_PLAY_PAUSE    0xfd807f
#define ADAF_MINI_VOLUME_UP     0xfd40bf
#define ADAF_MINI_SETUP         0xfd20df
#define ADAF_MINI_UP_ARROW      0xfda05f
#define ADAF_MINI_STOP_MODE     0xfd609f
#define ADAF_MINI_LEFT_ARROW    0xfd10ef
#define ADAF_MINI_ENTER_SAVE    0xfd906f
#define ADAF_MINI_RIGHT_ARROW   0xfd50af
#define ADAF_MINI_0_10_PLUS     0xfd30cf
#define ADAF_MINI_DOWN_ARROW    0xfdb04f
#define ADAF_MINI_REPEAT        0xfd708f
#define ADAF_MINI_1             0xfd08f7
#define ADAF_MINI_2             0xfd8877
#define ADAF_MINI_3             0xfd48b7
#define ADAF_MINI_4             0xfd28d7
#define ADAF_MINI_5             0xfda857
#define ADAF_MINI_6             0xfd6897
#define ADAF_MINI_7             0xfd18e7
#define ADAF_MINI_8             0xfd9867
#define ADAF_MINI_9             0xfd58a7

// Define which remote buttons are associated with sketch actions.
#define COLOR_CHANGE      ADAF_MINI_RIGHT_ARROW   // Button that cycles through color animations.
#define ANIMATION_CHANGE  ADAF_MINI_LEFT_ARROW    // Button that cycles through animation types (only two supported).
#define SPEED_CHANGE      ADAF_MINI_UP_ARROW      // Button that cycles through speed choices.
#define POWER_OFF         ADAF_MINI_VOLUME_DOWN   // Button that turns off/sleeps the pixels.
#define POWER_ON          ADAF_MINI_VOLUME_UP     // Button that turns on the pixels.  Must be pressed twice to register!


// Build lookup table/palette for the color animations so they aren't computed at runtime.
// The colorPalette two-dimensional array below has a row for each color animation and a column
// for each step within the animation.  Each value is a 24-bit RGB color.  By looping through
// the columns of a row the colors of pixels will animate.
const int colorSteps = 8;   // Number of rows/animations.
const int colorCount = 24;  // Number of columns/steps.
const uint32_t colorPalette[colorCount][colorSteps] = {
  // Complimentary colors  
  { 0xFF0000, 0xDA2424, 0xB64848, 0x916D6D, 0x6D9191, 0x48B6B6, 0x24DADA, 0x00FFFF }, // Red-cyan
  { 0xFFFF00, 0xDADA24, 0xB6B648, 0x91916D, 0x6D6D91, 0x4848B6, 0x2424DA, 0x0000FF }, // Yellow-blue
  { 0x00FF00, 0x24DA24, 0x48B648, 0x6D916D, 0x916D91, 0xB648B6, 0xDA24DA, 0xFF00FF }, // Green-magenta

  // Adjacent colors (on color wheel).
  { 0xFF0000, 0xFF2400, 0xFF4800, 0xFF6D00, 0xFF9100, 0xFFB600, 0xFFDA00, 0xFFFF00 }, // Red-yellow
  { 0xFFFF00, 0xDAFF00, 0xB6FF00, 0x91FF00, 0x6DFF00, 0x48FF00, 0x24FF00, 0x00FF00 }, // Yellow-green
  { 0x00FF00, 0x00FF24, 0x00FF48, 0x00FF6D, 0x00FF91, 0x00FFB6, 0x00FFDA, 0x00FFFF }, // Green-cyan
  { 0x00FFFF, 0x00DAFF, 0x00B6FF, 0x0091FF, 0x006DFF, 0x0048FF, 0x0024FF, 0x0000FF }, // Cyan-blue
  { 0x0000FF, 0x2400FF, 0x4800FF, 0x6D00FF, 0x9100FF, 0xB600FF, 0xDA00FF, 0xFF00FF }, // Blue-magenta
  { 0xFF00FF, 0xFF00DA, 0xFF00B6, 0xFF0091, 0xFF006D, 0xFF0048, 0xFF0024, 0xFF0000 }, // Magenta-red

  // Other combos.
  { 0xFF0000, 0xDA2400, 0xB64800, 0x916D00, 0x6D9100, 0x48B600, 0x24DA00, 0x00FF00 }, // Red-green
  { 0xFFFF00, 0xDAFF24, 0xB6FF48, 0x91FF6D, 0x6DFF91, 0x48FFB6, 0x24FFDA, 0x00FFFF }, // Yellow-cyan
  { 0x00FF00, 0x00DA24, 0x00B648, 0x00916D, 0x006D91, 0x0048B6, 0x0024DA, 0x0000FF }, // Green-blue
  { 0x00FFFF, 0x24DAFF, 0x48B6FF, 0x6D91FF, 0x916DFF, 0xB648FF, 0xDA24FF, 0xFF00FF }, // Cyan-magenta
  { 0x0000FF, 0x2400DA, 0x4800B6, 0x6D0091, 0x91006D, 0xB60048, 0xDA0024, 0xFF0000 }, // Blue-red
  { 0xFF00FF, 0xFF24DA, 0xFF48B6, 0xFF6D91, 0xFF916D, 0xFFB648, 0xFFDA24, 0xFFFF00 }, // Magenta-yellow  

  // Solid colors fading to dark.
  { 0xFF0000, 0xDF0000, 0xBF0000, 0x9F0000, 0x7F0000, 0x5F0000, 0x3F0000, 0x1F0000 }, // Red
  { 0xFF9900, 0xDF8500, 0xBF7200, 0x9F5F00, 0x7F4C00, 0x5F3900, 0x3F2600, 0x1F1300 }, // Orange
  { 0xFFFF00, 0xDFDF00, 0xBFBF00, 0x9F9F00, 0x7F7F00, 0x5F5F00, 0x3F3F00, 0x1F1F00 }, // Yellow
  { 0x00FF00, 0x00DF00, 0x00BF00, 0x009F00, 0x007F00, 0x005F00, 0x003F00, 0x001F00 }, // Green
  { 0x0000FF, 0x0000DF, 0x0000BF, 0x00009F, 0x00007F, 0x00005F, 0x00003F, 0x00001F }, // Blue
  { 0x4B0082, 0x410071, 0x380061, 0x2E0051, 0x250041, 0x1C0030, 0x120020, 0x090010 }, // Indigo
  { 0x8B00FF, 0x7900DF, 0x6800BF, 0x56009F, 0x45007F, 0x34005F, 0x22003F, 0x11001F }, // Violet
  { 0xFFFFFF, 0xDFDFDF, 0xBFBFBF, 0x9F9F9F, 0x7F7F7F, 0x5F5F5F, 0x3F3F3F, 0x1F1F1F }, // White

  // Rainbow colors.
  { 0xFF0000, 0xFF9900, 0xFFFF00, 0x00FF00, 0x0000FF, 0x4B0082, 0x8B00FF, 0xFFFFFF }
};

// List of animations speeds (in milliseconds).  This is how long an animation spends before
// changing to the next step.  Higher values are slower.
const uint16_t speeds[5] = { 400, 200, 100, 50, 25 };

// Global state used by the sketch:
uint8_t colorIndex = 0;
uint8_t animationIndex = 0;
uint8_t speedIndex = 2;
bool powerDown = false;


void setup(void) {
  CircuitPlayground.begin(BRIGHTNESS);
  CircuitPlayground.irReceiver.enableIRIn();
  Serial.begin(115200);
}

void loop(void) {
  // Check for remote control presses.
  handleRemote();
  // Skip doing anything if in power down mode.  This prevents the pixels from animating.
  if (powerDown) {
    return;
  }
  // Main loop will first update all the pixels based on the current animation.
  for (int i = 0; i < CircuitPlayground.strip.numPixels(); ++i) {
    switch (animationIndex) {
    case 0: 
    {
      // Animation 0, solid color pulse of all pixels.
      uint8_t currentStep = (millis()/speeds[speedIndex])%(colorSteps*2-2);
      if (currentStep >= colorSteps) {
        currentStep = colorSteps-(currentStep-(colorSteps-2));
      }
      uint32_t color = colorPalette[colorIndex][currentStep];
      CircuitPlayground.strip.setPixelColor(i, color);
      break;
    }
    case 1: 
    {
      // Animation 1, moving color pulse.  Use position to change brightness.
      uint8_t currentStep = (millis()/speeds[speedIndex]+i)%(colorSteps*2-2);
      if (currentStep >= colorSteps) {
        currentStep = colorSteps-(currentStep-(colorSteps-2));
      }
      uint32_t color = colorPalette[colorIndex][currentStep];
      CircuitPlayground.strip.setPixelColor(i, color);
      break;
    }
    }
  }
  // Show the updated pixels.
  CircuitPlayground.strip.show();
  delay(100);
}

void handleRemote() {
  // Stop if no remote code was received.
  if (!CircuitPlayground.irReceiver.getResults()) {
    return;
  }
  
  // Stop if no NEC IR message was decoded yet.
  if (!CircuitPlayground.irDecoder.decode() || (CircuitPlayground.irDecoder.protocolNum != NEC)) {
    CircuitPlayground.irReceiver.enableIRIn(); // Restart receiver  
    return;
  }

  // Perform the appropriate remote control action.
  switch(CircuitPlayground.irDecoder.value) {
  case COLOR_CHANGE:
    // Color change command, increment the current color animation and wrap
    // back to zero when past the end.
    Serial.println("Color change!");
    colorIndex = (colorIndex+1)%colorCount;
    break;
  case ANIMATION_CHANGE:
    // Animation change command, increment the current animation type and wrap
    // back to zero when past the end.
    Serial.println("Animation change!");
    animationIndex = (animationIndex+1)%2;
    break;
  case SPEED_CHANGE:
    // Speed change command, increment the current speed and wrap back to zero
    // when past the end.
    Serial.println("Speed change!");
    speedIndex = (speedIndex+1)%5;
    break;
  case POWER_OFF:
    // Enter full power down sleep mode.
    // First turn off the NeoPixels.
    Serial.println("Power down!");
    CircuitPlayground.strip.clear();
    CircuitPlayground.strip.show();
    powerDown = true;
    break;
  case POWER_ON:
    Serial.println("Power up!");
    powerDown = false;
    break;
  }
  //Restart receiver
  CircuitPlayground.irReceiver.enableIRIn(); 
}


