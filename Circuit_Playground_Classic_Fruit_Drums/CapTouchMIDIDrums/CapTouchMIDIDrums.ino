// SPDX-FileCopyrightText: 2020 Carter Nelson for Adafruit Industries
//
// SPDX-License-Identifier: MIT

////////////////////////////////////////////////////////////////////////////
// Circuit Playground Capacitive Touch USB MIDI Drums
//
// Send MIDI percussion commands over USB.
// https://www.arduino.cc/en/Reference/MIDIUSB
// https://en.wikipedia.org/wiki/General_MIDI#Percussion
//
// Author: Carter Nelson
// MIT License (https://opensource.org/licenses/MIT)

#include <Adafruit_CircuitPlayground.h>
#include "MIDIUSB.h"

#define CAP_THRESHOLD   50
#define DEBOUNCE        100

uint8_t pads[] = {3, 2, 0, 1, 12, 6, 9, 10};
uint8_t numberOfPads = sizeof(pads)/sizeof(uint8_t);

////////////////////////////////////////////////////////////////////////////
void takeAction(uint8_t pad) {
  Serial.print("PAD "); Serial.print(pad); Serial.print(". Sending MIDI: ");
  switch (pad) {
    case 3:
      Serial.println("36");
      drumHit(36);
      break;
    case 2:
      Serial.println("37");
      drumHit(37);
      break;
    case 0:
      Serial.println("38");
      drumHit(38);
      break;
    case 1:
      Serial.println("39");
      drumHit(39);
      break;
    case 12:
      Serial.println("40");
      drumHit(40);
      break;
    case 6:
      Serial.println("41");
      drumHit(41);
      break;
    case 9:
      Serial.println("42");
      drumHit(42);
      break;
    case 10:
      Serial.println("43");
      drumHit(43);
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
void noteOn(byte channel, byte pitch, byte velocity) {
  // Send a MIDI Note On command.
  midiEventPacket_t noteOn = {0x09, 0x90 | channel, pitch, velocity};
  MidiUSB.sendMIDI(noteOn);
}

////////////////////////////////////////////////////////////////////////////
void noteOff(byte channel, byte pitch, byte velocity) {
  // Send a MIDI Note Off command.
  midiEventPacket_t noteOff = {0x08, 0x80 | channel, pitch, velocity};
  MidiUSB.sendMIDI(noteOff);
}

////////////////////////////////////////////////////////////////////////////
void drumHit(byte drum) {
  // Send Note On/Off command for given drum (note) number.
  noteOn(9, drum, 125);
  MidiUSB.flush();
  noteOff(9, drum, 0);
  MidiUSB.flush();
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
