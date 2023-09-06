// SPDX-FileCopyrightText: 2019 Ha Thach for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// The MIT License (MIT)
// Copyright (c) 2019 Ha Thach for Adafruit Industries

#include <SPI.h>
#include <SdFat.h>

#include <Adafruit_SPIFlash.h>

#define CS_PIN 10

Adafruit_FlashTransport_SPI flashTransport(CS_PIN, SPI);
Adafruit_SPIFlash flash(&flashTransport);

// the setup function runs once when you press reset or power the board
void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(100); // wait for native usb
  }

  Serial.println("Adafruit Serial Flash Info example");
  flash.begin();

  Serial.print("JEDEC ID: 0x");
  Serial.println(flash.getJEDECID(), HEX);
  Serial.print("Flash size: ");
  Serial.print(flash.size() / 1024);
  Serial.println(" KB");
}

void loop() {
  // nothing to do
}
