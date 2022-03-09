// SPDX-FileCopyrightText: 2022 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include "Adafruit_TestBed.h"
#include <WiFi.h>
extern Adafruit_TestBed TB;

#define NEOPIXEL_PIN 2

void setup() {
  Serial.begin(115200);
  //while (! Serial) delay(10);

  Serial.println("QT Py ESP32 C3!");

  TB.neopixelPin = NEOPIXEL_PIN;
  TB.neopixelNum = 1; 
  TB.begin();
  TB.setColor(0xFF0000);
  delay(50);
  TB.setColor(0x00FF00);
  delay(50);
  TB.setColor(0x0000FF);
  delay(50);
}

uint8_t j = 0;

void loop() {  
  TB.setColor(TB.Wheel(j++));
  delay(10);

  if (j == 255) {
    TB.setColor(GREEN);
    Serial.println("scan start");
    // WiFi.scanNetworks will return the number of networks found
    int n = WiFi.scanNetworks();
    Serial.println("scan done");
    if (n == 0) {
      Serial.println("no networks found");
    } else {
      Serial.print(n);
      Serial.println(" networks found");
      for (int i = 0; i < n; ++i) {
          // Print SSID and RSSI for each network found
          Serial.print(i + 1);
          Serial.print(": ");
          Serial.print(WiFi.SSID(i));
          Serial.print(" (");
          Serial.print(WiFi.RSSI(i));
          Serial.print(")");
          Serial.println((WiFi.encryptionType(i) == WIFI_AUTH_OPEN)?" ":"*");
          delay(10);
      }
    }
    Serial.println("");
  }
}
