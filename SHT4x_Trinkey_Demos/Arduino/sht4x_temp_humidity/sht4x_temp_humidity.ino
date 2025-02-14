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
  
  Serial.println("# Adafruit SHT4x Trinkey Temperature and Humidity Demo");
  if (! sht4.begin()) {
    Serial.println("# Couldn't find SHT4x");
    while (1) delay(1);
  }
  Serial.println("# Found SHT4x sensor.");

  sht4.setPrecision(SHT4X_HIGH_PRECISION);  
  sht4.setHeater(SHT4X_NO_HEATER);
  Serial.println("Temperature in *C, Relative Humidity %");
}

void loop() {
  sensors_event_t humidity, temp;

  sht4.getEvent(&humidity, &temp);// populate temp and humidity objects with fresh data
  Serial.print(temp.temperature);
  Serial.print(", ");
  Serial.println(humidity.relative_humidity);

  // 1 second between readings
  delay(1000);  
}
