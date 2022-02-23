// SPDX-FileCopyrightText: 2017 Dano Wall for Adafruit Industries
// SPDX-FileCopyrightText: 2017 Becky Stern for Adafruit Industries
//
// SPDX-License-Identifier: MIT

//Random Flash animation for Neopixel Ring Bangle Bracelet
//by Dano Wall and Becky Stern for Adafruit Industries
//based on the Sparkle Skirt, minus the accelerometer
#include <Adafruit_NeoPixel.h>

#define PIN       1 // Marked D1 on GEMMA
#define NUM_LEDS 64

// Parameter 1 = number of pixels in strip
// Parameter 2 = pin number (most are valid)
// Parameter 3 = pixel type:
//   NEO_GRB  Pixels are wired for GRB bitstream (most NeoPixel products)
//   NEO_RGB  Pixels are wired for RGB bitstream (v1 FLORA pixels, not v2)
Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_LEDS, PIN, NEO_GRB);

// Here is where you can put in your favorite colors that will appear!
// just add new {nnn, nnn, nnn}, lines. They will be picked out randomly
uint8_t myColors[][3] = {
  {232, 100, 255}, // purple
  {200, 200,  20}, // yellow
  { 30, 200, 200}, // blue
};

// don't edit the line below
#define FAVCOLORS sizeof(myColors) / 3

void setup() {
  strip.begin();
  strip.show();            // Initialize all pixels to 'off'
  strip.setBrightness(40); // 40/255 brightness (about 15%)
}

void loop() {
  flashRandom(5); // Number is 'wait' delay, smaller num = faster twinkle
}

void flashRandom(int wait) {

  // pick a random favorite color!
  int c     = random(FAVCOLORS);
  int red   = myColors[c][0];
  int green = myColors[c][1];
  int blue  = myColors[c][2];

  // get a random pixel from the list
  int j = random(strip.numPixels());

  // now we will fade in over 5 steps
  for (int x=1; x <= 5; x++) {
    int r = red   * x / 5;
    int g = green * x / 5;
    int b = blue  * x / 5;

    strip.setPixelColor(j, strip.Color(r, g, b));
    strip.show();
    delay(wait);
  }
  // & fade out in 5 steps
  for (int x=5; x >= 0; x--) {
    int r = red   * x / 5;
    int g = green * x / 5;
    int b = blue  * x / 5;

    strip.setPixelColor(j, strip.Color(r, g, b));
    strip.show();
    delay(wait);
  }
  // LED will be off when done (they are faded to 0)
}
