/*
*/

#include <Adafruit_IS31FL3741.h> // For LED driver
#include <PDM.h>                 // For microphone
#include <Adafruit_ZeroFFT.h>    // For math

Adafruit_EyeLights_buffered glasses; // Buffered for smooth animation
extern PDMClass             PDM;

#define NUM_SAMPLES 512 // FFT size, MUST be a power of two
short sampleBuffer[NUM_SAMPLES];  // buffer to read samples into, each sample is 16-bits
volatile int samplesRead; // number of samples read (set in interrupt)

#define SPECTRUM_SIZE (NUM_SAMPLES / 2) // Output spectrum is 1/2 of FFT result

// Bottom of spectrum tends to be noisy, while top often exceeds musical
// range and is just harmonics, so clip both ends off:
//#define LOW_BIN  10  // Lowest bin of spectrum that contributes to graph
//#define HIGH_BIN 75 // Highest bin "

#define LOW_BIN  3   // Lowest bin of spectrum that contributes to graph
#define HIGH_BIN 180 // Highest bin "

// Crude error handler, prints message to Serial console, flashes LED
void err(char *str, uint8_t hz) {
  Serial.println(str);
  pinMode(LED_BUILTIN, OUTPUT);
  for (;;) digitalWrite(LED_BUILTIN, (millis() * hz / 500) & 1);
}

float data[SPECTRUM_SIZE];

struct {
  int      first_bin;
  int      num_bins;
  float   *bin_weights;
  uint32_t color;
  float    dot;
  float    velocity;  
} column_table[18];

int frames;
uint32_t start_time;

void setup() { // Runs once at program start...

  // Initialize hardware
  Serial.begin(115200);
//while(!Serial);
  if (! glasses.begin()) err("IS3741 not found", 2);

  uint8_t spectrum_bits = (int)log2f((float)SPECTRUM_SIZE);
  float low_frac = log2f((float)LOW_BIN) / (float)spectrum_bits;
  float frac_range = log2((float)HIGH_BIN) / (float)spectrum_bits - low_frac;
Serial.printf("%d %f %f\n", spectrum_bits, low_frac, frac_range);

  for (int column=0; column<18; column++) {
    float lower = low_frac + frac_range * ((float)column / 18.0 * 0.95);
    float upper = low_frac + frac_range * ((float)(column + 1) / 18.0);
    float mid = (lower + upper) * 0.5;  // Center of lower-to-upper range
    float half_width = (upper - lower) * 0.5 + 1e-2; // 1/2 of lower-to-upper range
    // Map fractions back to spectrum bin indices that contribute to column
    int first_bin = int(pow(2, (float)spectrum_bits * lower) + 1e-4);
    int last_bin = int(pow(2, (float)spectrum_bits * upper) + 1e-4);
    Serial.printf("%d %d %d\n", column, first_bin, last_bin);
    float total_weight = 0.0;
    int num_bins = last_bin - first_bin + 1;
    column_table[column].bin_weights = (float *)malloc(num_bins * sizeof(float));
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
    Serial.println();
    Serial.println(column);
    for (int i=0; i<num_bins; i++) {
      column_table[column].bin_weights[i] = column_table[column].bin_weights[i] / total_weight * (0.6 + (float)i / 18.0 * 1.8);
      Serial.printf("  %f\n", column_table[column].bin_weights[i]);
    }
    column_table[column].first_bin = first_bin;
    column_table[column].num_bins = num_bins;
    column_table[column].color = glasses.color565(glasses.ColorHSV(57600UL * column / 18, 255, 255));
    column_table[column].dot = 5.0;
    column_table[column].velocity = 0.0;
  }

  for (int i=0; i<SPECTRUM_SIZE; i++) {
    data[i] = 0.0;
  }

  // Configure glasses for max brightness, enable output
  glasses.setLEDscaling(0xFF);
  glasses.setGlobalCurrent(0xFF);
  glasses.enable(true);

  // Configure PDM mic, mono 16 KHz
  PDM.onReceive(onPDMdata);
  PDM.begin(1, 16000);

  start_time = millis();
}

float dynamic_level = 6.0;

volatile bool mic_on = false;

void loop() { // Repeat forever...
  int samplesRemaining = NUM_SAMPLES;
  samplesRead = 0;
  mic_on = true;
  while (samplesRemaining) {
    if(samplesRead) { // Set in onPDMdata()
      samplesRemaining -= samplesRead;
    }
    yield();
  }
  mic_on = false;

// To do: could record into alternating buffers

  ZeroFFT(sampleBuffer, NUM_SAMPLES);



  // Convert FFT output to spectrum
  for(int i=0; i<SPECTRUM_SIZE; i++) {
//    data[i] = (data[i] * 0.25) + ((float)sampleBuffer[i] * 0.75);
    data[i] = (data[i] * 0.2) + ((sampleBuffer[i] ? log((float)sampleBuffer[i]) : 0.0) * 0.8);
//    data[i] = (float)sampleBuffer[i];
#if 0
    uint32_t mag2 = fr[i] * fr[i] + fi[i] * fi[i];
    if (mag2) {
      data[i] = log(sqrt((float)mag2));
//      data[i] = sqrt((float)mag2);
    } else {
      data[i] = 0.0;
    }
#endif
  }

  float lower = data[0], upper = data[0];
  for (int i=1; i<SPECTRUM_SIZE; i++) {
    if (data[i] < lower) lower = data[i];
    if (data[i] > upper) upper = data[i];
  }
//  Serial.printf("%f %f\n", lower, upper);
//  if (lower < 4) lower = 4;
//  if (upper < 10) upper = 10;
  if (upper < 4.5) upper = 4.5; // because log



  if (upper > dynamic_level) {
    // Got louder. Move level up quickly but allow initial "bump."
    dynamic_level = upper * 0.5 + dynamic_level * 0.5;
  } else {
    // Got quieter. Ease level down, else too many bumps.
    dynamic_level = dynamic_level * 0.7 + lower * 0.3;
  }
//  dynamic_level = 20.0;
//dynamic_level = upper;

  // Apply vertical scale to spectrum data. Results may exceed
  // matrix height...that's OK, adds impact!
  float scale = 10.0 / (dynamic_level - lower);
  for (int i=0; i<SPECTRUM_SIZE; i++) {
    data[i] = (data[i] - lower) * scale;
  }

  glasses.fill(0);
  for(int column=0; column<18; column++) {
    int first_bin = column_table[column].first_bin;
    float column_top = 7.0;
    for (int bin_offset=0; bin_offset<column_table[column].num_bins; bin_offset++) {
      column_top -= data[first_bin + bin_offset] * column_table[column].bin_weights[bin_offset];
    }
    if(column_top < column_table[column].dot) {
      column_table[column].dot = column_top - 0.5;
      column_table[column].velocity = 0.0;
    } else {
      column_table[column].dot += column_table[column].velocity;
      column_table[column].velocity += 0.01;
    }

    int itop = (int)column_top;
    glasses.drawLine(column, itop, column, itop + 50, column_table[column].color);
    glasses.drawPixel(column, (int)column_table[column].dot, 0xE410);
  }

  glasses.show();

  frames += 1;
  uint32_t elapsed = millis() - start_time;
//  Serial.println(frames * 1000 / elapsed);
}


void onPDMdata() {
  if (mic_on) {
    // query the number of bytes available
    int bytesAvailable = PDM.available();
  
    // read into the sample buffer
    PDM.read(sampleBuffer, bytesAvailable);
  
    // 16-bit, 2 bytes per sample
    samplesRead = bytesAvailable / 2;
  }
}
