// SPDX-FileCopyrightText: 2024 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_FreeTouch.h>

Adafruit_FreeTouch touch = Adafruit_FreeTouch(1, OVERSAMPLE_4, RESISTOR_50K, FREQ_MODE_NONE);

void setup() {
  Serial.begin(115200);

  while (!Serial) {
    delay(10);     // will pause until serial console opens
  }

  if (! touch.begin())  {
    Serial.println("Failed to begin QTouch on pin 1");
  }
}


void loop() {

  Serial.println(touch.measure());
  delay(1000);  
}
