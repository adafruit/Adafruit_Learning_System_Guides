/*
Dalek voice effect using Wave Shield.  This is based on the adavoice sketch
with a lot of code & comments ripped out, so see that code for more insight,
parts list, etc.  This sketch doesn't do any pitch bending, just the Dalek
modulation...you'll need to perform your own monotone & British accent. :)

This should still let you play sounds off the SD card (voice effect stops
during playback), haven't tested, but worked in prior code this came from.

Written by Adafruit industries, with portions adapted from the
'PiSpeakHC' sketch included with WaveHC library.
*/

#include <WaveHC.h>
#include <WaveUtil.h>

SdReader  card;
FatVolume vol;
FatReader root;
FatReader file;
WaveHC    wave;

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

uint8_t adc_save;

// Keypad information:
uint8_t
  rows[] = { A2, A3, A4, A5 }, // Keypad rows connect to these pins
  cols[] = { 6, 7, 8 },        // Keypad columns connect to these pins
  r      = 0,                  // Current row being examined
  prev   = 255,                // Previous key reading (or 255 if none)
  count  = 0;                  // Counter for button debouncing
#define DEBOUNCE 10            // Number of iterations before button 'takes'

// Keypad/WAV information.  Number of elements here should match the
// number of keypad rows times the number of columns, plus one:
const char *sound[] = {
  "breath" , "destroy", "saber"   , // Row 1 = Darth Vader sounds
  "zilla"  , "crunch" , "burp"    , // Row 2 = Godzilla sounds
  "hithere", "smell"  , "squirrel", // Row 3 = Dug the dog sounds
  "carhorn", "foghorn", "door"    , // Row 4 = Cartoon/SFX sound
  "startup" };                      // Extra item = boot sound


//////////////////////////////////// SETUP

void setup() {
  uint8_t i;

  Serial.begin(9600);           

  pinMode(2, OUTPUT);    // Chip select
  pinMode(3, OUTPUT);    // Serial clock
  pinMode(4, OUTPUT);    // Serial data
  pinMode(5, OUTPUT);    // Latch
  digitalWrite(2, HIGH); // Set chip select high

  if(!card.init())             Serial.print(F("Card init. failed!"));
  else if(!vol.init(card))     Serial.print(F("No partition!"));
  else if(!root.openRoot(vol)) Serial.print(F("Couldn't open dir"));
  else {
    Serial.println(F("Files found:"));
    root.ls();
    // Play startup sound (last file in array).
    playfile(sizeof(sound) / sizeof(sound[0]) - 1);
  }

  // Optional, but may make sampling and playback a little smoother:
  // Disable Timer0 interrupt.  This means delay(), millis() etc. won't
  // work.  Comment this out if you really, really need those functions.
  TIMSK0 = 0;

  // Set up Analog-to-Digital converter:
  analogReference(EXTERNAL); // 3.3V to AREF
  adc_save = ADCSRA;         // Save ADC setting for restore later

  // Set keypad rows to outputs, set to HIGH logic level:
  for(i=0; i<sizeof(rows); i++) {
    pinMode(rows[i], OUTPUT);
    digitalWrite(rows[i], HIGH);
  }
  // Set keypad columns to inputs, enable pull-up resistors:
  for(i=0; i<sizeof(cols); i++) {
    pinMode(cols[i], INPUT);
    digitalWrite(cols[i], HIGH);
  }

  while(wave.isplaying); // Wait for startup sound to finish...
  startDalek();          // and start the Dalek effect
}


//////////////////////////////////// LOOP

// As written here, the loop function scans a keypad to triggers sounds
// (stopping and restarting the voice effect as needed).  If all you need
// is a couple of buttons, it may be easier to tear this out and start
// over with some simple digitalRead() calls.

void loop() {

  uint8_t c, button;

  // Set current row to LOW logic state...
  digitalWrite(rows[r], LOW);
  // ...then examine column buttons for a match...
  for(c=0; c<sizeof(cols); c++) {
    if(digitalRead(cols[c]) == LOW) { // First match.
      button = r * sizeof(cols) + c;  // Get button index.
      if(button == prev) {            // Same button as before?
        if(++count >= DEBOUNCE) {     // Yes.  Held beyond debounce threshold?
          if(wave.isplaying) wave.stop();      // Stop current WAV (if any)
          else               stopDalek();      // or stop voice effect
          playfile(button);                    // and play new sound.
          while(digitalRead(cols[c]) == LOW);  // Wait for button release.
          prev  = 255;                // Reset debounce values.
          count = 0;
        }
      } else {                        // Not same button as prior pass.
        prev  = button;               // Record new button and
        count = 0;                    // restart debounce counter.
      }
    }
  }

  // Restore current row to HIGH logic state and advance row counter...
  digitalWrite(rows[r], HIGH);
  if(++r >= sizeof(rows)) { // If last row scanned...
    r = 0;                  // Reset row counter
    // If no new sounds have been triggered at this point, restart Dalek...
    if(!wave.isplaying) startDalek();
  }
}


//////////////////////////////////// HELPERS

// Open and start playing a WAV file
void playfile(int idx) {
  char filename[13];

  (void)sprintf(filename,"%s.wav", sound[idx]);
  Serial.print("File: ");
  Serial.println(filename);

  if(!file.open(root, filename)) {
    Serial.print(F("Couldn't open file "));
    Serial.print(filename);
    return;
  }
  if(!wave.create(file)) {
    Serial.println(F("Not a valid WAV"));
    return;
  }
  wave.play();
}


//////////////////////////////////// DALEK MODULATION CODE

void startDalek() {

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
}

void stopDalek() {
  ADCSRA = adc_save; // Disable ADC interrupt and allow normal use
}

// Dalek sound is produced by a 'ring modulator' which multiplies microphone
// input by a 30 Hz sine wave.  sin() is a time-consuming floating-point
// operation so instead a canned 8-bit integer table is used...the number of
// elements here takes into account the ADC sample rate (~9615 Hz) and the
// desired sine wave frequency (traditionally ~30 Hz for Daleks).
// This is actually abs(sin(x)) to slightly simplify some math later.

volatile uint16_t ringPos = 0; // Current index into ring table below

static const uint8_t PROGMEM ring[] = {
  0x00, 0x03, 0x05, 0x08, 0x0A, 0x0D, 0x0F, 0x12,
  0x14, 0x17, 0x19, 0x1B, 0x1E, 0x20, 0x23, 0x25,
  0x28, 0x2A, 0x2D, 0x2F, 0x32, 0x34, 0x37, 0x39,
  0x3C, 0x3E, 0x40, 0x43, 0x45, 0x48, 0x4A, 0x4C,
  0x4F, 0x51, 0x54, 0x56, 0x58, 0x5B, 0x5D, 0x5F,
  0x62, 0x64, 0x66, 0x68, 0x6B, 0x6D, 0x6F, 0x72,
  0x74, 0x76, 0x78, 0x7A, 0x7D, 0x7F, 0x81, 0x83,
  0x85, 0x87, 0x89, 0x8C, 0x8E, 0x90, 0x92, 0x94,
  0x96, 0x98, 0x9A, 0x9C, 0x9E, 0xA0, 0xA2, 0xA4,
  0xA6, 0xA8, 0xA9, 0xAB, 0xAD, 0xAF, 0xB1, 0xB3,
  0xB4, 0xB6, 0xB8, 0xBA, 0xBB, 0xBD, 0xBF, 0xC0,
  0xC2, 0xC4, 0xC5, 0xC7, 0xC8, 0xCA, 0xCB, 0xCD,
  0xCE, 0xD0, 0xD1, 0xD3, 0xD4, 0xD5, 0xD7, 0xD8,
  0xD9, 0xDB, 0xDC, 0xDD, 0xDE, 0xE0, 0xE1, 0xE2,
  0xE3, 0xE4, 0xE5, 0xE7, 0xE8, 0xE9, 0xEA, 0xEB,
  0xEC, 0xED, 0xED, 0xEE, 0xEF, 0xF0, 0xF1, 0xF2,
  0xF3, 0xF3, 0xF4, 0xF5, 0xF5, 0xF6, 0xF7, 0xF7,
  0xF8, 0xF9, 0xF9, 0xFA, 0xFA, 0xFB, 0xFB, 0xFB,
  0xFC, 0xFC, 0xFD, 0xFD, 0xFD, 0xFE, 0xFE, 0xFE,
  0xFE, 0xFE, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
  0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE,
  0xFE, 0xFE, 0xFE, 0xFE, 0xFD, 0xFD, 0xFD, 0xFC,
  0xFC, 0xFB, 0xFB, 0xFB, 0xFA, 0xFA, 0xF9, 0xF9,
  0xF8, 0xF7, 0xF7, 0xF6, 0xF5, 0xF5, 0xF4, 0xF3,
  0xF3, 0xF2, 0xF1, 0xF0, 0xEF, 0xEE, 0xED, 0xED,
  0xEC, 0xEB, 0xEA, 0xE9, 0xE8, 0xE7, 0xE5, 0xE4,
  0xE3, 0xE2, 0xE1, 0xE0, 0xDE, 0xDD, 0xDC, 0xDB,
  0xD9, 0xD8, 0xD7, 0xD5, 0xD4, 0xD3, 0xD1, 0xD0,
  0xCE, 0xCD, 0xCB, 0xCA, 0xC8, 0xC7, 0xC5, 0xC4,
  0xC2, 0xC0, 0xBF, 0xBD, 0xBB, 0xBA, 0xB8, 0xB6,
  0xB4, 0xB3, 0xB1, 0xAF, 0xAD, 0xAB, 0xA9, 0xA8,
  0xA6, 0xA4, 0xA2, 0xA0, 0x9E, 0x9C, 0x9A, 0x98,
  0x96, 0x94, 0x92, 0x90, 0x8E, 0x8C, 0x89, 0x87,
  0x85, 0x83, 0x81, 0x7F, 0x7D, 0x7A, 0x78, 0x76,
  0x74, 0x72, 0x6F, 0x6D, 0x6B, 0x68, 0x66, 0x64,
  0x62, 0x5F, 0x5D, 0x5B, 0x58, 0x56, 0x54, 0x51,
  0x4F, 0x4C, 0x4A, 0x48, 0x45, 0x43, 0x40, 0x3E,
  0x3C, 0x39, 0x37, 0x34, 0x32, 0x2F, 0x2D, 0x2A,
  0x28, 0x25, 0x23, 0x20, 0x1E, 0x1B, 0x19, 0x17,
  0x14, 0x12, 0x0F, 0x0D, 0x0A, 0x08, 0x05, 0x03 };

ISR(ADC_vect, ISR_BLOCK) { // ADC conversion complete

  uint8_t  hi, lo, bit;
  int32_t  v; // Voice in
  uint16_t r; // Ring in
  uint32_t o; // Output

  lo = ADCL;
  hi = ADCH;

  // Multiply signed 10-bit input by abs(sin(30 Hz)):
  v = ((int32_t)hi << 8 | lo) - 512;               // voice = -512 to +511
  r = (uint16_t)pgm_read_byte(&ring[ringPos]) + 1; // ring = 1 to 256
  o = v * r + 131072;                              // 0-261888 (18-bit)
  hi = (o >> 14);                                  // Scale 18- to 12-bit
  lo = (o >> 16) | (o >> 6);

  if(++ringPos >= sizeof(ring)) ringPos = 0; // Cycle through table

  // Issue result to DAC:
  DAC_CS_PORT  &= ~_BV(DAC_CS);
  DAC_DI_PORT  &= ~_BV(DAC_DI);
  DAC_CLK_PORT |=  _BV(DAC_CLK); DAC_CLK_PORT &= ~_BV(DAC_CLK);
  DAC_CLK_PORT |=  _BV(DAC_CLK); DAC_CLK_PORT &= ~_BV(DAC_CLK);
  DAC_DI_PORT  |=  _BV(DAC_DI);
  DAC_CLK_PORT |=  _BV(DAC_CLK); DAC_CLK_PORT &= ~_BV(DAC_CLK);
  DAC_CLK_PORT |=  _BV(DAC_CLK); DAC_CLK_PORT &= ~_BV(DAC_CLK);
  for(bit=0x08; bit; bit>>=1) {
    if(hi & bit) DAC_DI_PORT |=  _BV(DAC_DI);
    else         DAC_DI_PORT &= ~_BV(DAC_DI);
    DAC_CLK_PORT |=  _BV(DAC_CLK); DAC_CLK_PORT &= ~_BV(DAC_CLK);
  }
  for(bit=0x80; bit; bit>>=1) {
    if(lo & bit) DAC_DI_PORT |=  _BV(DAC_DI);
    else         DAC_DI_PORT &= ~_BV(DAC_DI);
    DAC_CLK_PORT |=  _BV(DAC_CLK); DAC_CLK_PORT &= ~_BV(DAC_CLK);
  }
  DAC_CS_PORT    |=  _BV(DAC_CS);
}

