// SPDX-FileCopyrightText: 2022 Phillip Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
Conway's Game of Life for 6X square RGB LED matrices.
Uses same physical matrix arrangement as "globe" program; see notes there.

usage: sudo ./life [options]

(You may or may not need the 'sudo' depending how the rpi-rgb-matrix
library is configured)

Options include all of the rpi-rgb-matrix flags, such as --led-pwm-bits=N
or --led-gpio-slowdown=N, and then the following:

  -k <int>   : Index of color palette to use. 0 = default black & white.
               (Sorry, -c and -p are both rpi-rgb-matrix abbreviations.
                Consider this a Monty Python Travel Agent Sketch nod.)
  -t <float> : Run time in seconds. Program will exit after this.
               Default is to run indefinitely, until crtl+C received.
  -f <float> : Fade in/out time in seconds. Used in combination with the
               -t option, this provides a nice fade-in, run for a while,
               fade-out and exit.

rpi-rgb-matrix has the following single-character abbreviations for
some configurables: -b (--led-brightness), -c (--led-chain),
-m (--led-gpio-mapping), -p (--led-pwm-bits), -P (--led-parallel),
-r (--led-rows). AVOID THESE in any future configurables added to this
program, as some users may have "muscle memory" for those options.

This code depends on the rpi-rgb-matrix library. While this .cc file has
a permissive MIT licence, libraries may (or not) have restrictions on
commercial use, distributing precompiled binaries, etc.  Check their
license terms if this is relevant to your situation.
*/

#include <getopt.h>
#include <led-matrix.h>
#include <math.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/time.h>

using namespace rgb_matrix;

// GLOBAL VARIABLES --------------------------------------------------------

typedef enum {
  EDGE_TOP = 0,
  EDGE_LEFT,
  EDGE_RIGHT,
  EDGE_BOTTOM,
} Edge;

// Colormaps appear reversed from what one might expect. The first element
// of each is the 'on' pixel color, and each subsequent element is the color
// as a pixel 'ages,' up to the final 'background' color. Hence simple B&W
// on/off palette is white in index 0, black in index 1.

uint8_t map_bw[][3] = { // Simple B&W
    {255, 255, 255},
    {0, 0, 0}};

uint8_t map_gray[][3] = { // Log2 grayscale
    {255, 255, 255},      // clang-format,
    {127, 127, 127},      // I love you
    {63, 63, 63},         // but
    {31, 31, 31},         // why
    {15, 15, 15},         // you
    {7, 7, 7},            // gotta
    {3, 3, 3},            // do
    {1, 1, 1},            // this
    {0, 0, 0}};           // to me?

uint8_t map_heat[][3] = {
    // Heatmap (white-yellow-red-black)
    {255, 255, 255}, // White
    {255, 255, 127}, // Two steps to...
    {255, 255, 0},   // Yellow
    {255, 170, 0},   // Three steps...
    {255, 85, 0},    // to...
    {255, 0, 0},     // Red
    {204, 0, 0},     // Four steps...
    {153, 0, 0},     //
    {102, 0, 0},     // to...
    {51, 0, 0},      //
    {0, 0, 0}        // Black
};

uint8_t map_spec[][3] = {
    // Color spectrum
    {255, 255, 255}, // White (100%)
    {127, 0, 0},     // Red (50%)
    {127, 31, 0},    // to...
    {127, 63, 0},    // Orange (50%)
    {127, 95, 0},    // to...
    {127, 127, 0},   // Yellow (etc)
    {63, 127, 0},    // to...
    {0, 127, 0},     // Green
    {0, 127, 127},   // Cyan
    {0, 0, 127},     // Blue
    {63, 0, 127},    // to...
    {127, 0, 127},   // Magenta
    {82, 0, 82},     // fade...
    {41, 0, 41},     // to...
    {0, 0, 0}        // Black
};

struct {
  uint8_t *data;
  uint8_t max;
} colormaps[] = {
    {(uint8_t *)map_bw, sizeof(map_bw) / sizeof(map_bw[0]) - 1},
    {(uint8_t *)map_gray, sizeof(map_gray) / sizeof(map_gray[0]) - 1},
    {(uint8_t *)map_heat, sizeof(map_heat) / sizeof(map_heat[0]) - 1},
    {(uint8_t *)map_spec, sizeof(map_spec) / sizeof(map_spec[0]) - 1},
};

#define NUM_PALETTES (sizeof(colormaps) / sizeof(colormaps[0]))

struct {
  uint8_t face;  // Index of face off this edge
  Edge edge;     // Which edge of face its entering that way
} face[6][4] = { // Order is top, left, right, bottom
  {{1, EDGE_LEFT}, {2, EDGE_TOP}, {4, EDGE_TOP}, {3, EDGE_RIGHT}},
  {{2, EDGE_LEFT}, {0, EDGE_TOP}, {5, EDGE_TOP}, {4, EDGE_RIGHT}},
  {{0, EDGE_LEFT}, {1, EDGE_TOP}, {3, EDGE_TOP}, {5, EDGE_RIGHT}},
  {{2, EDGE_RIGHT}, {5, EDGE_BOTTOM}, {0, EDGE_BOTTOM}, {4, EDGE_LEFT}},
  {{0, EDGE_RIGHT}, {3, EDGE_BOTTOM}, {1, EDGE_BOTTOM}, {5, EDGE_LEFT}},
  {{1, EDGE_RIGHT}, {4, EDGE_BOTTOM}, {2, EDGE_BOTTOM}, {3, EDGE_LEFT}}};


// These globals have defaults but are runtime configurable:
uint16_t matrix_size = 64; // Matrix X&Y pixel count (must be square)
uint16_t matrix_max = matrix_size - 1; // Matrix X&Y max coord
float run_time = -1.0;        // Time before exit (negative = run forever)
float fade_time = 0.0;        // Fade in/out time (if run_time is set)
float max_brightness = 255.0; // Fade up to, down from this value

// These globals are computed or allocated at runtime after taking input:
uint8_t *data[2]; // Cell arrays; current and next-in-progress
uint8_t idx = 0;  // Which data[] array is current
uint8_t *colormap;
uint8_t colormap_max;

// INTERRUPT HANDLER (to allow clearing matrix on exit) --------------------

volatile bool interrupt_received = false;
static void InterruptHandler(int signo) { interrupt_received = true; }

// COMMAND-LINE HELP -------------------------------------------------------

static int usage(const char *progname) {
  fprintf(stderr, "usage: %s [options]\n", progname);
  fprintf(stderr, "Options:\n");
  rgb_matrix::PrintMatrixFlags(stderr);
  fprintf(stderr, "\t-k <int>   : Color palette (0-%d)\n", NUM_PALETTES - 1);
  fprintf(stderr, "\t-t <float> : Run time in seconds\n");
  fprintf(stderr, "\t-f <float> : Fade in/out time in seconds\n");
  return 1;
}

// SUNDRY UTILITY-LIKE FUNCTIONS -------------------------------------------

uint8_t cross(uint8_t f, Edge e, int16_t *x, int16_t *y) {
  switch ((e << 2) | face[f][e].edge) {
  case (EDGE_TOP << 2) | EDGE_TOP:
    *x = matrix_max - *x;
    *y = 0;
    break;
  case (EDGE_TOP << 2) | EDGE_LEFT:
    *y = *x;
    *x = 0;
    break;
  case (EDGE_TOP << 2) | EDGE_RIGHT:
    *y = matrix_max - *x;
    *x = matrix_max;
    break;
  case (EDGE_TOP << 2) | EDGE_BOTTOM:
    *y = matrix_max;
    break;
  case (EDGE_LEFT << 2) | EDGE_TOP:
    *x = *y;
    *y = 0;
    break;
  case (EDGE_LEFT << 2) | EDGE_LEFT:
    *x = 0;
    *y = matrix_max - *y;
    break;
  case (EDGE_LEFT << 2) | EDGE_RIGHT:
    *x = matrix_max;
    break;
  case (EDGE_LEFT << 2) | EDGE_BOTTOM:
    *x = matrix_max - *y;
    *y = matrix_max;
    break;
  case (EDGE_RIGHT << 2) | EDGE_TOP:
    *x = matrix_max - *y;
    *y = 0;
    break;
  case (EDGE_RIGHT << 2) | EDGE_LEFT:
    *x = 0;
    break;
  case (EDGE_RIGHT << 2) | EDGE_RIGHT:
    *x = matrix_max;
    *y = matrix_max - *y;
    break;
  case (EDGE_RIGHT << 2) | EDGE_BOTTOM:
    *x = *y;
    *y = matrix_max;
    break;
  case (EDGE_BOTTOM << 2) | EDGE_TOP:
    *y = 0;
    break;
  case (EDGE_BOTTOM << 2) | EDGE_LEFT:
    *y = matrix_max - *x;
    *x = 0;
    break;
  case (EDGE_BOTTOM << 2) | EDGE_RIGHT:
    *y = *x;
    *x = matrix_max;
    break;
  case (EDGE_BOTTOM << 2) | EDGE_BOTTOM:
    *x = matrix_max - *x;
    *y = matrix_max;
    break;
  }

  return face[f][e].face;
}

uint8_t getPixel(uint8_t f, int16_t x, int16_t y) {
  if (x >= 0) {
    if (x < matrix_size) {
      // Pixel is within X range
      if (y >= 0) {
        if (y < matrix_size) {
          // Pixel is within face bounds
          return data[idx][(f * matrix_size + y) * matrix_size + x];
        } else {
          // Pixel is off bottom edge (but within X bounds)
          f = cross(f, EDGE_BOTTOM, &x, &y);
          return data[idx][(f * matrix_size + y) * matrix_size + x];
        }
      } else {
        // Pixel is off top edge (but within X bounds)
        f = cross(f, EDGE_TOP, &x, &y);
        return data[idx][(f * matrix_size + y) * matrix_size + x];
      }
    } else {
      // Pixel is off right edge
      if ((y >= 0) && (y < matrix_size)) {
        // Pixel is off right edge (but within Y bounds)
        f = cross(f, EDGE_RIGHT, &x, &y);
        return data[idx][(f * matrix_size + y) * matrix_size + x];
      }
    }
  } else {
    // Pixel is off left edge
    if ((y >= 0) && (y < matrix_size)) {
      // Pixel is off left edge (but within Y bounds)
      f = cross(f, EDGE_LEFT, &x, &y);
      return data[idx][(f * matrix_size + y) * matrix_size + x];
    }
  }

  // Pixel is off both X&Y edges. Because of cube topology,
  // there isn't really a pixel there.
  return 1; // 1 = dead pixel
}

void setPixel(uint8_t f, int16_t x, int16_t y, uint8_t value) {
  data[1 - idx][(f * matrix_size + y) * matrix_size + x] = value;
}

// MAIN CODE ---------------------------------------------------------------

int main(int argc, char *argv[]) {
  RGBMatrix *matrix;
  FrameCanvas *canvas;

  // INITIALIZE DEFAULTS and PROCESS COMMAND-LINE INPUT --------------------

  RGBMatrix::Options matrix_options;
  rgb_matrix::RuntimeOptions runtime_opt;

  matrix_options.cols = matrix_options.rows = matrix_size;
  matrix_options.chain_length = 6;
  runtime_opt.gpio_slowdown = 4; // For Pi 4 w/6 matrices

  // Parse matrix-related command line options first
  if (!ParseOptionsFromFlags(&argc, &argv, &matrix_options, &runtime_opt)) {
    return usage(argv[0]);
  }

  // Validate inputs for cube-like behavior
  if (matrix_options.cols != matrix_options.rows) {
    fprintf(stderr, "%s: matrix columns, rows must be equal (square matrix)\n",
            argv[0]);
    return 1;
  }
  if (matrix_options.chain_length * matrix_options.parallel != 6) {
    fprintf(stderr, "%s: total chained/parallel matrices must equal 6\n",
            argv[0]);
    return 1;
  }

  max_brightness = (float)matrix_options.brightness * 2.55; // 0-100 -> 0-255

  // Then parse any lingering program options (filename, etc.)
  int opt;
  uint8_t palettenum = 0;
  while ((opt = getopt(argc, argv, "k:t:f:")) != -1) {
    switch (opt) {
    case 'k':
      palettenum = atoi(optarg);
      if (palettenum >= NUM_PALETTES)
        palettenum = NUM_PALETTES - 1;
      else if (palettenum < 0)
        palettenum = 0;
      break;
    case 't':
      run_time = fabs(strtof(optarg, NULL));
      break;
    case 'f':
      fade_time = fabs(strtof(optarg, NULL));
      break;
    default: // '?'
      return usage(argv[0]);
    }
  }

  // LOAD and ALLOCATE DATA STRUCTURES -------------------------------------

  // Allocate cell arrays
  matrix_size = matrix_options.rows;
  matrix_max = matrix_size - 1;
  int num_elements = 6 * matrix_size * matrix_size;
  if (!(data[0] = (uint8_t *)malloc(num_elements * 2 * sizeof(uint8_t)))) {
    fprintf(stderr, "%s: can't allocate space for cell data\n", argv[0]);
    return 1;
  }
  data[1] = &data[0][num_elements];

  colormap = colormaps[palettenum].data;
  colormap_max = colormaps[palettenum].max;

  // Randomize initial state; 50% chance of any pixel being set
  int i;
  for (i = 0; i < num_elements; i++) {
    data[idx][i] = (rand() & 1) * colormap_max;
  }

  // INITIALIZE RGB MATRIX CHAIN and OFFSCREEN CANVAS ----------------------

  if (!(matrix = RGBMatrix::CreateFromOptions(matrix_options, runtime_opt))) {
    fprintf(stderr, "%s: couldn't create matrix object\n", argv[0]);
    return 1;
  }
  if (!(canvas = matrix->CreateFrameCanvas())) {
    fprintf(stderr, "%s: couldn't create canvas object\n", argv[0]);
    return 1;
  }

  // OTHER MINOR INITIALIZATION --------------------------------------------

  signal(SIGTERM, InterruptHandler);
  signal(SIGINT, InterruptHandler);

  struct timeval startTime, now;
  gettimeofday(&startTime, NULL); // Program start time

  // LOOP RUNS INDEFINITELY OR UNTIL CTRL+C or run_time ELAPSED ------------

  uint32_t frames = 0;
  int prevsec = -1;

  while (!interrupt_received) {
    gettimeofday(&now, NULL);
    double elapsed = ((now.tv_sec - startTime.tv_sec) +
                      (now.tv_usec - startTime.tv_usec) / 1000000.0);
    if (run_time > 0.0) { // Handle time limit and fade in/out if needed...
      if (elapsed >= run_time)
        break;
      if (elapsed < fade_time) {
        matrix->SetBrightness((int)(max_brightness * elapsed / fade_time));
      } else if (elapsed > (run_time - fade_time)) {
        matrix->SetBrightness(
            (int)(max_brightness * (run_time - elapsed) / fade_time));
      } else {
        matrix->SetBrightness(max_brightness);
      }
    }
    // Do life stuff...
    int newidx = 1 - idx;
    for (uint8_t f = 0; f < 6; f++) {
      // Upper-left corner of face in canvas space:
      int xoffset = (f % matrix_options.chain_length) * matrix_size;
      int yoffset = (f / matrix_options.chain_length) * matrix_size;
      for (int y = 0; y < matrix_size; y++) {
        for (int x = 0; x < matrix_size; x++) {
          // Value returned by getPixel is the "age" of that pixel being
          // empty...thus, 0 actually means pixel is currently occupied,
          // hence all the ! here when counting neighbors...
          uint8_t neighbors =
              !getPixel(f, x - 1, y - 1) + !getPixel(f, x, y - 1) +
              !getPixel(f, x + 1, y - 1) + !getPixel(f, x - 1, y) +
              !getPixel(f, x + 1, y) + !getPixel(f, x - 1, y + 1) +
              !getPixel(f, x, y + 1) + !getPixel(f, x + 1, y + 1);
          // Live cell w/2 or 3 neighbors continues, else dies.
          // Empty cell w/3 neighbors goes live.
          uint8_t n = getPixel(f, x, y);
          if (n == 0) { // Pixel (x,y) is 'alive'
            if ((neighbors < 2) || (neighbors > 3))
              n = 1; // Pixel 'dies'
          } else {   // Pixel (x,y) is 'dead'
            if (neighbors == 3)
              n = 0; // Wake up!
            else if (n < colormap_max)
              n += 1; // Decay
          }
          setPixel(f, x, y, n);
          n *= 3; // Convert color index to RGB offset
          canvas->SetPixel(xoffset + x, yoffset + y, colormap[n],
                           colormap[n + 1], colormap[n + 2]);
        }
      }
    }
    canvas = matrix->SwapOnVSync(canvas);
    idx = newidx;
    frames++;
    if (now.tv_sec != prevsec) {
      if (prevsec >= 0) {
        printf("%f\n", frames / elapsed);
      }
      prevsec = now.tv_sec;
    }
  }

  canvas->Clear();
  delete matrix;

  return 0;
}
