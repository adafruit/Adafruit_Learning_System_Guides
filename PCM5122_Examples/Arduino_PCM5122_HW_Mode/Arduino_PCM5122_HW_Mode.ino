// SPDX-FileCopyrightText: 2025 Ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <I2S.h>
#include <math.h>

#define pBCLK D9   // BITCLOCK - I2S clock
#define pWS   D10  // LRCLOCK - Word select
#define pDOUT D11  // DATA - I2S data

// Create I2S port
I2S i2s(OUTPUT);

const int frequency = 440; // frequency of square wave in Hz
const int amplitude = 500; // amplitude of square wave
const int sampleRate = 16000; // 16 KHz is a good quality

const int halfWavelength = (sampleRate / frequency); // half wavelength of square wave

int16_t sample = amplitude; // current sample value
int count = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);

  Serial.println(F("Adafruit PCM51xx Hardware Mode Test"));

  // Initialize I2S peripheral
  Serial.println("Initializing I2S...");
  i2s.setBCLK(pBCLK);
  i2s.setDATA(pDOUT);
  i2s.setBitsPerSample(16);
  
  // Start I2S at the sample rate
  if (!i2s.begin(sampleRate)) {
    Serial.println("Failed to initialize I2S!");
  }
  
}

void loop() {
  if (count % halfWavelength == 0) {
    // invert the sample every half wavelength count multiple to generate square wave
    sample = -1 * sample;
  }

  // write the same sample twice, once for left and once for the right channel
  i2s.write(sample);
  i2s.write(sample);

  // increment the counter for the next sample
  count++;
}
