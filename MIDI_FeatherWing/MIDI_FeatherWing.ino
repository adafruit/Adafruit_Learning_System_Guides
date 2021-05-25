// SPDX-FileCopyrightText: 2021 John Park for Adafruit Industries
// SPDX-License-Identifier: MIT

// MIDI FeatherWing note player example


#include <MIDI.h>

#ifdef USE_TINYUSB
#include <Adafruit_TinyUSB.h>
#endif

MIDI_CREATE_DEFAULT_INSTANCE();

int notes[] = {69, 72, 74, 76, 72, 81, 79};  // melody notes
int vels[] = {127, 96, 64, 96, 32, 127, 64};  // velocity per note
int rests[] = {50, 50, 50, 50, 50, 200, 50};  // rests between notes
int note_mods[] = {0, 0, 0, 0, 3, 3, 3, 3, 0, 0, 0, 0, 5, 5, 3, 3};  // modifies notes for progression

void setup(){
    MIDI.begin(MIDI_CHANNEL_OMNI);
}

void loop() {

  for(int j=0; j<16; j++){  // loop through four measures for progression
    for(int i=0; i<7; i++){ //
      MIDI.sendNoteOn(notes[i]+note_mods[j], vels[i], 1);
      delay(100);
      MIDI.sendNoteOff(notes[i]+note_mods[j], 0, 1);
      delay(rests[i]);
    }
  }
}
