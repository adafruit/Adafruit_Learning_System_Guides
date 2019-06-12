/*
This is a mash-up of the adavoice and wavface sketches.
Using an Arduino, Wave Shield and some supporting components,
creates a voice-changing mask with animated features.

The BOM for the complete project is rather lengthy to put here, so
please see this tutorial for info (and parts) for the voice changer:
http://learn.adafruit.com/wave-shield-voice-changer
And see this tutorial for info/parts for the face animation:
http://learn.adafruit.com/animating-multiple-led-backpacks

This version doesn't do WAV playback, as there's no keypad or
buttons.  Just the voice.  Some WAV-related hooks have been left
in place if you want to adapt it.  This will be difficult though,
as RAM is VERY tight...we're using nearly the whole thing.
*/

#include <WaveHC.h>
#include <WaveUtil.h>
#include <Wire.h>
#include "Adafruit_LEDBackpack.h"
#include "Adafruit_GFX.h"

// The SD card stuff is declared but not actually used in this sketch --
// I wanted to keep the ability for WAVs here, even if they're not being
// exercised right now.  RAM is VERY tight with all this in here...so if
// you adapt the sketch and run out of ram, and if you don't need WAV
// playback, I'd start by tearing this stuff out...
SdReader  card;  // This object holds the information for the card
FatVolume vol;   // This holds the information for the partition on the card
FatReader root;  // This holds the information for the volumes root directory
FatReader file;  // This object represent the WAV file for a pi digit or period
WaveHC    wave;  // This is the only wave (audio) object, -- we only play one at a time
#define error(msg) error_P(PSTR(msg))  // Macro allows error messages in flash memory

#define ADC_CHANNEL 0 // Microphone on Analog pin 0

// Wave shield DAC: digital pins 2, 3, 4, 5
#define DAC_CS_PORT    PORTD
#define DAC_CS         PORTD2
#define DAC_CLK_PORT   PORTD
#define DAC_CLK        PORTD3
#define DAC_DI_PORT    PORTD
#define DAC_DI         PORTD4
#define DAC_LATCH_PORT PORTD
#define DAC_LATCH      PORTD5

uint16_t in = 0, out = 0, xf = 0, nSamples; // Audio sample counters
uint8_t  adc_save;                          // Default ADC mode

// WaveHC didn't declare it's working buffers private or static,
// so we can be sneaky and borrow the same RAM for audio sampling!
extern uint8_t
  buffer1[PLAYBUFFLEN],                   // Audio sample LSB
  buffer2[PLAYBUFFLEN];                   // Audio sample MSB
#define XFADE     16                      // Number of samples for cross-fade
#define MAX_SAMPLES (PLAYBUFFLEN - XFADE) // Remaining available audio samples

// Used for averaging all the audio samples currently in the buffer
uint8_t       oldsum = 0;
unsigned long newsum = 0L;

#define MATRIX_EYES         0
#define MATRIX_MOUTH_LEFT   1
#define MATRIX_MOUTH_MIDDLE 2
#define MATRIX_MOUTH_RIGHT  3

Adafruit_8x8matrix matrix[4] = { // Array of Adafruit_8x8matrix objects
  Adafruit_8x8matrix(), Adafruit_8x8matrix(),
  Adafruit_8x8matrix(), Adafruit_8x8matrix() };

static const uint8_t PROGMEM // Bitmaps are stored in program memory
  blinkImg[][8] = {    // Eye animation frames
  { B11111100,         // Fully open eye
    B11111110,         // The eye matrices are installed
    B11111111,         // in the mask at a 45 degree angle...
    B11111111,         // you can edit these bitmaps if you opt
    B11111111,         // for a rectilinear arrangement.
    B11111111,
    B01111111,
    B00111111 },
  { B11110000,
    B11111100,
    B11111110,
    B11111110,
    B11111111,
    B11111111,
    B01111111,
    B00111111 },
  { B11100000,
    B11111000,
    B11111100,
    B11111110,
    B11111110,
    B01111111,
    B00111111,
    B00011111 },
  { B11000000,
    B11110000,
    B11111000,
    B11111100,
    B11111110,
    B01111110,
    B00111111,
    B00011111 },
  { B10000000,
    B11100000,
    B11111000,
    B11111100,
    B01111100,
    B01111110,
    B00111110,
    B00001111 },
  { B10000000,
    B11000000,
    B11100000,
    B11110000,
    B01111000,
    B01111100,
    B00111110,
    B00001111 },
  { B10000000,
    B10000000,
    B11000000,
    B01000000,
    B01100000,
    B00110000,
    B00011100,
    B00000111 },
  { B10000000,         // Fully closed eye
    B10000000,
    B10000000,
    B01000000,
    B01000000,
    B00100000,
    B00011000,
    B00000111 } },
  pupilImg[] = {      // Pupil bitmap
    B00000000,        // (only top-left 7x7 is used)
    B00011000,
    B00111000,
    B01110000,
    B01100000,
    B00000000,
    B00000000,
    B00000000 },
  landingImg[] = {    // This is a bitmask of where
    B01111000,        // the pupil can safely "land" when
    B11111100,        // a new random position is selected,
    B11111110,        // so it doesn't run too far off the
    B11111110,        // edge and look bad.  If you edit the
    B11111110,        // eye or pupil bitmaps, you may want
    B01111110,        // to adjust this...use '1' for valid
    B00111100,        // pupil positions, '0' for off-limits
    B00000000 },      // points.
  mouthImg[][24] = {                 // Mouth animation frames
  { B00000000, B11000011, B00000000, // Mouth position 0
    B00000001, B01000010, B10000000, // Unlike the original 'roboface'
    B00111110, B01111110, B01111100, // sketch (using AF animation),
    B11000000, B00000000, B00000011, // the mouth positions here are
    B00000000, B00000000, B00000000, // proportional to the current
    B00000000, B00000000, B00000000, // sound amplitude.  Position 0
    B00000000, B00000000, B00000000, // is closed, #7 is max open.
    B00000000, B00000000, B00000000 },
  { B00000000, B00000000, B00000000, // Mouth position 1
    B00000000, B11000011, B00000000,
    B00000011, B01111110, B11000000,
    B00111110, B00000000, B01111100,
    B11000000, B00000000, B00000011,
    B00000000, B00000000, B00000000,
    B00000000, B00000000, B00000000,
    B00000000, B00000000, B00000000 },
  { B00000000, B00000000, B00000000, // Mouth position 2
    B00000011, B11111111, B11000000,
    B00011011, B01111110, B11011000,
    B01111110, B01111110, B01111110,
    B00000000, B00000000, B00000000,
    B00000000, B00000000, B00000000,
    B00000000, B00000000, B00000000,
    B00000000, B00000000, B00000000 },
  { B00000000, B00000000, B00000000, // Mouth position 3
    B00000011, B11111111, B11000000,
    B01111011, B11111111, B11011110,
    B00011111, B01111110, B11111000,
    B00001110, B01111110, B01110000,
    B00000000, B00000000, B00000000,
    B00000000, B00000000, B00000000,
    B00000000, B00000000, B00000000 },
  { B00000000, B00000000, B00000000, // Mouth position 4
    B00000001, B11111111, B10000000,
    B01111001, B11111111, B10011110,
    B00111101, B11111111, B10111100,
    B00011111, B01111110, B11111000,
    B00000110, B01111110, B01100000,
    B00000000, B00000000, B00000000,
    B00000000, B00000000, B00000000 },
  { B00000000, B00000000, B00000000, // Mouth position 5
    B00000001, B11111111, B10000000,
    B00111001, B11111111, B10011100,
    B00011101, B11111111, B10111000,
    B00011111, B11111111, B11111000,
    B00001111, B01111110, B11110000,
    B00000110, B01111110, B01100000,
    B00000000, B00000000, B00000000 },
  { B00000000, B00000000, B00000000, // Mouth position 6
    B00000001, B11111111, B10000000,
    B00111001, B11111111, B10011100,
    B00111101, B11111111, B10111100,
    B00011111, B11111111, B11111100,
    B00011111, B11111111, B11111000,
    B00001111, B01111110, B11110000,
    B00000110, B01111110, B01100000 },
  { B00000000, B01111110, B00000000, // Mouth position 7
    B00001001, B11111111, B10010000,
    B00011001, B11111111, B10011000,
    B00011101, B11111111, B10111000,
    B00011111, B11111111, B11111000,
    B00011111, B11111111, B11111000,
    B00001111, B01111110, B11110000,
    B00000110, B01111110, B01100000 } },
  blinkIndex[] = { 1, 2, 3, 4, 5, 6, 7, 6, 5, 3, 2, 1 }, // Blink bitmap sequence
  matrixAddr[] = { 0x70, 0x71, 0x72, 0x73 }; // I2C addresses of 4 matrices

uint8_t
  blinkCountdown = 100, // Countdown to next blink (in frames)
  gazeCountdown  =  75, // Countdown to next eye movement
  gazeFrames     =  50, // Duration of eye movement (smaller = faster)
  mouthPos       =   0, // Current image number for mouth
  mouthCountdown =  10; // Countdown to next mouth change
int8_t
  eyeX = 3, eyeY = 3,   // Current eye position
  newX = 3, newY = 3,   // Next eye position
  dX   = 0, dY   = 0;   // Distance from prior to new position


//////////////////////////////////// SETUP

void setup() {
  uint8_t i;

  Serial.begin(9600);

  // Seed random number generator from an unused analog input:
  randomSeed(analogRead(A2));

  // Initialize each matrix object:
  for(i=0; i<4; i++) {
    matrix[i].begin(pgm_read_byte(&matrixAddr[i]));
  }

  // The WaveHC library normally initializes the DAC pins...but only after
  // an SD card is detected and a valid file is passed.  Need to init the
  // pins manually here so that voice FX works even without a card.
  pinMode(2, OUTPUT);    // Chip select
  pinMode(3, OUTPUT);    // Serial clock
  pinMode(4, OUTPUT);    // Serial data
  pinMode(5, OUTPUT);    // Latch
  digitalWrite(2, HIGH); // Set chip select high

  // Init SD library, show root directory.  Note that errors are displayed
  // but NOT regarded as fatal -- the program will continue with voice FX!
  if(!card.init())             SerialPrint_P("Card init. failed!");
  else if(!vol.init(card))     SerialPrint_P("No partition!");
  else if(!root.openRoot(vol)) SerialPrint_P("Couldn't open dir");
  else {
    PgmPrintln("Files found:");
    root.ls();
  }

  // Optional, but may make sampling and playback a little smoother:
  // Disable Timer0 interrupt.  This means delay(), millis() etc. won't
  // work.  Comment this out if you really, really need those functions.
  TIMSK0 = 0;

  // Set up Analog-to-Digital converter:
  analogReference(EXTERNAL); // 3.3V to AREF
  adc_save = ADCSRA;         // Save ADC setting for restore later

  startPitchShift();     // and start the pitch-shift mode by default.
}


//////////////////////////////////// LOOP

void loop() {
  // Draw eyeball in current state of blinkyness (no pupil).  Note that
  // only one eye needs to be drawn.  Because the two eye matrices share
  // the same address, the same data will be received by both.
  matrix[MATRIX_EYES].clear();
  // When counting down to the next blink, show the eye in the fully-
  // open state.  On the last few counts (during the blink), look up
  // the corresponding bitmap index.
  matrix[MATRIX_EYES].drawBitmap(0, 0,
    blinkImg[
      (blinkCountdown < sizeof(blinkIndex)) ? // Currently blinking?
      pgm_read_byte(&blinkIndex[blinkCountdown]) :            // Yes, look up bitmap #
      0                                       // No, show bitmap 0
    ], 8, 8, LED_ON);
  // Decrement blink counter.  At end, set random time for next blink.
  if(--blinkCountdown == 0) blinkCountdown = random(5, 180);

  // Add a pupil atop the blinky eyeball bitmap.
  // Periodically, the pupil moves to a new position...
  if(--gazeCountdown <= gazeFrames) {
    // Eyes are in motion - draw pupil at interim position
    matrix[MATRIX_EYES].drawBitmap(
      newX - (dX * gazeCountdown / gazeFrames) - 2,
      newY - (dY * gazeCountdown / gazeFrames) - 2,
      pupilImg, 7, 7, LED_OFF);
    if(gazeCountdown == 0) {    // Last frame?
      eyeX = newX; eyeY = newY; // Yes.  What's new is old, then...
      do { // Pick random positions until one is within the eye circle
        newX = random(7); newY = random(7);
      } while(!((pgm_read_byte(&landingImg[newY]) << newX) & 0x80));
      dX            = newX - eyeX;             // Horizontal distance to move
      dY            = newY - eyeY;             // Vertical distance to move
      gazeFrames    = random(3, 15);           // Duration of eye movement
      gazeCountdown = random(gazeFrames, 120); // Count to end of next movement
    }
  } else {
    // Not in motion yet -- draw pupil at current static position
    matrix[MATRIX_EYES].drawBitmap(eyeX - 2, eyeY - 2, pupilImg, 7, 7, LED_OFF);
  }

  drawMouth(mouthImg[oldsum / 32]);

  // Refresh all of the matrices in one quick pass
  for(uint8_t i=0; i<4; i++) matrix[i].writeDisplay();

  delay(20); // ~50 FPS
}

// Draw mouth image across three adjacent displays
void drawMouth(const uint8_t *img) {
  for(uint8_t i=0; i<3; i++) {
    matrix[MATRIX_MOUTH_LEFT + i].clear();
    matrix[MATRIX_MOUTH_LEFT + i].drawBitmap(i * -8, 0, img, 24, 8, LED_ON);
  }
}


//////////////////////////////////// PITCH-SHIFT CODE

void startPitchShift() {

  // Read analog pitch setting before starting audio sampling:
  int pitch = analogRead(1);
  Serial.print("Pitch: ");
  Serial.println(pitch);

  // Right now the sketch just uses a fixed sound buffer length of
  // 128 samples.  It may be the case that the buffer length should
  // vary with pitch for better results...further experimentation
  // is required here.
  nSamples = 128;
  //nSamples = F_CPU / 3200 / OCR2A; // ???
  //if(nSamples > MAX_SAMPLES)      nSamples = MAX_SAMPLES;
  //else if(nSamples < (XFADE * 2)) nSamples = XFADE * 2;

  memset(buffer1, 0, nSamples + XFADE); // Clear sample buffers
  memset(buffer2, 2, nSamples + XFADE); // (set all samples to 512)

  // WaveHC library already defines a Timer1 interrupt handler.  Since we
  // want to use the stock library and not require a special fork, Timer2
  // is used for a sample-playing interrupt here.  As it's only an 8-bit
  // timer, a sizeable prescaler is used (32:1) to generate intervals
  // spanning the desired range (~4.8 KHz to ~19 KHz, or +/- 1 octave
  // from the sampling frequency).  This does limit the available number
  // of speed 'steps' in between (about 79 total), but seems enough.
  TCCR2A = _BV(WGM21) | _BV(WGM20); // Mode 7 (fast PWM), OC2 disconnected
  TCCR2B = _BV(WGM22) | _BV(CS21) | _BV(CS20);  // 32:1 prescale
  OCR2A  = map(pitch, 0, 1023,
    F_CPU / 32 / (9615 / 2),  // Lowest pitch  = -1 octave
    F_CPU / 32 / (9615 * 2)); // Highest pitch = +1 octave

  // Start up ADC in free-run mode for audio sampling:
  DIDR0 |= _BV(ADC0D);  // Disable digital input buffer on ADC0
  ADMUX  = ADC_CHANNEL; // Channel sel, right-adj, AREF to 3.3V regulator
  ADCSRB = 0;           // Free-run mode
  ADCSRA = _BV(ADEN) |  // Enable ADC
    _BV(ADSC)  |        // Start conversions
    _BV(ADATE) |        // Auto-trigger enable
    _BV(ADIE)  |        // Interrupt enable
    _BV(ADPS2) |        // 128:1 prescale...
    _BV(ADPS1) |        //  ...yields 125 KHz ADC clock...
    _BV(ADPS0);         //  ...13 cycles/conversion = ~9615 Hz

  TIMSK2 |= _BV(TOIE2); // Enable Timer2 overflow interrupt
  sei();                // Enable interrupts
}

void stopPitchShift() {
  ADCSRA = adc_save; // Disable ADC interrupt and allow normal use
  TIMSK2 = 0;        // Disable Timer2 Interrupt
}

ISR(ADC_vect, ISR_BLOCK) { // ADC conversion complete

  // Save old sample from 'in' position to xfade buffer:
  buffer1[nSamples + xf] = buffer1[in];
  buffer2[nSamples + xf] = buffer2[in];
  if(++xf >= XFADE) xf = 0;

  // Store new value in sample buffers:
  buffer1[in] = ADCL; // MUST read ADCL first!
  buffer2[in] = ADCH;

  newsum += abs((((int)buffer2[in] << 8) | buffer1[in]) - 512);

  if(++in >= nSamples) {
    in     = 0;
    oldsum = (uint8_t)((newsum / nSamples) >> 1); // 0-255
    newsum = 0L;
  }
}

ISR(TIMER2_OVF_vect) { // Playback interrupt
  uint16_t s;
  uint8_t  w, inv, hi, lo, bit;
  int      o2, i2, pos;

  // Cross fade around circular buffer 'seam'.
  if((o2 = (int)out) == (i2 = (int)in)) {
    // Sample positions coincide.  Use cross-fade buffer data directly.
    pos = nSamples + xf;
    hi = (buffer2[pos] << 2) | (buffer1[pos] >> 6); // Expand 10-bit data
    lo = (buffer1[pos] << 2) |  buffer2[pos];       // to 12 bits
  } if((o2 < i2) && (o2 > (i2 - XFADE))) {
    // Output sample is close to end of input samples.  Cross-fade to
    // avoid click.  The shift operations here assume that XFADE is 16;
    // will need adjustment if that changes.
    w   = in - out;  // Weight of sample (1-n)
    inv = XFADE - w; // Weight of xfade
    pos = nSamples + ((inv + xf) % XFADE);
    s   = ((buffer2[out] << 8) | buffer1[out]) * w +
          ((buffer2[pos] << 8) | buffer1[pos]) * inv;
    hi = s >> 10; // Shift 14 bit result
    lo = s >> 2;  // down to 12 bits
  } else if (o2 > (i2 + nSamples - XFADE)) {
    // More cross-fade condition
    w   = in + nSamples - out;
    inv = XFADE - w;
    pos = nSamples + ((inv + xf) % XFADE);
    s   = ((buffer2[out] << 8) | buffer1[out]) * w +
          ((buffer2[pos] << 8) | buffer1[pos]) * inv;
    hi = s >> 10; // Shift 14 bit result
    lo = s >> 2;  // down to 12 bits
  } else {
    // Input and output counters don't coincide -- just use sample directly.
    hi = (buffer2[out] << 2) | (buffer1[out] >> 6); // Expand 10-bit data
    lo = (buffer1[out] << 2) |  buffer2[out];       // to 12 bits
  }

  // Might be possible to tweak 'hi' and 'lo' at this point to achieve
  // different voice modulations -- robot effect, etc.?

  DAC_CS_PORT &= ~_BV(DAC_CS); // Select DAC
  // Clock out 4 bits DAC config (not in loop because it's constant)
  DAC_DI_PORT  &= ~_BV(DAC_DI); // 0 = Select DAC A, unbuffered
  DAC_CLK_PORT |=  _BV(DAC_CLK); DAC_CLK_PORT &= ~_BV(DAC_CLK);
  DAC_CLK_PORT |=  _BV(DAC_CLK); DAC_CLK_PORT &= ~_BV(DAC_CLK);
  DAC_DI_PORT  |=  _BV(DAC_DI); // 1X gain, enable = 1
  DAC_CLK_PORT |=  _BV(DAC_CLK); DAC_CLK_PORT &= ~_BV(DAC_CLK);
  DAC_CLK_PORT |=  _BV(DAC_CLK); DAC_CLK_PORT &= ~_BV(DAC_CLK);
  for(bit=0x08; bit; bit>>=1) { // Clock out first 4 bits of data
    if(hi & bit) DAC_DI_PORT |=  _BV(DAC_DI);
    else         DAC_DI_PORT &= ~_BV(DAC_DI);
    DAC_CLK_PORT |=  _BV(DAC_CLK); DAC_CLK_PORT &= ~_BV(DAC_CLK);
  }
  for(bit=0x80; bit; bit>>=1) { // Clock out last 8 bits of data
    if(lo & bit) DAC_DI_PORT |=  _BV(DAC_DI);
    else         DAC_DI_PORT &= ~_BV(DAC_DI);
    DAC_CLK_PORT |=  _BV(DAC_CLK); DAC_CLK_PORT &= ~_BV(DAC_CLK);
  }
  DAC_CS_PORT    |=  _BV(DAC_CS);    // Unselect DAC

  if(++out >= nSamples) out = 0;
}

