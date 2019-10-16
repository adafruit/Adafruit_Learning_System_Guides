// Example of rotating accelerometer to change NeoPixel color.
// Author: Tony DiCola
// License: Public Domain
#include <Adafruit_NeoPixel.h>
#include <Wire.h>
#include <SPI.h>
#include <Adafruit_LIS3DH.h>
#include <Adafruit_Sensor.h>


#define PIXEL_PIN        8  // Pin connected to NeoPixels.  Use 8 for the NeoPixel built into Flora V2.

#define PIXEL_COUNT      1  // Number of NeoPixels.

#define PIXEL_TYPE       NEO_GRB + NEO_KHZ800  // NeoPixel type, stick with default unless using different pixels.
                                               // See the NeoPixel Uberguide for information on different types:
                                               //   https://learn.adafruit.com/adafruit-neopixel-uberguide/overview

#define COLOR_MIN        Adafruit_NeoPixel::Color(255, 0, 0)  // RGB color for minimum axis value.

#define COLOR_MAX        Adafruit_NeoPixel::Color(0, 0, 255)  // RGB color for maximum axis value.

#define AXIS_MIN         -2000  // Minimum axis value, when at this or below the pixel color is the minimum color above.

#define AXIS_MAX         2000   // Maximum axis value, when at this or above the pixel color is the maximum color above.

#define ACCEL_RANGE      LIS3DH_RANGE_4_G  // Range of acceleration values for the LIS3DH.  Can
                                           // change to 2G, 4G, 8G, or 16G values.

#define SAMPLE_SIZE      4                 // Number of samples to use for a moving average of
                                           // on each accelerometer axis.  This smoothes out the
                                           // readings so they're less noisey.


// Create NeoPixel object.
Adafruit_NeoPixel pixels = Adafruit_NeoPixel(PIXEL_COUNT, PIXEL_PIN, PIXEL_TYPE);

// Create LIS3DH accelerometer library object, this will by default use an I2C connection.
Adafruit_LIS3DH accel = Adafruit_LIS3DH();

// Keep a moving average of the last few accelerometer samples to smooth out the readings.
// This helps reduce random noise and spikes/jumps in the data.
long x_samples[SAMPLE_SIZE] = { 0 };
long y_samples[SAMPLE_SIZE] = { 0 };
long z_samples[SAMPLE_SIZE] = { 0 };


void lightPixels(uint32_t color, Adafruit_NeoPixel& strip) {
  // Light all the NeoPixels in the strip with the provided color.
  for (int i=0; i < strip.numPixels(); ++i) {
    strip.setPixelColor(i, color);
  }
  strip.show();
}

uint32_t colorLerp(float x, float x0, float x1, uint32_t c0, uint32_t c1)
{
  // Simple linear interpolation of a color within the range c0, c1 based on
  // a value x that falls within the range of x0, x1.  The Arduino map function
  // is similar but only works on signed integer values.
  // First clamp x to be in the provided range.
  x = constrain(x, x0, x1);
  // Next compute the scaling factor based on X's position between x0 and x1.
  float scale = (x-x0)/(x1-x0);
  // Pull out the red, green, blue component values from each min/max color.
  uint8_t c0_red   = (c0 >> 16) & 0xFF;
  uint8_t c1_red   = (c1 >> 16) & 0xFF;
  uint8_t c0_green = (c0 >> 8) & 0xFF;
  uint8_t c1_green = (c1 >> 8) & 0xFF;
  uint8_t c0_blue  = c0 & 0xFF;
  uint8_t c1_blue  = c1 & 0xFF;
  // Scale each color component independently, then reassemble into a new color.
  uint8_t red   = c0_red   + (c1_red   - c0_red  ) * scale;
  uint8_t green = c0_green + (c1_green - c0_green) * scale;
  uint8_t blue  = c0_blue  + (c1_blue  - c0_blue ) * scale;
  return Adafruit_NeoPixel::Color(red, green, blue);
}

void addSample(long newSample, long* samples) {
  // Add a new sample to the array of samples.  Will shift out the earliest sample
  // to make room for the new sample.
  memmove(samples, samples+1, SAMPLE_SIZE-1);
  samples[SAMPLE_SIZE-1] = newSample;
}

long avgSample(long* samples) {
  // Return the average sample value in the provided array of samples.
  long result = 0;
  for (int i=0; i < SAMPLE_SIZE; ++i) {
    result += samples[i];
  }
  return result/SAMPLE_SIZE;
}

void setup() {
  // Initialize serial port to print accelerometer output.
  Serial.begin(9600);
  // Initialize LIS3DH accelerometer library.
  if (!accel.begin()) {
    Serial.println("Couldn't find LIS3DH, is it connected?");
    while(1);
  }
  accel.setRange(ACCEL_RANGE);
  // Initialize NeoPixels.
  pixels.begin();
}

void loop() {
  // Take an accelerometer reading and add to lists of samples.
  accel.read();
  addSample(accel.x, x_samples);
  addSample(accel.y, y_samples);
  addSample(accel.z, z_samples);
  // Now print out the average X, Y, Z sample values.
  long x = avgSample(x_samples);
  long y = avgSample(y_samples);
  long z = avgSample(z_samples);
  Serial.print("X:  ");
  Serial.print(x); 
  Serial.print("  \tY:  ");
  Serial.print(y); 
  Serial.print("  \tZ:  ");
  Serial.println(z);
  // Map the Y axis accelerometer value to a pixel color and light the pixels.
  uint32_t color = colorLerp(y, AXIS_MIN, AXIS_MAX, COLOR_MIN, COLOR_MAX);
  lightPixels(color, pixels);
  // Delay to slow things down and prevent spamming serial port.
  delay(100);
}

