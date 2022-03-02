// SPDX-FileCopyrightText: 2020 Phillip Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#if 0 // Change to 1 to enable this code (must enable ONE user*.cpp only!)

// PIR motion sensor on pin 3 makes eyes open when motion is detected.

#include "globals.h"

#define PIR_PIN 3  // PIR sensor on D3 connector (between MIC & BAT)

static uint8_t priorState;

void user_setup(void) {
  pinMode(PIR_PIN, INPUT);
  priorState = digitalRead(PIR_PIN);
  for(uint8_t e=0; e<NUM_EYES; e++) {
    // Init to DEBLINK with an impossibly large duration to hold eyes shut.
    eye[e].blink.state     = DEBLINK;
    eye[e].blink.duration  = 0x7FFFFFFF;
    eye[e].blink.startTime = micros();
  }
}

void user_loop(void) {
  uint8_t e, newState = digitalRead(PIR_PIN);
  if(newState != priorState) {
    if(newState) {
      // Initial motion sensed
      for(e=0; e<NUM_EYES; e++) {          // For each eye...
        eye[e].blink.state     = DEBLINK;  // Opening...
        eye[e].blink.duration  = 500000;   // Slowly, about 1/2 sec
        eye[e].blink.startTime = micros(); // Starting now
      }
    } else {
      // PIR timeout; "end" of motion
      for(e=0; e<NUM_EYES; e++) {            // For each eye...
        if(eye[e].blink.state != ENBLINK) {  // If not already blinking...
          eye[e].blink.state     = ENBLINK;  // Start closing...
          eye[e].blink.duration  = 1500000;  // Even slower, about 1.5 sec
          eye[e].blink.startTime = micros(); // Starting now
        }
      }
    }
    priorState = newState;
  } else if(!newState) {
    // No change in state. If currently no motion active,
    // force eyes into closed position at every opportunity.
    for(e=0; e<NUM_EYES; e++) {           // For each eye...
      if(eye[e].blink.state != ENBLINK) { // If not currently blinking...
        // Set to DEBLINK with an impossibly large duration -- eyes will
        // hold shut until motion event above resets start & duration.
        eye[e].blink.state     = DEBLINK;
        eye[e].blink.duration  = 0x7FFFFFFF;
        eye[e].blink.startTime = micros();
      }
    }
  }
}

#endif // 0
