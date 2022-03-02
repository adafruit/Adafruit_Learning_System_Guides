// SPDX-FileCopyrightText: 2020 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

void setup() {
  Serial.begin(115200);
  
  pinMode(BUTTON_A, INPUT_PULLUP);
  pinMode(BUTTON_B, INPUT_PULLUP);
  pinMode(BUTTON_C, INPUT_PULLUP);
  pinMode(BUTTON_D, INPUT_PULLUP);
}

void loop() {
  if (! digitalRead(BUTTON_A)) {
    Serial.println("Button A pressed");
  }
  if (! digitalRead(BUTTON_B)) {
    Serial.println("Button B pressed"); 
  }
  if (! digitalRead(BUTTON_C)) {
    Serial.println("Button C pressed");  
  }
  if (! digitalRead(BUTTON_D)) {
    Serial.println("Button D pressed");
  }

  // small debugging delay
  delay(10);
}
