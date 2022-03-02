// SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_CircuitPlayground.h>

void setup() {
  pinMode(CPLAY_LEFTBUTTON, INPUT_PULLDOWN);
  pinMode(CPLAY_REDLED, OUTPUT);
}

void loop() {
  // If the left button is pressed....
  if (digitalRead(CPLAY_LEFTBUTTON)) {
      digitalWrite(CPLAY_REDLED, HIGH);  // LED on
  } else {
      digitalWrite(CPLAY_REDLED, LOW);  // LED off
  }
}

