// SPDX-FileCopyrightText: 2017 Mikey Sklar for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#ifdef __AVR__
  #include <avr/power.h>
#endif

#include <Adafruit_NeoPixel.h>

#define PIXEL_PIN    1  // Pin connected to neo pixels
#define PIXEL_COUNT  7  // Count of neo pixels

Adafruit_NeoPixel strip = Adafruit_NeoPixel(PIXEL_COUNT, PIXEL_PIN, NEO_GRB + NEO_KHZ800);

void setup() {

  strip.begin();
  strip.show();

}

// Linear interpolation of y value given min/max x, min/max y, and x position.
float lerp(float x, float x0, float x1, float y0, float y1)
{
  // Clamp x within x0 and x1 bounds.
  x = x > x1 ? x1 : x;
  x = x < x0 ? x0 : x;
  // Calculate linear interpolation of y value.
  return y0 + (y1-y0)*((x-x0)/(x1-x0));
}

// Set all pixels to the specified color.
void fill_pixels(Adafruit_NeoPixel& pixels, uint32_t color)
{
  for (int i=0; i < pixels.numPixels(); ++i) {
    pixels.setPixelColor(i, color);
  }
  strip.show();
}

// Get the color of a pixel within a smooth gradient of two colors.
uint32_t color_gradient(uint8_t start_r, // Starting R,G,B color
                        uint8_t start_g,
                        uint8_t start_b, 
                        uint8_t end_r,   // Ending R,G,B color
                        uint8_t end_g,
                        uint8_t end_b,
                        float pos)       // Position along gradient, should be a value 0 to 1.0
{
  // Interpolate R,G,B values and return them as a color.  
  uint8_t red   = (uint8_t) lerp(pos, 0.0, 1.0, start_r, end_r);
  uint8_t green = (uint8_t) lerp(pos, 0.0, 1.0, start_g, end_g);
  uint8_t blue  = (uint8_t) lerp(pos, 0.0, 1.0, start_b, end_b);
  return Adafruit_NeoPixel::Color(red, green, blue);
}

void animate_gradient_fill(Adafruit_NeoPixel& pixels, // NeoPixel strip/loop/etc.
                           uint8_t start_r,           // Starting R,G,B color
                           uint8_t start_g,
                           uint8_t start_b, 
                           uint8_t end_r,             // Ending R,G,B color
                           uint8_t end_g,
                           uint8_t end_b,
                           int duration_ms)           // Total duration of animation, in milliseconds
{
  unsigned long start = millis();
  // Display start color.
  fill_pixels(pixels, Adafruit_NeoPixel::Color(start_r, start_g, start_b));
  // Main animation loop.
  unsigned long delta = millis() - start;
  while (delta < duration_ms) {
    // Calculate how far along we are in the duration as a position 0...1.0
    float pos = (float)delta / (float)duration_ms;
    // Get the gradient color and fill all the pixels with it.
    uint32_t color = color_gradient(start_r, start_g, start_b, end_r, end_g, end_b, pos);
    fill_pixels(pixels, color);
    // Update delta and repeat.
    delta = millis() - start;
  }
  // Display end color.
  fill_pixels(pixels, Adafruit_NeoPixel::Color(end_r, end_g, end_b));
}
void loop() { 
  
  // Run It:    

  // Nice fade from dim red to full red for 1/2 of a second:
  animate_gradient_fill(strip,         
                      10, 0, 0,
                      255, 0, 0,
                      500);
  // Then fade from full red to dim red for 1/2 a second.
  animate_gradient_fill(strip,         
                      255, 0, 0,
                      10, 0, 0,
                      500);
  //delay(1000); Use this delay if using multiple color fades
  }
