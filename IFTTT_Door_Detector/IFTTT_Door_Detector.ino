// Adafruit IO IFTTT Door Detector Example
// Tutorial Link: https://learn.adafruit.com/using-ifttt-with-adafruit-io
//
// Adafruit invests time and resources providing this open source code.
// Please support Adafruit and open source hardware by purchasing
// products from Adafruit!
//
// Written by Todd Treece for Adafruit Industries
// modified by Brent Rubell for Adafruit Industries
// Copyright (c) 2018 Adafruit Industries
// Licensed under the MIT license.
//
// All text above must be included in any redistribution.

/************************** Configuration ***********************************/
// edit the config.h tab and enter your Adafruit IO credentials
// and any additional configuration needed for WiFi, cellular,
// or ethernet clients.
#include "config.h"
/************************ Example Starts Here *******************************/
// door pin
#define DOOR_PIN 13

// how often to report battery level to Adafruit IO (in minutes)
#define BATTERY_INTERVAL 5

// how long to sleep between checking the door state (in seconds)
#define SLEEP_LENGTH 30

// holds the count of the battery check (in minutes)
int loop_cycles = 0;

// set up the `door` feed
AdafruitIO_Feed *door = io.feed("door");

// set up the `battery` feed
AdafruitIO_Feed *battery = io.feed("battery");

void setup() {
  // start the serial connection
  Serial.begin(115200);

  // wait for serial monitor to open
  while (!Serial);
  Serial.println("IFTTT Door Detector");

  pinMode(DOOR_PIN, INPUT_PULLUP);

  // connect to io.adafruit.com
  Serial.println("Connecting to Adafruit IO");
  io.connect();

  // wait for a connection
  while(io.status() < AIO_CONNECTED) {
    Serial.print(".");
    delay(500);
  }

  // we are connected
  Serial.println();
  Serial.println(io.statusText());
}

void loop() {
  // io.run(); is required for all sketches.
  // it should always be present at the top of your loop
  // function. it keeps the client connected to
  // io.adafruit.com, and processes any incoming data.
  io.run();

  // check the loop interval against the battery check interval
  if (loop_cycles == BATTERY_INTERVAL) {
    // reset the counter
    loop_cycles = 0;
    // report the battery level to the IO 'battery' feed
    battery_level();
  }
  else {
    loop_cycles++; 
  }

  if (digitalRead(DOOR_PIN) == LOW) {
    // if the door isn't open, we don't need to send anything.
    Serial.println("\tDoor Closed");
  }
  else {
    // door open, let's send a value to adafruit io
    Serial.println("\tDoor Open");
    door->save(1);
  }

  // delay the loop by SLEEP_LENGTH seconds
  delay(SLEEP_LENGTH*1000);
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
  battery->save(level);
}

