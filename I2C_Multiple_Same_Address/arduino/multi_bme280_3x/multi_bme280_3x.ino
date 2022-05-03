// SPDX-FileCopyrightText: 2022 Carter Nelson for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_BME280.h>

#define TCAADDR 0x70

// For each device, create a separate instance.
Adafruit_BME280 bme1;  // BME280 #1
Adafruit_BME280 bme2;  // BME280 #2
Adafruit_BME280 bme3;  // BME280 #3

// Helper function for changing TCA output channel
void tcaselect(uint8_t channel) {
  if (channel > 7) return;
  Wire.beginTransmission(TCAADDR);
  Wire.write(1 << channel);
  Wire.endTransmission();  
}

void setup() {
  Serial.begin(9600);
  while(!Serial);
  Serial.println(F("Three BME280 Example"));

  // NOTE!!! VERY IMPORTANT!!!
  // Must call this once manually before first call to tcaselect()
  Wire.begin();
  
  // Before using any BME280, call tcaselect to set the channel.
  tcaselect(0);      // TCA channel for bme1
  bme1.begin();      // use the default address of 0x77

  tcaselect(1);      // TCA channel for bme2
  bme2.begin();      // use the default address of 0x77

  tcaselect(2);      // TCA channel for bme3
  bme3.begin();      // use the default address of 0x77
}


void loop() {
  float pressure1, pressure2, pressure3;

  // Read each device separately
  tcaselect(0);
  pressure1 = bme1.readPressure();
  tcaselect(1);
  pressure2 = bme2.readPressure();
  tcaselect(2);
  pressure3 = bme3.readPressure();

  Serial.println("------------------------------------");
  Serial.print("BME280 #1 Pressure = "); Serial.println(pressure1);
  Serial.print("BME280 #2 Pressure = "); Serial.println(pressure2);
  Serial.print("BME280 #3 Pressure = "); Serial.println(pressure3);

  delay(1000);
}
