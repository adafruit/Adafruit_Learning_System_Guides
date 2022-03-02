// SPDX-FileCopyrightText: 2017 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
 This example generates a sine wave based tone at a specified frequency
 and sample rate. Then outputs the data using the I2S interface.

 Public Domain
*/

#include <I2S.h>

#define FREQUENCY    440  // frequency of sine wave in Hz
#define AMPLITUDE  10000  // amplitude of sine wave
#define SAMPLERATE 44100  // sample rate in Hz

int16_t sinetable[SAMPLERATE / FREQUENCY];
uint32_t sample = 0;

#define PI 3.14159265

void setup() {
  Serial.begin(115200);
  Serial.println("I2S sine wave tone");

  // start I2S at the sample rate with 16-bits per sample
  if (!I2S.begin(I2S_PHILIPS_MODE, SAMPLERATE, 16)) {
    Serial.println("Failed to initialize I2S!");
    while (1); // do nothing
  }

  // fill in sine wave table
  for (uint16_t s=0; s < (SAMPLERATE / FREQUENCY); s++) {
    sinetable[s] = sin(2.0 * PI * s / (SAMPLERATE/FREQUENCY)) * AMPLITUDE;
  }
}


void loop() {
  if (sample == (SAMPLERATE / FREQUENCY)) {
    sample = 0;
  }

  // write the same sample twice, once for left and once for the right channel
  I2S.write((int16_t) sinetable[sample]);  // We'll just have same tone on both!
  I2S.write((int16_t) sinetable[sample]);

  // increment the counter for the next sample in the sine wave table
  sample++;
}
