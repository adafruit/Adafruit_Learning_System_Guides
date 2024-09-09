// SPDX-FileCopyrightText: 2024 Ha Thach for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Arduino.h>
#include <Adafruit_TinyUSB.h> // required for USB Serial

const int led = PA6;

void setup () {
  pinMode(led, OUTPUT);
}

void loop () {
  Serial.println("LED on");
  digitalWrite(led, HIGH);   // turn the LED on (HIGH is the voltage level)
  delay(1000);               // wait for a second
  
  Serial.println("LED off");
  digitalWrite(led, LOW);    // turn the LED off by making the voltage LOW
  delay(1000);               // wait for a second
}
