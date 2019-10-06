#if 0 // Change to 1 to enable this code (must enable ONE user*.cpp only!)

// WIP DO NOT USE

#include "globals.h"
#include <Servo.h>

// Servo stuff
Servo myservo;
#define SERVO_MOUTH_OPEN     0
#define SERVO_MOUTH_CLOSED 180
// TO DO: move servo when sound is playing.
// At end of WAV, move mouth to closed position.

// WAV player stuff
#define WAV_BUFFER_SIZE 256
static uint8_t     wavBuf[2][WAV_BUFFER_SIZE];
static File        wavFile;
static bool        playing = false;
static int         remainingBytesInChunk;
static uint8_t     activeBuf;
static uint16_t    bufIdx, bufEnd, nextBufEnd;
static bool        startWav(char *filename);
static void        wavOutCallback(void);
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
  myservo.attach(3);
}

void user_loop(void) {
  if(!playing && wavListPtr) {
    pinMode(2, INPUT_PULLUP);
    delayMicroseconds(20); // Avoid boop code interference
    if(!digitalRead(2)) {
      arcada.chdir(wav_path);
      startWav(wavListPtr->filename);
      wavListPtr = wavListPtr->next; // Will loop around from end to start of list
    }
  }

// 'pos' will be determined periodically, maybe not every frame. TBD.
// needs to go to a closed position when WAV is finished.
//  myservo.write(pos);
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
          bufIdx   = 0;
          playing = true;
          arcada.timerCallback(buf.fmt.sampleRate, wavOutCallback);
          nextBufEnd = readWaveData(wavBuf[1]);
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
      playing = false;
      return;
    }
    bufIdx     = 0;
    bufEnd     = nextBufEnd;
    nextBufEnd = readWaveData(wavBuf[activeBuf]);
    activeBuf  = 1 - activeBuf;
  }
}

#endif // 0
