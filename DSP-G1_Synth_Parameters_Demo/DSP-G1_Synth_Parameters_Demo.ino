// SPDX-FileCopyrightText: 2018 John Park for Adafruit Industries
//
// SPDX-License-Identifier: MIT

//DSP-G1_Synth_Parameters_Demo
//Feather M0 Express connected to DSP-G1 voice chip over TX pin

#include <MIDI.h>
MIDI_CREATE_DEFAULT_INSTANCE();
static const unsigned LED = 13;      // LED pin on the Feather

void setup() {
  Serial.begin(115200);
  pinMode(LED, OUTPUT);
  MIDI.begin(1);

/////////////DSP-G1 CC Parameter Settings
//arguments are CC number, followed by value, and MIDI out channel
  MIDI.sendControlChange( 7, 120, 1);   //volume
  MIDI.sendControlChange( 1,   0, 1);   //LFO mod
  MIDI.sendControlChange(16,   6, 1);   //LFO rate
  MIDI.sendControlChange(20,   0, 1);   //LFO waveform 0-63 sine, 64-127 S/H
  MIDI.sendControlChange(74,  80, 1);   //DC Filter cutoff - higher number lets more harmonics through
  MIDI.sendControlChange(71,   0, 1);   //DC Filter resonance
  MIDI.sendControlChange(82,  32, 1);   //DC Filter envelope Attack
  MIDI.sendControlChange(83,  38, 1);   //DC Filter envelope Decay
  MIDI.sendControlChange(28,  64, 1);   //DC Filter envelope Sustain
  MIDI.sendControlChange(29,  32, 1);   //DC Filter envelope Release
  MIDI.sendControlChange(81,  57, 1);   //DC Filter envelope modulation
  MIDI.sendControlChange(76, 100, 1);   //DC Oscillator waveform* 100
  MIDI.sendControlChange( 4,   0, 1);   //DC Oscillator wrap
  MIDI.sendControlChange(21,   0, 1);   //DC Oscillator range
  MIDI.sendControlChange(93,   4, 1);   //DC Oscillator detune
  MIDI.sendControlChange(73,   5, 1);   //DC Oscillator envelope Attack
  MIDI.sendControlChange(75,  12, 1);   //DC Oscillator envelope Decay
  MIDI.sendControlChange(31,  60, 1);   //DC Oscillator envelope Sustain
  MIDI.sendControlChange(72,  80, 1);   //DC Oscillator envelope Release
// Wavforms: 0 tri, 25 squarish, 50 pulse, 75 other squarish, 100 saw
}

void loop() {
  digitalWrite(LED, HIGH);
  Serial.println("Playing notes");
  //Play a C
  MIDI.sendNoteOn(24,127,1); //note 24 is C1, velocity 127, channel 1)
  //Velocity isn't implemented, but it's a good habit to specify it
  delay(1000);

  //Play an E
  MIDI.sendNoteOff(24,0,1); // note 24, velocity 0, channel 1
  delay(250);
  MIDI.sendNoteOn(28,127,1); //note E1
  delay(1000);

  //Play a G
  MIDI.sendNoteOff(28,0,1);
  delay(250);
  MIDI.sendNoteOn(31,127,1); //note G1
  delay(1000);

  //Play an A#
  MIDI.sendNoteOff(31,0,1);
  delay(250);
  MIDI.sendNoteOn(34,127,1); //note G1
  delay(1000);
  MIDI.sendNoteOff(34,0,1);

  //rest
  delay(500);
  //chord
  MIDI.sendNoteOn(12,127,1); //C0
  MIDI.sendNoteOn(28,127,1); //E2
  MIDI.sendNoteOn(31,127,1); //G2
  MIDI.sendNoteOn(34,127,1); //A#2
  MIDI.sendNoteOn(48,127,1); //C3
  //hold
  delay(4000);

  //filter cutoff frequency sweep
  sweepFilterCutoff(1,15); //turn the filter cutoff knob to the right
  sweepFilterCutoff(0,15); //turn the filter cutoff knob to the left

  //filter cutoff and resonance sweeps
  sweepFilterCutoff(1,15); //turn the filter cutoff knob to the right
  sweepFilterResonance(1,15); //turn the filter resonance peak knob to the right
  sweepFilterCutoff(0,15); //turn down the cutoff
  sweepFilterResonance(0,15); //and turn down the resonance
  //hold here
  delay(2000);

  //oscillator detune
  sweepDetune(1,15); //turn up the detune
  //hold to listen to that detune
  delay(3000);
  sweepDetune(0, 15); //turn it back down
  delay(2000);

  digitalWrite(LED, LOW);
  Serial.println("Notes off");
  MIDI.sendNoteOff(12,0,1);
  MIDI.sendNoteOff(28,0,1);
  MIDI.sendNoteOff(31,0,1);
  MIDI.sendNoteOff(34,0,1);
  MIDI.sendNoteOff(48,0,1);
  delay(200);
}

void sweepFilterCutoff(int dir,int rate){ //dir 0 down, dir 1 up. rate in ms, e.g. 30
  if(dir==1){ //sweep up
    for(int i = 0; i < 128; i++){
      MIDI.sendControlChange(74,i,1);
      delay(rate);
      Serial.print("Filter cutoff: "); Serial.println(i);
    }
  }
  else{ //sweep down
    for(int i = 127; i >=0 ; i--){
      MIDI.sendControlChange(74,i,1);
      delay(rate);
      Serial.print("Filter cutoff: "); Serial.println(i);
    }
  }
}

void sweepDetune(int dir,int rate){ //dir 0 down, dir 1 up. rate in ms, e.g. 30
  if(dir==1){ //sweep up
    for(int i = 0; i < 128; i++){
      MIDI.sendControlChange(93,i,1);
      delay(rate);
      Serial.print("Detune: "); Serial.println(i);
    }
  }
  else{ //sweep down
    for(int i = 127; i >=0 ; i--){
      MIDI.sendControlChange(93,i,1);
      delay(rate);
      Serial.print("Detune: "); Serial.println(i);
    }
  }
}

void sweepFilterResonance(int dir,int rate){ //dir 0 down, dir 1 up. rate in ms, e.g. 30
  if(dir==1){ //sweep up
    for(int i = 0; i < 100; i++){ //127 has loads of feedback
      MIDI.sendControlChange(71,i,1);
      delay(rate);
      Serial.print("Filter resonance: "); Serial.println(i);
    }
  }
  else{ //sweep down
    for(int i = 127; i >=0 ; i--){
      MIDI.sendControlChange(71,i,1);
      delay(rate);
      Serial.print("Filter resonance: "); Serial.println(i);
    }
  }
}
