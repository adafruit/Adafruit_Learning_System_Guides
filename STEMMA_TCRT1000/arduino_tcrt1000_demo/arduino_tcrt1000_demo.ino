// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

void setup() {
  //start serial connection
  Serial.begin(115200);
  pinMode(5, INPUT_PULLUP);

}

void loop() {
  int sensorVal = digitalRead(5);

  if (sensorVal == LOW) {
    Serial.println("object detected!");
  } else {
    Serial.println("waiting for object..");
  }
  delay(200);
}
