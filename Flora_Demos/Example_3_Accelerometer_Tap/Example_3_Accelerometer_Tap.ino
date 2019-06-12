// Example of tapping accelerometer to light NeoPixels.
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

#define SINGLE_COLOR     Adafruit_NeoPixel::Color(255, 0, 0)  // RGB color for single tap/click.

#define DOUBLE_COLOR     Adafruit_NeoPixel::Color(0, 0, 255)  // RGB color for double tap/click.

#define LIGHT_ON_MS      1000              // Number of milliseconds to turn on the LED
                                           // when a tap or double tap occurs.


#define ACCEL_RANGE      LIS3DH_RANGE_2_G  // Range of acceleration values for the LIS3DH.
                                           // Can change to 2G, 4G, 8G, or 16G values.

#define CLICK_THRESHOLD  80                // Sensitivity of click force.  Depends on the range above,
                                           // for 16G try 5-10, for 8G try 10-20, for 4G try 20-40, 
                                           // for 2G try 40-80.


// Create NeoPixel object.
Adafruit_NeoPixel pixels = Adafruit_NeoPixel(PIXEL_COUNT, PIXEL_PIN, PIXEL_TYPE);

// Create LIS3DH accelerometer library object, this will by default use an I2C connection.
Adafruit_LIS3DH accel = Adafruit_LIS3DH();

// Keep track of when to turn off the pixels if they've been lit by a tap.
uint32_t pixelOff = 0;

void lightPixels(uint32_t color, Adafruit_NeoPixel& strip) {
  // Light all the NeoPixels in the strip with the provided color.
  for (int i=0; i < strip.numPixels(); ++i) {
    strip.setPixelColor(i, color);
  }
  strip.show();
}

void setup() {
  // Initialize serial port.
  Serial.begin(9600);
  // Initialize LIS3DH accelerometer library.
  if (!accel.begin()) {
    Serial.println("Couldn't find LIS3DH, is it connected?");
    while(1);
  }
  accel.setRange(ACCEL_RANGE);
  accel.setClick(2, CLICK_THRESHOLD);
  // Initialize NeoPixels and clear them.
  pixels.begin();
  pixels.clear();
  pixels.show();
}

void loop() {
  // Turn off the pixels if we're past the time they should turn off.
  if (millis() >= pixelOff) {
    pixels.clear();
    pixels.show();
  }
  // Check for an accelerometer tap/click.
  uint8_t click = accel.getClick();
  // Stop if nothing was detected or an error.
  if ((click == 0) || !(click & 0x30)) {
    return;
  }
  // Check if a single click and light the pixels.
  if (click & 0x10) {
    lightPixels(SINGLE_COLOR, pixels);
    // Set time for pixels to turn off 
    pixelOff = millis() + LIGHT_ON_MS;
  }
  // Check if a double click and light the pixels.
  if (click & 0x20) {
    lightPixels(DOUBLE_COLOR, pixels);
    pixelOff = millis() + LIGHT_ON_MS;
  }
  // Small delay to keep from grabbing LIS3DH data too quickly.
  delay(10);
}

