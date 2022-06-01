// SPDX-FileCopyrightText: 2022 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_I2CDevice.h>
// requires https://github.com/adafruit/Adafruit_BusIO

#define SR04_I2CADDR 0x57
Adafruit_I2CDevice sonar_dev = Adafruit_I2CDevice(SR04_I2CADDR);


void setup() {
  Serial.begin(115200);
  while (!Serial);

  if (! sonar_dev.begin(&Wire)) {
    Serial.println("Could not find I2C sonar!");
    while (1);
  }
  Serial.println("Found RCWL I2C sonar!");
}

void loop() {
  Serial.print("Ping mm: "); Serial.println(ping_mm());
  delay(100);
}

uint32_t ping_mm()
{
  uint32_t distance = 0;
  byte buffer[3];
  buffer[0] = 1;
  // write one byte then read 3 bytes
  if (! sonar_dev.write(buffer, 1)) {
    return 0;
  }
  delay(10);  // wait for the ping echo
  if (! sonar_dev.read(buffer, 3)) {
    return 0;
  }
  
  distance = ((uint32_t)buffer[0] << 16) | ((uint32_t)buffer[1] << 8) | buffer[2];
  distance /= 1000;
  
  if ((distance <= 1) || (distance >= 4500)) {   // reject readings too low and too high
    return 0;
  }

  return distance;
}
