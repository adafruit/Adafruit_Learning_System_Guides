// SPDX-FileCopyrightText: 2022 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include "Adafruit_TestBed.h"
#include <WiFi.h>
#include <WiFiAP.h>
#include <esp_wifi.h>

extern Adafruit_TestBed TB;

IPAddress myIP;


void setup() {
  Serial.begin(115200);
  //while (! Serial) delay(10);

  delay(100);
  Serial.println("QT Py ESP32 Pico factory test!");

  Serial.printf("Total heap: %d\n", ESP.getHeapSize());
  Serial.printf("Free heap: %d\n", ESP.getFreeHeap());
  Serial.printf("Total PSRAM: %d\n", ESP.getPsramSize());
  Serial.printf("Free PSRAM: %d\n", ESP.getFreePsram());

  pinMode(NEOPIXEL_POWER, OUTPUT);
  digitalWrite(NEOPIXEL_POWER, HIGH);
  
  TB.neopixelPin = PIN_NEOPIXEL;
  TB.neopixelNum = 1; 
  TB.begin();
  TB.setColor(0x0);
}

uint8_t j = 0;

void loop() {
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
  
  TB.setColor(TB.Wheel(j++));
  delay(10);
}
