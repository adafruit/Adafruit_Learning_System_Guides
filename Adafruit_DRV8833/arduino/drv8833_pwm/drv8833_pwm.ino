// SPDX-FileCopyrightText: 2025 Carter Nelson for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// PWM speed control of DC motor via DRV8833

#define AIN1   5
#define AIN2   6
#define SLP    7

void setup() {
  Serial.begin(115200);
  Serial.println("Adafruit DRV8833 DC Motor Example - PWM");

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
  digitalWrite(AIN2, LOW);
  // ramp speed up
  Serial.println("  ramping up");
  for (int duty_cycle=0; duty_cycle<256; duty_cycle++) {
    analogWrite(AIN1, duty_cycle);
    delay(10);
  }
  // ramp speed down
  Serial.println("  ramping down");
  for (int duty_cycle=255; duty_cycle>=0; duty_cycle--) {
    analogWrite(AIN1, duty_cycle);
    delay(10);
  }

  //
  // REVERSE
  //
  Serial.println("Reverse");
  digitalWrite(AIN1, LOW);
  // ramp speed up
  Serial.println("  ramping up");
  for (int duty_cycle=0; duty_cycle<256; duty_cycle++) {
    analogWrite(AIN2, duty_cycle);
    delay(10);
  }
  // ramp speed down
  Serial.println("  ramping down");
  for (int duty_cycle=255; duty_cycle>=0; duty_cycle--) {
    analogWrite(AIN2, duty_cycle);
    delay(10);
  }
}
