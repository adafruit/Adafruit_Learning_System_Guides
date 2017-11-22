/*
 This example generates a square wave based tone at a specified frequency
 and sample rate. Then outputs the data using the I2S interface to a
 MAX08357 I2S Amp Breakout board.

 Circuit:
 * Arduino/Genuino Zero, MKRZero or MKR1000 board
 * MAX08357:
   * GND connected GND
   * VIN connected 5V
   * LRC connected to pin 0 (Zero) or pin 3 (MKR1000, MKRZero)
   * BCLK connected to pin 1 (Zero) or pin 2 (MKR1000, MKRZero)
   * DIN connected to pin 9 (Zero) or pin A6 (MKR1000, MKRZero)

 created 17 November 2016
 by Sandeep Mistry
 */

#include <I2S.h>

const int frequency = 440; // frequency of square wave in Hz
const int amplitude = 500; // amplitude of square wave
const int sampleRate = 8000; // sample rate in Hz

const int halfWavelength = (sampleRate / frequency); // half wavelength of square wave

short sample = amplitude; // current sample value
int count = 0;

void setup() {
  Serial.begin(9600);
  Serial.println("I2S simple tone");

  // start I2S at the sample rate with 16-bits per sample
  if (!I2S.begin(I2S_PHILIPS_MODE, sampleRate, 16)) {
    Serial.println("Failed to initialize I2S!");
    while (1); // do nothing
  }
}

void loop() {
  if (count % halfWavelength == 0) {
    // invert the sample every half wavelength count multiple to generate square wave
    sample = -1 * sample;
  }

  // write the same sample twice, once for left and once for the right channel
  I2S.write(sample);
  I2S.write(sample);

  // increment the counter for the next sample
  count++;
}
