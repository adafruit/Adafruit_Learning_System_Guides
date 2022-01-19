// SPDX-FileCopyrightText: 2022 John Park and Tod Kurt for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Arcade Synth Controller II: Son of Pianocade -- The Enriffening
// written by  John Park and Tod Kurt
// Synthesizer/MIDI arpeggiator for with multiple LED Arcade boards & joystick input

// Arpy library: https://github.com/todbot/mozzi_experiments/blob/main/eighties_arp/Arpy.h
// midi_to_freq and ADT patch: https://github.com/todbot/tal_experiments/tree/main/arpy_test

// - to do: when arp is off it acts as a normal keyboard.

#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <MIDI.h>
#include <Audio.h>
#include <Bounce2.h>
#include "Adafruit_seesaw.h"

#include "ADT.h"
#include "midi_to_freq.h"
#include "Arpy.h"

// ----- LED Arcade 1x4 STEMMA QT board pins-----
// pin definitions on each LED Arcade 1x4
#define  SWITCH1  18  // PA01
#define  SWITCH2  19 // PA02
#define  SWITCH3  20 // PA03
#define  SWITCH4  2 // PA04
#define  PWM1  12  // PC00
#define  PWM2  13 // PC01
#define  PWM3  0 // PA04
#define  PWM4  1 // PA05

#define  I2C_BASE_ADDR 0x3A //  boards are in order, 0x3A, 0x3B, 0x3C, 0x3D
#define  NUM_BOARDS 4

Adafruit_seesaw ledArcades[ NUM_BOARDS ];

//----- board variables
int boardNum = 0;  //used to read each board
int switchNum = 0; //used to read each switch
int boardSwitchNum = 0; //unique button ID accross all boards/buttons
int led_low = 10;  //min pwm brightness
int led_med = 60; 
int led_high = 220; // max brightness

bool lastButtonState[16] ;
bool currentButtonState[16] ;

//-----joystick pins-----
const int joyDownPin = 11;  //down
const int joyUpPin = 12; // up
const int joyLeftPin = 9; // left
const int joyRightPin = 10;  //right
const int joyGroundPin = 6; //"fake" ground pin

//-----joystick debouncer
Bounce joyDown = Bounce();
Bounce joyUp = Bounce();
Bounce joyLeft = Bounce();
Bounce joyRight = Bounce();


//-----MIDI instances-----
Adafruit_USBD_MIDI usb_midi;
MIDI_CREATE_INSTANCE(Adafruit_USBD_MIDI, usb_midi, MIDIusb); // USB MIDI
MIDI_CREATE_INSTANCE(HardwareSerial, Serial1, MIDIclassic);  // classic midi over RX/TX

//-----Audio Library Syth parameters
#define NUM_VOICES 4

AudioSynthWaveform *waves[] = {
  &wave0, &wave1, &wave2, &wave3
};

int filterf_max = 6000;
int filterf = filterf_max;

uint32_t lastControlMillis=0;

uint8_t arp_octaves = 1;
uint8_t root_note = 0;

//----- create arpy arpeggiator
Arpy arp = Arpy();

int bpm = 160;
int octave_offset = 3;  // initially starts on MIDI note 36 with the offset of 3 octaves from zero
bool arp_on_off_state;

void setup() {
    Wire.setClock(400000);
    //----- MIDI and Serial setup-----
    //
    MIDIusb.begin(MIDI_CHANNEL_OMNI);
    MIDIclassic.begin(MIDI_CHANNEL_OMNI);
    Serial.begin(115200);
    MIDIusb.turnThruOff();
    delay(2000); // it's hard getting started in the morning
    Serial.println("[.::.:::.] Welcome to Arcade Synth Controller II: Son of Pianocade -- The Enriffening [.::.:::.]");
    Serial.println("MIDI USB/Classic and Serial have begun");
    //----- end MIDI and Serial setup-----
    
    //----- joystick pins setup-----
    //
    pinMode( joyDownPin, INPUT);
    pinMode( joyUpPin, INPUT);
    pinMode( joyLeftPin, INPUT);
    pinMode( joyRightPin, INPUT);
    pinMode( joyGroundPin, OUTPUT);

    joyDown.attach( joyDownPin, INPUT_PULLUP);
    joyUp.attach( joyUpPin, INPUT_PULLUP);
    joyLeft.attach( joyLeftPin, INPUT_PULLUP);
    joyRight.attach( joyRightPin, INPUT_PULLUP);
    digitalWrite(joyGroundPin, LOW);
    //----- end joystick pins setup-----

    //----- LED Arcade 1x4 setup-----
    //
    for ( int i = 0; i < NUM_BOARDS; i++ ) {
      if ( !ledArcades[i].begin( I2C_BASE_ADDR + i ) ) {
      Serial.println(F("LED Arcade not found!"));
      while (1) delay(10);
      } 
    }
    Serial.println(F("LED Arcade boards started"));
  
    for ( int i = 0; i < NUM_BOARDS; i++ ) {
      ledArcades[i].pinMode(SWITCH1, INPUT_PULLUP);
      ledArcades[i].pinMode(SWITCH2, INPUT_PULLUP);
      ledArcades[i].pinMode(SWITCH3, INPUT_PULLUP);
      ledArcades[i].pinMode(SWITCH4, INPUT_PULLUP);
      ledArcades[i].analogWrite(PWM1, led_low);
      ledArcades[i].analogWrite(PWM2, led_low);
      ledArcades[i].analogWrite(PWM3, led_low);
      ledArcades[i].analogWrite(PWM4, led_low);  
    }
    // brighten default root note
    ledArcades[0].analogWrite(PWM1, led_high);
    // turn down brightness of the function buttons
    ledArcades[3].analogWrite(PWM2, 0);
    ledArcades[3].analogWrite(PWM3, led_low);
    ledArcades[3].analogWrite(PWM4, led_low);
    //----- end LED Arcade 1x4 setup-----
    

    //-----Arpy setup-----
    //
    arp.setNoteOnHandler(noteOn);
    arp.setNoteOffHandler(noteOff);
    arp.setRootNote( root_note );
    arp.setOctaveOffset(octave_offset);
    arp.setBPM( bpm );
    arp.setGateTime( 0.75 ); // percentage of bpm
    arp.off();
    
    //----- Audio Library Synth setup-----
    // (patch is saved in ADT.h file)
    AudioMemory(120);

    filter0.frequency(filterf_max);
    filter0.resonance(0.5);
  
    env0.attack(10);
    env0.hold(2);
    env0.decay(100);
    env0.sustain(0.5);
    env0.release(100);

  // Initialize processor and memory measurements
  AudioProcessorUsageMaxReset();
  AudioMemoryUsageMaxReset();

  Serial.println("Arpy setup done");

} // end setup()


int waveform = WAVEFORM_SQUARE;


void noteOn(uint8_t note) {
  waves[0]->begin( 0.9, tune_frequencies2_PGM[note], waveform);
  waves[1]->begin( 0.9, tune_frequencies2_PGM[note] * 1.01, waveform); // detune
  waves[2]->begin( 0.9, tune_frequencies2_PGM[note] * 1.005, waveform); // detune
  waves[3]->begin( 0.9, tune_frequencies2_PGM[note] * 1.025, waveform); // detune
  filterf = filterf_max;
  filter0.frequency(filterf);
  env0.noteOn();
  MIDIusb.sendNoteOn(note, 127, 1);
  MIDIclassic.sendNoteOn(note, 127, 1);
}


void noteOff(uint8_t note) {
  env0.noteOff();
  MIDIusb.sendNoteOn(note, 0, 1);
  MIDIclassic.sendNoteOn(note, 0, 1);
}

void midiPanic(){
  for( uint8_t m = 0; m < 128; m++ ){
    MIDIusb.sendNoteOn(m, 0, 1) ;
    MIDIclassic.sendNoteOn(m, 0, 1) ;
    yield();  // keep usb midi from flooding
  }
}

void lightLED(uint8_t buttonLED) {
    uint8_t pwms[4] = {PWM1, PWM2, PWM3, PWM4};
    boardNum = map(buttonLED, 0, 12, 0, 3);
    // first dim all buttons on first three boards
    for( int b = 0; b < 3; b++) {
      for( int p = 0; p < 4; p ++) {
        ledArcades[b].analogWrite(pwms[p], led_low);
      }
    }
    // dim first button on fourth board (the other two are function buttons)
    ledArcades[3].analogWrite(PWM1, led_low);
    // then brighten the selected one
    ledArcades[boardNum].analogWrite(pwms[buttonLED % 4], led_high);
}


#define SWITCHMASK ((1 << SWITCH1) | (1 << SWITCH2) | (1 << SWITCH3) | (1 << SWITCH4))

void arcadeButtonCheck() {
    for ( boardNum = 0; boardNum < NUM_BOARDS; boardNum++) {  // check all boards, all switches
      int pos = boardNum*4;
      uint32_t switches = ledArcades[boardNum].digitalReadBulk(SWITCHMASK);
      currentButtonState[pos+0] = ! (switches & (1<<SWITCH1));
      currentButtonState[pos+1] = ! (switches & (1<<SWITCH2));
      currentButtonState[pos+2] = ! (switches & (1<<SWITCH3));
      currentButtonState[pos+3] = ! (switches & (1<<SWITCH4));
    }
    for( int i = 0;  i < 4*NUM_BOARDS;  i++ ) {
      bool state = currentButtonState[i];
      if(state != lastButtonState[i]) {
        
        if( state == HIGH ) { //pressed
          // ---button functions---
          // --root notes--
          if (i < 13){  // these are the piano keys for picking root notes
            root_note = 0 + i ; // MIDI note        
            lightLED(i);
          }
          
        
          //--  start/stop toggle button--
          if (i == 13) {  // arp pattern button on front panel
            if( !arp_on_off_state) {
              arp.on();
              ledArcades[3].analogWrite(PWM2, led_med);
              arp_on_off_state = true;
            }
            else {
              arp.off();
              midiPanic();  // just to be on the safe side...
              ledArcades[3].analogWrite(PWM2, 0);
              arp_on_off_state = false;
            }
          }
          //-- arp octave range button--
          if (i == 14) {  // arp range button on front panel
            ledArcades[3].analogWrite(PWM3, led_high);
            arp_octaves = arp_octaves + 1; if( arp_octaves==4) { arp_octaves=1; }
            arp.setTransposeSteps( arp_octaves );
            //Serial.printf("arp steps:%d\n",arp_octaves);
            ledArcades[3].analogWrite(PWM3, led_low);
          }
          //-- pattern button--
          if (i == 15) {  // arp pattern button on front panel
            ledArcades[3].analogWrite(PWM4, led_high);
            arp.nextArpId();
            ledArcades[3].analogWrite(PWM4, led_low);
          }
        }
      }
    }
    for( int i=0; i<4*NUM_BOARDS; i++ ) {
      lastButtonState[i] = currentButtonState[i];
    }
}
//----- end arcade button check


void loop(){
    arcadeButtonCheck();  // see if any buttons are pressed, send notes or adjust parameters
        
    joyDown.update();
    joyUp.update();
    joyLeft.update();
    joyRight.update();

    if ( joyUp.fell() ) {  // read a joystick single tap
      ledArcades[3].analogWrite(PWM3, led_high);  // feedback on front panel button
      octave_offset = octave_offset + 1; if( octave_offset>7) { octave_offset=7; }
      arp.setOctaveOffset(octave_offset);
      ledArcades[3].analogWrite(PWM3, led_low);
    }
    
    if ( joyDown.fell() ) {
      ledArcades[3].analogWrite(PWM3, led_high);   // feedback on front panel button
      octave_offset = octave_offset - 1; if( octave_offset<0) { octave_offset=0; }
      arp.setOctaveOffset(octave_offset);
      ledArcades[3].analogWrite(PWM3, led_low);
    }

    int joyLeftVal = joyLeft.read();  // read a held joystick (autorepeat) instead of single tap
    if( joyLeftVal == LOW ) {
      bpm = bpm - 1; if(bpm < 100) { bpm = 100; }
      ledArcades[3].analogWrite(PWM4, led_high);
      arp.setBPM( bpm );
      ledArcades[3].analogWrite(PWM4, led_low);
    }

    int joyRightVal = joyRight.read();  // for a held joystick instead of single tap
    if( joyRightVal == LOW ) {
      bpm = bpm + 1; if(bpm > 3000) { bpm = 3000; }
      ledArcades[3].analogWrite(PWM4, led_high);
      arp.setBPM( bpm );
      ledArcades[3].analogWrite(PWM4, led_low);
    }

    arp.update(root_note);  //
  
    if( millis() - lastControlMillis > 20 ) { 
      lastControlMillis = millis();
    }
} 
//end loop()
