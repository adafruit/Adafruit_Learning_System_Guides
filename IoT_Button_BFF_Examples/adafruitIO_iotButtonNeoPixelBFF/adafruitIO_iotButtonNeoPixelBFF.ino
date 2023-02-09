// SPDX-FileCopyrightText: 2016 Todd Treece, Adapted 2023 Liz Clark for Adafruit Industries
//
// SPDX-License-Identifier: MIT
// Adafruit IO IoT Button with NeoPixel BFF Demo
//
// Adafruit invests time and resources providing this open source code.
// Please support Adafruit and open source hardware by purchasing
// products from Adafruit!
//
// Written by Todd Treece for Adafruit Industries
// Copyright (c) 2016 Adafruit Industries
// Licensed under the MIT license.
//
// All text above must be included in any redistribution.

/************************** Configuration ***********************************/

// edit the config.h tab and enter your Adafruit IO credentials
// and any additional configuration needed for WiFi, cellular,
// or ethernet clients.
#include "config.h"
#include <Adafruit_NeoPixel.h>

/************************ Example Starts Here *******************************/

#define BUTTON_PIN A2
#define LED_PIN    A3
#define LED_COUNT 1
Adafruit_NeoPixel pixel(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

// button state
bool current = false;
bool last = false;

// set up the 'digital' feed
AdafruitIO_Feed *digital = io.feed("digital");

void setup() {
  pixel.begin();
  pixel.show();            
  pixel.setBrightness(50); 
  pixel.setPixelColor(0, pixel.Color(150, 0, 0));
  pixel.show();
  
  // set button pin as an input
  pinMode(BUTTON_PIN, INPUT);

  // start the serial connection
  Serial.begin(115200);

  // wait for serial monitor to open
  while(! Serial);

  // connect to io.adafruit.com
  Serial.print("Connecting to Adafruit IO");
  io.connect();

  // wait for a connection
  while(io.status() < AIO_CONNECTED) {
    Serial.print(".");
    delay(500);
  }

  // we are connected
  Serial.println();
  Serial.println(io.statusText());
  pixel.setPixelColor(0, pixel.Color(0, 150, 0));
  pixel.show();

}

void loop() {

  // io.run(); is required for all sketches.
  // it should always be present at the top of your loop
  // function. it keeps the client connected to
  // io.adafruit.com, and processes any incoming data.
  io.run();

  // grab the current state of the button.
  // we have to flip the logic because we are
  // using a pullup resistor.
  if(digitalRead(BUTTON_PIN) == LOW){
    current = true;
    pixel.setPixelColor(0, pixel.Color(0, 0, 150));
    pixel.show();
  }
  else {
    current = false;
    pixel.setPixelColor(0, pixel.Color(0, 150, 0));
    pixel.show();
  }
  // return if the value hasn't changed
  if(current == last)
    return;

  // save the current state to the 'digital' feed on adafruit io
  Serial.print("sending button -> ");
  Serial.println(current);
  digital->save(current);

  // store last button state
  last = current;

}
