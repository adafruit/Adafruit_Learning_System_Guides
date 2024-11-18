// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include "Adafruit_VCNL4200.h"

Adafruit_VCNL4200 vcnl4200;

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10); // wait for native USB
  }

  Serial.println("Adafruit VCNL4200 ALS simple test");

  if (!vcnl4200.begin()) {
    Serial.println("Could not find a valid VCNL4200 sensor, check wiring!");
    while (1) {
      delay(10);
    }
  }
  Serial.println("VCNL4200 found!");

  vcnl4200.setALSshutdown(false);
  vcnl4200.setALSIntegrationTime(VCNL4200_ALS_IT_100MS);
  vcnl4200.setALSPersistence(VCNL4200_ALS_PERS_2);

  vcnl4200.setProxShutdown(false);
  vcnl4200.setProxHD(false);
  vcnl4200.setProxLEDCurrent(VCNL4200_LED_I_200MA);
  vcnl4200.setProxIntegrationTime(VCNL4200_PS_IT_8T);
}

void loop() {
  uint16_t proxData = vcnl4200.readProxData();
  Serial.print("Prox Data: ");
  Serial.println(proxData);
  // Read the ambient light sensor (ALS) data
  uint16_t alsData = vcnl4200.readALSdata();
  Serial.print("ALS Data: ");
  Serial.print(alsData);
  uint16_t whiteData = vcnl4200.readWhiteData();
  Serial.print(", White Data: ");
  Serial.println(whiteData);

  delay(100);
}
