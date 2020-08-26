// "Make-Believe" sketch for Adafruit Circuit Playground.
// Lights and sounds react to motion and taps.

#include <Adafruit_CircuitPlayground.h>

// Enable ONE of these lines to select a theme:
//#include "knight.h" // Swoosh & clank metal sword
//#include "laser.h"  // MWAAAW! "laser" sword
#include "wand.h"   // Magic wand

void setup() {
  // Initialize Circuit Playground board, accelerometer, NeoPixels
  CircuitPlayground.begin();
  CircuitPlayground.setAccelRange(LIS3DH_RANGE_16_G);
  CircuitPlayground.strip.setBrightness(255); // Full brightness

  // Start default "idle" looping animation and sound
  playAnim( idlePixelData, idleFPS       , sizeof(idlePixelData), true);
  playSound(idleAudioData, idleSampleRate, sizeof(idleAudioData), true);
}

// Global values used by the animation and sound functions
uint16_t         *pixelBaseAddr, // Address of active animation table
                  pixelLen,      // Number of pixels in active table
                  pixelIdx,      // Index of first pixel of current frame
                  audioLen;      // Number of audio samples in active table
volatile uint16_t audioIdx;      // Index of current audio sample
uint8_t           pixelFPS,      // Frames/second for active animation
                 *audioBaseAddr; // Address of active sound table
boolean           pixelLoop,     // If true, animation repeats
                  audioLoop;     // If true, audio repeats

// Begin playing a sound from PROGMEM table (unless NULL)
void playSound(const uint8_t *addr, uint16_t rate, uint16_t len, boolean repeat) {
  audioBaseAddr = addr;
  if(addr) {
    CircuitPlayground.speaker.begin();
    audioLen  = len;
    audioLoop = repeat;
    audioIdx  = 0;
  
    // Timer/Counter 1 interrupt is used to play sound in background
    TCCR1A = 0;                           // Timer1: No PWM output
    TCCR1B = _BV(WGM12) | _BV(CS10);      // CTC mode, no prescale
    OCR1A  = (F_CPU + (rate / 2)) / rate; // Value for timer match
    TCNT1  = 0;                           // Reset counter
    TIMSK1 = _BV(OCIE1A);                 // Start interrupt
  } else {         // NULL addr = audio OFF
    TIMSK1 = 0;    // Stop interrupt
    while(OCR4A) { // Ease speaker into off position
      OCR4A--;     // to avoid audible 'pop' at end
      delayMicroseconds(3);
    }
    CircuitPlayground.speaker.end();
  }
}

// Timer/Counter 1 interrupt; periodically sets PWM speaker output from audio table
ISR(TIMER1_COMPA_vect) {
  OCR4A = pgm_read_byte(&audioBaseAddr[audioIdx]);
  if(++audioIdx >= audioLen) { // Past end of table?
    if(audioLoop) {       // Loop sound?
      audioIdx = 0;       // Reset counter to start of table
    } else {              // Don't loop...
      playSound(idleAudioData, idleSampleRate, sizeof(idleAudioData), true);
    }
  }
}

// Begin playing a NeoPixel animation from a PROGMEM table
void playAnim(const uint16_t *addr, uint8_t fps, uint16_t bytes, boolean repeat) {
  pixelBaseAddr = addr;
  if(addr) {
    pixelFPS    = fps;
    pixelLen    = bytes / 2;
    pixelLoop   = repeat;
    pixelIdx    = 0;
  } else {
    CircuitPlayground.strip.clear();
  }
}

uint32_t prev = 0; // Time of last NeoPixel refresh

void loop() {
  uint32_t t;      // Current time in milliseconds
  // Until the next animation frame interval has elapsed...
  while(((t = millis()) - prev) < (1000 / pixelFPS)) {
    // Read accelerometer, test for swing/tap thresholds
    float x = CircuitPlayground.motionX() / 9.8, // m/s2 to G
          y = CircuitPlayground.motionY() / 9.8,
          z = CircuitPlayground.motionZ() / 9.8,
          d = sqrt(x * x + y * y + z * z); // Acceleration magnitude in 3D
    d = fabs(d - 1.0); // Neutral is 1G; d is relative acceleration now
    if(d >= TAP_THRESHOLD) { // Big acceleration?
      if(audioBaseAddr != tapAudioData) { // If not already playing tap sound,
        // Start playing tap sound and animation
        playSound(tapAudioData, tapSampleRate, sizeof(tapAudioData), false);
        playAnim(tapPixelData, tapFPS, sizeof(tapPixelData), false);
      }
    } else if(d >= SWING_THRESHOLD) { // Medium acceleration?
      if(audioBaseAddr == idleAudioData) { // If not already swinging or tapping,
        // start playing swing sound and animation
        playSound(swingAudioData, swingSampleRate, sizeof(swingAudioData), false);
        playAnim(swingPixelData, swingFPS, sizeof(swingPixelData), false);
      }
    }
  }

  // Show LEDs rendered on prior pass.  It's done this way so animation timing
  // is a bit more consistent (frame rendering time may vary slightly).
  CircuitPlayground.strip.show();
  prev = t; // Save refresh time for next frame sync

  if(pixelBaseAddr) {
    for(uint8_t i=0; i<10; i++) { // For each NeoPixel...
      // Read pixel color from PROGMEM table
      uint16_t rgb = pgm_read_word(&pixelBaseAddr[pixelIdx++]);
      // Expand 16-bit color to 24 bits using gamma tables
      // RRRRRGGGGGGBBBBB -> RRRRRRRR GGGGGGGG BBBBBBBB
      CircuitPlayground.strip.setPixelColor(i,
        pgm_read_byte(&gamma5[ rgb >> 11        ]),
        pgm_read_byte(&gamma6[(rgb >>  5) & 0x3F]),
        pgm_read_byte(&gamma5[ rgb        & 0x1F]));
    }
  
    if(pixelIdx >= pixelLen) { // End of animation table reached?
      if(pixelLoop) { // Repeat animation?
        pixelIdx = 0; // Reset index to start of table
      } else {        // else switch back to "idle" animation
        playAnim(idlePixelData, idleFPS, sizeof(idlePixelData), true);
      }
    }
  }
}
