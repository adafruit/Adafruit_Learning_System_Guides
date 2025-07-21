// SPDX-FileCopyrightText: 2025 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/* micro:bit Simple Soil Sensor Demo */

#include <Adafruit_Microbit.h>

Adafruit_Microbit_Matrix microbit;

int sensorPin = 0;
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
  Serial.println("micro:bit simple soil sensor");
  microbit.begin();

}

void loop() {
  // read the value from the sensor:
  moisture = analogRead(sensorPin);
  Serial.print("Soil moisture: ");
  Serial.println(moisture);
  if (moisture > 200) {
    microbit.show(smile_bmp);
  } else {
    microbit.show(frown_bmp);
  }
  delay(5000);
}
