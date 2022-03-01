// SPDX-FileCopyrightText: 2021 John Park for Adafruit Industries
//
// SPDX-License-Identifier: MIT

//Wii Guitar Hero MIDI Controller
// by John Park for Adafruit Industries
#include <WiiChuck.h>
#include <Adafruit_TinyUSB.h>
#include <MIDI.h>

Accessory guitar;
Adafruit_USBD_MIDI usb_midi;
MIDI_CREATE_INSTANCE(Adafruit_USBD_MIDI, usb_midi, MIDI);

int MIDI_OUT_CH = 1;  // pick your midi output channel here
bool DEBUG = 0;  // set to 1 to use serial monitor to check out controller values

int whammyBar;
int joyX;
int joyY;
int minusButton;  // drop an octave w each press
int plusButton;  // up and octave w each press
int strumDown;
int strumUp;
int fretButtons[5];

bool minusButtonOn = 0;
bool plusButtonOn = 0;
bool strumDownOn = 0;
bool strumUpOn = 0;
bool fretButtonOn[] = {0, 0, 0, 0, 0};

int octave = 12;  // note offset value, used to change octaves

int strumDownChord[] = {36, 40, 43, 45};  //all note values will be offset by octave value
int strumUpChord[] = {36, 41, 43, 45} ;
int fretNotes[] = {24, 26, 28, 29, 31};

int lastWhammy = 16;  // Use the resting state value of your whammy bar
int whammyPitchVal = 8192;  // resting position of pitchwheel

int lastJoyX = 223;  // resting value of joyX
int joyXCCNum = 71; // VCF or whatever you assign in synth software
int joyXCCVal = 0;
int lastJoyY = 224;  // resting value of joyY
int joyYCCNum = 72; // VCA
int joyYCCVal = 0;

void setup() {
  Serial.begin(115200);
  MIDI.begin(MIDI_CHANNEL_OMNI);
  guitar.begin();
  guitar.type = GuitarHeroController;
}

void loop() {
  guitar.readData();    // Read inputs and update maps
  fretButtons[0] = guitar.values[10];  // green
  fretButtons[1] = guitar.values[11];  // red
  fretButtons[2] = guitar.values[12];  // yellow
  fretButtons[3] = guitar.values[13];  //blue
  fretButtons[4] = guitar.values[14]; // orange
  minusButton = guitar.values[6];
  plusButton = guitar.values[16];
  strumDown = guitar.values[7];
  strumUp = guitar.values[7];
  whammyBar = guitar.values[0];
  joyX = guitar.values[20];
  joyY = guitar.values[21];

  for(int i=0;i<5;i++){
    if(fretButtons[i]==255 && fretButtonOn[i]==0){
      MIDI.sendNoteOn(fretNotes[i]+octave, 127, MIDI_OUT_CH);
      fretButtonOn[i] = 1;}
    if(fretButtons[i]==0 && fretButtonOn[i]==1){
      MIDI.sendNoteOff(fretNotes[i]+octave, 0, MIDI_OUT_CH);
      fretButtonOn[i] = 0;}
    }

  if(whammyBar!=lastWhammy){
    whammyPitchVal=map(whammyBar, 15, 26, 8192, 16383); // remap to pitch value range, two semitones here
    MIDI.sendPitchBend(whammyPitchVal, MIDI_OUT_CH);
    lastWhammy=whammyBar;
  }
  if(joyX!=lastJoyX){
    joyXCCVal=map(joyX, 190, 255, 0, 127); // remap to bigger range
    MIDI.sendControlChange(joyXCCNum, joyXCCVal, MIDI_OUT_CH);
    lastJoyX=joyX;
  }
  if(joyY!=lastJoyY){
    joyYCCVal=map(joyY, 190, 255, 0, 127); // remap to bigger range
    MIDI.sendControlChange(joyYCCNum, joyYCCVal, MIDI_OUT_CH);
    lastJoyY=joyY;
  }

  if(minusButton==0 && minusButtonOn==0){
    octave = constrain((octave - 12), 0, 108);
    minusButtonOn = 1;}
  if(minusButton==128 && minusButtonOn==1){
    minusButtonOn = 0;}

  if(plusButton==255 && plusButtonOn==0){
    octave = constrain((octave + 12), 0, 108);
    plusButtonOn = 1;}
  if(plusButton==0 && plusButtonOn==1){
    plusButtonOn = 0;}

  if(strumDown==0 && strumDownOn==0){
    for(int c=0; c<4; c++){
      MIDI.sendNoteOn(strumDownChord[c]+octave, 127, MIDI_OUT_CH);}
    strumDownOn = 1;}
  if(strumDown==128 && strumDownOn==1){
    for(int c=0; c<4; c++){
      MIDI.sendNoteOff(strumDownChord[c]+octave, 0, MIDI_OUT_CH);}
    strumDownOn = 0;}

  if(strumUp==255 && strumUpOn==0){
    for(int c=0; c<4; c++){
      MIDI.sendNoteOn(strumUpChord[c]+octave, 127, MIDI_OUT_CH);}
    strumUpOn = 1;}
  if(strumUp==128 && strumUpOn==1){
    for(int c=0; c<4; c++){
      MIDI.sendNoteOff(strumUpChord[c]+octave, 0, MIDI_OUT_CH);}
    strumUpOn = 0;}

  delay(5);

  if(DEBUG){
    Serial.println("-------------------------------------------");
    guitar.printInputs();
    for (int i = 0; i < WII_VALUES_ARRAY_SIZE+3; i++) {
      Serial.println(
          "Controller Val " + String(i) + " = "
              + String((uint8_t) guitar.values[i]));
    }
    delay(50);  // keeps the terminal from flooding
  }
}
