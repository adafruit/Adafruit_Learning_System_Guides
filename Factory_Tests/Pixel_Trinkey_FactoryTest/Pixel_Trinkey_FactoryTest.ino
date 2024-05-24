// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_DotStar.h>
#include <Adafruit_NeoPixel.h>

#define NUMPIXELS 64
Adafruit_DotStar  dotstrip(NUMPIXELS, PIN_DATA, PIN_CLOCK, DOTSTAR_BRG);
Adafruit_NeoPixel neostrip(NUMPIXELS, PIN_DATA, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel pixel(1, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800); // internal board pixel

void setup() {
  Serial.begin(115200);
  
  dotstrip.begin();
  dotstrip.setBrightness(25);
  dotstrip.show();

  neostrip.begin();
  neostrip.setBrightness(25);
  neostrip.show();

  pixel.begin();
  pixel.setBrightness(25);
  pixel.show();
}

uint16_t firstPixelHue = 0;
bool which_strip = false;

void loop() {  
  firstPixelHue += 256;

  if (which_strip == true) {
    // neopixel
    for(int i=0; i<neostrip.numPixels(); i++) {
      int pixelHue = firstPixelHue + (i * 65536L / neostrip.numPixels());
      neostrip.setPixelColor(i, neostrip.gamma32(neostrip.ColorHSV(pixelHue)));
    }
    neostrip.show();
  } else {
    // dotstar
    for(int i=0; i<dotstrip.numPixels(); i++) {
      int pixelHue = firstPixelHue + (i * 65536L / dotstrip.numPixels());
      dotstrip.setPixelColor(i, dotstrip.gamma32(dotstrip.ColorHSV(pixelHue)));
    }
    dotstrip.show();
  }
  pixel.setPixelColor(0, pixel.gamma32(pixel.ColorHSV(firstPixelHue)));
  pixel.show();
  delay(10);

  if (firstPixelHue == 0) {
    which_strip = !which_strip;
  }

  float powerVoltage;
  powerVoltage = analogRead(A0) / 1023.0 * 3.3;
  powerVoltage *= 2; // resistor divider by 2, so * by 2
  Serial.print("Power voltage: ");
  Serial.print(powerVoltage);
  Serial.println(" V");
}
