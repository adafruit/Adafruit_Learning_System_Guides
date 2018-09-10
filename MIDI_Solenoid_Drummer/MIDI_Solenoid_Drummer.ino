/*  MIDI Solenoid Drummer
 *  for use with Adafruit Feather + Crickit Featherwing
 *  assumes a 5V solenoid connected to each of Crickit's four Drive ports
 */

#include "Adafruit_Crickit.h"
#include "MIDIUSB.h"

Adafruit_Crickit crickit;

#define NUM_DRIVES 4
int drives[] = {CRICKIT_DRIVE1, CRICKIT_DRIVE2, CRICKIT_DRIVE3, CRICKIT_DRIVE4};
int cym = CRICKIT_DRIVE4;
int kick = CRICKIT_DRIVE3;
int snare = CRICKIT_DRIVE2;
int shake = CRICKIT_DRIVE1;
int hitDur = 8; //solenoid on duration for each hit (in milliseconds)

void setup() {

  if (!crickit.begin()) {
    while (1);
  }

  for (int i = 0; i < NUM_DRIVES; i++)
    crickit.setPWMFreq(drives[i], 1000);  //default frequency is 1khz

  test(); //test solenoids at start
}

void loop() {

  midiEventPacket_t rx = MidiUSB.read();  //listen for new MIDI messages

  switch (rx.header) {
    case 0x9:            //Note On message
      handleNoteOn(
        rx.byte1 & 0xF,  //channel
        rx.byte2,        //pitch
        rx.byte3         //velocity
      );
      break;
    default:
      break;
  }
}

void handleNoteOn(byte channel, byte pitch, byte velocity) {

  switch (pitch) {
    case 24:      //kick = C1/24
      hit(kick);
      break;
    case 25:      //snare = C#1/25
      hit(snare);
      break;
    case 26:      //shake = D1/26
      hit(shake);
      break;
    case 27:      //cymbal = D#1/27
      hit(cym);
      break;
    default:
      break;
  }
}

void hit(int drum) {
  crickit.analogWrite(drum, CRICKIT_DUTY_CYCLE_MAX);  //turn solenoid all the way on
  delay(hitDur);                                      // wait
  crickit.analogWrite(drum, CRICKIT_DUTY_CYCLE_OFF);  //turn solenoid all the way off
}

void test() {   //for debugging
  hit(cym);
  delay(400);
  hit(kick);
  delay(400);
  hit(snare);
  delay(400);
  hit(shake);
  delay(400);
}
