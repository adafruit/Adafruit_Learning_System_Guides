// SPDX-FileCopyrightText: 2021 Phil Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
MOVE-AND-BLINK EYES for Adafruit EyeLights (LED Glasses + Driver).
*/

#include <Adafruit_IS31FL3741.h> // For LED driver

Adafruit_EyeLights_buffered glasses; // Buffered for smooth animation

#define GAMMA 2.6

// Crude error handler, prints message to Serial console, flashes LED
void err(char *str, uint8_t hz) {
  Serial.println(str);
  pinMode(LED_BUILTIN, OUTPUT);
  for (;;) digitalWrite(LED_BUILTIN, (millis() * hz / 500) & 1);
}

void setup() { // Runs once at program start...

  // Initialize hardware
  Serial.begin(115200);
  if (! glasses.begin()) err("IS3741 not found", 2);

  // Configure glasses for reduced brightness, enable output
  glasses.setLEDscaling(0xFF);
  glasses.setGlobalCurrent(20);
  glasses.enable(true);
}

void loop() { // Repeat forever...
  glasses.show();
}
