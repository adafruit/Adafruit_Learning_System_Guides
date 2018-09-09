/*  MIDI Solenoid Drummer
    for use with Adafruit Feather + Crickit Featherwing
    assumes a 5V solenoid connected to each of Crickit's four Drive ports
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

int cymLED = CRICKIT_SIGNAL4;
int kickLED = CRICKIT_SIGNAL3;
int snareLED = CRICKIT_SIGNAL2;
int shakeLED = CRICKIT_SIGNAL1;

void setup() {

  if (!crickit.begin()) {
    while (1);
  }

  for (int i = 0; i < NUM_DRIVES; i++)
    crickit.setPWMFreq(drives[i], 1000);  //default frequency is 1khz
    
  crickit.pinMode(cymLED, OUTPUT);

  crickit.digitalWrite(cymLED, HIGH);
  delay(5000);
  crickit.digitalWrite(cymLED, LOW);
  
  test(); //test solenoids at start
}

void loop() {

  midiEventPacket_t rx = MidiUSB.read();

  switch (rx.header) {
    case 0x9:
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
      hit(kick, hitDur);
      break;
    case 28:      //snare = E1/28
      hit(snare, hitDur);
      break;
    case 36:      //shake = C2/36
      hit(shake, hitDur);
      break;
    case 37:      //cymbal = C#2/37
      hit(cym, hitDur);
      break;
    default:
      break;
  }
}

void hit(int drum, int dur) {

  crickit.analogWrite(drum, CRICKIT_DUTY_CYCLE_MAX);  //turn all the way on
  crickit.digitalWrite(cymLED, HIGH);
  delay(dur);                                         // wait
  crickit.analogWrite(drum, CRICKIT_DUTY_CYCLE_OFF);  //turn all the way off
  crickit.digitalWrite(cymLED, LOW);
}

void test() {   //for debugging
  hit(cym, hitDur);
  delay(400);
  hit(kick, hitDur);
  delay(400);
  hit(snare, hitDur);
  delay(400);
  hit(shake, hitDur);
  delay(400);
}

