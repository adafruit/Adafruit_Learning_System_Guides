// SPDX-FileCopyrightText: 2017 Dave Astels for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Humidity Monitor
// Copyright (C) 2017 Dave Astels
// Released until the MIT license
//
// The trinket is controlled by an external Power Timer Breakout
//     (https://www.adafruit.com/product/3435)
// 1. Every however often, the timer will power up the trinket which will run
//    this file.
// 2. Relative humidity is checked
//   - if it's within range, the trinket tells the timer to shut it down and start
//     the timing cycle
//   - if it's out of range, it beeps & flashes the neopixel for 2 seconds, then
//     sleeps for 10 seconds, then goes to 2

#include "Adafruit_Si7021.h"
#include <Adafruit_DotStar.h>
#include <SPI.h>

const unsigned long falling_tones[] = { 2000, 1980, 1960, 1940, 1920, 1900, 1880, 1860, 1840, 1820, 1800, 1780, 1760, 1740, 1720, 1700, 1680, 1660, 1640, 1620 };
const unsigned long rising_tones[] =  { 2000, 2020, 2040, 2060, 2080, 3000, 3020, 3040, 3060, 3080, 4000, 4020, 4040, 4060, 4080, 5000, 5020, 5040, 5060, 5080 };

const int dotstar_data_pin = 7;
const int dotstar_clock_pin = 8;
const int sound_pin = 3;
const int sleep_pin = 4;

const int target_humidity = 61.0;
const unsigned long alert_interval = 20000;
const unsigned long alert_duration = 500;
const unsigned long comparison_delay = alert_interval - alert_duration;
const unsigned long number_of_freq_steps = 20;
const unsigned long alert_freq_step_time = alert_duration / number_of_freq_steps;

Adafruit_Si7021 sensor = Adafruit_Si7021();
//Adafruit_DotStar strip = Adafruit_DotStar(1, DOTSTAR_BRG);

//--------------------------------------------------------------------------------
// Sound the alert.

void chirp(boolean direction)
{
  const unsigned long *freqs = direction ? rising_tones : falling_tones;
  for (int i = 0; i < number_of_freq_steps; i++) {
    tone(sound_pin, freqs[i]);
    delay(alert_freq_step_time);
  }
  noTone(sound_pin);
}


//--------------------------------------------------------------------------------
// Measure relative humidity and return whether it is under/in/over range.

int check_rh()
{
  float relative_humidity = sensor.readHumidity();
  if (relative_humidity < (target_humidity - 5)) {
    return -1;
  } else if (relative_humidity > (target_humidity + 5)) {
    return 1;
  } else {
    return 0;
  }
}

//--------------------------------------------------------------------------------
// Repeatedly check the humidity and light the neopixel and sound the buzzer as
// appropriate, for as long as the reading is out of range.
// Initial comparison result is passed in.

void warn_if_out_of_range(int comparison)
{
  while (comparison != 0) {
    chirp(comparison > 0);
    delay(comparison_delay);
    comparison = check_rh();
  }
}



void setup()
{
  pinMode(sleep_pin, OUTPUT);
  digitalWrite(sleep_pin, LOW);
  //  strip.setPixelColor(0, 0);
  //  strip.show();

  sensor.begin();
  warn_if_out_of_range(check_rh());

}

void loop()
{
  digitalWrite(sleep_pin, HIGH);
  delay(50);
  digitalWrite(sleep_pin, LOW);
  delay(50);
}
