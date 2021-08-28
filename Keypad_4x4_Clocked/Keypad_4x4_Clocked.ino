// SPDX-FileCopyrightText: 2021 John Park for Adafruit Industries
// SPDX-License-Identifier: MIT
// Keypad 4x4 for NeoKey Ortho Snap-apart PCB & QT Py M0
// Sends MIDI NoteOn/Off and Clock
// --works well in VCV Rack for keeping clock timing via MIDI-CV CLK

#include <Adafruit_TinyUSB.h>
#include "Adafruit_Keypad.h"
#include <Adafruit_NeoPixel.h>
#include <MIDI.h>

// User variables
bool latch_mode = false;  // set latch/toggle mode
int BPM = 120;  // set BPM
int MIDI_OUT_CH = 1;  // pick your midi output channel here


uint32_t interval = 60000 / BPM;

Adafruit_USBD_MIDI usb_midi;
MIDI_CREATE_INSTANCE(Adafruit_USBD_MIDI, usb_midi, MIDI);

const byte ROWS = 4; // rows
const byte COLS = 4; // columns

//define the symbols on the buttons of the keypads -- used for Serial output, debugging
char keys[ROWS][COLS] = {
  {'1','2','3','4'},
  {'5','6','7','8'},
  {'A','B','C','D'},
  {'E','F','G','H'}
};

byte rowPins[ROWS] = {A3, A2, A1, A0}; //connect to the row pinouts of the keypad
byte colPins[COLS] = {SCL, A6, A7, A8}; //connect to the column pinouts of the keypad

//define the MIDI notes to send per key
int pads[] = {  // two A scales with added G#
  76, 77, 79, 80,
  69, 71, 72, 74,
  64, 65, 67, 68,
  57, 59, 60, 62
};

/*int pads[] = {  // corresponds to 1010music blackbox pads for sample launching
  48, 49, 50, 51,
  44, 45, 46, 47,
  40, 41, 42, 43,
  36, 37, 38, 39
};*/


int current_key = 0;  // current key press int
int pixorder[] = { // to convert "snake" order to grid order
  0, 1, 2, 3,
  7, 6, 5, 4,
  8, 9, 10, 11,
  15, 14, 13, 12
} ;

//initialize an instance of keypad
Adafruit_Keypad customKeypad = Adafruit_Keypad( makeKeymap(keys), rowPins, colPins, ROWS, COLS);

#define NEO_PIN SDA
#define NUMPIXELS ROWS*COLS
Adafruit_NeoPixel pixels(NUMPIXELS, NEO_PIN, NEO_GRB + NEO_KHZ800);

uint32_t red = pixels.Color(100, 0, 0);
uint32_t light_blue = pixels.Color(0, 50, 60);
uint32_t black = pixels.Color(0, 0, 0);

uint32_t priorcolor = pixels.Color(0,0,0);  // store state of color before sequence changes it
uint32_t currentcolor = pixels.Color(0,0,0);

int current_pixel = 0; // current pixel

unsigned long previousMillis = 0;

void setup() {
  //Serial.begin(9600);  // use for debugging
  MIDI.begin(MIDI_OUT_CH); // begin MIDI before the delay to settle
  delay(1000);
  customKeypad.begin();  // begin keypad
  pixels.begin();  // begin neopixels

  for(int i=0; i<NUMPIXELS+1; i++) { // light up each pixel
    pixels.setPixelColor(pixorder[i], light_blue);
    pixels.setPixelColor(pixorder[i-1], black);
    pixels.show();   // Send the updated pixel colors to the hardware.
    delay(int(interval/4));
  }
}

void loop() {
  customKeypad.tick();
  unsigned long currentMillis = millis();

  while(customKeypad.available()){
    keypadEvent e = customKeypad.read();  // scan the keypad for changes
    //Serial.print((char)e.bit.KEY);

    if(e.bit.EVENT == KEY_JUST_PRESSED){
      current_key = (e.bit.ROW * ROWS) + e.bit.COL ;
      //Serial.println(" pressed");
      //Serial.println(interval);
      currentcolor = pixels.getPixelColor(pixorder[current_key]);
      if (latch_mode == true){
        if (currentcolor==0){
          MIDI.sendNoteOn(pads[current_key], 127, MIDI_OUT_CH);
          pixels.setPixelColor(pixorder[current_key], light_blue);
        }
        else{
          MIDI.sendNoteOff(pads[current_key], 0, MIDI_OUT_CH);
          pixels.setPixelColor(pixorder[current_key], black);
        }
      }
      else{
        MIDI.sendNoteOn(pads[current_key], 127, MIDI_OUT_CH);
        pixels.setPixelColor(pixorder[current_key], light_blue);
      }
      pixels.show();
    }

    else if(e.bit.EVENT == KEY_JUST_RELEASED){
      current_key = (e.bit.ROW * ROWS) + e.bit.COL ;
      //Serial.println(" released");
      if (latch_mode == false){
        MIDI.sendNoteOff(pads[current_key], 0, MIDI_OUT_CH);
        pixels.setPixelColor(pixorder[current_key], black);
        pixels.show();
      }
    }
  // delay(10);
  }
    //----- Running light
    if (currentMillis - previousMillis >= interval) {
      MIDI.sendClock();
      if (current_pixel==0){  // loop around to last pixel for color reset
        pixels.setPixelColor(pixorder[NUMPIXELS-1], priorcolor);
      }
      else{
        pixels.setPixelColor(pixorder[current_pixel-1], priorcolor);
      }
      priorcolor = pixels.getPixelColor(pixorder[current_pixel]);  // grabs the current color of the pixel for later use

      pixels.setPixelColor(pixorder[current_pixel], red);
      pixels.show();
      current_pixel++;
      previousMillis = currentMillis;
    }
    if (current_pixel==NUMPIXELS){
      current_pixel=0;
    }
}
