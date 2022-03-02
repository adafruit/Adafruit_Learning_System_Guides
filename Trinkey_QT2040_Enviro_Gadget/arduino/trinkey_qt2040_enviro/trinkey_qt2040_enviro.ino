// SPDX-FileCopyrightText: 2021 Carter Nelson for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>
#include <Adafruit_BME280.h>
#include <SensirionI2CScd4x.h>
#include <Wire.h>

//--| User Config |-----------------------------------------------
#define DATA_FORMAT   0         // 0=CSV, 1=JSON
#define DATA_RATE     5000      // generate new number ever X ms
#define BEAT_COLOR    0xADAF00  // neopixel heart beat color
#define BEAT_RATE     1000      // neopixel heart beat rate in ms, 0=none
//----------------------------------------------------------------

Adafruit_BME280 bme;
SensirionI2CScd4x scd4x;
Adafruit_NeoPixel neopixel(1, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);

uint16_t CO2, data_ready;
float scd4x_temp, scd4x_humid;
float temperature, humidity, pressure;
int current_time, last_data, last_beat;

void setup() {
  Serial.begin(115200);

  // init status neopixel
  neopixel.begin();
  neopixel.fill(0);
  neopixel.show();

  // init BME280 first, this calls Wire.begin()
  if (!bme.begin()) {
    Serial.println("Failed to initialize BME280.");
    neoPanic();
  }

  // init SCD40
  scd4x.begin(Wire);
  scd4x.stopPeriodicMeasurement();
  if (scd4x.startPeriodicMeasurement()) {
    Serial.println("Failed to start SCD40.");
    neoPanic();
  }

  // init time tracking
  last_data = last_beat = millis();
}

void loop() {
  current_time = millis();

  //-----------
  // Send Data
  //-----------
  if (current_time - last_data > DATA_RATE) {
    temperature = bme.readTemperature();
    pressure = bme.readPressure() / 100;
    humidity = bme.readHumidity();
    scd4x.setAmbientPressure(uint16_t(pressure));
    scd4x.readMeasurement(CO2, scd4x_temp, scd4x_humid);
    switch (DATA_FORMAT) {
      case 0:
        sendCSV(); break;
      case 1:
        sendJSON(); break;
      default:
        Serial.print("Unknown data format: "); Serial.println(DATA_FORMAT);
        neoPanic();
    }
    last_data = current_time;
  }

  //------------
  // Heart Beat
  //------------
  if ((BEAT_RATE) && (current_time - last_beat > BEAT_RATE)) {
    if (neopixel.getPixelColor(0)) {
      neopixel.fill(0);
    } else {
      neopixel.fill(BEAT_COLOR);
    }
    neopixel.show();
    last_beat = current_time;
  }
}

void sendCSV() {
  Serial.print(CO2); Serial.print(", ");
  Serial.print(pressure); Serial.print(", ");
  Serial.print(temperature); Serial.print(", ");
  Serial.println(humidity);
}

void sendJSON() {
  Serial.print("{");
  Serial.print("\"CO2\" : "); Serial.print(CO2); Serial.print(", ");
  Serial.print("\"pressure\" : "); Serial.print(pressure); Serial.print(", ");
  Serial.print("\"temperature\" : "); Serial.print(temperature); Serial.print(", ");
  Serial.print("\"humidity\" : "); Serial.print(humidity);
  Serial.println("}");
}

void neoPanic() {
  while (1) {
    neopixel.fill(0xFF0000); neopixel.show(); delay(100);
    neopixel.fill(0x000000); neopixel.show(); delay(100);
  }
}
