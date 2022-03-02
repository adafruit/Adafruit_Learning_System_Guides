// SPDX-FileCopyrightText: 2017 Carter Nelson for Adafruit Industries
//
// SPDX-License-Identifier: MIT

//
// Gordon Cole MP3 Player
//

#include <SPI.h>
#include <SD.h>
#include <Adafruit_VS1053.h>

// Guide is based on Feather M0 Express
// ARDUINO_SAMD_FEATHER_M0 defines only
// VS1053 Pins
#define VS1053_RESET   -1     // VS1053 reset pin (not used!)
#define VS1053_CS       6     // VS1053 chip select pin (output)
#define VS1053_DCS      10    // VS1053 Data/command select pin (output)
#define CARDCS          5     // Card chip select pin
#define VS1053_DREQ     9     // VS1053 Data request, ideally an Interrupt pin
// Button Pins
#define BUTTON_PLAY     13    // PLAY / STOP button
#define BUTTON_PAUSE    12    // PAUSE / RESUME button
#define BUTTON_NEXT     11    // NEXT button
// Status LED
#define LED_STATUS      19    // status LED
#define BLINK_RATE      500   // blink rate in ms
// Volume Control
#define KNOB_VOLUME     0     // volume knob
#define KNOB_MIN        0     // min ADC value
#define KNOB_MAX        1023  // max ADC value
#define VOL_MIN         0     // min volume (most loud)
#define VOL_MAX         50    // max volume (most quiet)
#define VOL_UPDATE      250   // update rate in ms
#define VOL_SAMPLES     10    // number of reads for average
#define VOL_SAMPLE_RATE 5     // ms delay per sample
#define VOL_THRESHOLD   20    // vol must change by this many counts
// Maximum number of files (tracks) to load
#define TRACKS_MAX      100
// Player behavior
#define AUTO_PLAY_NEXT  true  // true to automatically go to next track

unsigned long currentMillis;
unsigned long previousBlinkMillis, previousVolMillis;
int currentKnob, previousKnob;
int volume;
int currentTrack, totalTracks;
char trackListing[TRACKS_MAX][13] = {' '};
enum mode {
  PLAYING,
  PAUSED,
  STOPPED
} currentMode = STOPPED;

Adafruit_VS1053_FilePlayer musicPlayer = 
  Adafruit_VS1053_FilePlayer(VS1053_RESET, VS1053_CS, VS1053_DCS, VS1053_DREQ, CARDCS);

//-----------------------------------------------------------------------------
void setup() {
  Serial.begin(9600);
  // Leave commented for standalone operation, uncomment for troubleshooting
  //while (!Serial) ;

  // Initialize pins
  pinMode(BUTTON_PLAY, INPUT_PULLUP);
  pinMode(BUTTON_PAUSE, INPUT_PULLUP);
  pinMode(BUTTON_NEXT, INPUT_PULLUP);
  pinMode(LED_STATUS, OUTPUT);

  // Initialize status LED
  previousBlinkMillis = millis();
  digitalWrite(LED_STATUS, LOW);

  Serial.println("\n\nGordon Cole MP3 Player");

  // Initialize the music player  
  if (! musicPlayer.begin()) { 
     Serial.println(F("Couldn't find VS1053, do you have the right pins defined?"));
     while (1) {
       digitalWrite(LED_STATUS, !digitalRead(LED_STATUS));
       delay(100);        
     }
  }
  Serial.println(F("VS1053 found"));
  musicPlayer.softReset();

  // Make a tone to indicate VS1053 is working 
  musicPlayer.sineTest(0x44, 500);    

  // Set volume for left, right channels. lower numbers == louder volume!
  previousVolMillis = millis();  
  previousKnob = analogRead(KNOB_VOLUME);
  volume = map(previousKnob, KNOB_MIN, KNOB_MAX, VOL_MIN, VOL_MAX);
  Serial.print("Volume = "); Serial.println(volume);
  musicPlayer.setVolume(volume, volume);

  // Initialize the SD card
  if (!SD.begin(CARDCS)) {
    Serial.println(F("SD failed, or not present"));
    while (1) {
       digitalWrite(LED_STATUS, !digitalRead(LED_STATUS));
       delay(100);        
    }
  }
  Serial.println("SD OK!");

  // Load list of tracks
  Serial.println("Track Listing");
  Serial.println("=============");  
  totalTracks = 0;
  loadTracks(SD.open("/"), 0);
  currentTrack = 0;

  // Setup interrupts (DREQ) for playback 
  musicPlayer.useInterrupt(VS1053_FILEPLAYER_PIN_INT); 
}

//-----------------------------------------------------------------------------
void loop() {
  // Check and set volume
  updateVolume();

  // Update status LED
  updateStatusLED();

  // Auto play next track if feature enabled
  if (AUTO_PLAY_NEXT) {
    if (currentMode==PLAYING && musicPlayer.stopped()) {
      currentTrack = ++currentTrack < totalTracks ? currentTrack : 0; 
      Serial.print("Next ");
      Serial.print(currentTrack); Serial.print("=");
      Serial.println(trackListing[currentTrack]);
      musicPlayer.startPlayingFile(trackListing[currentTrack]);
      currentMode = PLAYING;
    }
  }

  // Start / Stop
  if (!digitalRead(BUTTON_PLAY)) {
    if (musicPlayer.stopped()) {
      Serial.print("Start ");
      Serial.print(currentTrack); Serial.print("=");
      Serial.println(trackListing[currentTrack]);
      musicPlayer.startPlayingFile(trackListing[currentTrack]);
      currentMode = PLAYING;
    } else {
      Serial.println("Stopped.");
      musicPlayer.stopPlaying();
      currentMode = STOPPED;      
    }
    delay(250);
  }

  // Pause / Resume
  if (!digitalRead(BUTTON_PAUSE)) {
    if (!musicPlayer.stopped()) {
      if (musicPlayer.paused()) {
        Serial.println("Resumed");
        musicPlayer.pausePlaying(false);
        currentMode = PLAYING;
      } else { 
        Serial.println("Paused");
        musicPlayer.pausePlaying(true);
        currentMode = PAUSED;
      }    
    }
    delay(250);
  }

  // Next
  if (!digitalRead(BUTTON_NEXT)) {
    if (!musicPlayer.stopped()) {
      Serial.println("Stopping current playback.");
      musicPlayer.stopPlaying();
    }
    currentTrack = ++currentTrack < totalTracks ? currentTrack : 0; 
    Serial.print("Next ");
    Serial.print(currentTrack); Serial.print("=");
    Serial.println(trackListing[currentTrack]);
    musicPlayer.startPlayingFile(trackListing[currentTrack]);
    currentMode = PLAYING;
    delay(250);
  }
}

//-----------------------------------------------------------------------------
void updateVolume() {
  // Rate limit
  currentMillis = millis();
  if (currentMillis - previousVolMillis < VOL_UPDATE) return;
  previousVolMillis = currentMillis;
  // Get an average reading
  currentKnob = 0;
  for (int i=0; i<VOL_SAMPLES; i++) {
    currentKnob += analogRead(KNOB_VOLUME);
    delay(VOL_SAMPLE_RATE);
  }
  currentKnob /= VOL_SAMPLES;
  // Only update if it's changed
  if (abs(currentKnob-previousKnob) > VOL_THRESHOLD) {
    Serial.print("["); Serial.print(currentKnob);
    Serial.print(","); Serial.print(previousKnob);
    Serial.print("] ");
    previousKnob = currentKnob;
    volume = map(currentKnob, KNOB_MIN, KNOB_MAX, VOL_MIN, VOL_MAX);
    Serial.print("Volume set to: "); Serial.println(volume);
    musicPlayer.setVolume(volume, volume);  
  }  
}

//-----------------------------------------------------------------------------
void updateStatusLED() {
  if (musicPlayer.paused()) {
    // Blink it like a polaroid
    currentMillis = millis();
    if (currentMillis - previousBlinkMillis > BLINK_RATE) {
       previousBlinkMillis = currentMillis;
       digitalWrite(LED_STATUS, !digitalRead(LED_STATUS));
    }
  } else if (!musicPlayer.stopped()) {
    // It's so on again
    digitalWrite(LED_STATUS, HIGH);
  } else {
    // It's so off again
    digitalWrite(LED_STATUS, LOW);
  }
}

//-----------------------------------------------------------------------------
void loadTracks(File dir, int level) {
  while (true) {
    File entry = dir.openNextFile();
    if (!entry) return;
    if (entry.isDirectory()) {
      // Recursive call to scan next dir level
      loadTracks(entry, level + 1);
    } else {
      // Only add files in root dir
      if (level == 0) {
        // And only if they have good names
        if (nameCheck(entry.name())) {
          strncpy(trackListing[totalTracks], entry.name(), 12);
          Serial.print(totalTracks); Serial.print("=");
          Serial.println(trackListing[totalTracks]);
          totalTracks++;
        }
      }
    }
    entry.close();
    // Stop scanning if we hit max
    if (totalTracks >= TRACKS_MAX) return;
  } 
}

//-----------------------------------------------------------------------------
bool nameCheck(char* name) {
  int len = strlen(name);
  // Check length
  if (len <= 4) return false;
  // Check extension
  char* ext = strrchr(name,'.');
  if (!(
    strcmp(ext,".MP3") == 0  ||
    strcmp(ext,".OGG") == 0
    )) return false;
  // Check first character
  switch(name[0]) {
    case '_': return false;
  }
  return true;
}
