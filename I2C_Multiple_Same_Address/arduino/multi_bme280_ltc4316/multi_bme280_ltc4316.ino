// SPDX-FileCopyrightText: 2024 Carter Nelson for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_BME280.h>

// For each device, create a separate instance.
Adafruit_BME280 bme1;  // BME280 #1 @ 0x77
Adafruit_BME280 bme2;  // BME280 #2 @ 0x37

void setup() {
  Serial.begin(9600);
  while(!Serial);
  Serial.println(F("Two BME280 Example"));

  // NOTE: There's no need to manually call Wire.begin().
  // The BME280 library does that in its begin() method. 
  
  // In the call to begin, pass in the I2C address.
  // If left out, the default address is used.
  // But also OK to just be explicit and specify.
  bme1.begin(0x77);  // address = 0x77 (default)
  bme2.begin(0x37);  // address = 0x37 (behind LTC4316)
}


void loop() {
  float pressure1, pressure2;

  // Read each device separately
  pressure1 = bme1.readPressure();
  pressure2 = bme2.readPressure();

  Serial.println("------------------------------------");
  Serial.print("BME280 #1 Pressure = "); Serial.println(pressure1);
  Serial.print("BME280 #2 Pressure = "); Serial.println(pressure2);

  delay(1000);
}
