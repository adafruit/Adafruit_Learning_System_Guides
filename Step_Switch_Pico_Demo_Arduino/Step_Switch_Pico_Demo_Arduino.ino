// SPDX-FileCopyrightText: 2022 John Park for Adafruit Industries
// SPDX-License-Identifier: MIT
// Step Switch Party for Pico

// extra library used:
// Bounce2 -- https://github.com/thomasfredericks/Bounce2

#include <Wire.h>
#include <Bounce2.h>


const int num_buttons = 4;
const int led_pins[num_buttons] = {2, 3, 4, 5};
const int button_pins[num_buttons] = {6, 7, 8, 9}; 
Bounce buttons[num_buttons];
bool led_vals[num_buttons];


void setup() {
  Serial.begin(9600);
  delay(1000);
  Serial.println("Step Switch Pico Party");

  for (uint8_t i=0; i< num_buttons; i++){
    buttons[i].attach( button_pins[i], INPUT_PULLUP);
  }

  for (uint8_t i=0; i< num_buttons; i++){
      pinMode(led_pins[i], OUTPUT);
      digitalWrite(led_pins[i], HIGH);
      led_vals[i] = HIGH;
  }
}


void loop() {
  for (uint8_t i=0; i< num_buttons; i++){
    buttons[i].update();
    if( buttons[i].fell()) {
      // do something here, such as send MIDI, change a NeoPixel animation, etc.
      Serial.println(i);
      led_vals[i] = !led_vals[i];
      digitalWrite(led_pins[i], led_vals[i]);
    }
  }
  
}
