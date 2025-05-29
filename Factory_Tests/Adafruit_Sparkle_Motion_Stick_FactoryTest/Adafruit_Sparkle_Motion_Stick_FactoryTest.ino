// SPDX-FileCopyrightText: 2025 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT
#include <Arduino.h>
#include "WiFi.h"
#include <Adafruit_TestBed.h>
#include "ESP_I2S.h"
extern Adafruit_TestBed TB;

// I2S pin definitions
const uint8_t I2S_SCK = 14;  // BCLK
const uint8_t I2S_WS = 12;   // LRCLK
const uint8_t I2S_DIN = 13;  // DATA_IN
I2SClass i2s;

// the setup routine runs once when you press reset:
void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);
  i2s.setPins(I2S_SCK, I2S_WS, -1, I2S_DIN);
  if (!i2s.begin(I2S_MODE_STD, 44100, I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO, I2S_STD_SLOT_LEFT)) {
    Serial.println("Failed to initialize I2S bus!");
    return;
  }
  // TestBed will handle the neopixel swirl for us
  TB.neopixelPin = PIN_NEOPIXEL;
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
    for (int i=0; i < 5; i++) {
      int32_t sample = i2s.read();
      if (sample >= 0){
        Serial.print("Amplitude: ");
        Serial.println(sample);
    
        // Delay to avoid printing too quickly
        delay(200);
        }
      }
  }

  TB.setColor(TB.Wheel(wheelColor++)); // swirl NeoPixel
  digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));

  delay(5);
}
