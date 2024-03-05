// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

int analogIn = A1;
// in arduino, feather rp2040 pin 5 is pin 7
int digitalOut = 7;
int analogValue = 0;
unsigned long timer = 2000;
unsigned long startTime = millis();

void setup() {
  Serial.begin(115200);
  pinMode(digitalOut, OUTPUT);
}

// the loop function runs over and over again forever
void loop() {
  analogValue = analogRead(analogIn);
  Serial.println(analogValue);
  if ((millis() - startTime) >= timer) {
    digitalWrite(digitalOut, !digitalRead(digitalOut));
    startTime = millis();
  }
  delay(10);
}
