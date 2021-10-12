// SPDX-FileCopyrightText: 2021 Phil Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
FIRE EFFECT for Adafruit EyeLights (LED Glasses + Driver).
A demoscene classic that produces a cool analog-esque look with
modest means, iteratively scrolling and blurring raster data.
*/

#include <Adafruit_IS31FL3741.h> // For LED driver

Adafruit_EyeLights_buffered glasses; // Buffered for smooth animation

// The raster data is intentionally one row taller than the LED matrix.
// Each frame, random noise is put in the bottom (off matrix) row. There's
// also an extra column on either side, to avoid needing edge clipping when
// neighboring pixels (left, center, right) are averaged later.
float data[6][20]; // 2D array where elements are accessed as data[y][x]

// Each element in the raster is a single value representing brightness.
// A pre-computed lookup table maps these to RGB colors. This one happens
// to have 32 elements, but as we're not on an actual paletted hardware
// framebuffer it could be any size really (with suitable changes throughout).
uint32_t colormap[32];
#define GAMMA 2.6

// Crude error handler, prints message to Serial console, flashes LED
void err(char *str, uint8_t hz) {
  Serial.println(str);
  pinMode(LED_BUILTIN, OUTPUT);
  for (;;) digitalWrite(LED_BUILTIN, (millis() * hz / 500) & 1);
}

void setup() { // Runs once at program start...

  // Initialize hardware
  Serial.begin(115200);
  if (! glasses.begin()) err("IS3741 not found", 2);

  // Configure glasses for reduced brightness, enable output
  glasses.setLEDscaling(0xFF);
  glasses.setGlobalCurrent(20);
  glasses.enable(true);

  memset(data, 0, sizeof data);

  for(uint8_t i=0; i<32; i++) {
    float n = i * 3.0 / 31.0; // 0.0 <= n <= 3.0 from start to end of map
    float r, g, b;
    if (n <= 1) { //             0.0 <= n <= 1.0 : black to red
      r = n;      //               r,g,b are initially calculated 0 to 1 range
      g = b = 0.0;
    } else if (n <= 2) { //      1.0 <= n <= 2.0 : red to yellow
      r = 1.0;
      g = n - 1.0;
      b = 0.0;
    } else { //                  2.0 <= n <= 3.0 : yellow to white
      r = g = 1.0;
      b = n - 2.0;
    }
    // Gamma correction linearizes perceived brightness, then scale to
    // 0-255 for LEDs and store as a 'packed' RGB color.
    colormap[i] = (uint32_t(pow(r, GAMMA) * 255.0) << 16) |
                  (uint32_t(pow(g, GAMMA) * 255.0) <<  8) |
                   uint32_t(pow(b, GAMMA) * 255.0);
  }
}

// Linearly interpolate a range of brightnesses between two LEDs of
// one eyeglass ring, mapping through the global color table. LED range
// is non-inclusive; the first and last LEDs (which overlap matrix pixels)
// are not set. led2 MUST be > led1. LED indices may be >= 24 to 'wrap
// around' the seam at the top of the ring.
void interp(bool isRight, int led1, int led2, float level1, float level2) {
  int span = led2 - led1 + 1;                   // Number of LEDs
  float delta = level2 - level1;                // Difference in brightness
  for (int led = led1 + 1; led < led2; led++) { // For each LED in-between,
    float ratio = (float)(led - led1) / span;   // interpolate brightness level
    uint32_t color = colormap[min(31, int(level1 + delta * ratio))];
    if (isRight) glasses.right_ring.setPixelColor(led % 24, color);
    else         glasses.left_ring.setPixelColor(led % 24, color);
  }
}

void loop() { // Repeat forever...
  // At the start of each frame, fill the bottom (off matrix) row
  // with random noise. To make things less strobey, old data from the
  // prior frame still has about 1/3 'weight' here. There's no special
  // real-world significance to the 85, it's just an empirically-
  // derived fudge factor that happens to work well with the size of
  // the color map.
  for (uint8_t x=1; x<19; x++) {
    data[5][x] = 0.33 * data[5][x] + 0.67 * ((float)random(1000) / 1000.0) * 85.0;
  }
  // If this were actual SRS BZNS 31337 D3M0SC3N3 code, great care
  // would be taken to avoid floating-point math. But with few pixels,
  // and so this code might be less obtuse, a casual approach is taken.

  // Each row (except last) is then processed, top-to-bottom. This
  // order is important because it's an iterative algorithm...the
  // output of each frame serves as input to the next, and the steps
  // below (looking at the pixels below each row) are what makes the
  // "flames" appear to move "up."
  for (uint8_t y=0; y<5; y++) {        // Current row of pixels
    float *y1 = &data[y + 1][0];       // One row down
    for (uint8_t x = 1; x < 19; x++) { // Skip left, right columns in data
      // Each pixel is sort of the average of the three pixels
      // under it (below left, below center, below right), but not
      // exactly. The below center pixel has more 'weight' than the
      // others, and the result is scaled to intentionally land
      // short, making each row bit darker as they move up.
      data[y][x] = (y1[x] + ((y1[x - 1] + y1[x + 1]) * 0.33)) * 0.35;
      glasses.drawPixel(x - 1, y, glasses.color565(colormap[min(31, int(data[y][x]))]));
      // Remember that the LED matrix uses GFX-style "565" colors,
      // hence the round trip through color565() here, whereas the LED
      // rings (referenced in interp()) use NeoPixel-style 24-bit colors
      // (those can reference colormap[] directly).
    }
  }

  // That's all well and good for the matrix, but what about the extra
  // LEDs in the rings? Since these don't align to the pixel grid,
  // rather than trying to extend the raster data and filter it in
  // somehow, we'll fill those arcs with colors interpolated from the
  // endpoints where rings and matrix intersect. Maybe not perfect,
  // but looks okay enough!
  interp(false, 7, 17, data[4][8], data[4][1]);   // Left ring bottom
  interp(false, 21, 29, data[0][2], data[1][8]);  // Left ring top
  interp(true, 7, 17, data[4][18], data[4][11]);  // Right ring bottom
  interp(true, 19, 27, data[1][11], data[0][17]); // Right ring top

  glasses.show();
  delay(25);
}
