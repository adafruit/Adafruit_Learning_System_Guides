// SPDX-FileCopyrightText: 2022 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include "WiFi.h"
#include <Adafruit_TestBed.h>
extern Adafruit_TestBed TB;

#define NEOPIXEL_I2C_POWER 2
#define NEOPIXEL_PIN 0

// the setup routine runs once when you press reset:
void setup() {
  Serial.begin(115200);

  // turn on the QT port and NeoPixel
  pinMode(NEOPIXEL_I2C_POWER, OUTPUT);
  digitalWrite(NEOPIXEL_I2C_POWER, HIGH);
  
  // TestBed will handle the neopixel swirl for us
  TB.neopixelPin = NEOPIXEL_PIN;
  TB.neopixelNum = 1;
  TB.begin();

  // Set WiFi to station mode and disconnect from an AP if it was previously connected
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
}

// the loop routine runs over and over again forever:
uint8_t wheelColor=0;
void loop() {
  if (wheelColor == 0) {
    // Test I2C!
    Serial.print("I2C port ");
    TB.theWire = &Wire;
    TB.printI2CBusScan();

    // Test WiFi Scan!
    // WiFi.scanNetworks will return the number of networks found
    int n = WiFi.scanNetworks();
    Serial.print("WiFi AP scan done...");
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

  TB.setColor(TB.Wheel(wheelColor++)); // swirl NeoPixel

  delay(5);
}
