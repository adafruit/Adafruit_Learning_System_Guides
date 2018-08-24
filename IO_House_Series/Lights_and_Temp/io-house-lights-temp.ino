// Adafruit IO House: Lights and Temperature
//
// Learn Guide: https://learn.adafruit.com/adafruit-io-house-lights-and-temperature
//
// Adafruit invests time and resources providing this open source code.
// Please support Adafruit and open source hardware by purchasing
// products from Adafruit!
//
// Written by Brent Rubell for Adafruit Industries
// Copyright (c) 2018 Adafruit Industries
// Licensed under the MIT license.
//
// All text above must be included in any redistribution.

/************************** Configuration ***********************************/

// edit the config.h tab and enter your Adafruit IO credentials
// and any additional configuration needed for WiFi, cellular,
// or ethernet clients.
#include "config.h"

// include the NeoPixel library
#include "Adafruit_NeoPixel.h"

// include the si7021 library
#include "Adafruit_Si7021.h"
/************************ Example Starts Here *******************************/

// pin the NeoPixel strip is connected to
#define STRIP_PIN            12
// pin the NeoPixel Jewel is connected to
#define JEWEL_PIN 2

// amount of neopixels on the NeoPixel strip
#define STRIP_PIXEL_COUNT   34
// amount of neopixels on the NeoPixel jewel
#define JEWEL_PIXEL_COUNT 7

// type of neopixels used by the NeoPixel strip and jewel.
#define PIXEL_TYPE    NEO_GRB + NEO_KHZ800

// main loop() delay, in seconds
#define TEMP_DELAY  7

// Temperature and Humidity: Si7021 Sensor
int temperatureData;
int humidityData;

// initalize neopixel strip
Adafruit_NeoPixel strip = Adafruit_NeoPixel(STRIP_PIXEL_COUNT, STRIP_PIN, PIXEL_TYPE);
// initalize neopixel jewel
Adafruit_NeoPixel jewel = Adafruit_NeoPixel(JEWEL_PIXEL_COUNT, JEWEL_PIN, PIXEL_TYPE);

// initalize the sensor object
Adafruit_Si7021 sensor = Adafruit_Si7021();

// set up the Adafruit IO House Group
AdafruitIO_Group *houseGroup  = io.group("io-house");

void setup() {

  // start the serial connection
  Serial.begin(115200);

  // wait for serial monitor to open
  while(! Serial);

  // connect to io.adafruit.com
  Serial.print("Connecting to Adafruit IO");
  io.connect();

  // subscribe to lighting feeds and register message handlers
  houseGroup->onMessage("indoor-lights", indoorLightHandler);
  houseGroup->onMessage("outside-lights", outdoorLightHandler);

  // wait for a connection
  while(io.status() < AIO_CONNECTED) {
    Serial.print(".");
    delay(500);
  }

  // we are connected
  Serial.println();
  Serial.println(io.statusText());

  // initalize the Si7021 sensor
  if (!sensor.begin()) {
    Serial.println("Did not find Si7021 sensor!");
    while (true);
  }
  Serial.println("Si7021 sensor set up!");
  
  // initalize the neopixel strip and jewel.
  strip.begin();
  jewel.begin();

  // set all neopixels on the strip and jewel to `off`.
  strip.show();
  jewel.show();
}

void loop() {
  // io.run(); is required for all sketches.
  // it should always be present at the top of your loop
  // function. it keeps the client connected to
  // io.adafruit.com, and processes any incoming data.
  io.run();

  temperatureData = sensor.readTemperature() * 1.8 + 32;
  humidityData = sensor.readHumidity();

  
  Serial.print("-> Sending Temperature to Adafruit IO: ");
  Serial.println(temperatureData);
  Serial.print("-> Sending Humidity to Adafruit IO: ");
  Serial.println(humidityData);

  // set feeds to temperature and humidity data
  houseGroup->set("humidity", temperatureData);
  houseGroup->set("temperature", humidityData);
  // send these values to Adafruit IO
  houseGroup->save();

  // delay the loop to avoid flooding Adafruit IO
  delay(1000*TEMP_DELAY);

}

void indoorLightHandler(AdafruitIO_Data *data) {
  Serial.print("-> indoor light HEX: ");
  Serial.println(data->value());

  long color = data->toNeoPixel();

  // set the color of each NeoPixel in the jewel
  for(int i=0; i<JEWEL_PIXEL_COUNT; ++i) {
    jewel.setPixelColor(i, color);
  }
  // 'set' the neopixel jewel to the new color
  jewel.show();
}

void outdoorLightHandler(AdafruitIO_Data *data) {
  Serial.print("-> outdoor light HEX: ");
  Serial.println(data->value());

  long color = data->toNeoPixel();

   // set the color of each NeoPixel in the strip
  for(int i=0; i<STRIP_PIXEL_COUNT; ++i) {
    strip.setPixelColor(i, color);
  }
  // 'set' the neopixel strip to the new color
  strip.show();
}


