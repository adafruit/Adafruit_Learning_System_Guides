// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

const int DIR = 5;
const int STEP = 6;
const int microMode = 16; // microstep mode, default is 1/16 so 16; ex: 1/4 would be 4
// full rotation * microstep divider
const int steps = 200 * microMode;

void setup()
{
  // setup step and dir pins as outputs
  pinMode(STEP, OUTPUT);
  pinMode(DIR, OUTPUT);
}

void loop()
{
  // change direction every loop
  digitalWrite(DIR, !digitalRead(DIR));
  // toggle STEP to move
  for(int x = 0; x < steps; x++)
  {
    digitalWrite(STEP, HIGH);
    delay(2);
    digitalWrite(STEP, LOW);
    delay(2);
  }
  delay(1000); // 1 second delay
}
