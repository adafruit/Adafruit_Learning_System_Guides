// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_ADG72x.h>

Adafruit_ADG72x adg72x;

bool isADG728 = false; // which chip are we connected to?

int analogIn = A0;
int analogValue = 0;
unsigned long timer = 2000;
unsigned long startTime = millis();

void setup() {
  Serial.begin(115200);

  // Wait for serial port to open
  while (!Serial) {
    delay(1);
  }

  // Try with the ADG728 default address first...
  if (adg72x.begin(ADG728_DEFAULT_ADDR, &Wire)) {
    Serial.println("ADG728 found!");
    isADG728 = true;
  }
  // Maybe they have an ADG729?
  else if (adg72x.begin(ADG729_DEFAULT_ADDR, &Wire)) {
    Serial.println("ADG729 found!");
    isADG728 = false;
  }
  else {
    Serial.println("No ADG device found? Check wiring!");
    while (1); // Stop here if no device was found
  }
}

void loop() {
  analogValue = analogRead(analogIn);
  Serial.println(analogValue);

  if ((millis() - startTime) >= timer) {
  for (uint8_t i = 0; i < 8; i++) {
    if (isADG728) {
    } else {
      if (i < 4) Serial.println("A");
      else       Serial.println("B");
    }
    uint8_t bits = 1 << i; // Shift a '1' from LSB to MSB
    if (!adg72x.selectChannels(bits)) {
    }
    startTime = millis();
  }
  }
  delay(10);
}
