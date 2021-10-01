// SPDX-FileCopyrightText: 2021 Phil Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*
AUDIO SPECTRUM LIGHT SHOW for Adafruit EyeLights (LED Glasses + Driver).
Uses onboard microphone and a lot of math to react to music.
REQUIRES Adafruit_ZeroFFT LIBRARY, install via Arduino Library manager.
*/

#include <Adafruit_IS31FL3741.h> // For LED driver
#include <PDM.h>                 // For microphone
#include <Adafruit_ZeroFFT.h>    // For math

// FFT/SPECTRUM CONFIG ----

#define NUM_SAMPLES   512               // Audio & FFT buffer, MUST be a power of two
#define SPECTRUM_SIZE (NUM_SAMPLES / 2) // Output spectrum is 1/2 of FFT output
// Bottom of spectrum tends to be noisy, while top often exceeds musical
// range and is just harmonics, so clip both ends off:
#define LOW_BIN  5   // Lowest bin of spectrum that contributes to graph
#define HIGH_BIN 150 // Highest bin "

// GLOBAL VARIABLES -------

Adafruit_EyeLights_buffered glasses; // LED matrix is buffered for smooth animation
extern PDMClass PDM;                 // Microphone
short audio_buf[3][NUM_SAMPLES];     // Audio input buffers, 16-bit signed
uint8_t active_buf = 0;              // Buffer # into which audio is currently recording
volatile int samples_read = 0;       // # of samples read into current buffer thus far
volatile bool mic_on = false;        // true when reading from mic, false when full/stopped
float spectrum[SPECTRUM_SIZE];       // FFT results are stored & further processed here
float dynamic_level = 10.0;          // For adapting to changing audio volume
int frames;                          // For frames-per-second calculation
uint32_t start_time;                 // Ditto

struct { // Values associated with each column of the matrix
  int      first_bin;   // First spectrum bin index affecting column
  int      num_bins;    // Number of spectrum bins affecting column
  float   *bin_weights; // List of spectrum bin weightings
  uint32_t color;       // GFX-style 'RGB565' color for column
  float    top;         // Current column top position
  float    dot;         // Current column 'falling dot' position
  float    velocity;    // Current velocity of falling dot
} column_table[18];

// Crude error handler, prints message to Serial console, flashes LED
void err(char *str, uint8_t hz) {
  Serial.println(str);
  pinMode(LED_BUILTIN, OUTPUT);
  for (;;) digitalWrite(LED_BUILTIN, (millis() * hz / 500) & 1);
}

void setup() { // Runs once at program start...

  Serial.begin(115200);
  //while(!Serial);
  if (! glasses.begin()) err("IS3741 not found", 2);

  // FFT/SPECTRUM SETUP -----

  uint8_t spectrum_bits = (int)log2f((float)SPECTRUM_SIZE); // e.g. 8 = 256 bin spectrum
  // Scale LOW_BIN and HIGH_BIN to 0.0 to 1.0 equivalent range in spectrum
  float low_frac = log2f((float)LOW_BIN) / (float)spectrum_bits;
  float frac_range = log2((float)HIGH_BIN) / (float)spectrum_bits - low_frac;
  // Serial.printf("%d %f %f\n", spectrum_bits, low_frac, frac_range);

  // To keep the display lively, tables are precomputed where each column of
  // the matrix (of which there are few) is the sum value and weighting of
  // several bins from the FFT spectrum output (of which there are many).
  // The tables also help visually linearize the output so octaves are evenly
  // spaced, as on a piano keyboard, whereas the source spectrum data is
  // spaced by frequency in Hz.

  for (int column=0; column<18; column++) {
    // Determine the lower and upper frequency range for this column, as
    // fractions within the scaled 0.0 to 1.0 spectrum range. 0.95 below
    // creates slight frequency overlap between columns, looks nicer.
    float lower = low_frac + frac_range * ((float)column / 18.0 * 0.95);
    float upper = low_frac + frac_range * ((float)(column + 1) / 18.0);
    float mid = (lower + upper) * 0.5;               // Center of lower-to-upper range
    float half_width = (upper - lower) * 0.5 + 1e-2; // 1/2 of lower-to-upper range
    // Map fractions back to spectrum bin indices that contribute to column
    int first_bin = int(pow(2, (float)spectrum_bits * lower) + 1e-4);
    int last_bin = int(pow(2, (float)spectrum_bits * upper) + 1e-4);
    //Serial.printf("%d %d %d\n", column, first_bin, last_bin);
    float total_weight = 0.0; // Accumulate weight for this bin
    int num_bins = last_bin - first_bin + 1;
    // Allocate space for bin weights for column, stop everything if out of RAM.
    column_table[column].bin_weights = (float *)malloc(num_bins * sizeof(float));
    if (column_table[column].bin_weights == NULL) err("Malloc fail", 10);
    for (int bin_index = first_bin; bin_index <= last_bin; bin_index++) {
      // Find distance from column's overall center to individual bin's
      // center, expressed as 0.0 (bin at center) to 1.0 (bin at limit of
      // lower-to-upper range).
      float bin_center = log2f((float)bin_index + 0.5) / (float)spectrum_bits;
      float dist = fabs(bin_center - mid) / half_width;
      if (dist < 1.0) {  // Filter out a few math stragglers at either end
        // Bin weights have a cubic falloff curve within range:
        dist = 1.0 - dist; // Invert dist so 1.0 is at center
        float bin_weight = (((3.0 - (dist * 2.0)) * dist) * dist);
        column_table[column].bin_weights[bin_index - first_bin] = bin_weight;
        total_weight += bin_weight;
      }
    }
    //Serial.println(column);
    // Scale bin weights so total is 1.0 for each column, but then mute
    // lower columns slightly and boost higher columns. It graphs better.
    for (int i=0; i<num_bins; i++) {
      column_table[column].bin_weights[i] = column_table[column].bin_weights[i] /
        total_weight * (0.6 + (float)i / 18.0 * 2.0);
      //Serial.printf("  %f\n", column_table[column].bin_weights[i]);
    }
    column_table[column].first_bin = first_bin;
    column_table[column].num_bins = num_bins;
    column_table[column].color = glasses.color565(glasses.ColorHSV(
      57600UL * column / 18, 255, 255)); // Red (0) to purple (57600)
    column_table[column].top = 6.0;      // Start off bottom of graph
    column_table[column].dot = 6.0;
    column_table[column].velocity = 0.0;
  }

  for (int i=0; i<SPECTRUM_SIZE; i++) spectrum[i] = 0.0;

  // HARDWARE SETUP ---------

  // Configure glasses for max brightness, enable output
  glasses.setLEDscaling(0xFF);
  glasses.setGlobalCurrent(0xFF);
  glasses.enable(true);

  // Configure PDM mic, mono 16 KHz
  PDM.onReceive(onPDMdata);
  PDM.begin(1, 16000);

  start_time = millis();
}

void loop() { // Repeat forever...

  short *audio_data; // Pointer to newly-received audio

  while (mic_on) yield(); // Wait for next buffer to finish recording
  // Full buffer received -- active_buf is index to new data
  audio_data = &audio_buf[active_buf][0]; // New data is here
  active_buf = 1 - active_buf; // Swap buffers to record into other one,
  mic_on = true;               // and start recording next batch

  // Perform FFT operation on newly-received data,
  // results go back into the same buffer.
  ZeroFFT(audio_data, NUM_SAMPLES);

  // Convert FFT output to spectrum. log(y) looks better than raw data.
  // Only LOW_BIN to HIGH_BIN elements are needed.
  for(int i=LOW_BIN; i<=HIGH_BIN; i++) {
    spectrum[i] = (audio_data[i] > 0) ? log((float)audio_data[i]) : 0.0;
  }

  // Find min & max range of spectrum bin values, with limits.
  float lower = spectrum[LOW_BIN], upper = spectrum[LOW_BIN];
  for (int i=LOW_BIN+1; i<=HIGH_BIN; i++) {
    if (spectrum[i] < lower) lower = spectrum[i];
    if (spectrum[i] > upper) upper = spectrum[i];
  }
  //Serial.printf("%f %f\n", lower, upper);
  if (upper < 2.5) upper = 2.5;

  // Adjust dynamic level to current spectrum output, keeps the graph
  // 'lively' as ambient volume changes. Sparkle but don't saturate.
  if (upper > dynamic_level) {
    // Got louder. Move level up quickly but allow initial "bump."
    dynamic_level = dynamic_level * 0.5 + upper * 0.5;
  } else {
    // Got quieter. Ease level down, else too many bumps.
    dynamic_level = dynamic_level * 0.75 + lower * 0.25;
  }

  // Apply vertical scale to spectrum data. Results may exceed
  // matrix height...that's OK, adds impact!
  float scale = 15.0 / (dynamic_level - lower);
  for (int i=LOW_BIN; i<=HIGH_BIN; i++) {
    spectrum[i] = (spectrum[i] - lower) * scale;
  }

  // Clear screen, filter and draw each column of the display...
  glasses.fill(0);
  for(int column=0; column<18; column++) {
    int first_bin = column_table[column].first_bin;
    // Start BELOW matrix and accumulate bin weights UP, saves math
    float column_top = 7.0;
    for (int bin_offset=0; bin_offset<column_table[column].num_bins; bin_offset++) {
      column_top -= spectrum[first_bin + bin_offset] * column_table[column].bin_weights[bin_offset];
    }
    // Column top positions are filtered to appear less 'twitchy' --
    // last data still has a 30% influence on current positions.
    column_top = (column_top * 0.7) +  (column_table[column].top * 0.3);
    column_table[column].top = column_top;

    if(column_top < column_table[column].dot) {    // Above current falling dot?
      column_table[column].dot = column_top - 0.5; // Move dot up
      column_table[column].velocity = 0.0;         // and clear out velocity
    } else {
      column_table[column].dot += column_table[column].velocity; // Move dot down
      column_table[column].velocity += 0.015;                    // and accelerate
    }

    // Draw column and peak dot
    int itop = (int)column_top; // Quantize column top to pixel space
    glasses.drawLine(column, itop, column, itop + 20, column_table[column].color);
    glasses.drawPixel(column, (int)column_table[column].dot, 0xE410);
  }

  glasses.show(); // Buffered mode MUST use show() to refresh matrix

  frames += 1;
  uint32_t elapsed = millis() - start_time;
  //Serial.println(frames * 1000 / elapsed);
}

// PDM mic interrupt handler, called when new data is ready
void onPDMdata() {
  //digitalWrite(LED_BUILTIN, millis() & 1024); // Debug heartbeat
  if (int bytes_to_read = PDM.available()) {
    if (mic_on) {
      int byte_limit = (NUM_SAMPLES - samples_read) * 2; // Space remaining,
      bytes_to_read = min(bytes_to_read, byte_limit);    // don't overflow!
      PDM.read(&audio_buf[active_buf][samples_read], bytes_to_read);
      samples_read += bytes_to_read / 2; // Increment counter
      if (samples_read >= NUM_SAMPLES) { // Buffer full?
        mic_on = false;                  // Stop and
        samples_read = 0;                // reset counter for next time
      }
    } else {
      // Mic is off (code is busy) - must read but discard data.
      // audio_buf[2] is a 'bit bucket' for this.
      PDM.read(audio_buf[2], bytes_to_read);
    }
  }
}
