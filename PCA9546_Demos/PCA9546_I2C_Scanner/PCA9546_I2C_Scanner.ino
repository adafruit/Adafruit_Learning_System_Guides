// SPDX-FileCopyrightText: 2023 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT
/**
 * PCA9546 I2CScanner.ino -- I2C bus scanner for Arduino
 *
 * Based on https://playground.arduino.cc/Main/I2cScanner/
 *
 */

#include "Wire.h"

#define PCAADDR 0x70

void pcaselect(uint8_t i) {
  if (i > 3) return;
 
  Wire.beginTransmission(PCAADDR);
  Wire.write(1 << i);
  Wire.endTransmission();  
}


// standard Arduino setup()
void setup()
{
    while (!Serial);
    delay(1000);

    Wire.begin();
    
    Serial.begin(115200);
    Serial.println("\nPCAScanner ready!");
    
    for (uint8_t t=0; t<4; t++) {
      pcaselect(t);
      Serial.print("PCA Port #"); Serial.println(t);

      for (uint8_t addr = 0; addr<=127; addr++) {
        if (addr == PCAADDR) continue;

        Wire.beginTransmission(addr);
        if (!Wire.endTransmission()) {
          Serial.print("Found I2C 0x");  Serial.println(addr,HEX);
        }
      }
    }
    Serial.println("\ndone");
}

void loop() 
{
}
