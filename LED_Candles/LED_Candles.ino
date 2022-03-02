// SPDX-FileCopyrightText: 2017 Mikey Sklar for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Adafruit_NeoPixel.h>

// The onboard red LED's pin
#define REDLED_PIN              1
// The data-in pin of the NeoPixel
#define WICK_PIN                0
// Any unconnected pin, to try to generate a random seed
#define UNCONNECTED_PIN         2

// The LED can be in only one of these states at any given time
#define BRIGHT                  0
#define UP                      1
#define DOWN                    2
#define DIM                     3

#define BRIGHT_HOLD             4
#define DIM_HOLD                5

// Percent chance the LED will suddenly fall to minimum brightness
#define INDEX_BOTTOM_PERCENT    10
// Absolute minimum red value (green value is a function of red's value)
#define INDEX_BOTTOM            128
// Minimum red value during "normal" flickering (not a dramatic change)
#define INDEX_MIN               192
// Maximum red value
#define INDEX_MAX               255

// Decreasing brightness will take place over a number of milliseconds in this range
#define DOWN_MIN_MSECS          20
#define DOWN_MAX_MSECS          250
// Increasing brightness will take place over a number of milliseconds in this range
#define UP_MIN_MSECS            20
#define UP_MAX_MSECS            250
// Percent chance the color will hold unchanged after brightening
#define BRIGHT_HOLD_PERCENT     20
// When holding after brightening, hold for a number of milliseconds in this range
#define BRIGHT_HOLD_MIN_MSECS   0
#define BRIGHT_HOLD_MAX_MSECS   100
// Percent chance the color will hold unchanged after dimming
#define DIM_HOLD_PERCENT        5
// When holding after dimming, hold for a number of milliseconds in this range
#define DIM_HOLD_MIN_MSECS      0
#define DIM_HOLD_MAX_MSECS      50

#define MINVAL(A,B)             (((A) < (B)) ? (A) : (B))
#define MAXVAL(A,B)             (((A) > (B)) ? (A) : (B))

Adafruit_NeoPixel *wick;
byte state;
unsigned long flicker_msecs;
unsigned long flicker_start;
byte index_start;
byte index_end;

void set_color(byte index)
  {
  index = MAXVAL(MINVAL(index, INDEX_MAX), INDEX_BOTTOM);
  if (index >= INDEX_MIN)
    wick->setPixelColor(0, index, (index * 3) / 8, 0);
  else if (index < INDEX_MIN)
    wick->setPixelColor(0, index, (index * 3.25) / 8, 0);

  wick->show();
  return;
  }

void setup()
  {
  // There is no good source of entropy to seed the random number generator,
  // so we'll just read the analog value of an unconnected pin.  This won't be
  // very random either, but there's really nothing else we can do.
  //
  // True randomness isn't strictly necessary, we just don't want a whole
  // string of these things to do exactly the same thing at the same time if
  // they're all powered on simultaneously.
  randomSeed(analogRead(UNCONNECTED_PIN));

  // Turn off the onboard red LED
  pinMode(REDLED_PIN, OUTPUT);
  digitalWrite(REDLED_PIN, LOW);

  wick = new Adafruit_NeoPixel(1, WICK_PIN, NEO_RGB + NEO_KHZ800);
  // wick = new Adafruit_NeoPixel(1, WICK_PIN); // for RGBW, if you see green uncomment this line

  wick->begin();
  wick->show();

  set_color(255);
  index_start = 255;
  index_end = 255;
  state = BRIGHT;

  return;
  }

void loop()
  {
  unsigned long current_time;

  current_time = millis();

  switch (state)
    {
    case BRIGHT:
      flicker_msecs = random(DOWN_MAX_MSECS - DOWN_MIN_MSECS) + DOWN_MIN_MSECS;
      flicker_start = current_time;
      index_start = index_end;
      if ((index_start > INDEX_BOTTOM) &&
          (random(100) < INDEX_BOTTOM_PERCENT))
        index_end = random(index_start - INDEX_BOTTOM) + INDEX_BOTTOM;
      else
        index_end = random(index_start - INDEX_MIN) + INDEX_MIN;

      state = DOWN;
      break;
    case DIM:
      flicker_msecs = random(UP_MAX_MSECS - UP_MIN_MSECS) + UP_MIN_MSECS;
      flicker_start = current_time;
      index_start = index_end;
      index_end = random(INDEX_MAX - index_start) + INDEX_MIN;
      state = UP;
      break;
    case BRIGHT_HOLD:
    case DIM_HOLD:
      if (current_time >= (flicker_start + flicker_msecs))
        state = (state == BRIGHT_HOLD) ? BRIGHT : DIM;

      break;
    case UP:
    case DOWN:
      if (current_time < (flicker_start + flicker_msecs))
        set_color(index_start + ((index_end - index_start) * (((current_time - flicker_start) * 1.0) / flicker_msecs)));
      else
        {
        set_color(index_end);

        if (state == DOWN)
          {
          if (random(100) < DIM_HOLD_PERCENT)
            {
            flicker_start = current_time;
            flicker_msecs = random(DIM_HOLD_MAX_MSECS - DIM_HOLD_MIN_MSECS) + DIM_HOLD_MIN_MSECS;
            state = DIM_HOLD;
            }
          else
            state = DIM;
          }
        else
          {
          if (random(100) < BRIGHT_HOLD_PERCENT)
            {
            flicker_start = current_time;
            flicker_msecs = random(BRIGHT_HOLD_MAX_MSECS - BRIGHT_HOLD_MIN_MSECS) + BRIGHT_HOLD_MIN_MSECS;
            state = BRIGHT_HOLD;
            }
          else
            state = BRIGHT;
          }
        }

      break;
    }

  return;
  }
