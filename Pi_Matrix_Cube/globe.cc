// SPDX-FileCopyrightText: 2022 Phillip Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
IF GLOBES WERE SQUARE: a revolving "globe" for 6X square RGB LED matrices on
Raspberry Pi w/Adafruit Matrix Bonnet or HAT.

usage: sudo ./globe [options]

(You may or may not need the 'sudo' depending how the rpi-rgb-matrix
library is configured)

Options include all of the rpi-rgb-matrix flags, such as --led-pwm-bits=N
or --led-gpio-slowdown=N, and then the following:

  -i <filename> : Image filename for texture map. MUST be JPEG image format.
                  Default is maps/earth.jpg
  -v            : Orient cube with vertices at top & bottom, rather than
                  flat faces on top & bottom. No accompanying value.
  -s <float>    : Spin time in seconds (per revolution). Positive values
                  will revolve in the correct direction for the Earth map.
                  Negative values spin the opposite direction (magnitude
                  specifies seconds), maybe useful for text, logos or Uranus.
  -a <int>      : Antialiasing samples, per-axis. Range 1-8. Default is 2,
                  for 2x2 supersampling. Fast hardware can go higher, slow
                  devices should use 1.
  -t <float>    : Run time in seconds. Program will exit after this.
                  Default is to run indefinitely, until crtl+C received.
  -f <float>    : Fade in/out time in seconds. Used in combination with the
                  -t option, this provides a nice fade-in, revolve for a
                  while, fade-out and exit. Combined with a simple shell
                  script, it provides a classy way to cycle among different
                  planetoids/scenes/etc. without having to explicitly
                  implement such a feature here.
  -e <float>    : Edge-to-edge physical measure of LED matrix. Combined
                  with -E below, provides spatial compensation for edge
                  bezels when matrices are arranged in a cube (i.e. pixels
                  don't "jump" across the seam -- has a bit of dead space).
  -E <float>    : Edge-to-edge measure of opposite faces of assembled cube,
                  used in combination with -e above. This will be a little
                  larger than the -e value (lower/upper case is to emphasize
                  this relationship). Units for both are arbitrary; use
                  millimeters, inches, whatever, it's the ratio that's
                  important.

rpi-rgb-matrix has the following single-character abbreviations for
some configurables: -b (--led-brightness), -c (--led-chain),
-m (--led-gpio-mapping), -p (--led-pwm-bits), -P (--led-parallel),
-r (--led-rows). AVOID THESE in any future configurables added to this
program, as some users may have "muscle memory" for those options.

This code depends on libjpeg and rpi-rgb-matrix libraries. While this
.cc file has a permissive MIT licence, those libraries may (or not) have
restrictions on commercial use, distributing precompiled binaries, etc.
Check their license terms if this is relevant to your situation.
*/

#include <math.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <getopt.h>
#include <jpeglib.h>
#include <led-matrix.h>

using namespace rgb_matrix;

// GLOBAL VARIABLES --------------------------------------------------------

// Some constants first...
const char default_filename[] = "maps/earth.jpg";

/* Cube coordinates use a right-handed coordinate system;
   +X is to right, +Y is up, +Z is toward your face

   Default is a flat/square/axis-aligned cube.
   Poles are at center of top & bottom faces.
   Numbers here are vertex indices (0-7):

        1-------------2
       /|   +Y       /|
      / |    ^      / |
     /  |    |     /  |
    0-------------3   |
    |   |    |    |   |
    |   |    0----|->+X
    |   |   /     |   |
    |   5--/------|---6
    |  /  L       |  /
    | /  +Z       | /
    |/            |/
    4-------------7
*/
const float square_coords[8][3] = {{-1, 1, 1},  {-1, 1, -1}, {1, 1, -1},
                                   {1, 1, 1},   {-1, -1, 1}, {-1, -1, -1},
                                   {1, -1, -1}, {1, -1, 1}};

const uint8_t verts[6][3] = {
    {0, 1, 3}, // Vertex indices for UL, UR, LL of top face matrix
    {0, 4, 1}, // " left
    {0, 3, 4}, // " front face
    {7, 3, 6}, // " right
    {2, 1, 6}, // " back
    {5, 4, 6}, // " bottom matrix
};

// Alternate coordinates for a rotated cube with points at poles.
// Vertex indices are the same (does not need a new verts[] array),
// relationships are the same, the whole thing is just pivoted to
// "hang" from vertex 3 at top. I will NOT attempt ASCII art of this.
const float xx = sqrt(26.0 / 9.0);
const float yy = sqrt(3.0) / 3.0;
const float cc = -0.5;       // cos(120.0 * M_PI / 180.0);
const float ss = sqrt(0.75); // sin(120.0 * M_PI / 180.0);
const float pointy_coords[8][3] = {
    {-xx, yy, 0.0},          // Vertex 0 = leftmost point
    {xx * cc, -yy, -xx *ss}, // 1
    {-xx * cc, yy, -xx *ss}, // 2
    {0.0, sqrt(3.0), 0.0},   // 3 = top
    {xx * cc, -yy, xx *ss},  // 4
    {0.0, -sqrt(3.0), 0.0},  // 5 = bottom
    {xx, -yy, 0.0},          // 6 = rightmost point
    {-xx * cc, yy, xx *ss}   // 7
};

// These globals have defaults but are runtime configurable:
uint8_t aa = 2;             // Antialiasing samples, per axis
uint16_t matrix_size = 64;  // Matrix X&Y pixel count (must be square)
bool pointy = false;        // Cube orientation has a vertex at top
float matrix_measure = 1.0; // Edge-to-edge dimension of LED matrix
float cube_measure = 1.0;   // Face-to-face dimension of assembled cube
float spin_time = 10.0;     // Seconds per rotation
char *map_filename = (char *)default_filename; // Planet image file
float run_time = -1.0;        // Time before exit (negative = run forever)
float fade_time = 0.0;        // Fade in/out time (if run_time is set)
float max_brightness = 255.0; // Fade up to, down from this value

// These globals are computed or allocated at runtime after taking input:
uint16_t samples_per_pixel; // Total antialiasing samples per pixel
int map_width;              // Map image width in pixels
int map_height;             // Map image height in pixels
uint8_t *map_data;          // Map image pixel data in RAM
float *longitude;           // Table of longitude values
uint16_t *latitude;         // Table of latitude values

// INTERRUPT HANDLER (to allow clearing matrix on exit) --------------------

volatile bool interrupt_received = false;
static void InterruptHandler(int signo) { interrupt_received = true; }

// IMAGE LOADING -----------------------------------------------------------

// Barebones JPEG reader; no verbose error handling, etc.
int read_jpeg(const char *filename) {
  FILE *file;
  if ((file = fopen(filename, "rb"))) {
    struct jpeg_decompress_struct info;
    struct jpeg_error_mgr err;
    info.err = jpeg_std_error(&err);
    jpeg_create_decompress(&info);
    jpeg_stdio_src(&info, file);
    jpeg_read_header(&info, TRUE);
    jpeg_start_decompress(&info);
    map_width = info.image_width;
    map_height = info.image_height;
    if ((map_data = (uint8_t *)malloc(map_width * map_height * 3))) {
      unsigned char *rowptr[1] = {map_data};
      while (info.output_scanline < info.output_height) {
        (void)jpeg_read_scanlines(&info, rowptr, 1);
        if (info.output_components == 1) { // Convert gray to RGB if needed
          for (int x = map_width - 1; x >= 0; x--) {
            rowptr[0][x * 3] = rowptr[0][x * 3 + 1] = rowptr[0][x * 3 + 2] =
                rowptr[0][x];
          }
        }
        rowptr[0] += map_width * 3;
      }
    }
    jpeg_finish_decompress(&info);
    jpeg_destroy_decompress(&info);
    fclose(file);
    return (map_data != NULL);
  }
  return 0;
}

// COMMAND-LINE HELP -------------------------------------------------------

static int usage(const char *progname) {
  fprintf(stderr, "usage: %s [options]\n", progname);
  fprintf(stderr, "Options:\n");
  rgb_matrix::PrintMatrixFlags(stderr);
  fprintf(stderr, "\t-i <filename> : Image filename for texture map\n");
  fprintf(stderr, "\t-v            : Orient cube with vertex at top\n");
  fprintf(stderr, "\t-s <float>    : Spin time in seconds (per revolution)\n");
  fprintf(stderr, "\t-a <int>      : Antialiasing samples, per-axis\n");
  fprintf(stderr, "\t-t <float>    : Run time in seconds\n");
  fprintf(stderr, "\t-f <float>    : Fade in/out time in seconds\n");
  fprintf(stderr, "\t-e <float>    : Edge-to-edge measure of LED matrix\n");
  fprintf(stderr, "\t-E <float>    : Edge-to-edge measure of assembled cube\n");
  return 1;
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
  while ((opt = getopt(argc, argv, "i:vs:a:t:f:e:E:")) != -1) {
    switch (opt) {
    case 'i':
      map_filename = strdup(optarg);
      break;
    case 'v':
      pointy = true;
      break;
    case 's':
      spin_time = strtof(optarg, NULL);
      break;
    case 'a':
      aa = abs(atoi(optarg));
      if (aa < 1)
        aa = 1;
      else if (aa > 8)
        aa = 8;
      break;
    case 't':
      run_time = fabs(strtof(optarg, NULL));
      break;
    case 'f':
      fade_time = fabs(strtof(optarg, NULL));
      break;
    case 'e':
      matrix_measure = strtof(optarg, NULL);
      break;
    case 'E':
      cube_measure = strtof(optarg, NULL);
      break;
    default: /* '?' */
      return usage(argv[0]);
    }
  }

  // LOAD and ALLOCATE DATA STRUCTURES -------------------------------------

  // Load map image; initializes globals map_width, map_height, map_data:
  if (!read_jpeg(map_filename)) {
    fprintf(stderr, "%s: error loading image '%s'\n", argv[0], map_filename);
    return 1;
  }

  // Allocate huge arrays for longitude & latitude values
  matrix_size = matrix_options.rows;
  samples_per_pixel = aa * aa;
  int num_elements = 6 * matrix_size * matrix_size * samples_per_pixel;
  if (!(longitude = (float *)malloc(num_elements * sizeof(float))) ||
      !(latitude = (uint16_t *)malloc(num_elements * sizeof(uint16_t)))) {
    fprintf(stderr, "%s: can't allocate space for lat/long tables\n", argv[0]);
    return 1;
  }

  // PRECOMPUTE LONGITUDE, LATITUDE TABLES ---------------------------------

  float *coords = (float *)(pointy ? pointy_coords : square_coords);

  // Longitude & latitude tables have one entry for each pixel (or subpixel,
  // if supersampling) on each face of the cube. e.g. 64x64x2x2x6 pairs of
  // values when using 64x64 matrices and 2x2 supersampling. Although some
  // of the interim values through here could be computed and stored (e.g.
  // corner-to-corner distances, matrix_size * aa, etc.), it's the 21st
  // century and optimizing compilers are really dang good at this now, so
  // let it do its job and keep the code relatively short.
  int i = 0; // Index into longitude[] and latitude[] arrays
  float mr = matrix_measure / cube_measure;                // Scale ratio
  float mo = ((1.0 - mr) + mr / (matrix_size * aa)) * 0.5; // Axis offset
  for (uint8_t face = 0; face < 6; face++) {
    float *ul = &coords[verts[face][0] * 3];     // 3D coordinates of matrix's
    float *ur = &coords[verts[face][1] * 3];     // upper-left, upper-right
    float *ll = &coords[verts[face][2] * 3];     // and lower-left corners.
    for (int py = 0; py < matrix_size; py++) {   // For each pixel Y...
      for (int px = 0; px < matrix_size; px++) { // For each pixel X...
        for (uint8_t ay = 0; ay < aa; ay++) {    // " antialiased sample Y...
          float yfactor =
              mo + mr * (float)(py * aa + ay) / (float)(matrix_size * aa);
          for (uint8_t ax = 0; ax < aa; ax++) { // " antialiased sample X...
            float xfactor =
                mo + mr * (float)(px * aa + ax) / (float)(matrix_size * aa);
            float x, y, z;
            // Figure out the pixel's 3D position in space...
            x = ul[0] + (ll[0] - ul[0]) * yfactor + (ur[0] - ul[0]) * xfactor;
            y = ul[1] + (ll[1] - ul[1]) * yfactor + (ur[1] - ul[1]) * xfactor;
            z = ul[2] + (ll[2] - ul[2]) * yfactor + (ur[2] - ul[2]) * xfactor;
            // Then use trigonometry to convert to polar coords on a sphere...
            longitude[i] =
                fmod((M_PI + atan2(-z, x)) / (M_PI * 2.0) * (float)map_width,
                     (float)map_width);
            latitude[i] = (int)((M_PI * 0.5 - atan2(y, sqrt(x * x + z * z))) /
                                M_PI * (float)map_height);
            i++;
          }
        }
      }
    }
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
    float loffset =
        fmod(elapsed, fabs(spin_time)) / fabs(spin_time) * (float)map_width;
    if (spin_time > 0)
      loffset = map_width - loffset;
    i = 0; // Index into longitude[] and latitude[] arrays
    for (uint8_t face = 0; face < 6; face++) {
      int xoffset = (face % matrix_options.chain_length) * matrix_size;
      int yoffset = (face / matrix_options.chain_length) * matrix_size;
      for (int py = 0; py < matrix_size; py++) {
        for (int px = 0; px < matrix_size; px++) {
          uint16_t r = 0, g = 0, b = 0;
          for (uint16_t s = 0; s < samples_per_pixel; s++) {
            int sx = (int)(longitude[i] + loffset) % map_width;
            int sy = latitude[i];
            uint8_t *src = &map_data[(sy * map_width + sx) * 3];
            r += src[0];
            g += src[1];
            b += src[2];
            i++;
          }
          canvas->SetPixel(xoffset + px, yoffset + py, r / samples_per_pixel,
                           g / samples_per_pixel, b / samples_per_pixel);
        }
      }
    }
    canvas = matrix->SwapOnVSync(canvas);
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
