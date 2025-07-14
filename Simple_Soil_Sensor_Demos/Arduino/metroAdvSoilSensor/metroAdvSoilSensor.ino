// SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/* Advanced Soil Sensor Demo */

int sensorPin = A0;
int onPin = 2;
int moisture = 0;

void setup() {
  Serial.begin(115200);
  while ( !Serial ) delay(10);
  pinMode(onPin, OUTPUT);

}

void loop() {
  digitalWrite(onPin, HIGH);
  delay(1000);
  // read the value from the sensor:
  moisture = analogRead(sensorPin);
  Serial.println(moisture);
  digitalWrite(onPin, LOW);
  delay(1000);
}
