// SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/* Simple Soil Sensor Demo */

int sensorPin = A0;
int moisture = 0;

void setup() {
  Serial.begin(115200);
  while ( !Serial ) delay(10);

}

void loop() {
  // read the value from the sensor:
  moisture = analogRead(sensorPin);
  Serial.println(moisture);
  delay(2000);
}
