// SPDX-FileCopyrightText: 2018 Dave Astels for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Crickit + Adafruit IO Subscribe Example
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

/************************** Configuration ***********************************/

// edit the config.h tab and enter your Adafruit IO credentials
// and any additional configuration needed for WiFi, cellular,
// or ethernet clients.
#include "config.h"
#include <Adafruit_Crickit.h>
#include <seesaw_servo.h>
#include <seesaw_neopixel.h>

#define NEOPIX_PIN (20)                  /* Neopixel pin */
#define NEOPIX_NUMBER_OF_PIXELS (7)


// set up the feeds
AdafruitIO_Feed *servo1_control;
AdafruitIO_Feed *neopixel_control;

// set up the Crickit

Adafruit_Crickit crickit;
seesaw_Servo servo_1(&crickit);  // create servo object to control a servo

// Parameter 1 = number of pixels in strip
// Parameter 2 = Arduino pin number (most are valid)
// Parameter 3 = pixel type flags, add together as needed:
//   NEO_KHZ800  800 KHz bitstream (most NeoPixel products w/WS2812 LEDs)
//   NEO_KHZ400  400 KHz (classic 'v1' (not v2) FLORA pixels, WS2811 drivers)
//   NEO_GRB     Pixels are wired for GRB bitstream (most NeoPixel products)
//   NEO_RGB     Pixels are wired for RGB bitstream (v1 FLORA pixels, not v2)
//   NEO_RGBW    Pixels are wired for RGBW bitstream (NeoPixel RGBW products)
seesaw_NeoPixel strip = seesaw_NeoPixel(NEOPIX_NUMBER_OF_PIXELS, NEOPIX_PIN, NEO_GRB + NEO_KHZ800);

void setup_feeds()
{
  servo1_control = io.feed("crickit.servo1-control");
  neopixel_control = io.feed("crickit.neopixel-control");
}


void setup()
{
  // start the serial connection
  Serial.begin(115200);

  // wait for serial monitor to open
  while(! Serial);

  setup_feeds();
  Serial.println("Feeds set up");

  Serial.println("Connecting to Adafruit IO");

  // connect to io.adafruit.com
  io.connect();

  // set up message handlers for the servo and neopixel feeds.
  // the handle_*_message functions (defined below)
  // will be called whenever a message is
  // received from adafruit io.

  servo1_control->onMessage(handle_servo_message);
  neopixel_control->onMessage(handle_neopixel_message);

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

  if(!strip.begin()){
    Serial.println("Error starting Neopixels!");
    while(1);
  } else {
    Serial.println("Neopixels started");
  }

  servo1_control->get();

  servo_1.attach(CRICKIT_SERVO1);

  Serial.println("setup complete");
}


void loop()
{

  // io.run(); is required for all sketches.
  // it should always be present at the top of your loop
  // function. it keeps the client connected to
  // io.adafruit.com, and processes any incoming data.
  io.run();
}


void handle_servo_message(AdafruitIO_Data *data)
{
  Serial.print("received servo control <- ");
  Serial.println(data->value());
  int angle = data->toInt();
  if(angle < 0) {
    angle = 0;
  } else if(angle > 180) {
    angle = 180;
  }
  servo_1.write(angle);

}


void handle_neopixel_message(AdafruitIO_Data *data)
{
  Serial.print("received neopixel control <- ");
  Serial.println(data->value());
  long color = data->toNeoPixel();
  for (int pixel = 0; pixel < NEOPIX_NUMBER_OF_PIXELS; pixel++) {
    strip.setPixelColor(pixel, color);
  }
  strip.show();
}
