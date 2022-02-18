// SPDX-FileCopyrightText: 2018 Anne Barela for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Random HAL demo; adapted from PiSpeak sketch.  When button
// on A0 is pressed, plays a random WAV file from a list.
 
#include <WaveHC.h>
#include <WaveUtil.h>
 
// REPLACE THESE WITH YOUR ACTUAL WAVE FILE NAMES:
// These should be at the root level, not in a folder.
static const char PROGMEM
  file00[] = "0.wav",
  file01[] = "1.wav",
  file02[] = "2.wav",
  file03[] = "3.wav",
  file04[] = "4.wav",
  file05[] = "5.wav",
  file06[] = "6.wav",
  file07[] = "7.wav",
  file08[] = "8.wav",
  file09[] = "9.wav";
// If adding files above, include corresponding items here:
static const char * const filename[] PROGMEM = {
  file00, file01, file02, file03, file04,
  file05, file06, file07, file08, file09 };
// Sorry for the sillyness, but this is how PROGMEM string
// arrays are handled.
 
#define error(msg) error_P(PSTR(msg))
SdReader  card;
FatVolume vol;
FatReader root;
FatReader file;
WaveHC    wave;
uint8_t   debounce = 0,   // Button debounce counter
          prev     = 255; // Index of last sound played
 
void setup() {
  Serial.begin(9600);
  if(!card.init())        error("Card init. failed!");
  if(!vol.init(card))     error("No partition!");
  if(!root.openRoot(vol)) error("Couldn't open dir");
  // PgmPrintln("Files found:");
  // root.ls();
 
  digitalWrite(A0, HIGH);     // Enable pullup on button
  randomSeed(analogRead(A1)); // Randomize first sound
}
 
void loop() {
  if(digitalRead(A0) == HIGH) { // Button not pressed
    debounce = 0;               // Reset debounce counter
    return;                     // and nothing else
  }
 
  if(++debounce >= 20) { // Debounced button press
    uint8_t n;
    char    name[20];
 
    do { // Choose a random file...
      n = random(sizeof(filename) / sizeof(filename[0]));
    } while(n == prev); // ...but don't repeat last one
 
    prev     = n;                       // Save file #
    debounce = 0;                       // Reset debounce counter
    strcpy_P(name, (char *)pgm_read_word(&filename[n])); // PROGMEM->RAM
    if(wave.isplaying) wave.stop();     // Stop WAV if playing
 
    if(!file.open(root, name)) {
      PgmPrint("Couldn't open file ");
      Serial.print(name);
      return;
    }
    if(!wave.create(file)) {
      PgmPrintln("Not a valid WAV");
      return;
    }
 
    wave.play();                   // Start playing
    while(wave.isplaying);         // Wait for completion
    sdErrorCheck();                // Check for error during play
    while(digitalRead(A0) == LOW); // Wait for button release
  }
}
 
void error_P(const char *str) {
  PgmPrint("Error: ");
  SerialPrint_P(str);
  sdErrorCheck();
  for(;;);
}
 
void sdErrorCheck(void) {
  if(!card.errorCode()) return;
  PgmPrint("\r\nSD I/O error: ");
  Serial.print(card.errorCode(), HEX);
  PgmPrint(", ");
  Serial.println(card.errorData(), HEX);
  for(;;);
}
