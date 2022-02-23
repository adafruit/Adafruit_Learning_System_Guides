// SPDX-FileCopyrightText: 2019 Phillip Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Basic voice changer code. This version is specific to the Adafruit
// MONSTER M4SK board using a PDM microphone.

#if defined(ADAFRUIT_MONSTER_M4SK_EXPRESS)

#include "globals.h"
#include <SPI.h>
#include <Adafruit_ZeroPDMSPI.h>

#define MIN_PITCH_HZ   65
#define MAX_PITCH_HZ 1600
#define TYP_PITCH_HZ  175

static void  voiceOutCallback(void);
static float actualPlaybackRate;

// PDM mic allows 1.0 to 3.25 MHz max clock (2.4 typical).
// SPI native max is is 24 MHz, so available speeds are 12, 6, 3 MHz.
#define SPI_BITRATE 3000000
// 3 MHz / 32 bits = 93,750 Hz interrupt frequency
// 2 interrupts/sample = 46,875 Hz audio sample rate
const float sampleRate = (float)SPI_BITRATE / 64.0;
// sampleRate is float in case factors change to make it not divide evenly.
// It DOES NOT CHANGE over time, only playbackRate does.

// Although SPI lib now has an option to get an SPI object's SERCOM number
// at run time, the interrupt handler MUST be declared at compile time...
// so it's necessary to know the SERCOM # ahead of time anyway, oh well.
#define PDM_SPI            SPI2    // PDM mic SPI peripheral
#define PDM_SERCOM_HANDLER SERCOM3_0_Handler

Adafruit_ZeroPDMSPI pdmspi(&PDM_SPI);

static float          playbackRate     = sampleRate;
static uint16_t      *recBuf           = NULL;
// recBuf currently gets allocated (in voiceSetup()) for two full cycles of
// the lowest pitch we're likely to encounter. Right now it doesn't really
// NEED to be this size, but if pitch detection is added in the future then
// this'll become more useful.
// 46,875 sampling rate from mic, 65 Hz lowest pitch -> 2884 bytes.
static const uint16_t recBufSize       = (uint16_t)(sampleRate / (float)MIN_PITCH_HZ * 2.0 + 0.5);
static int16_t        recIndex         = 0;
static int16_t        playbackIndex    = 0;

volatile uint16_t     voiceLastReading = 32768;
volatile uint16_t     voiceMin         = 32768;
volatile uint16_t     voiceMax         = 32768;

#define MOD_MIN 20 // Lowest supported modulation frequency (lower = more RAM use)
static uint8_t        modWave          = 0;     // Modulation wave type (none, sine, square, tri, saw)
static uint8_t       *modBuf           = NULL;  // Modulation waveform buffer
static uint32_t       modIndex         = 0;     // Current position in modBuf
static uint32_t       modLen           = 0;     // Currently used amount of modBuf based on modFreq

// Just playing back directly from the recording circular buffer produces
// audible clicks as the waveforms rarely align at the beginning and end of
// the buffer. So what we do is advance or push back the playback index a
// certain amount when it's likely to overtake or underflow the recording
// index, and interpolate from the current to the jumped-forward-or-back
// readings over a short period. In a perfect world, that "certain amount"
// would be one wavelength of the current voice pitch...BUT...with no pitch
// detecton currently, we instead use a fixed middle-of-the-road value:
// TYP_PITCH_HZ, 175 by default, which is a bit below typical female spoken
// vocal range and a bit above typical male spoken range. This all goes out
// the window with singing, and of course young people will have a higher
// speech range, is just a crude catch-all approximation.
static const uint16_t jump      = (int)(sampleRate / (float)TYP_PITCH_HZ + 0.5);
static const uint16_t interp    = jump / 4; // Interp time = 1/4 waveform
static bool           jumping   = false;
static uint16_t       jumpCount = 1;
static int16_t        jumpThreshold;
static int16_t        playbackIndexJumped;
static uint16_t       nextOut   = 2048;

float voicePitch(float p);

// START PITCH SHIFT (no arguments) ----------------------------------------

bool voiceSetup(bool modEnable) {

  // Allocate circular buffer for audio
  if(NULL == (recBuf = (uint16_t *)malloc(recBufSize * sizeof(uint16_t)))) {
    return false; // Fail
  }

  // Allocate buffer for voice modulation, if enabled
  if(modEnable) {
    // 250 comes from min period in voicePitch()
    modBuf = (uint8_t *)malloc((int)(48000000.0 / 250.0 / MOD_MIN + 0.5));
    // If malloc fails, program will continue without modulation
  }

  pdmspi.begin(sampleRate);  // Set up PDM microphone
  analogWriteResolution(12); // Set up analog output
  voicePitch(1.0);           // Set timer interval

  return true; // Success
}

// SET PITCH ---------------------------------------------------------------

// Set pitch adjustment, higher numbers = higher pitch. 0 < pitch < inf
// 0.5 = halve frequency (1 octave down)
// 1.0 = normal playback
// 2.0 = double frequency (1 octave up)
// Available pitch adjustment range depends on various hardware factors
// (SPI speed, timer/counter resolution, etc.), and the actual pitch
// adjustment (after appying constraints) will be returned.
float voicePitch(float p) {
  float   desiredPlaybackRate = sampleRate * p;
  // Clip to sensible range
  if(desiredPlaybackRate < 19200)       desiredPlaybackRate = 19200;  // ~0.41X
  else if(desiredPlaybackRate > 192000) desiredPlaybackRate = 192000; // ~4.1X
  arcada.timerCallback(desiredPlaybackRate, voiceOutCallback);
  // Making this assumption here knowing Arcada will use 1:1 prescale:
  int32_t period = (int32_t)(48000000.0 / desiredPlaybackRate);
  actualPlaybackRate = 48000000.0 / (float)period;
  p = (actualPlaybackRate / sampleRate); // New pitch
  jumpThreshold = (int)(jump * p + 0.5);
  return p;
}

// SET GAIN ----------------------------------------------------------------

void voiceGain(float g) {
  pdmspi.setMicGain(g); // Handles its own clipping
}

// SET MODULATION ----------------------------------------------------------

// This needs to be called after any call to voicePitch() -- the modulation
// table is not currently auto-regenerated. Maybe that'll change.

void voiceMod(uint32_t freq, uint8_t waveform) {
  if(modBuf) { // Ignore if no modulation buffer allocated
    if(freq < MOD_MIN) freq = MOD_MIN;
    modLen = (uint32_t)(actualPlaybackRate / freq + 0.5);
    if(modLen   < 2) modLen   = 2;
    if(waveform > 4) waveform = 4;
    modWave = waveform;
    yield();
    switch(waveform) {
     case 0: // None
      break;
     case 1: // Square
      memset(modBuf, 255, modLen / 2);
      memset(&modBuf[modLen / 2], 0, modLen - modLen / 2);
      break;
     case 2: // Sine
      for(uint32_t i=0; i<modLen; i++) {
        modBuf[i] = (int)((sin(M_PI * 2.0 * (float)i / (float)modLen) + 1.0) * 0.5 * 255.0 + 0.5);
      }
      break;
     case 3: // Triangle
      for(uint32_t i=0; i<modLen; i++) {
        modBuf[i] = (int)(fabs(0.5 - (float)i / (float)modLen) * 2.0 * 255.0 + 0.5);
      }
      break;
     case 4: // Sawtooth (increasing)
      for(uint32_t i=0; i<modLen; i++) {
        modBuf[i] = (int)((float)i / (float)(modLen - 1) * 255.0 + 0.5);
      }
      break;
    }
  }
}

// INTERRUPT HANDLERS ------------------------------------------------------

void PDM_SERCOM_HANDLER(void) {
  uint16_t micReading = 0;
  if(pdmspi.decimateFilterWord(&micReading, true)) {
    // So, the theory is, in the future some basic pitch detection could be
    // added right about here, which could be used to improve the seam
    // transitions in the playback interrupt (and possibly other things,
    // like dynamic adjustment of the playback rate to do monotone and other
    // effects). Actual usable pitch detection on speech turns out to be One
    // Of Those Nearly Insurmountable Problems In Audio Processing...if
    // you're thinking "oh just count the zero crossings" "just use an FFT"
    // it's really not that simple, trust me, please, I've been reading
    // everything on this, speech waveforms are jerks. Had the beginnings of
    // some "maybe good enough approximation for a hacky microcontroller
    // project" code here, but it's pulled out for now for the sake of
    // getting something not-broken in folks' hands in a sensible timeframe.
    if(++recIndex >= recBufSize) recIndex = 0;
    recBuf[recIndex] = micReading;

    // Outside code can use the value of voiceLastReading if you want to
    // do an approximate live waveform display, or dynamic gain adjustment
    // based on mic input, or other stuff. This won't give you every single
    // sample in the recording buffer one-by-one sequentially...it's just
    // the last thing that was stored prior to whatever time you polled it,
    // but may still have some uses.
    voiceLastReading = micReading;

    // Similarly, user code can extern these variables and monitor the
    // peak-to-peak range. They are never reset in the voice code itself,
    // it's the duty of the user code to reset both to 32768 periodically.
    if(micReading < voiceMin)      voiceMin = micReading;
    else if(micReading > voiceMax) voiceMax = micReading;
  }
}

static void voiceOutCallback(void) {

  // Modulation is done on the output (rather than the input) because
  // pitch-shifting modulated input would cause weird waveform
  // discontinuities. This does require recalculating the modulation table
  // any time the pitch changes though.
  if(modWave) {
    nextOut = (((int32_t)nextOut - 2048) * (modBuf[modIndex] + 1) / 256) + 2048;
    if(++modIndex >= modLen) modIndex = 0;
  }

  // Do analog writes pronto so output timing is consistent
  analogWrite(A0, nextOut);
  analogWrite(A1, nextOut);
  // Then we can take whatever variable time for processing the next cycle...

  if(++playbackIndex >= recBufSize) playbackIndex = 0;

  if(jumping) {
    // A waveform-blending transition is in-progress
    uint32_t w1 = 65536UL * jumpCount / jump, // ramp playbackIndexJumped up (14 bits)
             w2 = 65536UL - w1;               // ramp playbackIndex down (14 bits)
    nextOut = (recBuf[playbackIndexJumped] * w1 + recBuf[playbackIndex] * w2) >> 20; // 28 bit result->12 bits
    if(++jumpCount >= jump) {
      playbackIndex = playbackIndexJumped;
      jumpCount     = 1;
      jumping       = false;
    } else {
      if(++playbackIndexJumped >= recBufSize) playbackIndexJumped = 0;
    }
  } else {
    nextOut = recBuf[playbackIndex] >> 4; // 16->12 bit
    if(playbackRate >= sampleRate) { // Sped up
      // Playback may overtake recording, need to back off periodically
      int16_t dist = (recIndex >= playbackIndex) ?
        (recIndex - playbackIndex) : (recBufSize - (playbackIndex - recIndex));
      if(dist <= jumpThreshold) {
        playbackIndexJumped = playbackIndex - jump;
        if(playbackIndexJumped < 0) playbackIndexJumped += recBufSize;
        jumping             = true;
      }
    } else { // Slowed down
      // Playback may underflow recording, need to advance periodically
      int16_t dist = (playbackIndex >= recIndex) ?
        (playbackIndex - recIndex) : (recBufSize - 1 - (recIndex - playbackIndex));
      if(dist <= jumpThreshold) {
        playbackIndexJumped = (playbackIndex + jump) % recBufSize;
        jumping             = true;
      }
    }
  }
}

#endif // ADAFRUIT_MONSTER_M4SK_EXPRESS
