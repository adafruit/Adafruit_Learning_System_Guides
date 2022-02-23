// SPDX-FileCopyrightText: 2021 Kattni Rembor for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>
#include <RotaryEncoder.h>
#include "HID-Project.h"  // https://github.com/NicoHood/HID

// Create the neopixel strip with the built in definitions NUM_NEOPIXEL and PIN_NEOPIXEL
Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_NEOPIXEL, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);
int16_t neo_brightness = 20; // initialize with 20 brightness (out of 255)

RotaryEncoder encoder(PIN_ENCODER_A, PIN_ENCODER_B, RotaryEncoder::LatchMode::FOUR3);
// This interrupt will do our encoder reading/checking!
void checkPosition() {
  encoder.tick(); // just call tick() to check the state.
}

int last_rotary = 0;
bool last_button = false;

void setup() {
  Serial.begin(115200);
  //while (!Serial);
  delay(100);
  
  Serial.println("Rotary Trinkey Volume Knob");
  
  // start neopixels
  strip.begin();
  strip.setBrightness(neo_brightness);
  strip.show(); // Initialize all pixels to 'off'

  attachInterrupt(PIN_ENCODER_A, checkPosition, CHANGE);
  attachInterrupt(PIN_ENCODER_B, checkPosition, CHANGE);
  
  // set up the encoder switch, which is separate from the encoder
  pinMode(PIN_ENCODER_SWITCH, INPUT_PULLDOWN);

  // Sends a clean report to the host. This is important on any Arduino type.
  Consumer.begin();
}


void loop() {
  // read encoder
  int curr_rotary = encoder.getPosition();
  RotaryEncoder::Direction direction = encoder.getDirection();
  // read switch
  bool curr_button = !digitalRead(PIN_ENCODER_SWITCH);
  
  if (direction != RotaryEncoder::Direction::NOROTATION) {
    Serial.print("Encoder value: ");
    Serial.print(curr_rotary);
    Serial.print(" direction: ");
    Serial.print((int)direction);

    if (direction == RotaryEncoder::Direction::CLOCKWISE) {
      Serial.println(" Vol +");
      Consumer.write(MEDIA_VOLUME_UP);
    }
    if (direction == RotaryEncoder::Direction::COUNTERCLOCKWISE) {
      Serial.println(" Vol -");
      Consumer.write(MEDIA_VOLUME_DOWN);
    }

    last_rotary = curr_rotary;
  }

  if (curr_button && !last_button) { // switch pressed!
    Serial.println("Play/Pause");
    Consumer.write(MEDIA_PLAY_PAUSE);
  }
  last_button = curr_button;

  delay(10); // debounce
}
