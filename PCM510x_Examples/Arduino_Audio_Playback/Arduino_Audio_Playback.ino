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

// GPIO pin numbers on Feather RP2040
#define pBCLK D9 // BITCLOCK
#define pWS   D10 // LRCLOCK
#define pDOUT D11 // DATA

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  Serial.println("I2S playback demo");
}

void loop() {
}

void setup1() {
  i2s.setBCLK(pBCLK);
  i2s.setDATA(pDOUT);
  i2s.setBitsPerSample(16);
}

void loop1() {
  // the main loop will tell us when it wants us to play!
    play_i2s(startupAudioData, sizeof(startupAudioData), startupSampleRate);
    delay(1000);
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
