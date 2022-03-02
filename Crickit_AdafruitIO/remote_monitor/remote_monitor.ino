// SPDX-FileCopyrightText: 2018 Dave Astels for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Crickit + Adafruit IO Publish Example
//
// Adafruit invests time and resources providing this open source code.
// Please support Adafruit and open source hardware by purchasing
// products from Adafruit!
//
// Written by Dave Astels for Adafruit Industries
// Copyright (c) 2018 Adafruit Industries
// Licensed under the MIT license.
//
// All text above must be included in any redistribution.

#include "config.h"
#include <Adafruit_Crickit.h>

#define CAPTOUCH_THRESH 500

#define IO_LOOP_DELAY (1000)
unsigned long lastUpdate = 0;

// set up the feeds
AdafruitIO_Feed *light;
uint16_t last_reported_light = 0;

AdafruitIO_Feed *touch;
boolean last_touch = false;

// set up the Crickit

Adafruit_Crickit crickit;

void setup_feeds()
{
  light = io.feed("crickit.light");
  touch = io.feed("crickit.touch-0");
}


void setup()
{
  setup_feeds();
  Serial.println("Feeds set up");

  // start the serial connection
  Serial.begin(115200);

  // wait for serial monitor to open
  while(! Serial);

  Serial.println("Connecting to Adafruit IO");

  // connect to io.adafruit.com
  io.connect();

  // wait for a connection
  while(io.status() < AIO_CONNECTED) {
    Serial.print(".");
    //    Serial.println(io.statusText());
    delay(500);
  }

  // we are connected
  Serial.println();
  Serial.println(io.statusText());

  if (!crickit.begin()) {
    Serial.println("Error starting Crickit!");
    while(1);
  } else {
    Serial.println("Crickit started");
  }

  Serial.println("setup complete");
}


void loop()
{

  // io.run(); is required for all sketches.
  // it should always be present at the top of your loop
  // function. it keeps the client connected to
  // io.adafruit.com, and processes any incoming data.
  io.run();

  if (millis() > (lastUpdate + IO_LOOP_DELAY)) {

    uint16_t light_level = crickit.analogRead(CRICKIT_SIGNAL1);
    uint16_t light_delta = abs(light_level - last_reported_light);

    if (light_delta > 10) {
      light->save(light_level);
      last_reported_light = light_level;
      Serial.print("Sending ");
    }
    Serial.print("Light: ");
    Serial.println(light_level);

    uint16_t val = crickit.touchRead(0);

    if (val >= CAPTOUCH_THRESH && !last_touch) {
      touch->save(1);
      last_touch = true;
      Serial.println("CT 0 touched.");
    } else if (val < CAPTOUCH_THRESH && last_touch) {
      touch->save(0);
      last_touch = false;
      Serial.println("CT 0 released.");
    }

    // after publishing, store the current time
    lastUpdate = millis();
  }

}
