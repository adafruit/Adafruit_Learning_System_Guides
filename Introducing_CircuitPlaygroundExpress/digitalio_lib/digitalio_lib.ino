// SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_CircuitPlayground.h>

void setup() {
  // Initialize the circuit playground
  CircuitPlayground.begin();
}

void loop() {
  // If the left button is pressed....
  if (CircuitPlayground.leftButton()) {
      CircuitPlayground.redLED(HIGH);  // LED on
  } else {
      CircuitPlayground.redLED(LOW);   // LED off
  }
}

