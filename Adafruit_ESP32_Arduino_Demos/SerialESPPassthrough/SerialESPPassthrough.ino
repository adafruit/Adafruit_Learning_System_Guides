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

unsigned long baud = 115200;

void setup() {
  Serial.begin(baud);

  SerialNina.begin(baud);

  pinMode(13, OUTPUT);
  pinMode(ESP32_GPIO0, OUTPUT);
  pinMode(ESP32_RESETN, OUTPUT);
  
  // manually put the ESP32 in upload mode
  digitalWrite(ESP32_GPIO0, LOW);

  digitalWrite(ESP32_RESETN, LOW);
  delay(100);
  digitalWrite(ESP32_RESETN, HIGH);

}

void loop() {
  if (Serial.available()) {
    digitalWrite(13, HIGH);
    SerialESP32.write(Serial.read());
    digitalWrite(13, LOW);
  }

  if (SerialESP32.available()) {
    Serial.write(SerialESP32.read());
  }
}
