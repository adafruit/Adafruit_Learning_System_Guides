// SPDX-FileCopyrightText: 2023 Carter Nelson for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// LTC4315 with two AHT20 sensors example
// Set the LTC4315 switch A5 on and switch A4 off
// The translated sensor will be on address 0x68

#include <Adafruit_AHTX0.h>

Adafruit_AHTX0 default_aht;
Adafruit_AHTX0 ltc4316_aht;

void setup() {
  Serial.begin(115200);
  while ( !Serial ) delay(10);
  Serial.println("Adafruit AHT20 with LTC4316 demo!");
  if (! default_aht.begin(&Wire, 0, 0x38)) {
    Serial.println("Could not find AHT20 on 0x38? Check wiring.");
    while (1) delay(10);
  }
  if (! ltc4316_aht.begin(&Wire, 0, 0x68)) {
    Serial.println("Could not find AHT20 attached to LTC4316 on 0x68? Check wiring and switches");
    while (1) delay(10);
  }
  Serial.println("AHT20 sensors found on 0x38 and 0x68");
}

void loop() {
  sensors_event_t humidity0, temp0;
  sensors_event_t humidity1, temp1;
  default_aht.getEvent(&humidity0, &temp0);// populate temp and humidity objects with fresh data
  ltc4316_aht.getEvent(&humidity1, &temp1);// populate temp and humidity objects with fresh data
  Serial.println("AHT20 on 0x38:");
  Serial.print("Temperature: "); Serial.print(temp0.temperature); Serial.println(" degrees C");
  Serial.print("Humidity: "); Serial.print(humidity0.relative_humidity); Serial.println("% rH");
  Serial.println();
  Serial.println("AHT20 on 0x68:");
  Serial.print("Temperature: "); Serial.print(temp1.temperature); Serial.println(" degrees C");
  Serial.print("Humidity: "); Serial.print(humidity1.relative_humidity); Serial.println("% rH");
  Serial.println();

  delay(500);
}
