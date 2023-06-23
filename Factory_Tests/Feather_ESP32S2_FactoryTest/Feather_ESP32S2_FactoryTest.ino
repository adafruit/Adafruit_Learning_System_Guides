// SPDX-FileCopyrightText: 2022 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Arduino.h>
#include "Adafruit_MAX1704X.h"
#include "Adafruit_LC709203F.h"
#include <Adafruit_NeoPixel.h>
#include "Adafruit_TestBed.h"
#include <Adafruit_BME280.h>

Adafruit_BME280 bme; // I2C
bool bmefound = false;
extern Adafruit_TestBed TB;

Adafruit_LC709203F lc_bat;
Adafruit_MAX17048 max_bat;

bool maxfound = false;
bool lcfound = false;

void setup() {
  Serial.begin(115200);
  // while (! Serial) delay(10);
  
  delay(100);

  pinMode(NEOPIXEL_POWER, OUTPUT);
  digitalWrite(NEOPIXEL_POWER, HIGH);
  delay(10);
  
  TB.neopixelPin = PIN_NEOPIXEL;
  TB.neopixelNum = 1; 
  TB.begin();
  TB.setColor(WHITE);

  if (lc_bat.begin()) {
    Serial.println("Found LC709203F");
    Serial.print("Version: 0x"); Serial.println(lc_bat.getICversion(), HEX);
    lc_bat.setPackSize(LC709203F_APA_500MAH);
    lcfound = true;
  }
  else {
    Serial.println(F("Couldnt find Adafruit LC709203F?\nChecking for Adafruit MAX1704X.."));
    delay(200);
    if (!max_bat.begin()) {
      Serial.println(F("Couldnt find Adafruit MAX1704X?\nMake sure a battery is plugged in!"));
      while (1) delay(10);
    }
    Serial.print(F("Found MAX17048"));
    Serial.print(F(" with Chip ID: 0x")); 
    Serial.println(max_bat.getChipID(), HEX);
    maxfound = true;
    
  }
  

  if (TB.scanI2CBus(0x77)) {
    Serial.println("BME280 address");

    unsigned status = bme.begin();  
    if (!status) {
      Serial.println("Could not find a valid BME280 sensor, check wiring, address, sensor ID!");
      Serial.print("SensorID was: 0x"); Serial.println(bme.sensorID(),16);
      Serial.print("        ID of 0xFF probably means a bad address, a BMP 180 or BMP 085\n");
      Serial.print("   ID of 0x56-0x58 represents a BMP 280,\n");
      Serial.print("        ID of 0x60 represents a BME 280.\n");
      Serial.print("        ID of 0x61 represents a BME 680.\n");
      return;
    }
    Serial.println("BME280 found OK");
    bmefound = true;
  }
}

uint8_t j = 0;

void loop() {

  if (j % 10 == 0) {
    Serial.println("**********************");
    if (lcfound == true) {
      Serial.print(F("Batt Voltage: ")); 
      Serial.print(lc_bat.cellVoltage(), 1);
      Serial.print(" V  /  ");
      Serial.print(F("Batt Percent: "));
      Serial.print(lc_bat.cellPercent(), 0);
      Serial.println("%");
    }
    else {
      Serial.print(F("Batt Voltage: ")); 
      Serial.print(max_bat.cellVoltage(), 1);
      Serial.print(" V  /  ");
      Serial.print(F("Batt Percent: "));
      Serial.print(max_bat.cellPercent(), 0);
      Serial.println("%");
    }
    TB.printI2CBusScan();
  }
  TB.setColor(TB.Wheel(j++));
  return;
}
