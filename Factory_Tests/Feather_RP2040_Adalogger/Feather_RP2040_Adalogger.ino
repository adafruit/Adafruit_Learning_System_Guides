// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <SPI.h>
#include <Adafruit_TestBed.h>

SdFat SD;
SdFile file;
SdSpiConfig config(PIN_SD_DAT3_CS, DEDICATED_SPI, SD_SCK_MHZ(16), &SPI1);

extern Adafruit_TestBed TB;

bool card_state = false;

void setup() {
  Serial.begin(115200);
  //while (!Serial) { yield(); delay(10); }     // wait till serial port is opened
  delay(100);  // RP2040 delay is not a bad idea

  TB.neopixelPin = 17;
  TB.neopixelNum = 1;
  TB.begin();

  pinMode(PIN_CARD_DETECT, INPUT_PULLUP);
}

uint8_t x = 0;
void loop() {

    TB.setColor(TB.Wheel(x++));
    delay(10);

    if (card_state && !digitalRead(PIN_CARD_DETECT)) {
      Serial.println("Card removed");
      card_state = digitalRead(PIN_CARD_DETECT);
    }

    if (!card_state && digitalRead(PIN_CARD_DETECT)) {
      Serial.println("Card inserted");
      card_state = digitalRead(PIN_CARD_DETECT);
      delay(100);
      
      if (!SD.begin(config)) {
        Serial.println("SD card initialization failed!");
        return;
      }
      Serial.println("SD card initialized OK!");
  
      // Print the SD card details
      uint32_t size = SD.card()->sectorCount();
      if (size == 0) {
        Serial.printf("Can't determine the card size.\n");
        return;
      }
      uint32_t sizeMB = 0.000512 * size + 0.5;
      Serial.printf("Card size: %lu MB (MB = 1,000,000 bytes)\n", sizeMB);
      Serial.printf("\nVolume is FAT%d, Cluster size (bytes): %lu\n\n", int(SD.vol()->fatType()), SD.vol()->bytesPerCluster());
      
      SD.ls(LS_R | LS_DATE | LS_SIZE);
    }
    
    return;

}
