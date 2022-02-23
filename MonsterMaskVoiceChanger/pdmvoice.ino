// SPDX-FileCopyrightText: 2019 Phillip Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Basic voice changer code. This version is specific to the Adafruit
// MONSTER M4SK board using a PDM microphone.

#include <SPI.h>

#define MIN_PITCH_HZ   65
#define MAX_PITCH_HZ 1600
#define TYP_PITCH_HZ  175

// Playback timer stuff - use TC3 on MONSTER M4SK (no TC4 on this board)
#define TIMER             TC3
#define TIMER_IRQN        TC3_IRQn
#define TIMER_IRQ_HANDLER TC3_Handler
#define TIMER_GCLK_ID     TC3_GCLK_ID
#define TIMER_GCM_ID      GCM_TC2_TC3

// PDM mic allows 1.0 to 3.25 MHz max clock (2.4 typical).
// SPI native max is is 24 MHz, so available speeds are 12, 6, 3 MHz.
#define SPI_BITRATE 3000000
static SPISettings settings(SPI_BITRATE, LSBFIRST, SPI_MODE0);
// 3 MHz / 32 bits = 93,750 Hz interrupt frequency
// 2 interrupts/sample = 46,875 Hz audio sample rate
const float sampleRate = (float)SPI_BITRATE / 64.0;
// sampleRate is float in case factors change to make it not divide evenly.
// It DOES NOT CHANGE over time, only playbackRate does.

// Although SPI lib now has an option to get an SPI object's SERCOM number
// at run time, the interrupt handler MUST be declared at compile time...
// so it's necessary to know the SERCOM # ahead of time anyway, oh well.
#define PDM_SERCOM         SERCOM3 // PDM mic SPI SERCOM on MONSTER M4SK
#define PDM_SPI            SPI2    // PDM mic SPI peripheral
#define PDM_SERCOM_HANDLER SERCOM3_0_Handler
#define PDM_SERCOM_IRQn    SERCOM3_0_IRQn // _0_IRQn is DRE interrupt

static Sercom            *sercom;
static volatile uint32_t *dataReg;

Sercom * const sercomList[] = {
  SERCOM0, SERCOM1, SERCOM2, SERCOM3,
#if defined(SERCOM4)
  SERCOM4,
#endif
#if defined(SERCOM5)
  SERCOM5,
#endif
#if defined(SERCOM6)
  SERCOM6,
#endif
#if defined(SERCOM7)
  SERCOM7,
#endif
};

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

volatile uint16_t     voiceLastReading = 0;

#define DC_PERIOD     4096 // Recalculate DC offset this many samplings
// DC_PERIOD does NOT need to be a power of 2, but might save a few cycles.
// PDM rate is 46875, so 4096 = 11.44 times/sec
static uint16_t       dcCounter        = 0;     // Rolls over every DC_PERIOD samples
static uint32_t       dcSum            = 0;     // Accumulates DC_PERIOD samples
static uint16_t       dcOffsetPrior    = 32768; // DC offset interpolates linearly
static uint16_t       dcOffsetNext     = 32768; // between these two values

static uint16_t       micGain          = 256;   // 1:1

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

bool voiceSetup(void) {

  // Allocate circular buffer for audio
  if(NULL == (recBuf = (uint16_t *)malloc(recBufSize * sizeof(uint16_t)))) {
    return false; // Fail
  }

  // Set up PDM microphone input -------------------------------------------

  PDM_SPI.begin();
  PDM_SPI.beginTransaction(settings); // this SPI transaction is left open
  sercom  = sercomList[PDM_SPI.getSercomIndex()];
  dataReg = PDM_SPI.getDataRegister();

  // Enabling 32-bit SPI must be done AFTER SPI.begin() which
  // resets registers. But SPI.CTRLC (where 32-bit mode is set) is
  // enable-protected, so peripheral must be disabled temporarily...
  sercom->SPI.CTRLA.bit.ENABLE  = 0;      // Disable SPI
  while(sercom->SPI.SYNCBUSY.bit.ENABLE); // Wait for disable
  sercom->SPI.CTRLC.bit.DATA32B = 1;      // Enable 32-bit mode
  sercom->SPI.CTRLA.bit.ENABLE  = 1;      // Re-enable SPI
  while(sercom->SPI.SYNCBUSY.bit.ENABLE); // Wait for enable
  // 4-byte word length is implicit in 32-bit mode,
  // no need to set up LENGTH register.

  sercom->SPI.INTENSET.bit.DRE  = 1;      // Data-register-empty interrupt
  NVIC_DisableIRQ(PDM_SERCOM_IRQn);
  NVIC_ClearPendingIRQ(PDM_SERCOM_IRQn);
  NVIC_SetPriority(PDM_SERCOM_IRQn, 0);   // Top priority
  NVIC_EnableIRQ(PDM_SERCOM_IRQn);

  sercom->SPI.DATA.bit.DATA     = 0;      // Kick off SPI free-run

  // Set up analog output & timer ------------------------------------------

  analogWriteResolution(12);

  // Feed TIMER off GCLK1 (already set to 48 MHz by Arduino core)
  GCLK->PCHCTRL[TIMER_GCLK_ID].bit.CHEN = 0;     // Disable channel
  while(GCLK->PCHCTRL[TIMER_GCLK_ID].bit.CHEN);  // Wait for disable
  GCLK_PCHCTRL_Type pchctrl;
  pchctrl.bit.GEN                       = GCLK_PCHCTRL_GEN_GCLK1_Val;
  pchctrl.bit.CHEN                      = 1;
  GCLK->PCHCTRL[TIMER_GCLK_ID].reg      = pchctrl.reg;
  while(!GCLK->PCHCTRL[TIMER_GCLK_ID].bit.CHEN); // Wait for enable

  // Disable timer before configuring it
  TIMER->COUNT16.CTRLA.bit.ENABLE       = 0;
  while(TIMER->COUNT16.SYNCBUSY.bit.ENABLE);

  // 16-bit counter mode, 1:1 prescale, match-frequency generation mode
  TIMER->COUNT16.CTRLA.bit.MODE      = TC_CTRLA_MODE_COUNT16;
  TIMER->COUNT16.CTRLA.bit.PRESCALER = TC_CTRLA_PRESCALER_DIV1_Val;
  TIMER->COUNT16.WAVE.bit.WAVEGEN    = TC_WAVE_WAVEGEN_MFRQ_Val;

  TIMER->COUNT16.CTRLBCLR.reg        = TC_CTRLBCLR_DIR; // Count up
  while(TIMER->COUNT16.SYNCBUSY.bit.CTRLB);

  voicePitch(1.0); // Set timer interval

  TIMER->COUNT16.INTENSET.reg        = TC_INTENSET_OVF; // Overflow interrupt
  NVIC_DisableIRQ(TIMER_IRQN);
  NVIC_ClearPendingIRQ(TIMER_IRQN);
  NVIC_SetPriority(TIMER_IRQN, 0); // Top priority
  NVIC_EnableIRQ(TIMER_IRQN);

  TIMER->COUNT16.CTRLA.bit.ENABLE    = 1;    // Enable timer
  while(TIMER->COUNT16.SYNCBUSY.bit.ENABLE); // Wait for it

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
  int32_t period = (int32_t)(48000000.0 / desiredPlaybackRate + 0.5);
  if(period > 2500)     period = 2500; // Hard limit is 65536, 2.5K is a practical limit
  else if(period < 250) period =  250; // Leave some cycles for IRQ handler
  TIMER->COUNT16.CC[0].reg = period - 1;
  while(TIMER->COUNT16.SYNCBUSY.bit.CC0);
  float   actualPlaybackRate = 48000000.0 / (float)period;
  p = (actualPlaybackRate / sampleRate); // New pitch
  jumpThreshold = (int)(jump * p + 0.5);
  return p;
}

// SET GAIN ----------------------------------------------------------------

void voiceGain(float g) {
  if(g >= (65535.0/256.0)) micGain = 65535;
  else if(g < 0.0)         micGain = 0;
  else                     micGain = (uint16_t)(g * 256.0 + 0.5);
}

// INTERRUPT HANDLERS ------------------------------------------------------

static uint16_t const sincfilter[64] = { 0, 2, 9, 21, 39, 63, 94, 132, 179, 236, 302, 379, 467, 565, 674, 792, 920, 1055, 1196, 1341, 1487, 1633, 1776, 1913, 2042, 2159, 2263, 2352, 2422, 2474, 2506, 2516, 2506, 2474, 2422, 2352, 2263, 2159, 2042, 1913, 1776, 1633, 1487, 1341, 1196, 1055, 920, 792, 674, 565, 467, 379, 302, 236, 179, 132, 94, 63, 39, 21, 9, 2, 0, 0 };

void PDM_SERCOM_HANDLER(void) {
  static bool     evenWord = 1; // Alternates 0/1 with each interrupt call
  static uint32_t sumTemp  = 0; // Temp. value used across 2 interrupt calls
  // Shenanigans: SPI data read/write are shadowed...even though it appears
  // the same register here, it's legit to write new MOSI value before
  // reading the received MISO value from the same location. This helps
  // avoid a gap between words...provides a steady stream of bits.
  *dataReg = 0;               // Write clears DRE flag, starts next xfer
  uint32_t sample = *dataReg; // Read last-received word

  uint32_t sum = 0;  // local var = register = faster than sumTemp
  if(evenWord) {     // Even-numbered 32-bit word...
    // At default speed and optimization settings (120 MHz -Os), the PDM-
    // servicing interrupt consumes about 12.5% of CPU time. Though this
    // code looks bulky, it's actually reasonably efficient (sincfilter[] is
    // const, so these compile down to constants, there is no array lookup,
    // any any zero-value element refs will be removed by the compiler).
    // Tested MANY methods and this was hard to beat. One managed just under
    // 10% load, but required 4KB of tables...not worth it for small boost.
    // Can get an easy boost with overclock and optimizer tweaks.
    if(sample & 0x00000001) sum += sincfilter[ 0];
    if(sample & 0x00000002) sum += sincfilter[ 1];
    if(sample & 0x00000004) sum += sincfilter[ 2];
    if(sample & 0x00000008) sum += sincfilter[ 3];
    if(sample & 0x00000010) sum += sincfilter[ 4];
    if(sample & 0x00000020) sum += sincfilter[ 5];
    if(sample & 0x00000040) sum += sincfilter[ 6];
    if(sample & 0x00000080) sum += sincfilter[ 7];
    if(sample & 0x00000100) sum += sincfilter[ 8];
    if(sample & 0x00000200) sum += sincfilter[ 9];
    if(sample & 0x00000400) sum += sincfilter[10];
    if(sample & 0x00000800) sum += sincfilter[11];
    if(sample & 0x00001000) sum += sincfilter[12];
    if(sample & 0x00002000) sum += sincfilter[13];
    if(sample & 0x00004000) sum += sincfilter[14];
    if(sample & 0x00008000) sum += sincfilter[15];
    if(sample & 0x00010000) sum += sincfilter[16];
    if(sample & 0x00020000) sum += sincfilter[17];
    if(sample & 0x00040000) sum += sincfilter[18];
    if(sample & 0x00080000) sum += sincfilter[19];
    if(sample & 0x00100000) sum += sincfilter[20];
    if(sample & 0x00200000) sum += sincfilter[21];
    if(sample & 0x00400000) sum += sincfilter[22];
    if(sample & 0x00800000) sum += sincfilter[23];
    if(sample & 0x01000000) sum += sincfilter[24];
    if(sample & 0x02000000) sum += sincfilter[25];
    if(sample & 0x04000000) sum += sincfilter[26];
    if(sample & 0x08000000) sum += sincfilter[27];
    if(sample & 0x10000000) sum += sincfilter[28];
    if(sample & 0x20000000) sum += sincfilter[29];
    if(sample & 0x40000000) sum += sincfilter[30];
    if(sample & 0x80000000) sum += sincfilter[31];
    sumTemp = sum; // Copy register to static var for next call
  } else {
    if(sample & 0x00000001) sum += sincfilter[32];
    if(sample & 0x00000002) sum += sincfilter[33];
    if(sample & 0x00000004) sum += sincfilter[34];
    if(sample & 0x00000008) sum += sincfilter[35];
    if(sample & 0x00000010) sum += sincfilter[36];
    if(sample & 0x00000020) sum += sincfilter[37];
    if(sample & 0x00000040) sum += sincfilter[38];
    if(sample & 0x00000080) sum += sincfilter[39];
    if(sample & 0x00000100) sum += sincfilter[40];
    if(sample & 0x00000200) sum += sincfilter[41];
    if(sample & 0x00000400) sum += sincfilter[42];
    if(sample & 0x00000800) sum += sincfilter[43];
    if(sample & 0x00001000) sum += sincfilter[44];
    if(sample & 0x00002000) sum += sincfilter[45];
    if(sample & 0x00004000) sum += sincfilter[46];
    if(sample & 0x00008000) sum += sincfilter[47];
    if(sample & 0x00010000) sum += sincfilter[48];
    if(sample & 0x00020000) sum += sincfilter[49];
    if(sample & 0x00040000) sum += sincfilter[50];
    if(sample & 0x00080000) sum += sincfilter[51];
    if(sample & 0x00100000) sum += sincfilter[52];
    if(sample & 0x00200000) sum += sincfilter[53];
    if(sample & 0x00400000) sum += sincfilter[54];
    if(sample & 0x00800000) sum += sincfilter[55];
    if(sample & 0x01000000) sum += sincfilter[56];
    if(sample & 0x02000000) sum += sincfilter[57];
    if(sample & 0x04000000) sum += sincfilter[58];
    if(sample & 0x08000000) sum += sincfilter[59];
    if(sample & 0x10000000) sum += sincfilter[60];
    if(sample & 0x20000000) sum += sincfilter[61];
    if(sample & 0x40000000) sum += sincfilter[62];
    if(sample & 0x80000000) sum += sincfilter[63];
    sum += sumTemp; // Add static var from last call

    // 'sum' is new raw audio value -- process it --------------------------

    uint16_t dcOffset;
  
    dcSum += sum; // Accumulate long-term average for DC offset correction
    if(++dcCounter < DC_PERIOD) {
      // Interpolate between dcOffsetPrior and dcOffsetNext
      dcOffset = dcOffsetPrior + (dcOffsetNext - dcOffsetPrior) * dcCounter / DC_PERIOD;
    } else {
      // End of period reached, move 'next' to 'previous,' calc new 'next' from avg
      dcOffsetPrior = dcOffset = dcOffsetNext;
      dcOffsetNext  = dcSum / DC_PERIOD;
      dcCounter     = dcSum    = 0;
    }

    // Adjust raw reading by DC offset to center (ish) it, scale by mic gain
    int32_t adjusted = ((int32_t)sum - dcOffset) * micGain / 256;

    // Go back to uint16_t space and clip to 16-bit range
    adjusted += 32768;
    if(adjusted > 65535)  adjusted = 65535;
    else if(adjusted < 0) adjusted = 0;

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
    recBuf[recIndex] = adjusted;

    // Outside code can use the value of voiceLastReading if you want to
    // do an approximate live waveform display, or dynamic gain adjustment
    // based on mic input, or other stuff. This won't give you every single
    // sample in the recording buffer one-by-one sequentially...it's just
    // the last thing that was stored prior to whatever time you polled it,
    // but may still have some uses.
    voiceLastReading = adjusted;
  }
  evenWord ^= 1;
}

// Playback timer interrupt
void TIMER_IRQ_HANDLER(void) {
  TIMER->COUNT16.INTFLAG.reg = TC_INTFLAG_OVF;

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
        (playbackIndex - recIndex) : (recBufSize - (recIndex - playbackIndex));
      if(dist <= jumpThreshold) {
        playbackIndexJumped = (playbackIndex + jump) % recBufSize;
        jumping             = true;
      }
    }
  }
}
