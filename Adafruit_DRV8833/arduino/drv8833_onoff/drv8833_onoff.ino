// SPDX-FileCopyrightText: 2025 Carter Nelson for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Basic ON/OFF control of DC motor via DRV8833

#define AIN1   5
#define AIN2   6
#define SLP    7

void setup() {
  Serial.begin(115200);
  Serial.println("Adafruit DRV8833 DC Motor Example - ON/OFF");

  // configure pins
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  pinMode(SLP, OUTPUT);

  // enable DRV8833
  digitalWrite(SLP, HIGH);
}

void loop() {
  //
  // FORWARD
  //
  Serial.println("Forward");
  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);
  delay(1000);

  //
  // REVERSE
  //
  Serial.println("Reverse");
  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, HIGH);
  delay(1000);
}
