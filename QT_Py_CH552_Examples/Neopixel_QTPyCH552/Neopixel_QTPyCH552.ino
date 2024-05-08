// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <WS2812.h>

#define NEOPIXEL_PIN P1_0
#define NUM_LEDS 1

#define COLOR_PER_LEDS 3
#define NUM_BYTES (NUM_LEDS*COLOR_PER_LEDS)
#if NUM_BYTES > 255
#error "NUM_BYTES can not be larger than 255."
#endif
__xdata uint8_t ledData[NUM_BYTES];

/***********************************************************************/
uint8_t neopixel_brightness = 255;
uint32_t Wheel(byte WheelPos);
void rainbowCycle(uint8_t wait);

#define NEOPIXEL_SHOW_FUNC CONCAT(neopixel_show_, NEOPIXEL_PIN)

void neopixel_begin() {
  pinMode(NEOPIXEL_PIN, OUTPUT); //Possible to use other pins. 
}

void neopixel_show() {
  NEOPIXEL_SHOW_FUNC(ledData, NUM_BYTES); //Possible to use other pins. 
}

void neopixel_setPixelColor(uint8_t i, uint32_t c) {
  uint16_t r, g, b;
  r = (((c >> 16) & 0xFF) * neopixel_brightness) >> 8;
  g = (((c >> 8) & 0xFF) * neopixel_brightness) >> 8;
  b = ((c & 0xFF) * neopixel_brightness) >> 8;

  set_pixel_for_GRB_LED(ledData, i, r, g, b);
}

void neopixel_setBrightness(uint8_t b) {
  neopixel_brightness = b;
}
/***********************************************************************/


void setup() {
  neopixel_begin();
  neopixel_setBrightness(50);
}

void loop() {
  rainbowCycle(5);
}


void rainbowCycle(uint8_t wait) {
  uint8_t i, j;

  for (j=0; j<255; j++) {
    for (i=0; i < NUM_LEDS; i++) {
      neopixel_setPixelColor(i, Wheel(((i * 256 / NUM_LEDS) + j) & 255));
    }
    neopixel_show();
    delay(wait);
  }
}


// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  uint8_t r, g, b;
  uint32_t c;
  
  if(WheelPos < 85) {
   r = WheelPos * 3;
   g = 255 - WheelPos * 3 ;
   b = 0;
  } else if(WheelPos < 170) {
   WheelPos -= 85;
   r = 255 - WheelPos * 3;
   g = 0;
   b = WheelPos * 3;
  } else {
   WheelPos -= 170;
   r = 0;
   g = WheelPos * 3;
   b = 255 - WheelPos * 3;
  }
  c = r;
  c <<= 8;
  c |= g;
  c <<= 8;
  c |= b;
  return c;
}
