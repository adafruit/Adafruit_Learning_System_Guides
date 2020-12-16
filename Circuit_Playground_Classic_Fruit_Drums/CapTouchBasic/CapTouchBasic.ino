////////////////////////////////////////////////////////////////////////////
// Circuit Playground Capacitive Touch Basic
//
// Print text messages for each touch pad.
//
// Author: Carter Nelson
// MIT License (https://opensource.org/licenses/MIT)

#include <Adafruit_CircuitPlayground.h>

#define CAP_THRESHOLD   50
#define DEBOUNCE        250

uint8_t pads[] = {3, 2, 0, 1, 12, 6, 9, 10};
uint8_t numberOfPads = sizeof(pads)/sizeof(uint8_t);

////////////////////////////////////////////////////////////////////////////
void takeAction(uint8_t pad) {
  Serial.print("PAD "); Serial.print(pad); Serial.print(" says: ");
  switch (pad) {
    case 3:
      Serial.println("The goggles! They do nothing!");
      break;
    case 2:
      Serial.println("Dental plan!");
      break;
    case 0:
      Serial.println("Lisa needs braces.");
      break;
    case 1:
      Serial.println("I call the large one Bitey.");
      break;
    case 12:
      Serial.println("I'm Idaho!");
      break;
    case 6:
      Serial.println("Monorail!");
      break;
    case 9:
      Serial.println("I choo-choo choose you.");
      break;
    case 10:
      Serial.println("Maaaattlllock!");
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
      
      // But not too often.
      delay(DEBOUNCE);
    }
  }
}
