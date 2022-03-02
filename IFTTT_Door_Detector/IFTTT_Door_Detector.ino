// SPDX-FileCopyrightText: 2018 Tod Treece for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Adafruit IO IFTTT Door Detector
// 
// Learn Guide: https://learn.adafruit.com/using-ifttt-with-adafruit-io
//
// Adafruit invests time and resources providing this open source code.
// Please support Adafruit and open source hardware by purchasing
// products from Adafruit!
//
// Written by Todd Treece for Adafruit Industries
// Copyright (c) 2018 Adafruit Industries
// Licensed under the MIT license.
//
// All text above must be included in any redistribution.

/************************** Configuration ***********************************/

// edit the config.h tab and enter your Adafruit IO credentials
// and any additional configuration needed for WiFi, cellular,
// or ethernet clients.
#include "config.h"
#include <EEPROM.h>
/************************ Example Starts Here *******************************/

// door gpio pin
#define DOOR 13

// how often to report battery level to adafruit IO (in minutes)
#define BATTERY_INTERVAL 5

// how long to sleep between checking the door state (in seconds)
#define SLEEP_LENGTH 3

void setup() {

  // start the serial connection
  Serial.begin(115200);

  while (!Serial);
  Serial.println("Adafruit IO Door Detector");

  EEPROM.begin(512);
  pinMode(DOOR, INPUT_PULLUP);

  // get the current count position from eeprom
  byte battery_count = EEPROM.read(0);

  // we only need this to happen once every X minutes,
  // so we use eeprom to track the count between resets.
  if(battery_count >= ((BATTERY_INTERVAL * 60) / SLEEP_LENGTH)) {
    // reset counter
    battery_count = 0;
    // report battery level to Adafruit IO
    battery_level();
  }
  else {
    // increment counter
    battery_count++;
  }

  // save the current count
  EEPROM.write(0, battery_count);
  EEPROM.commit();

  // if door isn't open, we don't need to send anything
  if(digitalRead(DOOR) == LOW) {
    Serial.println("Door closed");
    // we don't do anything
  }
  else {
    // the door is open if we have reached here,
    // so we should send a value to Adafruit IO.
    Serial.println("Door is open!");
    door_open();
  }

  // we are done here. go back to sleep.
  Serial.println("zzzz");
  ESP.deepSleep(SLEEP_LENGTH * 1000000);
}

void loop() {
  // noop
}

void door_open(){
  // connect us to Adafruit IO...
  connect_AIO();

  // grab the door feed
  AdafruitIO_Feed *door = io.feed("door");

  Serial.println("Sending door value to door feed...");
  door->save(1);
  io.run();
}

void battery_level() {
  // read the battery level from the ESP8266 analog in pin.
  // analog read level is 10 bit 0-1023 (0V-1V).
  // our 1M & 220K voltage divider takes the max
  // lipo value of 4.2V and drops it to 0.758V max.
  // this means our min analog read value should be 580 (3.14V)
  // and the max analog read value should be 774 (4.2V).
  int level = analogRead(A0);

  // convert battery level to percent
  level = map(level, 580, 774, 0, 100);
  Serial.print("Battery level: "); Serial.print(level); Serial.println("%");

  // connect us to Adafruit IO
  connect_AIO();
  // grab the battery feed
  AdafruitIO_Feed *battery = io.feed("battery");
  
  // send battery level to AIO
  battery->save(level);
  io.run();
}

void connect_AIO() {
  Serial.println("Connecting to Adafruit IO...");
  io.connect();

  // wait for a connection
  while (io.status() < AIO_CONNECTED) {
    Serial.print(".");
    delay(500);
  }

  // we are connected
  Serial.println();
  Serial.println(io.statusText());
}

