// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include "WiFi.h"
#include <Adafruit_TestBed.h>
extern Adafruit_TestBed TB;

void setup() {
  Serial.begin(115200);  
  Serial.println("ItsyBitsy ESP32 Factory Reset");

  TB.neopixelPin = PIN_NEOPIXEL;
  TB.neopixelNum = 1; 
  TB.begin();
  TB.setColor(0x0);
}

uint8_t j = 0;
void loop() {
    pinMode(13, OUTPUT);
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
    if (j % 20 == 10) digitalWrite(13, HIGH);
    if (j % 20 == 0) digitalWrite(13, LOW);
    return;
  
}
