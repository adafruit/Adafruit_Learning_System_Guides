// SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>
#include "Adafruit_FreeTouch.h"
#include "HID-Project.h"  // https://github.com/NicoHood/HID

// Create the neopixel strip with the built in definitions NUM_NEOPIXEL and PIN_NEOPIXEL
Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_NEOPIXEL, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

// Create the touch pad
Adafruit_FreeTouch qt = Adafruit_FreeTouch(PIN_TOUCH, OVERSAMPLE_4, RESISTOR_50K, FREQ_MODE_NONE);

int16_t neo_brightness = 20; // initialize with 20 brightness (out of 255)

bool last_switch = true;

void setup() {
  Serial.begin(9600);
  //while (!Serial);
  strip.begin();
  strip.setBrightness(neo_brightness);
  strip.show(); // Initialize all pixels to 'off'

  if (! qt.begin())
    Serial.println("Failed to begin qt");

  pinMode(PIN_SWITCH, INPUT_PULLDOWN);

  // Sends a clean report to the host. This is important on any Arduino type.
  Consumer.begin();
}

uint8_t j=0;
void loop() {
  // measure the captouches
  uint16_t touch = qt.measure();
  // don't print touch data constantly, only every 10 runs
  if (j % 10 == 0) {
    Serial.print("Touch: "); Serial.println(touch);
  }

  // If the pad is touched, turn on neopix!
  if (touch > 500) {
    Serial.println("Touched!");
    strip.setBrightness(neo_brightness);
  } else {
    strip.setBrightness(0);
  }

  // check mechswitch
  bool curr_switch = digitalRead(PIN_SWITCH);
  if (curr_switch != last_switch) {
    if (curr_switch) {
      Serial.println("Pressed");
      Consumer.write(MEDIA_PLAY_PAUSE);
    } else {
      Serial.println("Released");
    }
    last_switch = curr_switch;
  }


  // cycles of all colors on wheel, only visible if cap it touched
  strip.setPixelColor(0, Wheel(j++));
  strip.show();

  delay(10);
}

// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  if(WheelPos < 85) {
   return strip.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
  } else if(WheelPos < 170) {
   WheelPos -= 85;
   return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  } else {
   WheelPos -= 170;
   return strip.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
}