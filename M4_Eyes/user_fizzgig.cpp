// SPDX-FileCopyrightText: 2019 Phillip Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#if 0 // Change to 1 to enable this code (must enable ONE user*.cpp only!)

#include "globals.h"
#include <Servo.h>

// Servo stuff
Servo myservo;
#define SERVO_MOUTH_OPEN    750 // Servo pulse microseconds
#define SERVO_MOUTH_CLOSED 1850
#define SERVO_PIN             3

#define BUTTON_PIN            2

// WAV player stuff
#define WAV_BUFFER_SIZE    256
static uint8_t     wavBuf[2][WAV_BUFFER_SIZE];
static File        wavFile;
static bool        playing = false;
static int         remainingBytesInChunk;
static uint8_t     activeBuf;
static uint16_t    bufIdx, bufEnd, nextBufEnd;
static bool        startWav(char *filename);
static void        wavOutCallback(void);
static uint32_t    wavEventTime; // WAV start or end time, in ms
static const char *wav_path = "fizzgig";
static struct wavlist { // Linked list of WAV filenames
  char           *filename;
  struct wavlist *next;
} *wavListStart = NULL, *wavListPtr = NULL;
#define MAX_WAV_FILES 20

void user_setup(void) {
  File            entry;
  struct wavlist *wptr;
  char            filename[SD_MAX_FILENAME_SIZE+1];
  // Scan wav_path for .wav files:
  for(int i=0; i<MAX_WAV_FILES; i++) {
    entry = arcada.openFileByIndex(wav_path, i, O_READ, "wav");
    if(!entry) break;
    // Found one, alloc new wavlist struct, try duplicating filename
    if((wptr = (struct wavlist *)malloc(sizeof(struct wavlist)))) {
      entry.getName(filename, SD_MAX_FILENAME_SIZE);
      if((wptr->filename = strdup(filename))) {
        // Alloc'd OK, add to linked list...
        if(wavListPtr) {           // List already started?
          wavListPtr->next = wptr; // Point prior last item to new one
        } else {
          wavListStart = wptr;     // Point list head to new item
        }
        wavListPtr = wptr;         // Update last item to new one
      } else {
        free(wptr);                // Alloc failed, delete interim stuff
      }
    }
    entry.close();
  }
  if(wavListPtr) {                   // Any items in WAV list?
    wavListPtr->next = wavListStart; // Point last item's next to list head (list is looped)
    wavListPtr       = wavListStart; // Update list pointer to head
  }
}

void user_loop(void) {
  if(playing) {
    // While WAV is playing, wiggle servo between middle and open-mouth positions:
    uint32_t elapsed = millis() - wavEventTime;                // Time since audio start
    uint16_t frac    = elapsed % 500;                          // 0 to 499 = 0.5 sec
    float    n       = 1.0 - ((float)abs(250 - frac) / 500.0); // Ramp 0.5, 1.0, 0.5 in 0.5 sec
    myservo.writeMicroseconds((int)((float)SERVO_MOUTH_CLOSED + (float)(SERVO_MOUTH_OPEN - SERVO_MOUTH_CLOSED) * n));
    // BUTTON_PIN button is ignored while sound is playing.
  } else if(wavListPtr) {
    // Not currently playing WAV. Check for button press on pin BUTTON_PIN.
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    delayMicroseconds(20); // Avoid boop code interference
    if(!digitalRead(BUTTON_PIN)) {
      arcada.chdir(wav_path);
      startWav(wavListPtr->filename);
      wavListPtr = wavListPtr->next; // Will loop around from end to start of list
    }
    pinMode(BUTTON_PIN, INPUT);
    if(myservo.attached()) { // If servo still active (from recent WAV playing)
      myservo.writeMicroseconds(SERVO_MOUTH_CLOSED); // Make sure it's in closed position
      // If it's been more than 1 sec since audio stopped,
      // deactivate the servo to reduce power, heat & noise.
      if((millis() - wavEventTime) > 1000) {
        myservo.detach();
      }
    }
  }
}

static uint16_t readWaveData(uint8_t *dst) {
  if(remainingBytesInChunk <= 0) {
    // Read next chunk
    struct {
      char     id[4];
      uint32_t size;
    } header;
    for(;;) {
      if(wavFile.read(&header, 8) != 8) return 0;
      if(!strncmp(header.id, "data", 4)) {
        remainingBytesInChunk = header.size;
        break;
      }
      if(!wavFile.seekCur(header.size)) { // If not "data" then skip
        return 0; // Seek failed, return invalid count
      }
    }
  }

  int16_t bytesRead = wavFile.read(dst, min(WAV_BUFFER_SIZE, remainingBytesInChunk));
  if(bytesRead > 0) remainingBytesInChunk -= bytesRead;
  return bytesRead;
}

// Partially swiped from Wave Shield code.
// Is pared-down, handles 8-bit mono only to keep it simple.
static bool startWav(char *filename) {
  wavFile = arcada.open(filename);
  if(!wavFile) {
    Serial.println("Failed to open WAV file");
    return false;
  }

  union {
    struct {
      char     id[4];
      uint32_t size;
      char     data[4];
    } riff;  // riff chunk
    struct {
      uint16_t compress;
      uint16_t channels;
      uint32_t sampleRate;
      uint32_t bytesPerSecond;
      uint16_t blockAlign;
      uint16_t bitsPerSample;
      uint16_t extraBytes;
    } fmt; // fmt data
  } buf;

  uint16_t size;
  if((wavFile.read(&buf, 12) == 12)
    && !strncmp(buf.riff.id, "RIFF", 4)
    && !strncmp(buf.riff.data, "WAVE", 4)) {
    // next chunk must be fmt, fmt chunk size must be 16 or 18
    if((wavFile.read(&buf, 8) == 8)
      && !strncmp(buf.riff.id, "fmt ", 4)
      && (((size = buf.riff.size) == 16) || (size == 18))
      && (wavFile.read(&buf, size) == size)
      && ((size != 18) || (buf.fmt.extraBytes == 0))) {
      if((buf.fmt.channels == 1) && (buf.fmt.bitsPerSample == 8)) {
        Serial.printf("Samples/sec: %d\n", buf.fmt.sampleRate);
        bufEnd = readWaveData(wavBuf[0]);
        if(bufEnd > 0) {
          // Initialize A/D, speaker and start timer
          analogWriteResolution(8);
          analogWrite(A0, 128);
          analogWrite(A1, 128);
          arcada.enableSpeaker(true);
          wavEventTime = millis(); // WAV starting time
          bufIdx       = 0;
          playing      = true;
          arcada.timerCallback(buf.fmt.sampleRate, wavOutCallback);
          nextBufEnd   = readWaveData(wavBuf[1]);
          myservo.attach(SERVO_PIN);
        }
        return true;
      } else {
        Serial.println("Only 8-bit mono WAVs are supported");
      }
    } else {
      Serial.println("WAV uses compression or other unrecognized setting");
    }
  } else {
    Serial.println("Not WAV file");
  }

  wavFile.close();
  return false;
}

static void wavOutCallback(void) {
  uint8_t n = wavBuf[activeBuf][bufIdx];
  analogWrite(A0, n);
  analogWrite(A1, n);

  if(++bufIdx >= bufEnd) {
    if(nextBufEnd <= 0) {
      arcada.timerStop();
      arcada.enableSpeaker(false);
      playing      = false;
      wavEventTime = millis(); // Same var now holds WAV end time
      return;
    }
    bufIdx     = 0;
    bufEnd     = nextBufEnd;
    nextBufEnd = readWaveData(wavBuf[activeBuf]);
    activeBuf  = 1 - activeBuf;
  }
}

#endif // 0
