// Trellis M4 MIDI Keypad CC
// sends 32 notes, pitch bend & a CC from accelerometer tilt
// over USB MIDI
#include <Adafruit_Keypad.h>
#include <Adafruit_NeoPixel.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL343.h>

#include "MIDIUSB.h"

#define MIDI_CHANNEL     0  // default channel # is 0
// Set the value of first note, C is a good choice. Lowest C is 0.
// 36 is a good default. 48 is a high range. Set to 24 for a bass machine.
#define FIRST_MIDI_NOTE 36

#define NEO_PIN 10
#define NUM_KEYS 32
Adafruit_NeoPixel strip = Adafruit_NeoPixel(NUM_KEYS, NEO_PIN, NEO_GRB + NEO_KHZ800);
Adafruit_ADXL343 accel = Adafruit_ADXL343(123, &Wire1);

int xCC = 1;  //choose a CC number to control with x axis tilting of the board. 1 is mod wheel, for example.

int last_xbend = 0;
int last_ybend = 0;

const byte ROWS = 4; // four rows
const byte COLS = 8; // eight columns
//define the symbols on the buttons of the keypads
byte trellisKeys[ROWS][COLS] = {
  {1,  2,  3,  4,  5,  6,  7,  8},
  {9,  10, 11, 12, 13, 14, 15, 16},
  {17, 18, 19, 20, 21, 22, 23, 24},
  {25, 26, 27, 28, 29, 30, 31, 32}
};
byte rowPins[ROWS] = {14, 15, 16, 17}; //connect to the row pinouts of the keypad
byte colPins[COLS] = {2, 3, 4, 5, 6, 7, 8, 9}; //connect to the column pinouts of the keypad

//initialize an instance of class NewKeypad
Adafruit_Keypad customKeypad = Adafruit_Keypad( makeKeymap(trellisKeys), rowPins, colPins, ROWS, COLS);

void setup(){
  strip.begin();
  strip.show(); // Initialize all pixels to 'off'
  strip.setBrightness(80);
  customKeypad.begin();

  Serial.begin(9600);
  //while (!Serial);
  Serial.println("MIDI keypad & pitchbend!");

  if(!accel.begin()) {
    Serial.println("No accelerometer found");
    while(1);
  }
}

void loop() {
  // put your main code here, to run repeatedly:
  customKeypad.tick();

  // did any keys get pressed?
  boolean changed = false;
  while (customKeypad.available()){
    keypadEvent e = customKeypad.read();
    int key_name = (int)e.bit.KEY;
    Serial.print("Keypad key: ");
    Serial.println(key_name);
    Serial.print("MIDI note: ");
    Serial.println(FIRST_MIDI_NOTE+key_name-1);

    if (e.bit.EVENT == KEY_JUST_PRESSED) {
      Serial.println(" pressed\n");
      strip.setPixelColor(key_name-1, 0xFFFFFF);
      noteOn(MIDI_CHANNEL, FIRST_MIDI_NOTE+key_name-1, 64);
      changed = true;
    }
    else if (e.bit.EVENT == KEY_JUST_RELEASED) {
      Serial.println(" released\n");
      strip.setPixelColor(key_name-1, 0x0);
      noteOff(MIDI_CHANNEL, FIRST_MIDI_NOTE+key_name-1, 64);
      changed = true;
    }
  }

  // Check for accelerometer
  sensors_event_t event;
  accel.getEvent(&event);
  /* Display the results (acceleration is measured in m/s^2) */
  //Serial.print("X: "); Serial.print(event.acceleration.x); Serial.print("  ");
  //Serial.print("Y: "); Serial.print(event.acceleration.y); Serial.print("  ");
  //Serial.print("Z: "); Serial.print(event.acceleration.z); Serial.print("  ");Serial.println("m/s^2 ");
  int xbend = 0;
  int ybend = 0;

  if (abs(event.acceleration.y) < 2.0) {  // 2.0 m/s^2
    // don't make any bend unless they've really started moving it
    ybend = 8192; // 8192 means no bend
  } else {
    if (event.acceleration.y > 0) {
      ybend = ofMap(event.acceleration.y, 2.0, 10.0, 8192, 0, true);  // 2 ~ 10 m/s^2 is downward bend
    } else {
      ybend = ofMap(event.acceleration.y, -2.0, -10.0, 8192, 16383, true);  // -2 ~ -10 m/s^2 is upward bend
    }
  }
  if (ybend != last_ybend) {
    Serial.print("Y pitchbend: "); Serial.println(ybend);
    pitchBend(MIDI_CHANNEL, ybend);
    last_ybend = ybend;
    changed = true;
  }

  if (abs(event.acceleration.x) < 2.0) {  // 2.0 m/s^2
    // don't make any bend unless they've really started moving it
    xbend = 0;
  } else {
    if (event.acceleration.x > 0) {
      xbend = ofMap(event.acceleration.x, 2.0, 10.0, 0, 127, true);  // 2 ~ 10 m/s^2 is upward bend
    } else {
      xbend = ofMap(event.acceleration.x, -2.0, -10.0, 0, 127, true);  // -2 ~ -10 m/s^2 is downward bend
    }
  }
  if (xbend != last_xbend) {
    Serial.print("X mod: "); Serial.println(xbend);
    controlChange(MIDI_CHANNEL, xCC, xbend);  //xCC is set at top of sketch. e.g., CC 1 is Mod Wheel
    last_xbend = xbend;
    changed = true;
  }

  if (changed) {
    strip.show();  // update LEDs
    MidiUSB.flush(); // and send all MIDI messages
  }

  delay(10);
}

// First parameter is the event type (0x09 = note on, 0x08 = note off).
// Second parameter is note-on/note-off, combined with the channel.
// Channel can be anything between 0-15. Typically reported to the user as 1-16.
// Third parameter is the note number (48 = middle C).
// Fourth parameter is the velocity (64 = normal, 127 = fastest).

void noteOn(byte channel, byte pitch, byte velocity) {
  midiEventPacket_t noteOn = {0x09, 0x90 | channel, pitch, velocity};
  MidiUSB.sendMIDI(noteOn);
}

void noteOff(byte channel, byte pitch, byte velocity) {
  midiEventPacket_t noteOff = {0x08, 0x80 | channel, pitch, velocity};
  MidiUSB.sendMIDI(noteOff);
}

void pitchBend(byte channel, int value) {
  byte lowValue = value & 0x7F;
  byte highValue = value >> 7;
  midiEventPacket_t pitchBend = {0x0E, 0xE0 | channel, lowValue, highValue};
  MidiUSB.sendMIDI(pitchBend);
}

void controlChange(byte channel, byte control, byte value) {
  midiEventPacket_t event = {0x0B, 0xB0 | channel, control, value};
  MidiUSB.sendMIDI(event);
}
// floating point map
float ofMap(float value, float inputMin, float inputMax, float outputMin, float outputMax, bool clamp) {
    float outVal = ((value - inputMin) / (inputMax - inputMin) * (outputMax - outputMin) + outputMin);

    if (clamp) {
      if (outputMax < outputMin) {
        if (outVal < outputMax)  outVal = outputMax;
        else if (outVal > outputMin)  outVal = outputMin;
      } else {
        if (outVal > outputMax) outVal = outputMax;
        else if (outVal < outputMin)  outVal = outputMin;
      }
    }
    return outVal;

}

// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if(WheelPos < 85) {
    return strip.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if(WheelPos < 170) {
    WheelPos -= 85;
    return strip.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return strip.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}
