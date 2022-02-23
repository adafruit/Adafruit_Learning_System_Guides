// SPDX-FileCopyrightText: 2020 Carter Nelson for Adafruit Industries
//
// SPDX-License-Identifier: MIT

////////////////////////////////////////////////////////////////////////////
// Circuit Playground Capacitive Touch Tones
//
// Play a tone for each touch pad.
// Using 4th octave note frequencies, to nearest 1Hz.
// https://www.seventhstring.com/resources/notefrequencies.html
//
// Author: Carter Nelson
// MIT License (https://opensource.org/licenses/MIT)

#include <Adafruit_CircuitPlayground.h>

#define CAP_THRESHOLD   50

uint8_t pads[] = {3, 2, 0, 1, 12, 6, 9, 10};
uint8_t numberOfPads = sizeof(pads)/sizeof(uint8_t);

////////////////////////////////////////////////////////////////////////////
void takeAction(uint8_t pad) {
  Serial.print("PAD "); Serial.print(pad); Serial.print(" playing note: ");
  switch (pad) {
    case 3:
      Serial.println("C");
      CircuitPlayground.playTone(262, 100, false);
      break;
    case 2:
      Serial.println("D");
      CircuitPlayground.playTone(294, 100, false);
      break;
    case 0:
      Serial.println("E");
      CircuitPlayground.playTone(330, 100, false);
      break;
    case 1:
      Serial.println("F");
      CircuitPlayground.playTone(349, 100, false);
      break;
    case 12:
      Serial.println("G");
      CircuitPlayground.playTone(392, 100, false);
      break;
    case 6:
      Serial.println("A");
      CircuitPlayground.playTone(440, 100, false);
      break;
    case 9:
      Serial.println("B");
      CircuitPlayground.playTone(494, 100, false);
      break;
    case 10:
      Serial.println("C");
      CircuitPlayground.playTone(523, 100, false);
      break;
    default:
      Serial.println("THIS SHOULD NEVER HAPPEN.");
  }
}

////////////////////////////////////////////////////////////////////////////
boolean capButton(uint8_t pad) {
  // Check if capacitive touch exceeds threshold.
  if (CircuitPlayground.readCap(pad) > CAP_THRESHOLD) {
    return true;  
  } else {
    return false;
  }
}

////////////////////////////////////////////////////////////////////////////
void setup() {
  // Initialize serial.
  Serial.begin(9600); 
  
  // Initialize Circuit Playground library.
  CircuitPlayground.begin();

}

////////////////////////////////////////////////////////////////////////////
void loop() {
  // Loop over every pad.
  for (int i=0; i<numberOfPads; i++) {
    
    // Check if pad is touched.
    if (capButton(pads[i])) {
      
      // Do something.
      takeAction(pads[i]);
    }
  }
}
