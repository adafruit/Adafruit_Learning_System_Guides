// SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>
#include "Adafruit_FreeTouch.h"
#include <RotaryEncoder.h>

// Create the neopixel strip with the built in definitions NUM_NEOPIXEL and PIN_NEOPIXEL
Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_NEOPIXEL, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);
int16_t neo_brightness = 20; // initialize with 20 brightness (out of 255)

RotaryEncoder encoder(PIN_ENCODER_A, PIN_ENCODER_B, RotaryEncoder::LatchMode::FOUR3);
// This interrupt will do our encoder reading/checking!
void checkPosition() {
  encoder.tick(); // just call tick() to check the state.
}

uint8_t wheel_offset = 99;
int last_rotary = 0;

void setup() {
  Serial.begin(115200);
  //while (!Serial);

  // start neopixels
  strip.begin();
  strip.setBrightness(neo_brightness);
  strip.show(); // Initialize all pixels to 'off'

  attachInterrupt(PIN_ENCODER_A, checkPosition, CHANGE);
  attachInterrupt(PIN_ENCODER_B, checkPosition, CHANGE);
  
  // set up the encoder switch, which is separate from the encoder
  pinMode(PIN_ENCODER_SWITCH, INPUT_PULLDOWN);
}


void loop() {
  // read encoder
  int curr_rotary = encoder.getPosition();
  RotaryEncoder::Direction direction = encoder.getDirection();
  
  if (curr_rotary != last_rotary) {
    Serial.print("Encoder value: ");
    Serial.print(curr_rotary);
    Serial.print(" direction: ");
    Serial.print((int)direction);

    // behavior differs if switch is pressed
    if (!digitalRead(PIN_ENCODER_SWITCH)) {
      // update color
      if (direction == RotaryEncoder::Direction::CLOCKWISE) {
        wheel_offset++;
      }
      if (direction == RotaryEncoder::Direction::COUNTERCLOCKWISE) {
        wheel_offset--;
      }
    } else {
      // update brightness
      if (direction == RotaryEncoder::Direction::CLOCKWISE) {
        neo_brightness += 10;
      }
      if (direction == RotaryEncoder::Direction::COUNTERCLOCKWISE) {
        neo_brightness -= 10;
      }
      // ranges between 0 and 255
      if (neo_brightness > 255) neo_brightness = 255;
      if (neo_brightness < 0) neo_brightness = 0;
    }
    Serial.print(" wheel color: ");
    Serial.print(wheel_offset);
    Serial.print(" brightness: ");
    Serial.println(neo_brightness);

    last_rotary = curr_rotary;

    // update pixels!
    strip.setBrightness(neo_brightness);
    strip.setPixelColor(0, Wheel(wheel_offset));
    strip.show();
  }
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
