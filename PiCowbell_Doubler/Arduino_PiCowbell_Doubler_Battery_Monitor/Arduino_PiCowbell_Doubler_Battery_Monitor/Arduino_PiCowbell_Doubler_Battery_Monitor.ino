// SPDX-FileCopyrightText: 2024 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#define LED    LED_BUILTIN

void setup() {
  Serial.begin(115200);
  // while (!Serial)  delay(1);  // wait for serial port
  pinMode(LED, OUTPUT);
  delay (100);
  Serial.println("PiCowbell Doubler Battery Monitor");

}

void loop() {
  digitalWrite(LED, HIGH);
  // get the on-board voltage
  float vsys = analogRead(A3) * 3 * 3.3 / 1023.0;
  Serial.printf("Vsys: %0.1f V", vsys);
  Serial.println();

  digitalWrite(LED, LOW);
  delay(5000);
}
