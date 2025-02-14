// SPDX-FileCopyrightText: 2024 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_SHT4x.h>

Adafruit_SHT4x sht4 = Adafruit_SHT4x();

void setup() {
  Serial.begin(115200);

  while (!Serial) {
    delay(10);     // will pause until serial console opens
  }
  
  Serial.println("# Adafruit SHT4x Trinkey Vapor-Pressure Deficit Demo");
  if (! sht4.begin()) {
    Serial.println("# Couldn't find SHT4x");
    while (1) delay(1);
  }
  Serial.println("# Found SHT4x sensor.");

  sht4.setPrecision(SHT4X_HIGH_PRECISION);  
  sht4.setHeater(SHT4X_NO_HEATER);
  Serial.println("Vapor-Pressure Deficit (kPa)");
}

void loop() {
  sensors_event_t humidity, temp;

  sht4.getEvent(&humidity, &temp);// populate temp and humidity objects with fresh data
  // saturation vapor pressure is calculated
  float svp = 0.6108 * exp(17.27 * temp.temperature / (temp.temperature + 237.3));
  // actual vapor pressure
  float avp = humidity.relative_humidity / 100 * svp;
  // VPD = saturation vapor pressure - actual vapor pressure
  float vpd = svp - avp;
  Serial.println(vpd);

  // 1 second between readings
  delay(1000);  
}
