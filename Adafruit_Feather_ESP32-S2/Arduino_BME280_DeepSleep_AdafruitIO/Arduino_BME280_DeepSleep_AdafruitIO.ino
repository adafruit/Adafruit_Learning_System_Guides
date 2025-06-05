// SPDX-FileCopyrightText: 2025 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT
#include "config.h"
#include <Adafruit_BME280.h>
#include <Adafruit_NeoPixel.h>

Adafruit_BME280 bme; // I2C

AdafruitIO_Feed *temperature = io.feed("temperature");
AdafruitIO_Feed *humidity = io.feed("humidity");
AdafruitIO_Feed *pressure = io.feed("pressure");
float temp, humid, pres;

Adafruit_NeoPixel pixel(1, PIN_NEOPIXEL, NEO_GRB + NEO_KHZ800);


void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);

  // wait for serial monitor to open
  //while(! Serial);

  // turn on neopixel
  pinMode(NEOPIXEL_POWER, OUTPUT);
  digitalWrite(NEOPIXEL_POWER, HIGH);
  pixel.begin(); // INITIALIZE NeoPixel strip object (REQUIRED)
  pixel.setBrightness(10); // not so bright

  pixel.setPixelColor(0, 0xFF0000); // red
  pixel.show();

  if (! bme.begin()) {
      Serial.println("Could not find a valid BME280 sensor, check wiring, address, sensor ID!");
      deepSleep();
  }
  Serial.println("Found BME280");
  float temp = bme.readTemperature();
  float pres = bme.readPressure() / 100.0F;
  float hum = bme.readHumidity();
  // shhh time to close your eyes
  bme.setSampling(Adafruit_BME280::MODE_SLEEP,
                  Adafruit_BME280::SAMPLING_X16, Adafruit_BME280::SAMPLING_X16, Adafruit_BME280::SAMPLING_X16,
                  Adafruit_BME280::FILTER_OFF,
                  Adafruit_BME280::STANDBY_MS_1000);

  Serial.print("Connecting to Adafruit IO");

  pixel.setPixelColor(0, 0xFFFF00); // yellow
  pixel.show();

  // connect to io.adafruit.com
  io.connect();

  // wait for a connection
  while(io.status() < AIO_CONNECTED) {
    Serial.print(".");
    delay(100);
  }

  // we are connected
  pixel.setPixelColor(0, 0x00FF00); // green
  pixel.show();
  Serial.println();
  Serial.println(io.statusText());

  io.run();

  temp = temp * 9.0 / 5.0 + 32;
  Serial.print("Temperature = ");
  Serial.print(temp);
  Serial.println(" *F");
  temperature->save(temp);

  Serial.print("Pressure = ");
  Serial.print(pres);
  Serial.println(" hPa");
  pressure->save(pres);

  Serial.print("Humidity = ");
  Serial.print(hum);
  Serial.println(" %");
  humidity->save(hum);

  Serial.println();

  deepSleep();
}

void loop() {
   // we never get here!
}


void deepSleep() {
  pinMode(NEOPIXEL_POWER, OUTPUT);
  digitalWrite(NEOPIXEL_POWER, LOW); // off
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  esp_sleep_enable_timer_wakeup(300000000); // 5 minutes
  esp_deep_sleep_start();
}