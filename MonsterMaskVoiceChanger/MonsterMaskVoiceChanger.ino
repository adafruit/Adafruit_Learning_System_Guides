// SPDX-FileCopyrightText: 2019 Phillip Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Basic voice changer code. This version is specific to the Adafruit
// MONSTER M4SK board using a PDM microphone. Connect an amplified speaker
// or headphones to the M4SK audio jack. "Inner" button raises pitch,
// "outer" button lowers pitch, center button resets pitch to 1:1.
// SCREENS ARE OFF BY DEFAULT. THIS IS NORMAL.

#include <Adafruit_seesaw.h>

// The code in this file just sets up seesaw and handles button presses.
// All the voice-handling stuff is in the other tab, accessed through
// these functions and variables:
extern bool              voiceSetup(void);
extern float             voicePitch(float p);
extern void              voiceGain(float g);
extern volatile uint16_t voiceLastReading;

Adafruit_seesaw seesaw;
#define SEESAW_BACKLIGHT_PIN 5 // Left eye TFT backlight
#define BACKLIGHT_PIN       21 // Right eye TFT backlight
#define SPEAKER_ENABLE_PIN  20 // Set HIGH to enable speaker out

// Crude error handler. Prints message to Serial Monitor, blinks LED.
static void fatal(const char *message, uint16_t blinkDelay) {
  Serial.println(message);
  for(bool ledState = HIGH;; ledState = !ledState) {
    digitalWrite(LED_BUILTIN, ledState);
    delay(blinkDelay);
  }
}

void setup() {
  pinMode(SPEAKER_ENABLE_PIN, OUTPUT);
  digitalWrite(SPEAKER_ENABLE_PIN, LOW); // Speaker OFF

  Serial.begin(115200);
  //while(!Serial);

  // Screens off for now, not used by this sketch
  pinMode(BACKLIGHT_PIN, OUTPUT);
  analogWrite(BACKLIGHT_PIN, 0);
  if(!seesaw.begin()) fatal("Seesaw init fail", 1000);
  seesaw.analogWrite(SEESAW_BACKLIGHT_PIN, 0);

  if(!voiceSetup()) fatal("Voice init fail", 250);
  digitalWrite(SPEAKER_ENABLE_PIN, HIGH); // Speaker on

  // Configure Seesaw pins 9,10,11 as inputs
  seesaw.pinModeBulk(0b111000000000, INPUT_PULLUP);
}

static float pitch = 1.0;

void loop() {
  uint32_t buttonState = seesaw.digitalReadBulk(0b111000000000);
  if((buttonState & 0b111000000000) != 0b111000000000) {
    if(       !(buttonState & 0b001000000000)) { // Seesaw pin 9
      Serial.println("Higher");
      pitch = voicePitch(pitch * 1.05);
    } else if(!(buttonState & 0b010000000000)) { // Seesaw pin 10
      Serial.println("1:1");
      pitch = voicePitch(1.0);
    } else if(!(buttonState & 0b100000000000)) { // Seesaw pin 11
      Serial.println("Lower");
      pitch = voicePitch(pitch * 0.95);
    }
    Serial.println(pitch);
    while(seesaw.digitalReadBulk(0b111000000000) != 0b111000000000);
  }
}
