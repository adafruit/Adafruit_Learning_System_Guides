// SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/* micro:bit Advanced Soil Sensor Demo */

#include <Adafruit_Microbit.h>

Adafruit_Microbit_Matrix microbit;

int sensorPin = 0;
int onPin = 2;
int moisture = 0;

const uint8_t
  frown_bmp[] =
  { B00000,
    B01010,
    B00000,
    B01110,
    B10001, };
const uint8_t
  smile_bmp[] =
  { B00000,
    B01010,
    B00000,
    B10001,
    B01110, };

void setup() {
  Serial.begin(115200);
  while ( !Serial ) delay(10);
  Serial.println("micro:bit advanced soil sensor");
  microbit.begin();
  pinMode(onPin, OUTPUT);

}

void loop() {
  digitalWrite(onPin, HIGH);
  delay(50);
  // read the value from the sensor:
  moisture = analogRead(sensorPin);
  Serial.print("Soil moisture: ");
  Serial.println(moisture);
  if (moisture > 200) {
    microbit.show(smile_bmp);
  } else {
    microbit.show(frown_bmp);
  }
  digitalWrite(onPin, LOW);
  delay(5000);
}
