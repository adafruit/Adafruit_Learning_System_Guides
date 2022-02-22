// SPDX-FileCopyrightText: 2018 John Edgar Park for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <MIDI.h>
#include "Adafruit_Trellis.h"
//use Trellis 0-11 and 16-27 as input for notes.
//use Trellis 12-15 and 28-31 for input to modes, sequencer, patches
//six potentiometers as CC value input
//rotary switch to choose banks of CC numbers for knobs

//John Park for Adafruit Industries

MIDI_CREATE_DEFAULT_INSTANCE();
Adafruit_Trellis matrix0 = Adafruit_Trellis(); //left Trellis
Adafruit_Trellis matrix1 = Adafruit_Trellis(); //right Trellis
Adafruit_TrellisSet trellis =  Adafruit_TrellisSet(&matrix0, &matrix1);
#define NUMTRELLIS 2
#define numKeys (NUMTRELLIS * 16)
//#define INTPIN A2
#define MOMENTARY 0
#define LATCHING 1
int holdMode = 0;
int lastHoldMode = 0;
static const unsigned LED = 13;      // LED pin on the Feather

/*********************/
//pick scale mode here:
//0=chromatic, 1=major, 2=minor, 3=dorian, 4=mixolydian, 5=harmonic minor
int scaleMode = 0; //Dorian
/*********************/
int octave = 1;
int transpose[6] = {0, 12, 24, 36, 48, 60}; //multiply notes depending on octave
//Trellis assignments
/*
//First three rows map to MIDI Notes, bottom row is special functions
-------------------------------------------------------------------------------
      0          1         2         3        16        17        18       19
     M16       M17        M18       M19       M20      M21       M22      M23


      4          5         6         7        20        21        22       23
     M8         M9        M10       M11       M12      M13       M14      M15


      8          9        10        11        24        25        26       27
     M0         M1        M2        M3        M4        M5        M6       M7
-------------------------------------------------------------------------------

    12         13        14        15        28        29        30       31
   seq       patch    pause/play  rec        I         II      III   hold mode
-------------------------------------------------------------------------------
*/

//Map physical Trellis grids to single logical grid
int logicalPads[32] = { 0,  1,  2,  3,  8,  9, 10, 11,
                 16, 17,  18,  19, 24, 25, 26, 27,
                 4,  5, 6, 7, 12, 13, 14, 15,
                20, 21, 22, 23, 28, 29, 30, 31 } ;

int padNoteMap[24] = { 16, 17, 18, 19, 20, 21, 22, 23,
                        8,  9, 10, 11, 12, 13, 14, 15,
                        0,  1,  2,  3,  4,  5,  6,  7};

int padFuncMap[8] = { //note, only hold mode is implemented currently
                      0, // sequencer
                      1, // patch
                      2, // pause/play / recall
                      3, // record / store
                      4, // sequence I / patch I
                      5, // seq. II / patch II
                      6, // seq. III / patch III
                      7 //hold mode: LATCHING or MOMENTARY
                    };
//Define Scales
int scalesMatrix[6][24] = {
//Chromatic
  { 0,  1,  2,  3,  4,  5,  6,  7,
    8,  9, 10, 11, 12, 13, 14, 15,
   16, 17, 18, 19, 20, 21, 22, 23 },

//Major
   { 0,  2,  4,  5,  7,  9, 11, 12,
    12, 14, 16, 17, 19, 21, 23, 24,
    24, 26, 28, 29, 31, 33, 35, 36 },

//Minor
   { 0,  2,  3,  5,  7,  8, 10, 12,
    12, 14, 15, 17, 19, 20, 22, 24,
    24, 26, 27, 29, 31, 32, 34, 36 },

//Dorian
   { 0,  2,  3,  5,  6,  9, 10, 12,
    12, 14, 15, 17, 18, 21, 22, 24,
    24, 26, 27, 29, 30, 33, 34, 36 },

//Mixolydian
   { 0,  2,  4,  5,  7,  9, 10, 12,
    12, 14, 16, 17, 19, 21, 22, 24,
    24, 26, 28, 29, 31, 33, 34, 36 },

//Harmonic Minor
   { 0,  2,  3,  5,  7,  8, 11, 12,
    12, 14, 15, 17, 19, 20, 23, 24,
    24, 26, 27, 29, 31, 32, 35, 36 }
};

//Set up selector switch pins to read digital input pins that set the CC bank
const int CC_bankPin0 = 9;
const int CC_bankPin1 = 10;
const int CC_bankPin2 = 11;
const int CC_bankPin3 = 12;

int CC_bankState0 = 0;
int CC_bankState1 = 0;
int CC_bankState2 = 0;
int CC_bankState3 = 0;

//current bank per knob. assume not on 0-3
int currentBank[6] = {4, 4, 4, 4, 4, 4};
//last bank per knob. assume not on 0-3
int lastBank[6]    = {5, 5, 5, 5, 5, 5};

//Set up potentiometer pins
const int CC0_pin = A0; //potentiometer pin
int CC0_value; //store pot value
const int CC1_pin = A1;
int CC1_value;
const int CC2_pin = A2;
int CC2_value;
const int CC3_pin = A3;
int CC3_value;
const int CC4_pin = A4;
int CC4_value;
const int CC5_pin = A5;
int CC5_value;

int CC_read[4] ;

//Store previous values to enable hysteresis and pick-up mode for knobs
int CC_bank0_lastValue[6] = {32, 32, 32, 32, 32, 32};
int CC_bank1_lastValue[6] = {32, 32, 32, 32, 32, 32};
int CC_bank2_lastValue[6] = {32, 32, 32, 32, 32, 32};
int CC_bank3_lastValue[6] = {32, 32, 32, 32, 32, 32};

int CC_bank0_value[6] = {0, 0, 0, 0, 0, 0};
int CC_bank1_value[6] = {0, 0, 0, 0, 0, 0};
int CC_bank2_value[6] = {0, 0, 0, 0, 0, 0};
int CC_bank3_value[6] = {0, 0, 0, 0, 0, 0};

void setup() {
  Serial.begin(115200);
  pinMode(LED, OUTPUT);
  digitalWrite(LED, HIGH); //turn this on as a system power indicator
  pinMode(CC_bankPin0, INPUT_PULLUP); //loop this
  pinMode(CC_bankPin1, INPUT_PULLUP);
  pinMode(CC_bankPin2, INPUT_PULLUP);
  pinMode(CC_bankPin3, INPUT_PULLUP);

  // Default Arduino I2C speed is 100 KHz, but the HT16K33 supports
  // 400 KHz.  We can force this for faster read & refresh, but may
  // break compatibility with other I2C devices...so be prepared to
  // comment this out, or save & restore value as needed.
#ifdef ARDUINO_ARCH_SAMD
  Wire.setClock(400000L);
#endif
#ifdef __AVR__
  TWBR = 12; // 400 KHz I2C on 16 MHz AVR
#endif

  trellis.begin(0x70, 0x71);
  for (uint8_t i=0; i<numKeys; i++) {
    trellis.setLED(i);
    trellis.writeDisplay();
    delay(15);
  }
  // then turn them off
  for (uint8_t i=0; i<numKeys; i++) {
    trellis.clrLED(i);
    trellis.writeDisplay();
    delay(15);
  }

  MIDI.begin(1);

  //All notes off MIDI panic if reset
  for(int n=0; n<128; n++){
    MIDI.sendNoteOff(n, 127, 1);  //DC Filter cutoff
  }

/////////////DSP-G1 CC Parameter Settings Defaults (to be changed with knobs)
  MIDI.sendControlChange( 7, 119, 1);   //volume
  MIDI.sendControlChange( 1, 24, 1);   //LFO mod 24
  MIDI.sendControlChange(16,  6, 1);   //LFO rate 12
  MIDI.sendControlChange(20,  0, 1);    //LFO waveform 0-63 sine, 64-127 S/H
  MIDI.sendControlChange(74, 80, 1);  //DC Filter cutoff
  MIDI.sendControlChange(71, 70, 1);   //DC Filter resonance
  MIDI.sendControlChange(82, 32, 1);   //DC Filter envelope Attack
  MIDI.sendControlChange(83, 38, 1);   //DC Filter envelope Decay
  MIDI.sendControlChange(28, 64, 1);   //DC Filter envelope Sustain
  MIDI.sendControlChange(29, 32, 1);   //DC Filter envelope Release
  MIDI.sendControlChange(81, 57, 1);   //DC Filter envelope modulation
  MIDI.sendControlChange(76, 100, 1);  //DC Oscillator waveform* 100
  MIDI.sendControlChange( 4,  0, 1);   //DC Oscillator wrap
  MIDI.sendControlChange(21,  0, 1);    //DC Oscillator range
  MIDI.sendControlChange(93,  0, 1);    //DC Oscillator detune
  MIDI.sendControlChange(73,  0, 1);   //DC Oscillator envelope Attack
  MIDI.sendControlChange(75, 12, 1);   //DC Oscillator envelope Decay
  MIDI.sendControlChange(31, 60, 1);   //DC Oscillator envelope Sustain
  MIDI.sendControlChange(72, 80, 1);   //DC Oscillator envelope Release
/*Wavforms: 0 tri, 25 squarish, 50 pulse, 75 other squarish, 100 saw      */
}

void loop(){
  //read selector switch pins to find CC knob bank
  CC_bankState0 = digitalRead(CC_bankPin0);//loop this
  CC_bankState1 = digitalRead(CC_bankPin1);
  CC_bankState2 = digitalRead(CC_bankPin2);
  CC_bankState3 = digitalRead(CC_bankPin3);
  int b; //to increment through current bank state values
  if (CC_bankState0 == LOW){ //low means it's the selected bank
    for (b=0;b<6;b++){currentBank[b] = 0;}
    read_CC_Knobs(0);
  }
  else if (CC_bankState1 == LOW){
    for (b=0;b<6;b++){currentBank[b] = 1;}
    read_CC_Knobs(1);
  }
  else if (CC_bankState2 == LOW){
    for (b=0;b<6;b++){currentBank[b] = 2;}
    read_CC_Knobs(2);
  }
  else if (CC_bankState3 == LOW){
    for (b=0;b<6;b++){currentBank[b] = 3;}
    read_CC_Knobs(3);
  }
  else { //4-7 have been picked, not connected
    for (b=0;b<6;b++){currentBank[b] = 4;}
  }

  //Trellis MIDI out Keyboard
  delay(30); // 30ms delay is required, dont remove me!

  if (holdMode == MOMENTARY) {
    if (trellis.readSwitches()) { // If a button was just pressed or released...
      for (uint8_t i=0; i<numKeys; i++) { // go through every button
        if (trellis.justPressed(i)) { // if it was pressed, map what it actually does
          //remap the physical button to logical button. 'p' is logical pad, i is physical pad. these names stink.
          int p = logicalPads[i];
          // Serial.print("logical pad: "); Serial.println(p);
          if(p<24){ //it's a MIDI note pad, play a note
            int padNote = logicalPads[i];
            MIDI.sendNoteOn((scalesMatrix[scaleMode][padNoteMap[padNote]] + transpose[octave]), 127, 1);
            //uncomment for debugging:
            /*
            Serial.print("v"); Serial.println(p); //print which button pressed
            trellis.setLED(i); //light stuff up
            Serial.print("OUT: "); //print MIDI out command
            Serial.print("\tChannel: "); Serial.print(1);
            Serial.print("\tNote: "); Serial.print(scalesMatrix[scaleMode][padNoteMap[padNote]] + transpose[octave]);
            Serial.print("\tValue: "); Serial.println("127");
            */
          }
          else if (p==31){ // last button on bottom row swaps hold modes
            holdMode = !holdMode;
            lastHoldMode = holdMode;
            //Serial.println("Hold mode switch to Latching.");
            for (uint8_t n=0; n<24; n++) { //clear note LEDs
              trellis.clrLED(n);
              trellis.writeDisplay();
            }
            trellis.setLED(i); //light stuff up
            trellis.writeDisplay();
            delay(30);
          }
          else{
            Serial.println("not a note");
          }
        }
        if (trellis.justReleased(i)) { // if it was released, turn it off
          int p = logicalPads[i];
          //Serial.print("logical pad: "); Serial.println(p);
          if(p<24){ //it's a MIDI note pad, play a note
            int padNote=logicalPads[i];
            MIDI.sendNoteOff((scalesMatrix[scaleMode][padNoteMap[padNote]] + transpose[octave]), 127, 1);
            //Serial.print("^"); Serial.println(p);
            for (uint8_t i=0; i<numKeys; i++) {
               trellis.clrLED(i);
               trellis.writeDisplay();
            }
            trellis.setLED(i); //keep last one that was pressed turned on
            //uncomment for debugging
            /*
            Serial.print("OUT: ");
            Serial.print("\tChannel: "); Serial.print(1);
            Serial.print("\tNote: "); Serial.print(scalesMatrix[scaleMode][padNoteMap[padNote]]+ transpose[octave]);
            */

            //Serial.print("\tValue: "); Serial.println("0");
          }
          else if (p==31){ // last button on bottom row swaps hold modes
          }
          else{
            Serial.println("not a note");
          }
        }
      }
      trellis.writeDisplay(); // tell the trellis to set the LEDs we requested
    }
  }

  if (holdMode == LATCHING) {
    if (trellis.readSwitches()) {
      for (uint8_t i=0; i<numKeys; i++) {
        if (trellis.justPressed(i)) {
          int p = logicalPads[i];
          //Serial.print("logical pad: "); Serial.println(p);
          if(p<24){
            int padNote = logicalPads[i];
            //Serial.print("pad note: "); Serial.println(padNote);
            //Serial.print("v"); Serial.println(i);
            if (trellis.isLED(i)){ // Alternate the button
              MIDI.sendNoteOff((scalesMatrix[scaleMode][padNoteMap[padNote]] + transpose[octave]), 127, 1);
              trellis.clrLED(i);
            }
            else{
              MIDI.sendNoteOn((scalesMatrix[scaleMode][padNoteMap[padNote]] + transpose[octave]), 127, 1);
              trellis.setLED(i);
            }
          }
          else if (i==31){ // last button on bottom row swaps hold modes
            holdMode = !holdMode;
            lastHoldMode = holdMode;
            for(int n=0; n<128; n++){
              MIDI.sendNoteOff(n, 127, 1);  //DC Filter cutoff
            }
            for (uint8_t j=0; j<24; j++) { //clear all note pads
              trellis.clrLED(j);
            }
            trellis.clrLED(i); //clear holdMode pad
            trellis.writeDisplay();
            //Serial.println("holdMode switch to Momentary.");
            delay(30);
          }
          else{
            Serial.println("not a note");
          }
        }
        trellis.writeDisplay();
      }
    }
  }
  //clear key LEDs after a hold mode change
  if(holdMode != lastHoldMode){
    //Serial.print("Hold mode: "); Serial.println(holdMode);
    //Serial.print("Last hold mode: "); Serial.println(lastHoldMode);
    for (uint8_t j=0; j<24; j++) { //clear all note pads
      trellis.clrLED(j);
    }
    trellis.writeDisplay();
  }
}

void read_CC_Knobs(int CC_bank){
  int AnalogPin[6] = {A0, A1, A2, A3, A4, A5}; //define the analog pins
  int CCKnob[6] = {0, 1, 2, 3, 4, 5}; //define knobs
  // choose which CC numbers are on each knob per bank
  // definitions are at bottom of code
  //Note: can set knobs to "never change" by repeating CC numbers per array
  int CCNumber[6]; //variable array to store the CC numbers
  if(CC_bank == 0){ //set the CC numbers per knob per bank
    //OSC
    int CCNumberChoice[6] = {71, //Filter resonance bottom of left knobs
                             74, //Filter cutoff top of left two knobs
                             21, //DCO range upper row
                             93, //DCO detune
                              4,  //DCO wrap
                             76 //DCO waveform

                       };
    for(int n=0; n<6; n++){
      CCNumber[n] = CCNumberChoice[n];
    }
  }
  else if(CC_bank == 1){
    //Envelope (for main oscillators)
    int CCNumberChoice[6] = {71, //Filter resonance
                             74, //Filter cutoff top of left two knobs
                             82, //VCA Attack
                             83, //VCA Decay
                             28, //VCA Sustain
                             29  //VCA Release
                       };
    for(int n=0; n<6; n++){
      CCNumber[n] = CCNumberChoice[n];
    }
  }
  else if(CC_bank == 2){
    //LFO low frequency oscillator for main OSC
    int CCNumberChoice[6] = {71, //Filter resonance
                             74, //Filter cutoff top of left two knobs
                              1, //LFO mod
                             16, //LFO rate
                             20, //LFO waveform shape
                             81  //Filter mod
                       };
    for(int n=0; n<6; n++){
      CCNumber[n] = CCNumberChoice[n];
    }
  }

  else if(CC_bank == 3){
    //Envelope (for filter)
    int CCNumberChoice[6] = {71,  //Filter resonance
                             74, //Filter cutoff top of left two knobs
                              1, //Filter A
                             16, //Filter D
                             20, //Filter S
                             81 //Filter R
                       };
    for(int n=0; n<6; n++){
      CCNumber[n] = CCNumberChoice[n];
    }
  }
  //Knob pick-up mode -- to deal with multiple knob banks,
  //value doesn't get sent until knob reaches pravious ("last") position
  //NOTE: ugly way to do this, clean it up so a matrix is used instead
  //per bank loop currently

  //Send CC values only when they change beyond last value to avoid getting stuck between two values
  //thanks to Groovesizer Foxtrot code for this idea: https://groovesizer.com/foxtrot/
  //thanks to Todbot for the delta hysteresis idea

  if(CC_bank == 0){ //first bank is selected
    for(int k=0; k<6; k++){ //loop through each of six pots
      if(currentBank[k] != lastBank[k]){ //if the current bank for current knob
        //digitalWrite(LED, LOW);
        //is different than the last bank for the current knob:
       //read CC values from potentiometers
        CC_read[CC_bank] = analogRead(AnalogPin[k]);
        CC_bank0_value[k] = map(CC_read[CC_bank], 0, 1023, 0, 127); // remap range to 0-127
        //check against last read when we were on this bank, only send CC if value
        //of knob is withing a certain delta of the last value
        if((abs(CC_bank0_lastValue[k] - CC_bank0_value[k])) < 3){ //hysteresis for spinning knob too fast
          Serial.println("PICKUP ACHIEVED");
          //digitalWrite(LED, HIGH);
          Serial.print("\nCC_bank0_value for knob: "); Serial.print(k); Serial.print("\t"); Serial.println(CC_bank0_value[k]);
          Serial.print("CC_bank0_lastValue for knob: "); Serial.print(k); Serial.print("\t"); Serial.println(CC_bank0_lastValue[k]);
          lastBank[k] = 0;
        }
      }
      else if(currentBank[k] == lastBank[k]){
        //read CC values from potentiometers
        CC_read[CC_bank] = analogRead(AnalogPin[k]);
        CC_bank0_value[k] = map(CC_read[CC_bank], 0, 1023, 0, 127); // remap range to 0-127
        //check against last read, only send CC if value has changed since last read by a certain delta
        if((abs(CC_bank0_lastValue[k] - CC_bank0_value[k])) > 3){ //hysteresis for spinning knob too fast
          Serial.print("\nCC_bank0_value for knob: "); Serial.print(k); Serial.print("\t"); Serial.println(CC_bank0_value[k]);
          Serial.print("CC_bank0_lastValue for knob: "); Serial.print(k); Serial.print("\t"); Serial.println(CC_bank0_lastValue[k]);
          MIDI.sendControlChange(CCNumber[k], CC_bank0_value[k], 1);
          //Serial.print("CC number: "); Serial.println(CCNumber[k]);
          CC_bank0_lastValue[k] = CC_bank0_value[k];
          lastBank[k] = 0;
        }
      }
    }
  }

  if(CC_bank == 1){ //second bank is selected
    for(int k=0; k<6; k++){ //loop through each of six pots
      if(currentBank[k] != lastBank[k]){
       //read CC values from potentiometers
        CC_read[CC_bank] = analogRead(AnalogPin[k]);
        CC_bank1_value[k] = map(CC_read[CC_bank], 0, 1023, 0, 127); // remap range to 0-127
        //check against last read when we were on this bank, only send CC if value
        //of knob is withing a certain delta of the last value
        if((abs(CC_bank1_lastValue[k] - CC_bank1_value[k])) < 3){ //hysteresis for spinning knob too fast
          Serial.println("Pickup achieved.");
          Serial.print("\nCC_bank1_value for knob: "); Serial.print(k); Serial.print("\t"); Serial.println(CC_bank1_value[k]);
          Serial.print("CC_bank1_lastValue for knob: "); Serial.print(k); Serial.print("\t"); Serial.println(CC_bank1_lastValue[k]);
          lastBank[k] = 1;
        }
      }
      else if(currentBank[k] == lastBank[k]){
        //read CC values from potentiometers
          CC_read[CC_bank] = analogRead(AnalogPin[k]);
          CC_bank1_value[k] = map(CC_read[CC_bank], 0, 1023, 0, 127); // remap range to 0-127
          //check against last read, only send CC if value has changed since last read by a certain delta
        if((abs(CC_bank1_lastValue[k] - CC_bank1_value[k])) > 3){ //hysteresis for spinning knob too fast
          Serial.print("\nCC_bank1_value for knob: "); Serial.print(k); Serial.print("\t"); Serial.println(CC_bank1_value[k]);
          Serial.print("CC_bank1_lastValue for knob: "); Serial.print(k); Serial.print("\t"); Serial.println(CC_bank1_lastValue[k]);
          MIDI.sendControlChange(CCNumber[k], CC_bank1_value[k], 1);
          //Serial.print("CC number: "); Serial.println(CCNumber[k]);
          CC_bank1_lastValue[k] = CC_bank1_value[k];
          lastBank[k] = 1;
        }
      }
    }
  }
  if(CC_bank == 2){ //third bank is selected
    for(int k=0; k<6; k++){ //loop through each of six pots
      if(currentBank[k] != lastBank[k]){
        //read CC values from potentiometers
        CC_read[CC_bank] = analogRead(AnalogPin[k]);
        CC_bank2_value[k] = map(CC_read[CC_bank], 0, 1023, 0, 127); // remap range to 0-127
        //check against last read when we were on this bank, only send CC if value
        //of knob is withing a certain delta of the last value
        if((abs(CC_bank2_lastValue[k] - CC_bank2_value[k])) < 3){ //hysteresis for spinning knob too fast
          Serial.println("Pickup achieved.");
          Serial.print("\nCC_bank2_value for knob: "); Serial.print(k); Serial.print("\t"); Serial.println(CC_bank2_value[k]);
          Serial.print("CC_bank2_lastValue for knob: "); Serial.print(k); Serial.print("\t"); Serial.println(CC_bank2_lastValue[k]);
          lastBank[k] = 2;
        }
      }
      else if(currentBank[k] == lastBank[k]){
        //read CC values from potentiometers
          CC_read[CC_bank] = analogRead(AnalogPin[k]);
          CC_bank2_value[k] = map(CC_read[CC_bank], 0, 1023, 0, 127); // remap range to 0-127
          //check against last read, only send CC if value has changed since last read by a certain delta
        if((abs(CC_bank2_lastValue[k] - CC_bank2_value[k])) > 3){ //hysteresis for spinning knob too fast
          Serial.print("\nCC_bank2_value for knob: "); Serial.print(k); Serial.print("\t"); Serial.println(CC_bank2_value[k]);
          Serial.print("CC_bank2_lastValue for knob: "); Serial.print(k); Serial.print("\t"); Serial.println(CC_bank2_lastValue[k]);
          MIDI.sendControlChange(CCNumber[k], CC_bank2_value[k], 1);
          //Serial.print("CC number: "); Serial.println(CCNumber[k]);
          CC_bank2_lastValue[k] = CC_bank2_value[k];
          lastBank[k] = 2;
        }
      }
    }
  }
  if(CC_bank == 3){ //fourth bank is selected
    for(int k=0; k<6; k++){ //loop through each of six pots
      if(currentBank[k] != lastBank[k]){
       //read CC values from potentiometers
        CC_read[CC_bank] = analogRead(AnalogPin[k]);
        CC_bank3_value[k] = map(CC_read[CC_bank], 0, 1023, 0, 127); // remap range to 0-127
        //check against last read when we were on this bank, only send CC if value
        //of knob is withing a certain delta of the last value
        if((abs(CC_bank3_lastValue[k] - CC_bank3_value[k])) < 3){ //hysteresis for spinning knob too fast
          Serial.println("Pickup achieved.");
          Serial.print("\nCC_bank3_value for knob: "); Serial.print(k); Serial.print("\t"); Serial.println(CC_bank3_value[k]);
          Serial.print("CC_bank3_lastValue for knob: "); Serial.print(k); Serial.print("\t"); Serial.println(CC_bank3_lastValue[k]);
          lastBank[k] = 3;
        }
      }
      else if(currentBank[k] == lastBank[k]){
        //read CC values from potentiometers
          CC_read[CC_bank] = analogRead(AnalogPin[k]);
          CC_bank3_value[k] = map(CC_read[CC_bank], 0, 1023, 0, 127); // remap range to 0-127
          //check against last read, only send CC if value has changed since last read by a certain delta
        if((abs(CC_bank3_lastValue[k] - CC_bank3_value[k])) > 3){ //hysteresis for spinning knob too fast
          Serial.print("\nCC_bank3_value for knob: "); Serial.print(k); Serial.print("\t"); Serial.println(CC_bank3_value[k]);
          Serial.print("CC_bank3_lastValue for knob: "); Serial.print(k); Serial.print("\t"); Serial.println(CC_bank3_lastValue[k]);
          MIDI.sendControlChange(CCNumber[k], CC_bank3_value[k], 1);
          //Serial.print("CC number: "); Serial.println(CCNumber[k]);
          CC_bank3_lastValue[k] = CC_bank3_value[k];
          lastBank[k] = 3;
        }
      }
    }
  }
}
