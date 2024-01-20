// SPDX-FileCopyrightText: 2023 Kattni Rembor for Adafruit Industries
// SPDX-FileCopyrightText: Earle F. Philhower, III
//
// SPDX-License-Identifier: MIT

/*
  This example plays a tune through a mono amplifier using a simple sine wave.

  Released to the public domain by Earle F. Philhower, III <earlephilhower@yahoo.com>

  Adapted from stereo original example 2023 by Kattni Rembor
*/

#include <PWMAudio.h>

PWMAudio pwm(0, true); // GP0 = left, GP1 = right

const int freq = 48000; // Output frequency for PWM

int16_t mono = 0;

const int notes[] = { 784, 880, 698, 349, 523 };
const int dly[] =   { 400, 500, 700, 500, 1000 };
const int noteCnt = sizeof(notes) / sizeof(notes[0]);

int freqMono = 1;

double sineTable[128]; // Precompute sine wave in 128 steps

unsigned int cnt = 0;
void cb() {
  while (pwm.availableForWrite()) {
    double now = ((double)cnt) / (double)freq;
    int freqScale = freqMono << 7; // Prescale by 128 to avoid FP math later on
    pwm.write((int16_t)(mono * sineTable[(int)(now * freqScale) & 127]));
    cnt++;
  }
}

void setup() {
  // Set up sine table for waveform generation
  for (int i = 0; i < 128; i++) {
    sineTable[i] = sin(i * 2.0 * 3.14159 / 128.0);
  }
  pwm.setBuffers(4, 32); // Give larger buffers since we're are 48khz sample rate
  pwm.onTransmit(cb);
  pwm.begin(freq);
}

void loop() {
  delay(1000);
  mono = 0;
  Serial.println("loop");
  for (int i = 0; i < noteCnt; i++) {
    freqMono = notes[i];
    mono = 5000;
    delay(dly[i]);
  }
  mono = 0;
  delay(3000);
}
