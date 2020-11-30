// Techno-Tiki RGB LED Torch with IR Remote Control
// Created by Tony DiCola
//
// See guide at: https://learn.adafruit.com/techno-tiki-rgb-led-torch/overview
//
// Released under a MIT license: http://opensource.org/licenses/MIT
#include <avr/power.h>
#include <avr/sleep.h>
#include <Adafruit_NeoPixel.h> 

// Sketch configuration:
#define PIXEL_PIN      1    // Pin connected to the NeoPixel strip.

#define PIXEL_COUNT    6    // Number of NeoPixels.  At most only about 100 pixels
                            // can be used at a time before it will take too long
                            // to update the pixels and IR remote codes might be
                            // missed.

#define PIXEL_TYPE     NEO_GRB + NEO_KHZ800   // Type of NeoPixel.  Keep this the default
                                              // if unsure.  See the NeoPixel library examples
                                              // for more explanation and other possible values.

#define IR_PIN         2    // Pin connected to the IR receiver.

// Adafruit IR Remote Codes:
//   Button       Code         Button  Code
//   -----------  ------       ------  -----
//   VOL-:        0x0000       0/10+:  0x000C
//   Play/Pause:  0x0001       1:      0x0010
//   VOL+:        0x0002       2:      0x0011
//   SETUP:       0x0004       3:      0x0012
//   STOP/MODE:   0x0006       4:      0x0014
//   UP:          0x0005       5:      0x0015
//   DOWN:        0x000D       6:      0x0016
//   LEFT:        0x0008       7:      0x0018
//   RIGHT:       0x000A       8:      0x0019
//   ENTER/SAVE:  0x0009       9:      0x001A
//   Back:        0x000E
#define COLOR_CHANGE      0x000A   // Button that cycles through color animations.
#define ANIMATION_CHANGE  0x0008   // Button that cycles through animation types (only two supported).
#define SPEED_CHANGE      0x0005   // Button that cycles through speed choices.
#define POWER_OFF         0x0000   // Button that turns off/sleeps the pixels.
#define POWER_ON          0x0002   // Button that turns on the pixels.  Must be pressed twice to register!


// Build lookup table/palette for the color animations so they aren't computed at runtime.
// The colorPalette two-dimensional array below has a row for each color animation and a column
// for each step within the animation.  Each value is a 24-bit RGB color.  By looping through
// the columns of a row the colors of pixels will animate.
const int colorSteps = 8;   // Number of rows/animations.
const int colorCount = 24;  // Number of columns/steps.
const uint32_t colorPalette[colorCount][colorSteps] PROGMEM = {
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
Adafruit_NeoPixel strip = Adafruit_NeoPixel(PIXEL_COUNT, PIXEL_PIN, PIXEL_TYPE);
volatile bool receiverFell = false;
uint8_t colorIndex = 0;
uint8_t animationIndex = 0;
uint8_t speedIndex = 2;


void setup(void) {
  // Setup IR receiver pin as an input.
  pinMode(IR_PIN, INPUT);
  // Initialize and clear the NeoPixel strip.
  strip.begin();
  strip.clear();
  strip.show(); // Initialize all pixels to 'off'
  // Enable an interrupt that's called when the IR receiver pin signal falls
  // from high to low.  This indicates a remote control code being received.
  attachInterrupt(0, receiverFalling, FALLING);
}

void loop(void) {
  // Main loop will first update all the pixels based on the current animation.
  for (int i = 0; i < PIXEL_COUNT; ++i) {
    switch (animationIndex) {
    case 0: 
    {
      // Animation 0, solid color pulse of all pixels.
      uint8_t currentStep = (millis()/speeds[speedIndex])%(colorSteps*2-2);
      if (currentStep >= colorSteps) {
        currentStep = colorSteps-(currentStep-(colorSteps-2));
      }
      // Note that colors are stored in flash memory so they need to be read
      // using the pgmspace.h functions.
      uint32_t color = pgm_read_dword_near(&colorPalette[colorIndex][currentStep]);
      strip.setPixelColor(i, color);
      break;
    }
    case 1: 
    {
      // Animation 1, moving color pulse.  Use position to change brightness.
      uint8_t currentStep = (millis()/speeds[speedIndex]+i)%(colorSteps*2-2);
      if (currentStep >= colorSteps) {
        currentStep = colorSteps-(currentStep-(colorSteps-2));
      }
      // Note that colors are stored in flash memory so they need to be read
      // using the pgmspace.h functions.
      uint32_t color = pgm_read_dword_near(&colorPalette[colorIndex][currentStep]);
      strip.setPixelColor(i, color);
      break;
    }
    }
  }
  // Next check for any IR remote commands.
  handleRemote();
  // Show the updated pixels.
  strip.show();
  // Again check for IR remote commands.
  handleRemote();
}

void receiverFalling() {
  // Interrupt function that's called when the IR receiver pin falls from high to
  // low and indicates the start of an IR command being received.  Note that
  // interrupts need to be very fast and perform as little processing as possible.
  // This just sets a global variable which the main loop will periodically check
  // and perform appropriate IR command decoding when necessary.
  receiverFell = true;
}

bool readNEC(uint16_t* result) {
  // Check if a NEC IR remote command can be read and decoded from the IR receiver.
  // If the command is decoded then the result is stored in the provided pointer and
  // true is returned.  Otherwise if the command was not decoded then false is returned.
  // First check that a falling signal was detected and start reading pulses.
  if (!receiverFell) {
    return false;
  }
  // Read the first pulse with a large timeout since it's 9ms long, then
  // read subsequent pulses with a shorter 2ms timeout.
  uint32_t durations[33];
  durations[0] = pulseIn(IR_PIN, HIGH, 20000);
  for (uint8_t i = 1; i < 33; ++i) {
    durations[i] = pulseIn(IR_PIN, HIGH, 5000);
  }
  // Reset any state changed by the interrupt.
  receiverFell = false;
  // Check the received pulses are in a NEC format.
  // First verify the initial pulse is around 4.5ms long.
  if ((durations[0] < 4000) || (durations[1] > 5000)) {
    return false;
  }
  // Now read the bits from subsequent pulses.  Stop if any were a timeout (0 value).
  uint8_t data[4] = {0};
  for (uint8_t i=0; i<32; ++i) {
    if (durations[1+i] == 0) {
      return false; // Timeout
    }
    uint8_t b = durations[1+i] < 1000 ? 0 : 1;
    data[i/8] |= b << (i%8);
  }
  // Verify bytes and their inverse match.  Use the same two checks as the NEC IR remote
  // library here: https://github.com/adafruit/Adafruit-NEC-remote-control-library
  if ((data[0] == (~data[1] & 0xFF)) && (data[2] == (~data[3] & 0xFF))) {
    *result = data[0] << 8 | data[2];
    return true;
  }
  else if ((data[0] == 0) && (data[1] == 0xBF) && (data[2] == (~data[3] & 0xFF))) {
    *result = data[2];
    return true;
  }
  else {
    // Something didn't match, fail!
    return false;
  }
}

void handleRemote() {
  // Check if an IR remote code was received and perform the appropriate action.
  // First read a code.
  uint16_t irCode;
  if (!readNEC(&irCode)) {
    return;
  }
  switch(irCode) {
  case COLOR_CHANGE:
    // Color change command, increment the current color animation and wrap
    // back to zero when past the end.
    colorIndex = (colorIndex+1)%colorCount;
    break;
  case ANIMATION_CHANGE:
    // Animation change command, increment the current animation type and wrap
    // back to zero when past the end.
    animationIndex = (animationIndex+1)%2;
    break;
  case SPEED_CHANGE:
    // Speed change command, increment the current speed and wrap back to zero
    // when past the end.
    speedIndex = (speedIndex+1)%5;
    break;
  case POWER_OFF:
    // Enter full power down sleep mode.
    // First turn off the NeoPixels.
    strip.clear();
    strip.show();
    while (true) {
      // Next disable the current falling interrupt and enable a low value interrupt.
      // This is required because the ATtiny85 can't wake from a falling interrupt
      // and instead can only wake from a high or low value interrupt.
      detachInterrupt(0);
      attachInterrupt(0, receiverFalling, LOW);
      // Now enter full power down sleep mode.
      power_all_disable();
      set_sleep_mode(SLEEP_MODE_PWR_DOWN);
      sleep_mode();
      // Processor is currently asleep and will wake up when the IR receiver pin
      // is at a low value (i.e. when a IR command is received).
      // Sleep resumes here.  When awake power everything back up.
      power_all_enable();
      // Re-enable the falling interrupt.
      detachInterrupt(0);
      attachInterrupt(0, receiverFalling, FALLING);
      // Now wait up to 1 second for a second power on command to be received.
      // This is necessary because the first power on command will wake up the CPU
      // but happens a little too quickly to be reliably read.
      for (int i=0; i<200; ++i) {
        uint16_t irCode;
        if ((readNEC(&irCode) == 1) && (irCode == POWER_ON)) {
          // Second power on command was received, jump out of the power on loop and
          // return to normal operation.
          return;
        }
        delay(5);
      }
      // If no power on command was received within 1 second of awaking then the
      // code will loop back to the top and go to sleep again.
    }
  }
}


