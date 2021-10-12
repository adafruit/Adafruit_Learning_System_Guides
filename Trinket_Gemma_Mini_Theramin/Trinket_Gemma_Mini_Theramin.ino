// SPDX-FileCopyrightText: 2017 Anne Barela for Adafruit Industries
//
// SPDX-License-Identifier: MIT
//
/* Adafruit Trinket/Gemma Example: Simple Theramin

  Read the voltage from a Cadmium Sulfide (CdS) photocell voltage
  divider and output a corresponding tone to a piezo buzzer

  Wiring: Photocell voltage divider center wire to GPIO #2
  (analog 1) and output tone to GPIO #0 (digital 0)

  Note: The Arduino tone library does not work for the ATTiny85 on the
  Trinket and Gemma.  The beep function below is similar.  The beep
  code is adapted from Dr. Leah Buechley at
  http://web.media.mit.edu/~leah/LilyPad/07_sound_code.html
*/

#define SPEAKER   0    // Speaker connected to this DIGITAL pin #
#define PHOTOCELL 1    // CdS photocell connected to this ANALOG pin #
#define SCALE     2.0  // You can change this to change the tone scale

void setup() {
  // Set SPEAKER pin to output to drive the piezo buzzer (important)
  pinMode(SPEAKER, OUTPUT);
}

void loop() {
  // Read PHOTOCELL analog pin for the current CdS divider voltage
  int reading = analogRead(PHOTOCELL);
  // Change the voltage to a frequency.  You can change the values
  // to scale your frequency range.
  int freq = 220 + (int)(reading * SCALE);
  // Output the tone to SPEAKER pin.  You can change the '400'
  // to different times (in milliseconds).
  beep(SPEAKER, freq, 400);
  delay(50); // Delay a bit between notes (also adjustable to taste)
}

// The sound-producing function
void beep (unsigned char speakerPin, int frequencyInHertz, long timeInMilliseconds)
{ // http://web.media.mit.edu/~leah/LilyPad/07_sound_code.html
  int  x;
  long delayAmount = (long)(1000000 / frequencyInHertz);
  long loopTime = (long)((timeInMilliseconds * 1000) / (delayAmount * 2));
  for (x = 0; x < loopTime; x++) {
    digitalWrite(speakerPin, HIGH);
    delayMicroseconds(delayAmount);
    digitalWrite(speakerPin, LOW);
    delayMicroseconds(delayAmount);
  }
}
