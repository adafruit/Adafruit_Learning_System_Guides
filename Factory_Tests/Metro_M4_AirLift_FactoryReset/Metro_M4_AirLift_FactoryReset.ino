// SPDX-FileCopyrightText: 2026 Tyeth Gundry for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include "WiFi.h"
#include <Adafruit_TestBed.h>
extern Adafruit_TestBed TB;

#ifndef PIN_NEOPIXEL
#define PIN_NEOPIXEL (40u)
#endif

// the setup routine runs once when you press reset:
void setup() {
  Serial.begin(115200);

  // TestBed will handle the neopixel swirl for us
  TB.neopixelPin = PIN_NEOPIXEL;
  TB.neopixelNum = 1;
  TB.begin();
  TB.setColor(0xFF0000); 
  delay(50);
  TB.setColor(0x00FF00); 
  delay(50);
  TB.setColor(0x0000FF); 

  // Set up the wifi coproc
  WiFi.setPins(SPIWIFI_SS, SPIWIFI_ACK, ESP32_RESETN, ESP32_GPIO0, &SPIWIFI);
  // check for the WiFi module:
  if (WiFi.status() == WL_NO_MODULE) {
    Serial.println("Communication with WiFi module failed!");
  } else {
    String fv = WiFi.firmwareVersion();  
    Serial.print("Firmware OK: ");  
    Serial.println(fv);
  }

}

uint32_t last_wifi_scan = 0;

// the loop routine runs over and over again forever:
uint8_t wheelColor=0;
void loop() {
  if (wheelColor == 0) {
    // Test I2C!
    Serial.print("I2C port ");
    TB.theWire = &Wire;
    TB.printI2CBusScan();
  }
  TB.setColor(TB.Wheel(wheelColor++)); // swirl NeoPixel


  if ((millis() - last_wifi_scan) > 10000) {
    // every 10 sec, scan wifi (unless no results then try again next loop)
    Serial.println("** Scan Networks **");
    int numSsid = WiFi.scanNetworks();
    if (numSsid == -1) {
      Serial.println("Couldn't get a wifi connection");
      return;
    }
    Serial.printf("Number of available networks: %d\n\r", numSsid);
  
    // print the network number and name for each network found:
    for (int thisNet = 0; thisNet < numSsid; thisNet++) {
      Serial.printf("%d) %s\tSignal: %d dBm\n\r", thisNet, WiFi.SSID(thisNet), WiFi.RSSI(thisNet));
    }
    last_wifi_scan = millis();
  
    Serial.println("");
  }

  delay(5);
}
