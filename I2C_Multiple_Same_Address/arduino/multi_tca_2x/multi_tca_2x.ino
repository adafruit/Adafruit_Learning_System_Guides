// SPDX-FileCopyrightText: 2022 Carter Nelson for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_BME280.h>

// for each TCA9548A, add an entry with its address
const uint8_t TCA_ADDRESSES[] = {
  0x70,
  0x71
};
const uint8_t TCA_COUNT = sizeof(TCA_ADDRESSES) / sizeof(TCA_ADDRESSES[0]);

Adafruit_BME280 bme1;  // BME280 #1
Adafruit_BME280 bme2;  // BME280 #2
Adafruit_BME280 bme3;  // BME280 #3

void tcaselect(uint8_t tca, uint8_t channel) {
  if (tca >= TCA_COUNT) return;
  if (channel > 7) return;

  // loop over all TCA's
  for (uint8_t i=0; i<TCA_COUNT; i++) {
    Wire.beginTransmission(TCA_ADDRESSES[i]);
    if (i == tca)
      // set output channel for selected TCA
      Wire.write(1 << channel);
    else
      // for others, turn off all channels
      Wire.write(0);
    Wire.endTransmission();
  }
}


void setup() {
  Serial.begin(9600);
  while(!Serial);
  Serial.println("Multiple BME280 / Multiple TCA9548A Example.");

  Serial.print("Total number of TCA's = "); Serial.println(TCA_COUNT);
  for (uint8_t i=0; i<TCA_COUNT; i++) {
    Serial.print(i); Serial.print(" : 0x"); Serial.println(TCA_ADDRESSES[i], 16);
  }

  // NOTE!!! VERY IMPORTANT!!!
  // Must call this once manually before first call to tcaselect()
  Wire.begin();

  // Before using any BME280, call tcaselect to select its output channel
  tcaselect(0, 0);   // TCA 0, channel 0 for bme1
  bme1.begin();      // use the default address of 0x77

  tcaselect(0, 1);   // TCA 0, channel 1 for bme2
  bme2.begin();      // use the default address of 0x77

  tcaselect(1, 0);   // TCA 1, channel 0 for bme3
  bme3.begin();      // use the default address of 0x77
}

void loop() {
  float pressure1, pressure2, pressure3;

  tcaselect(0, 0);
  pressure1 = bme1.readPressure();
  tcaselect(0, 1);
  pressure2 = bme2.readPressure();
  tcaselect(1, 0);
  pressure3 = bme3.readPressure();

  Serial.println("------------------------------------");
  Serial.print("BME280 #1 Pressure = "); Serial.println(pressure1);
  Serial.print("BME280 #2 Pressure = "); Serial.println(pressure2);
  Serial.print("BME280 #3 Pressure = "); Serial.println(pressure3);

  delay(1000);
}