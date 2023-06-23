// SPDX-FileCopyrightText: 2023 Ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
  This example plays a 'raw' PCM file from memory to I2S
*/

#include <I2S.h>

#include "startup.h" // audio file in flash

// Create the I2S port using a PIO state machine
I2S i2s(OUTPUT);

// GPIO pin numbers
#define pBCLK A2 // QT Py BFF default BITCLOCK
#define pWS   A1 // QT Py BFF default LRCLOCK
#define pDOUT A0 // QT Py BFF default DATA

#define USERBUTTON 21 // QT Py RP2040 built in button

// variable shared between cores
volatile bool playaudio = false;

void setup() {
  Serial.begin(115200);
  //while (!Serial) delay(10);
  Serial.println("I2S playback demo");

  pinMode(USERBUTTON, INPUT_PULLUP);
}

void loop() {
  // on button press tell the other core to play audio clip!
  if (!digitalRead(USERBUTTON)) {
     playaudio = true;
  } else {
     playaudio = false;
  }
}

void setup1() {
  i2s.setBCLK(pBCLK);
  i2s.setDATA(pDOUT);
  i2s.setBitsPerSample(16);
}

void loop1() {
  // the main loop will tell us when it wants us to play!
  if (playaudio) {
    play_i2s(startupAudioData, sizeof(startupAudioData), startupSampleRate);
  }
}

void play_i2s(const uint8_t *data, uint32_t len, uint32_t rate) {
  // start I2S at the sample rate with 16-bits per sample
  if (!i2s.begin(rate)) {
    Serial.println("Failed to initialize I2S!");
    delay(500);
    i2s.end();
    return;
  }
  
  for(uint32_t i=0; i<len; i++) {
    uint16_t sample = (uint16_t)data[i] << 6; // our data is 10 bit but we want 16 bit so we add some gain
    // write the same sample twice, once for left and once for the right channel
    i2s.write(sample);
    i2s.write(sample);
  }
  i2s.end();
}
