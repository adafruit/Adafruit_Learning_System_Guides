/* Circuit Playground Express compass. */

/* Adafruit invests time and resources providing this open source code. */
/* Please support Adafruit and open source hardware by purchasing */
/* products from Adafruit! */

/* Written by Dave Astels for Adafruit Industries */
/* Copyright (c) 2018 Adafruit Industries */
/* Licensed under the MIT license. */

/* All text above must be included in any redistribution. */

#include <Wire.h>
#include <Adafruit_NeoPixel.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_LSM303_U.h>
#include <math.h>

/* Assign a unique ID to this sensor at the same time */
Adafruit_LSM303_Mag_Unified mag = Adafruit_LSM303_Mag_Unified(12345);

// Replace these two lines with the results of calibration
//---------------------------------------------------------------------------

float raw_mins[2] = {1000.0, 1000.0};
float raw_maxes[2] = {-1000.0, -1000.0};
//---------------------------------------------------------------------------

float mins[2];
float maxes[2];
float corrections[2] = {0.0, 0.0};


// Support both classic and express
#ifdef __AVR__
#define NEOPIXEL_PIN 17
#else
#define NEOPIXEL_PIN 8
#endif

// When we setup the NeoPixel library, we tell it how many pixels, and which pin to use to send signals.
// Note that for older NeoPixel strips you might need to change the third parameter--see the strandtest
// example for more information on possible values.
Adafruit_NeoPixel strip = Adafruit_NeoPixel(10, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);

// Map direction pie slices (of 30 deg each) to a neopixel, or two for the missing ones at USB & power.
int led_patterns[12][2] = {{4, 5}, {5, -1}, {6, -1}, {7, -1}, {8, -1}, {9, -1}, {9, 0}, {0 -1}, {1, -1}, {2, -1}, {3, -1}, {4, -1}};

#define BUTTON_A 4

void fill(int red, int green, int blue) {
  for (int i = 0; i < 10; i++) {
    strip.setPixelColor(i, red, green, blue);
  }
  strip.show();
}


// Do some initial reading to let the magnetometer settle in.
// This was found by experience to be required.
// Indicated to the user by blue LEDs.
void warm_up(void)
{
  sensors_event_t event;
  fill(0, 0, 64);
  for (int ignore = 0; ignore < 100; ignore++) {
    mag.getEvent(&event);
    delay(10);
  }
}


// Find the range of X and Y values.
// User needs to rotate the CPX a bunch during this.
// Can be refined by doing more of the saem by pressing the A button.
// Indicated to the user by green LEDs.
void calibrate(bool do_the_readings)
{
  sensors_event_t event;
  float values[2];

  fill(0, 64, 0);

  if (do_the_readings) {
    unsigned long start_time = millis();
    while (millis() - start_time < 5000) {

      mag.getEvent(&event);
      values[0] = event.magnetic.x;
      values[1] = event.magnetic.y * -1;
      if (values[0] != 0.0 && values[1] != 0.0) { /* ignore the random zero readings... it's bogus */
        for (int i = 0; i < 2; i++) {
          raw_mins[i] = values[i] < raw_mins[i] ? values[i] : raw_mins[i];
          raw_maxes[i] = values[i] > raw_maxes[i] ? values[i] : raw_maxes[i];
        }
      }
      delay(5);
    }
  }

  for (int i = 0; i < 2; i++) {
    corrections[i] = (raw_maxes[i] + raw_mins[i]) / 2;
    mins[i] = raw_mins[i] - corrections[i];
    maxes[i] = raw_maxes[i] - corrections[i];
  }
  fill(0, 0, 0);
}


void setup(void)
{
  strip.begin();
  strip.show();

  pinMode(BUTTON_A, INPUT_PULLDOWN);

  /* Enable auto-gain */
  mag.enableAutoRange(true);

  /* Initialise the sensor */
  if(!mag.begin())
  {
    /* There was a problem detecting the LSM303 ... check your connections */
    fill(255, 0, 0);
    while(1);
  }

  warm_up();

  // If reset with button A pressed or calibration hasn't been done, run calibration and report the results
  if (digitalRead(BUTTON_A) || (raw_mins[0] == 1000.0 && raw_mins[1] == 1000.0)) {
    while (!Serial);
    Serial.begin(9600);
    Serial.println("Compass calibration\n");

    raw_mins[0] = 1000.0;
    raw_mins[1] = 1000.0;
    raw_maxes[0] = -1000.0;
    raw_maxes[1] = -1000.0;
    calibrate(true);

    Serial.println("Calibration results\n");
    Serial.println("Update the corresponding lines near the top of the code\n");
    Serial.print("float raw_mins[2] = {"); Serial.print(raw_mins[0]); Serial.print(", "); Serial.print(raw_mins[1]); Serial.println("};");
    Serial.print("float raw_maxes[2] = {"); Serial.print(raw_maxes[0]); Serial.print(", "); Serial.print(raw_maxes[1]); Serial.println("};\n");

    while(1);
  } else {
    calibrate(false);
  }
}


// Map a value from the input range to the output range
// Used to map MAG values from the calibrated (min/max) range to (-100, 100)
float normalize(float value, float in_min, float in_max) {
  float mapped = (value - in_min) * 200 / (in_max - in_min) + -100;
  float max_clipped = mapped <  100 ? mapped : 100;
  float min_clipped = max_clipped > -100 ? max_clipped : -100;
  return min_clipped;
}


void loop(void)
{
  // Pressing button A does another round of calibration.
  if (digitalRead(BUTTON_A)) {
    calibrate(true);
  }

  sensors_event_t event;
  mag.getEvent(&event);

  float x = event.magnetic.x;
  float y = event.magnetic.y * -1;

  if (x == 0.0 && y == 0.0) {
    return;
  }

  float normalized_x = normalize(x - corrections[0], mins[0], maxes[0]);
  float normalized_y = normalize(y - corrections[1], mins[1], maxes[1]);

  int compass_heading = (int)(atan2(normalized_y, normalized_x) * 180.0 / 3.14159);
  // compass_heading is between -180 and +180 since atan2 returns -pi to +pi
  // this translates it to be between 0 and 360
  compass_heading += 180;

  // We add 15 to account to the zero position being 0 +/- 15 degrees.
  // mod by 360 to keep it within a circle
  // divide by 30 to find which pixel corresponding pie slice it's in
  int direction_index = ((compass_heading + 15) % 360) / 30;

  // light the pixel(s) for the direction the compass is pointing
  // the empty spots where the USB and power connects are use the two leds to either side.
  int *leds;
  leds = led_patterns[direction_index];
  for (int pixel = 0; pixel < 10; pixel++) {
    if (pixel == leds[0] || pixel == leds[1]) {
      strip.setPixelColor(pixel, 4, 0, 0);
    } else {
      strip.setPixelColor(pixel, 0, 0, 0);
    }
  }
  strip.show();
  delay(50);
}