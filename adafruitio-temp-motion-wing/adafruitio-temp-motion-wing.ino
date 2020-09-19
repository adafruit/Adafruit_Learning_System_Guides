// Adafruit IO - Analog Devices ADT7410 + ADXL343 Example
//
// Adafruit invests time and resources providing this open source code.
// Please support Adafruit and open source hardware by purchasing
// products from Adafruit!
//
// Written by Brent Rubell for Adafruit Industries
// Copyright (c) 2019 Adafruit Industries
// Licensed under the MIT license.
//
// All text above must be included in any redistribution.

/************************ Adafruit IO Config *******************************/
// visit io.adafruit.com if you need to create an account,
// or if you need your Adafruit IO key.
#define IO_USERNAME "YOUR_IO_USERNAME"
#define IO_KEY "YOUR_IO_KEY"

/******************************* WiFi Config ********************************/
#define WIFI_SSID "WIFI_NAME"
#define WIFI_PASS "WIFI_PASS"

// comment out the following two lines if you are using fona or ethernet
#include "AdafruitIO_WiFi.h"
AdafruitIO_WiFi io(IO_USERNAME, IO_KEY, WIFI_SSID, WIFI_PASS);

/************************** Configuration ***********************************/
// time between sending data to adafruit io, in seconds.
#define IO_DELAY 5
/************************ Example Starts Here *******************************/
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include "Adafruit_ADT7410.h"
#include <Adafruit_ADXL343.h>

float tempC, accelX, accelY, accelZ;

// Create the ADT7410 temperature sensor object
Adafruit_ADT7410 tempsensor = Adafruit_ADT7410();

// Create the ADXL343 accelerometer sensor object
Adafruit_ADXL343 accel = Adafruit_ADXL343(12345);

// set up the 'temperature' feed
AdafruitIO_Feed *huzzah_temperature = io.feed("temperature");

// set up the 'accelX' feed
AdafruitIO_Feed *huzzah_accel_x = io.feed("accelX");

// set up the 'accelY' feed
AdafruitIO_Feed *huzzah_accel_y = io.feed("accelY");

// set up the 'accelZ' feed
AdafruitIO_Feed *huzzah_accel_z= io.feed("accelZ");

void setup()
{
  // start the serial connection
  Serial.begin(115200);

  // wait for serial monitor to open
  while (!Serial)
    ;

  Serial.println("Adafruit IO - ADT7410 + ADX343");

  /* Initialise the ADXL343 */
  if(!accel.begin())
  {
    /* There was a problem detecting the ADXL343 ... check your connections */
    Serial.println("Ooops, no ADXL343 detected ... Check your wiring!");
    while(1);
  }

  /* Set the range to whatever is appropriate for your project */
  accel.setRange(ADXL343_RANGE_16_G);

  /* Initialise the ADT7410 */
  if (!tempsensor.begin())
  {
    Serial.println("Couldn't find ADT7410!");
    while (1)
      ;
  }

  // sensor takes 250 ms to get first readings
  delay(250);

  // connect to io.adafruit.com
  Serial.print("Connecting to Adafruit IO");
  io.connect();

  // wait for a connection
  while (io.status() < AIO_CONNECTED)
  {
    Serial.print(".");
    delay(500);
  }

  // we are connected
  Serial.println();
  Serial.println(io.statusText());
}

void loop()
{
  // io.run(); is required for all sketches.
  // it should always be present at the top of your loop
  // function. it keeps the client connected to
  // io.adafruit.com, and processes any incoming data.
  io.run();

   /* Get a new accel. sensor event */
  sensors_event_t event;
  accel.getEvent(&event);

  accelX = event.acceleration.x;
  accelY = event.acceleration.y;
  accelZ = event.acceleration.z;

  /* Display the results (acceleration is measured in m/s^2) */
  Serial.print("X: "); Serial.print(accelX); Serial.print("  ");
  Serial.print("Y: "); Serial.print(accelY); Serial.print("  ");
  Serial.print("Z: "); Serial.print(accelZ); Serial.print("  ");Serial.println("m/s^2 ");
  
  // Read and print out the temperature
  tempC = tempsensor.readTempC();
  Serial.print("Temperature: "); Serial.print(tempC); Serial.println("C");

  Serial.println("Sending to Adafruit IO...");
  huzzah_temperature->save(tempC, 0, 0, 0, 2);
  huzzah_accel_x->save(accelX);
  huzzah_accel_y->save(accelY);
  huzzah_accel_z->save(accelZ);
  Serial.println("Data sent!");

  Serial.print("Waiting ");Serial.print(IO_DELAY);Serial.println(" seconds...");
  // wait IO_DELAY seconds between sends
  for (int i = 0; i < IO_DELAY; i++)
  {
    delay(1000);
  }
}
