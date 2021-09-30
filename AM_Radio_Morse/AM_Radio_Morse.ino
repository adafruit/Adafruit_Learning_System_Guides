# SPDX-FileCopyrightText: 2018 John Edgar Park for Adafruit Industries
#
# SPDX-License-Identifier: MIT

// For Adafruit_AMRadio library -- Morse code transmits on AM 540.
// Connect antenna (40" wire) to pin A0 and GND
// RANGE IS LIMITED TO A FEW FEET
// Morse "dot" key is a contact switch connected to D2 and GND
// "Dash" key is switch connected to D0 and GND
// Adapted from Phil Burgess's AMRadio sketch

#include <Adafruit_AMRadio.h>

Adafruit_AMRadio radio;

const int buttonDotPin = 2; //pushbutton pin for dit
const int buttonDashPin = 0; //pushbutton pin for dah
const int ledPin = 13; //to light the onboard LED

int buttonDotState = 0; //to store button state
int buttonDashState = 0;

//Morse varaiblas
const int PITCH = 680;
const int DOT = 100; //duration of short dot in millis
const int DASH = DOT * 3;
const int GAP = DOT;


void setup() {
  pinMode(ledPin, OUTPUT);
  pinMode(buttonDotPin, INPUT_PULLUP);
  pinMode(buttonDashPin, INPUT_PULLUP);

  radio.begin(540000); //start radio object, transmits at 540MHz AM
}  


void loop() {
  buttonDotState = digitalRead(buttonDotPin);
  buttonDashState = digitalRead(buttonDashPin);
  
  if (buttonDotState == HIGH) {    // not pressed
    digitalWrite(ledPin, LOW);   // light is off
  }
  else {                        // pressed
    digitalWrite(ledPin, HIGH);  // light on
    radio.tone(PITCH, DOT);
    delay(GAP);
  }
  if (buttonDashState == HIGH) {    // not pressed
    digitalWrite(ledPin, LOW);   // light is off
  }
  else {                        // pressed
    digitalWrite(ledPin, HIGH);  // light on
    radio.tone(PITCH, DASH);
    delay(GAP);
  }
  
  delay(15);
}
