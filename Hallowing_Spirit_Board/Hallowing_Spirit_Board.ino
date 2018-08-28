// "Spirit Board" plaything for Adafruit Hallowing.  Uses DMA and related
// shenanigans to smoothly scroll around a large image.  Use the capacitive
// touch pads to get a random "spirit reading."  Ooooo...spooky!

#include <Adafruit_LIS3DH.h>
#include <Adafruit_FreeTouch.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <Adafruit_ZeroDMA.h>
#include "graphics.h"
#include "messages.h"         // List of "spirit reading" messages is here!

#define TFT_CS           39   // Hallowing display control pins: chip select
#define TFT_RST          37   // Display reset
#define TFT_DC           38   // Display data/command select
#define TFT_BACKLIGHT     7   // Display backlight pin

// A small finite-state machine toggles the software through various actions:
#define STATE_SCROLL      0   // Fidgeting around with accelerometer
#define STATE_CHAR_DIRECT 1   // Straight line to next character in message
#define STATE_CHAR_CIRCLE 2   // Repeating character; moves in a small circle
#define STATE_CHAR_PAUSE  3   // Pause between words

uint8_t state = STATE_SCROLL; // Initial state = scrolling

// Declarations for various Hallowing hardware -- display, accelerometer and
// capacitive touch pads.
Adafruit_ST7735    tft    = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_RST);
Adafruit_LIS3DH    accel  = Adafruit_LIS3DH();
Adafruit_FreeTouch pads[] = {
  Adafruit_FreeTouch(A2, OVERSAMPLE_4, RESISTOR_50K, FREQ_MODE_NONE),
  Adafruit_FreeTouch(A3, OVERSAMPLE_4, RESISTOR_50K, FREQ_MODE_NONE),
  Adafruit_FreeTouch(A4, OVERSAMPLE_4, RESISTOR_50K, FREQ_MODE_NONE),
  Adafruit_FreeTouch(A5, OVERSAMPLE_4, RESISTOR_50K, FREQ_MODE_NONE)
};

// Declarations related to DMA (direct memory access), which lets us walk
// and chew gum at the same time.  This is VERY specific to SAMD chips and
// means this is not trivially ported to other devices.
Adafruit_ZeroDMA  dma;
DmacDescriptor   *descriptor;
uint16_t          dmaBuf[2][128];
uint8_t           dmaIdx = 0; // Active DMA buffer # (alternate fill/send)

// DMA transfer-in-progress indicator and callback
static volatile bool dma_busy = false;
static void dma_callback(Adafruit_ZeroDMA *dma) {
  dma_busy = false;
}

// Sundry other global declarations

// (x,y) is the coordinate of the top-left pixel of the display relative to
// the larger board image that we'll be scrolling around.  Units are 16X the
// pixel grid, to allow for smoother subpixel scrolling off cardinal axes.
int         x = (BOARD_WIDTH  / 2 - 64) * 16,
            y = (BOARD_HEIGHT / 2 - 64) * 16,
            vX = 0, vY = 0;       // X & Y velocity when in manual SCROLL mode
uint8_t     messageNum,           // Index of message being "read"
            messageCharNum,       // Index of character within current message
            lastNonSpaceChar,     // Value of last character that's not a space
            backlight_prev = 160; // For candle flicker backlight effect
uint32_t    startTime;            // Start time of character-to-character motion
int16_t     startX, startY,       // Start & end positions when moving character-
            endX, endY,           // to-character (same coord sys as x & y).
            circleX, circleY;     // Center of motion when repeating character
float       angle, radius;        // Initial angle, distance for repeat circle
SPISettings settings(12000000, MSBFIRST, SPI_MODE0);

// SETUP FUNCTION -- runs once at startup ----------------------------------

void setup(void) {
  randomSeed(analogRead(A4));

  // Hardware init -- display, backlight, accelerometer, capacitive touch pads
  tft.initR(INITR_144GREENTAB);
  tft.setRotation(2); // Display is rotated 180° on Hallowing
  tft.fillScreen(0);

  pinMode(TFT_BACKLIGHT, OUTPUT);
  analogWriteResolution(8);

  if(accel.begin(0x18) || accel.begin(0x19)) {
    accel.setRange(LIS3DH_RANGE_2_G);
  }

  for(uint8_t i=0; i<4; i++) pads[i].begin();

  // Set up SPI DMA.  While the Hallowing has a known SPI peripheral and this
  // could be much simpler, the extra code here will help if adapting this
  // sketch to other SAMD boards (Feather M0, M4, etc.)
  int                dmac_id;
  volatile uint32_t *data_reg;
  dma.allocate();
  if(&PERIPH_SPI == &sercom0) {
    dma.setTrigger(SERCOM0_DMAC_ID_TX);
    data_reg = &SERCOM0->SPI.DATA.reg;
#if defined SERCOM1
  } else if(&PERIPH_SPI == &sercom1) {
    dma.setTrigger(SERCOM1_DMAC_ID_TX);
    data_reg = &SERCOM1->SPI.DATA.reg;
#endif
#if defined SERCOM2
  } else if(&PERIPH_SPI == &sercom2) {
    dma.setTrigger(SERCOM2_DMAC_ID_TX);
    data_reg = &SERCOM2->SPI.DATA.reg;
#endif
#if defined SERCOM3
  } else if(&PERIPH_SPI == &sercom3) {
    dma.setTrigger(SERCOM3_DMAC_ID_TX);
    data_reg = &SERCOM3->SPI.DATA.reg;
#endif
#if defined SERCOM4
  } else if(&PERIPH_SPI == &sercom4) {
    dma.setTrigger(SERCOM4_DMAC_ID_TX);
    data_reg = &SERCOM4->SPI.DATA.reg;
#endif
#if defined SERCOM5
  } else if(&PERIPH_SPI == &sercom5) {
    dma.setTrigger(SERCOM5_DMAC_ID_TX);
    data_reg = &SERCOM5->SPI.DATA.reg;
#endif
  }
  dma.setAction(DMA_TRIGGER_ACTON_BEAT);
  descriptor = dma.addDescriptor(
    NULL,               // move data
    (void *)data_reg,   // to here
    sizeof dmaBuf[0],   // this many...
    DMA_BEAT_SIZE_BYTE, // bytes/hword/words
    true,               // increment source addr?
    false);             // increment dest addr?
  dma.setCallback(dma_callback);
}

// LOOP FUNCTION -- repeats indefinitely -----------------------------------

void loop(void) {
  // This just picks a random backlight intensity then starts a fractal
  // subdivision (in the split() function) to make a candle flicker effect.
  // split(), in turn, calls further functions that handle input and update
  // the display...
  uint8_t backlight_next = random(128, 192);
  split(backlight_prev, backlight_next, 32);
  backlight_prev = backlight_next;
}

void split(uint8_t v1, uint8_t v2, uint8_t offset) {
 if(offset > 2) { // Split further into sub-segments w/midpoint at ±offset
    uint8_t mid = (v1 + v2 + 1) / 2 + random(-offset, offset);
    split(v1 , mid, offset / 2); // First segment (offset is halved)
    split(mid, v2 , offset / 2); // Second segment (ditto)
  } else { // No further subdivision; v1 determines LED brightness
    // But first, some gamma correction...
    v1 = (uint8_t)(pow((float)v1 / 255.0, 2.2) * 255.0 + 0.5);
    analogWrite(TFT_BACKLIGHT, v1);
    // We'll reach this point in the code at equal-ish intervals along the
    // fractalization process, so it's as good a time as any to process input
    // and render a new frame...
    processFrame();
  }
}

// Handle one iteration of the finite state machine
void processFrame(void) {

  if(state == STATE_SCROLL) {         // Manual scrolling mode?

    accel.read();                     // Read accelerometer
    vX += accel.y / 512;              // Horizontal scroll from accel. Y
    if(abs(accel.x) < abs(accel.z)) { // If device is sitting flat(ish),
      vY -= accel.x / 512;            // Use accel X for vertical scroll
    } else {                          // Else held upright(ish),
      vY += accel.z / 256;            // Use accel Z for vertical scroll
    }
    if(vX >  128) vX =  128;          // Limit scrolling velocity
    if(vX < -128) vX = -128;          // (units are 1/16 pixel, so 128
    if(vY >  128) vY =  128;          //  equals 8 pixels max).
    if(vY < -128) vY = -128;
    x += vX;                          // Add velocity to position
    y += vY;
    // Constrain position so we don't scroll off the edges of the board...
    if(x >= (BOARD_WIDTH - PLANCHETTE_WIDTH) * 16) {   // Right edge
      x  =  (BOARD_WIDTH - PLANCHETTE_WIDTH) * 16;
      vX = 0;
    } else if(x < 0) {                                 // Left edge
      x  = 0;
      vX = 0;
    }
    if(y >= (BOARD_HEIGHT - PLANCHETTE_HEIGHT) * 16) { // Bottom edge
      y  =  (BOARD_HEIGHT - PLANCHETTE_HEIGHT) * 16;
      vY = 0;
    } else if(y < 0) {                                 // Top edge
      y  = 0;
      vY = 0;
    }

    // If ANY of capacitive pads are touched while in scrolling mode...
    if(anyTouch()) {
      state            = STATE_CHAR_DIRECT;    // Now in go-to-character mode
      messageNum       = random(NUM_MESSAGES); // Pick a random message
      messageCharNum   = 0;                    // And start at the 1st char
      lastNonSpaceChar = 0;
      startTime        = micros();             // Note the starting time
      startX           = x;                    // and position for
      startY           = y;                    // go-to-character motion
      setupMotionEnd();                        // Initializes endX, endY
    }

  } else { // NOT in scrolling mode, one of the go-to-character states

    uint32_t currentTime = micros(), // Get time since startTime
             elapsed     = currentTime - startTime;

    if(elapsed >= 1250000) {         // If over 1.25 seconds...
      x = startX = endX;             // Advance to next character...
      y = startY = endY;
      startTime  = currentTime;
      messageCharNum++;
      uint8_t c = messages[messageNum][messageCharNum]; // New char
      if(c == 0) {                       // If end of string,
        state = STATE_SCROLL;            // go back to manual scroll mode
      } else if(c == ' ') {              // If space
        state      = STATE_CHAR_PAUSE;   // Hold steady for a moment,
        startTime -= 300000;             // but not a full char interval
      } else if(c == lastNonSpaceChar) { // If repeating the same character...
        // The cursor is moved in a small circular motion to return to the
        // same character, to emphasize that it's being repeated.
        state   = STATE_CHAR_CIRCLE;
        // In order to avoid scrolling off the board, the circular motion
        // is always toward the board center.  Save that direction:
        angle   = atan2(BOARD_HEIGHT * 8 - endY, BOARD_WIDTH * 8 - endX);
        radius  = random(150, 350);                 // Semi-random size
        circleX = endX + cos(angle) * radius + 0.5; // Center of motion
        circleY = endY + sin(angle) * radius + 0.5;
      } else { // NOT space or repeating char...new destination...
        state            = STATE_CHAR_DIRECT;
        lastNonSpaceChar = c;
        setupMotionEnd(); // Sets up endX, endY for linear motion
      }
    } else { // Still within 1.25 sec motion period
      if(state == STATE_CHAR_PAUSE) {
        // If in pause state, just do nothing!
      } else {
        // Last 1/4 second is a pause at end position.  So we really only
        // do work during the initial 1 second (1M microseconds), else
        // hold at the end position.
        if(elapsed > 1000000) elapsed = 1000000;
        float t = (float)elapsed / 1000000.0; // Linear motion 0.0-1.0
        t = t * t * 3.0 - t * t * t * 2.0;    // Apply ease in/out curve
        if(state == STATE_CHAR_CIRCLE) {      // Same-char circular motion
          t *= M_PI * 2.0; // 0.0-1.0 -> 0-360 degrees
          x  = (int)(circleX - cos(angle + t) * radius + 0.5);
          y  = (int)(circleY - sin(angle + t) * radius + 0.5);
        } else {                              // New char straight-line motion
          x  = (int)(startX + (endX - startX) * t + 0.5);
          y  = (int)(startY + (endY - startY) * t + 0.5);
        }
      }
    }
  }

  drawFrame(x / 16, y / 16); // Redraw screen at new (x, y) position
}

// Any cap sense pads touched?  Returns true if ANY, doesn't distinguish.
boolean anyTouch(void) {
  for(uint8_t i=0; i<4; i++) {
    if(pads[i].measure() > 700) return true;
  }
  return false;
}

// Initialize endX and endY based on the current messageCharNum.  This is
// done in a couple places in processFrame(), so is functionalized here...
// most of the inputs and outputs are existing global vars.
void setupMotionEnd(void) {
  int8_t n = getCoordIndex(messages[messageNum][messageCharNum]);
  if(n < 0) return; // Unknown character, do nothing!
  endX = (coord[n].x - 64) * 16; // Upper-left corner of screen
  endY = (coord[n].y - 64) * 16; // relative to character's center coord
  if(endX >= (BOARD_WIDTH - PLANCHETTE_WIDTH) * 16) { // Stay in bounds!
     endX  = (BOARD_WIDTH - PLANCHETTE_WIDTH) * 16;
  } else if(endX < 0) {
    endX   = 0;
  }
  if(endY >= (BOARD_HEIGHT - PLANCHETTE_HEIGHT) * 16) {
     endY  = (BOARD_HEIGHT - PLANCHETTE_HEIGHT) * 16;
  } else if(endY < 0) {
    endY   = 0;
  }
}

// Given an ASCII character, return the corresponding index in the coord[]
// array, or -1 if no matching character.  Only A-Z and 0-9 are supported,
// there's no punctuation on the spirit board!
int8_t getCoordIndex(uint8_t c) {
  c = toupper(c);
  if((c >= 'A') && (c <= 'Z')) return  c - 'A';
  if((c >= '0') && (c <= '9')) return (c - '0') + 26;
  if((c >=  1 ) && (c <=  6 )) return  c + 35; // Yes, no, etc.
  return -1; // Not in table
}

// Draw a single full frame of animation.  (x,y) represent the planchette's
// top-left pixel coordinate over the larger board image.  NO clipping or
// bounds-checking is performed...the given position must be in a valid range.
// Aside from DMA, it's just brute force...every pixel of every frame is
// computed.
void drawFrame(int x, int y) {
  uint32_t  // Graphics data, each 32-bit value holds 16 pixels (2 bits/pixel):
  *planchettePtr,  // Pointer into planchette graphics array
  *boardPtr,       // Pointer into board graphics array
  planchetteWord, // Current 16 pixel block of planchette gfx data
  boardWord;      // Current 16 pixel block of board graphics data
  uint16_t *dmaPtr;         // Pointer into DMA output buffer (16 bits/pixel)
  uint8_t   row,            // Current row along screen (top to bottom)
            col,            // Current column along screen (left to right)
            c16,            // Column # (0 to 15) within 16-pixel block
            bc,             // c16 value when boardWord value gets reloaded
            idx;            // Color palette index (2 bits/pixel = 0 to 3)

  SPI.beginTransaction(settings);    // SPI init
  digitalWrite(TFT_CS, LOW);         // Chip select
  tft.setAddrWindow(0, 0, 128, 128); // Set address window to full screen
  digitalWrite(TFT_CS, LOW);         // Re-select after addr function
  digitalWrite(TFT_DC, HIGH);        // Data mode...

  bc = 15 - (x & 15);
  for(row = 0; row < PLANCHETTE_HEIGHT; row++) { // For each row...
    // Set up source and destination pointers:
    planchettePtr = (uint32_t *)&planchetteData[
                      row * ((PLANCHETTE_WIDTH + 15) / 16)];
    boardPtr      = (uint32_t *)&boardData[
                      (y + row) * ((BOARD_WIDTH + 15) / 16) + (x / 16)];
    dmaPtr        = &dmaBuf[dmaIdx][0];
    // Initial boardWord value depends on starting column:
    boardWord     = *boardPtr++ >> ((15 - bc) * 2);
    for(col = 0; col < PLANCHETTE_WIDTH; col++) { // For each column...
      c16 = col & 15; // Column # (0-15) within 16-pixel block
      // On first pixel of block, reload planchetteWord, increment pointer:
      if(c16 == 0)  planchetteWord = *planchettePtr++;
      if((idx = (planchetteWord & 3))) {    // Color indices 1-3 are opaque,
        *dmaPtr++ = planchettePalette[idx]; // use planchettePalette color
      } else {                              // Color index 0 is transparent,
        *dmaPtr++ = boardPalette[boardWord & 3]; // use boardPalette color
      }
      planchetteWord >>= 2;                    // Shift down 2 bits/pixel
      if(c16 != bc) boardWord >>= 2;           // Same with board graphics,
      else          boardWord   = *boardPtr++; // except periodic reload
    }
    while(dma_busy);          // Wait for prior DMA transfer to finish
    // Set up DMA transfer from the newly-filled scan line buffer:
    descriptor->SRCADDR.reg = (uint32_t)&dmaBuf[dmaIdx] + sizeof dmaBuf[0];
    dma_busy = true;          // Mark as busy (DMA callback clears this)
    dma.startJob();           // Start new DMA transfer
    dmaIdx = 1 - dmaIdx;      // Swap DMA buffers
  }

  while(dma_busy);            // Wait for last DMA transfer to complete
  digitalWrite(TFT_CS, HIGH); // Deselect
  SPI.endTransaction();       // SPI done
}
