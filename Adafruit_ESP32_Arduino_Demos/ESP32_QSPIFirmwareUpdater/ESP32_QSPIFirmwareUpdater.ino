/*
  FirmwareUpdater - Firmware Updater for the 
  Arduino MKR WiFi 1010, Arduino MKR Vidor 4000, and Arduino UNO WiFi Rev.2.
  
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

#include "ESP32BootROM.h"
#include "SdFat.h"
#include "Adafruit_SPIFlash.h"

#if defined(ADAFRUIT_FEATHER_M4_EXPRESS) || \
  defined(ADAFRUIT_FEATHER_M0_EXPRESS) || \
  defined(ARDUINO_NRF52840_FEATHER) || \
  defined(ADAFRUIT_ITSYBITSY_M0_EXPRESS) || \
  defined(ADAFRUIT_ITSYBITSY_M4_EXPRESS)
  
  #define SerialESP32   Serial1
  #define SPIWIFI       SPI  // The SPI port
  #define SPIWIFI_SS    13   // Chip select pin
  #define ESP32_RESETN  12   // Reset pin
  #define SPIWIFI_ACK   11   // a.k.a BUSY or READY pin
  #define ESP32_GPIO0   10
  #define NEOPIXEL_PIN   8
#endif


#if defined(EXTERNAL_FLASH_USE_QSPI)
  Adafruit_FlashTransport_QSPI flashTransport;

#elif defined(EXTERNAL_FLASH_USE_SPI)
  Adafruit_FlashTransport_SPI flashTransport(EXTERNAL_FLASH_USE_CS, EXTERNAL_FLASH_USE_SPI);

#else
  #error No QSPI/SPI flash are defined on your board variant.h !
#endif

Adafruit_SPIFlash flash(&flashTransport);

// file system object from SdFat
FatFileSystem fatfs;

static const int MAX_PAYLOAD_SIZE = 1024;
uint32_t firmsize;
static uint8_t payload[MAX_PAYLOAD_SIZE];

File myFile;

ESP32BootROMClass ESP32BootROM(SerialESP32, ESP32_GPIO0, ESP32_RESETN);

void setup() {
  Serial.begin(115200);
  while (!Serial);
  delay(100);

  Serial.print("Initializing Filesystem on external flash...");
  flash.begin();  // Init external flash
  
  Serial.print("JEDEC ID: "); Serial.println(flash.getJEDECID(), HEX);
  Serial.print("Flash size: "); Serial.println(flash.size());
  
  if (!fatfs.begin(&flash)) {  // Init file system on the flash
    Serial.println("FLASH init. failed!");
    while (1);
  }

    
  myFile = fatfs.open("/NINA HCI BT.bin", FILE_READ);
  if (!myFile) {
    Serial.println("Failed to open firmware file");
    while (1);
  }
  firmsize = myFile.size();
  Serial.print(firmsize); Serial.println(" bytes");

}

void loop() {
    while (!ESP32BootROM.begin(921600)) {
    Serial.println("Unable to communicate with ESP32 boot ROM!");
    delay(100);
    return;
  }
  Serial.println("Ready!");

  uint32_t timestamp = millis();

  while (!ESP32BootROM.beginFlash(0, firmsize, MAX_PAYLOAD_SIZE)) {
    Serial.println("Failed to erase flash");
    delay(100);
    return;
  }
  Serial.println("Erase OK");

  for (uint32_t i=0; i<firmsize; i+=MAX_PAYLOAD_SIZE) {
    memset(payload, 0xFF, MAX_PAYLOAD_SIZE);
    uint32_t num_read = myFile.read(&payload, MAX_PAYLOAD_SIZE);
    Serial.print("Packet #"); Serial.print(i/MAX_PAYLOAD_SIZE); Serial.print(": ");
    Serial.print(num_read); Serial.print(" byte payload...");

    if (!ESP32BootROM.dataFlash(payload, MAX_PAYLOAD_SIZE)) {
      Serial.print("Failed to flash data");
      while (1);
    } else {
      Serial.println("OK");
    }
  }

  myFile.close();
  
  uint8_t md5[16];
  if (!ESP32BootROM.md5Flash(0, firmsize, md5)) {
    Serial.println("Error calculating MD5");
  } else {
    Serial.print("MD5 OK: ");
    for (int i=0; i<16; i++) {
      Serial.print("0x"); Serial.print(md5[i], HEX); Serial.print(" ");
    }
    Serial.println();
  }

  Serial.print("Took "); Serial.print(millis()-timestamp); Serial.println(" millis");
  while (1);
}
