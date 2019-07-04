/*
  SerialNINAPassthrough - Use esptool to flash the ESP32 module
  For use with PyPortal, Metro M4 WiFi...

  Copyright (c) 2018 Arduino SA. All rights reserved.

  This library is free software; you can redistribute it and/or
  modify it under the terms of the GNU Lesser General Public
  License as published by the Free Software Foundation; either
  version 2.1 of the License, or (at your option) any later version.

  This library is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
  Lesser General Public License for more details.

  You should have received a copy of the GNU Lesser General Public
  License along with this library; if not, write to the Free Software
  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
*/

#include <Adafruit_NeoPixel.h>

unsigned long baud = 115200;

#if defined(ADAFRUIT_FEATHER_M4_EXPRESS) || defined(ADAFRUIT_PYBADGE_M4_EXPRESS) || defined(ADAFRUIT_PYGAMER_M4_EXPRESS)
  // Configure the pins used for the ESP32 connection via 
  #define SerialESP32   Serial1
  #define SPIWIFI       SPI    // The SPI port
  #define SPIWIFI_SS    13   // Chip select pin
  #define ESP32_RESETN  12   // Reset pin
  #define SPIWIFI_ACK   11   // a.k.a BUSY or READY pin
  #define ESP32_GPIO0   10
  #define NEOPIXEL_PIN   8
#endif

Adafruit_NeoPixel pixel = Adafruit_NeoPixel(1, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);


void setup() {
  Serial.begin(baud);
  pixel.begin();
  pixel.setPixelColor(0, 10, 10, 10); pixel.show();

  while (!Serial);
  pixel.setPixelColor(0, 50, 50, 50); pixel.show();

  delay(100);
  SerialESP32.begin(baud);

  pinMode(SPIWIFI_SS, OUTPUT);
  pinMode(ESP32_GPIO0, OUTPUT);
  pinMode(ESP32_RESETN, OUTPUT);
  
  // manually put the ESP32 in upload mode
  digitalWrite(ESP32_GPIO0, LOW);

  digitalWrite(ESP32_RESETN, LOW);
  delay(100);
  digitalWrite(ESP32_RESETN, HIGH);
  pixel.setPixelColor(0, 20, 20, 0); pixel.show();
  delay(100);
}

void loop() {
  while (Serial.available()) {
    pixel.setPixelColor(0, 10, 0, 0); pixel.show();
    SerialESP32.write(Serial.read());
  }

  while (SerialESP32.available()) {
    pixel.setPixelColor(0, 0, 0, 10); pixel.show();
    Serial.write(SerialESP32.read());
  }
}
