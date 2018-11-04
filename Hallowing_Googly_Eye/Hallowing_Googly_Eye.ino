// "Googly eye" demo for Adafruit Hallowing.  Uses accelerometer for
// motion plus DMA and related shenanigans for smooth animation.

#include <Adafruit_LIS3DH.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include <Adafruit_ZeroDMA.h>
#include "graphics.h"

#define G_SCALE       45.0  // Accel scale; no science, just looks good
#define ELASTICITY     0.86  // Edge-bounce coefficient (MUST be <1.0!)
#define DRAG           0.98 // Dampens motion slightly

#define EYE_RADIUS    64.0  // Radius of eye, floating-point pixel units
#define PUPIL_RADIUS  (PUPIL_SIZE / 2.0)  // Radius of pupil, same units
// Pupil motion is computed as a single point constrained within a circle
// whose radius is the eye radius minus the pupil radius.
#define INNER_RADIUS (EYE_RADIUS - PUPIL_RADIUS)

#define TFT_CS        39    // Hallowing display control pins: chip select
#define TFT_RST       37    // Display reset
#define TFT_DC        38    // Display data/command select
#define TFT_BACKLIGHT  7    // Display backlight pin

// For the sake of math comprehension and simplicity, movement takes place
// in a traditional Cartesian coordinate system (+Y is up), floating point
// values, grid units equal to pixels, with (0.0, 0.0) at the literal center
// of the screen (e.g. between pixels 63 and 64).  Things get flipped to
// +Y down integer pixel units just before drawing.
float    x  = 0.0, y  = 0.0, // Pupil position, start at center
         vx = 0.0, vy = 0.0; // Pupil velocity (X,Y components)
uint32_t lastTime;           // Last-rendered frame time, microseconds
bool     firstFrame = true;  // Force full-screen update on initial frame

// Declarations for various Hallowing hardware -- display, accelerometer
// and SPI rate & mode.
Adafruit_ST7735 tft    = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_RST);
Adafruit_LIS3DH accel  = Adafruit_LIS3DH();
SPISettings settings(12000000, MSBFIRST, SPI_MODE0);

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

// SETUP FUNCTION -- runs once at startup ----------------------------------

void setup(void) {
  // Hardware init
  tft.initR(INITR_144GREENTAB);
  tft.setRotation(2); // Display is rotated 180° on Hallowing
  tft.fillScreen(0);

  pinMode(TFT_BACKLIGHT, OUTPUT);
  analogWriteResolution(8);

  if(accel.begin(0x18) || accel.begin(0x19)) {
    accel.setRange(LIS3DH_RANGE_4_G);
  }

  // Set up SPI DMA.  While the Hallowing has a known SPI peripheral and
  // this could be much simpler, the extra code here will help if adapting
  // the sketch to other SAMD boards (Feather M0, M4, etc.)
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

  analogWrite(TFT_BACKLIGHT, 255);
  lastTime = micros();
}

// LOOP FUNCTION -- repeats indefinitely -----------------------------------

void loop(void) {
  accel.read();

  // Get time since last frame, in floating-point seconds
  uint32_t t       = micros();
  float    elapsed = (float)(t - lastTime) / 1000000.0;
  lastTime = t;

  // Scale accelerometer readings based on an empirically-derived constant
  // (i.e. looks good, nothing scientific) and time since prior frame.
  // On HalloWing, accelerometer's Y axis is horizontal, X axis is vertical,
  // (vs screen's and conventional Cartesian coords being X horizontal,
  // Y vertical), so swap while we're here, store in ax, ay;
  float scale = G_SCALE * elapsed;
  float ax = accel.y_g * scale, // Horizontal acceleration, pixel units
        ay = accel.x_g * scale; // Vertical acceleration "

  // Add scaled accelerometer readings to pupil velocity, store interim
  // values in vxNew, vyNew...a little friction prevents infinite bounce.
  float vxNew = (vx + ax) * DRAG,
        vyNew = (vy + ay) * DRAG;

  // Add new velocity to prior position, store interim in xNew, yNew;
  float xNew = x + vxNew,
        yNew = y + vyNew;

  // Get pupil position (center point) distance-squared from origin...
  // here's why we put (0,0) at the center...
  float d = xNew * xNew + yNew * yNew;

  // Is pupil heading out of the eye constraints?  No need for a sqrt()
  // yet...since we're just comparing against a constant at this point,
  // we can square the constant instead, avoid math...
  float r2 = INNER_RADIUS * INNER_RADIUS; // r^2
  if(d >= r2) {

    // New pupil center position is outside the circle, now the math
    // suddenly gets intense...

    float dx = xNew - x, // Vector from old to new position
          dy = yNew - y; // (crosses INNER_RADIUS perimeter)

    // Find intersections between unbounded line and circle...
    float x2   =  x * x,  //  x^2
          y2   =  y * y,  //  y^2
          a2   = dx * dx, // dx^2
          b2   = dy * dy, // dy^2
          a2b2 = a2 + b2,
          n1, n2,
          n = a2*r2 - a2*y2 + 2.0*dx*dy*x*y + b2*r2 - b2*x2;
    if((n >= 0.0) & (a2b2 > 0.0)) {
      // Because there's a square root here...
      n  = sqrt(n);
      // There's two possible intersection points.  Consider both...
      n1 =  (n - dx * x - dy * y) / a2b2;
      n2 = -(n + dx * x + dy * y) / a2b2;
    } else {
      n1 = n2 = 0.0; // Avoid divide-by-zero
    }
    // ...and use the 'larger' one (may be -0.0, that's OK!)
    if(n2 > n1) n1 = n2;
    float ix = x + dx * n1, // Single intersection point of
          iy = y + dy * n1; // movement vector and circle.

    // Pupil needs to be constrained within eye circle, but we can't just
    // stop it's motion at the edge, that's cheesy and looks wrong.  On its
    // way out, it was moving with a certain direction and speed, and needs
    // to bounce back in with suitable changes to both...

    float mag1 = sqrt(dx * dx + dy * dy), // Full velocity vector magnitude
          dx1  = (ix - x),                // Vector from prior pupil pos.
          dy1  = (iy - y),                // to point of edge intersection
          mag2 = sqrt(dx1*dx1 + dy1*dy1); // Magnitude of above vector
    // Difference between the above two magnitudes is the distance the pupil
    // will bounce back into the eye circle on this frame (i.e. it rarely
    // stops exactly at the edge...in the course of a single frame, it will
    // be moving outward a certain amount, contact edge, and move inward
    // a certain amount.  The latter amount is scaled back slightly as it
    // loses some energy in edge the collision.
    float mag3 = (mag1 - mag2) * ELASTICITY;

    float ax = -ix / INNER_RADIUS, // Unit surface normal (magnitude 1.0)
          ay = -iy / INNER_RADIUS, // at contact point with circle.
          rx, ry;                  // Reverse velocity vector, normalized
    if(mag1 > 0.0) {
      rx = -dx / mag1;
      ry = -dy / mag1;
    } else {
      rx = ry = 0.0;
    }
    // Dot product between the two vectors is cosine of angle between them
    float dot = rx * ax + ry * ay,
          rpx = ax * dot,          // Point to reflect across
          rpy = ay * dot;
    rx += (rpx - rx) * 2.0;        // Reflect velocity vector across point
    ry += (rpy - ry) * 2.0;        // (still normalized)

    // New position is the intersection point plus the reflected vector
    // scaled by mag3 (the elasticity-reduced velocity remainder).
    xNew = ix + rx * mag3;
    yNew = iy + ry * mag3;

    // Velocity magnitude is scaled by the elasticity coefficient.
    mag1 *= ELASTICITY;
    vxNew = rx * mag1;
    vyNew = ry * mag1;
  }

  int x1, y1, x2, y2,            // Bounding rect of screen update area
      px1 = 64 + (int)xNew - 24, // Bounding rect of new pupil pos. only
      px2 = 64 + (int)xNew + 23,
      py1 = 64 - (int)yNew - 24,
      py2 = 64 - (int)yNew + 23;

  if(firstFrame) {
    x1 = y1 = 0;
    x2 = y2 = 127;
    firstFrame = false;
  } else {
    if(xNew >= x) { // Moving right
      x1 = 64 + (int)x    - 24;
      x2 = 64 + (int)xNew + 23;
    } else {       // Moving left
      x1 = 64 + (int)xNew - 24;
      x2 = 64 + (int)x    + 23;
    }
    if(yNew >= y) { // Moving up (still using +Y Cartesian coords)
      y1 = 64 - (int)yNew - 24;
      y2 = 64 - (int)y    + 23;
    } else {        // Moving down
      y1 = 64 - (int)y    - 24;
      y2 = 64 - (int)yNew + 23;
    }
  }

  x  = xNew;  // Save new position, velocity
  y  = yNew;
  vx = vxNew;
  vy = vyNew;

  // Clip update rect.  This shouldn't be necessary, but it looks
  // like very occasionally an off-limits situation may occur, so...
  if(x1 < 0)   x1 = 0;
  if(y1 < 0)   y1 = 0;
  if(x2 > 127) x2 = 127;
  if(y2 > 127) y2 = 127;

  SPI.beginTransaction(settings);    // SPI init
  digitalWrite(TFT_CS, LOW);         // Chip select
  tft.setAddrWindow(x1, y1, x2-x1+1, y2-y1+1);
  digitalWrite(TFT_CS, LOW);         // Re-select after addr function
  digitalWrite(TFT_DC, HIGH);        // Data mode...

  uint16_t *dmaPtr;   // Pointer into DMA output buffer (16 bits/pixel)
  uint8_t  *srcPtr1,  // Pointer into eye background bitmap (8bpp)
           *srcPtr2,  // Pointer into pupil bitmap (8bpp)
            b,        // Resulting pixel brightness (0-255)
            col, row; // X,Y pixel counters
  uint16_t  result,   // Expanded 16-bit pixel color
            nBytes;   // Size of DMA transfer

  descriptor->BTCNT.reg = nBytes = (x2 - x1 + 1) * 2;

  // Macro converts 8-bit grayscale to 16-bit '565' RGB value
  #define STORE565(x)                                            \
   result   = (((x * 0x801) >> 3) & 0xF81F) | ((x & 0xFC) << 3); \
  *dmaPtr++ = __builtin_bswap16(result);

  // Process rows ABOVE pupil
  for(row=y1; row<py1; row++) {
    dmaPtr  = &dmaBuf[dmaIdx][0];
    srcPtr1 = &borderData[row][x1];
    for(col=x1; col<=x2; col++) {
      b = *srcPtr1++;
      STORE565(b)
    }
    dmaXfer(nBytes);
  }

  // Process rows WITH pupil
  for(; row<=py2; row++) {
    dmaPtr  = &dmaBuf[dmaIdx][0];     // Output to start of DMA buf
    srcPtr1 = &borderData[row][x1];   // Initial byte of eye border
    srcPtr2 = &pupilData[row-py1][0]; // Initial byte of pupil
    for(col=x1; col<px1; col++) { // LEFT of pupil
      b = *srcPtr1++;
      STORE565(b)
    }
    for(; col<=px2; col++) {      // Overlap pupil
      b = (*srcPtr1++ * (*srcPtr2++ + 1)) >> 8;
      STORE565(b)
    }
    for(; col<=x2; col++) {       // RIGHT of pupil
      b = *srcPtr1++;
      STORE565(b)
    }
    dmaXfer(nBytes);
  }

  // Process rows BELOW pupil
  for(; row<=y2; row++) {
    dmaPtr  = &dmaBuf[dmaIdx][0];
    srcPtr1 = &borderData[row][x1];
    for(col=x1; col<=x2; col++) {
      b = *srcPtr1++;
      STORE565(b)
    }
    dmaXfer(nBytes);
  }

  while(dma_busy);            // Wait for last DMA transfer to complete
  digitalWrite(TFT_CS, HIGH); // Deselect
  SPI.endTransaction();       // SPI done
}

void dmaXfer(uint16_t n) { // n = Transfer size in bytes
  while(dma_busy);         // Wait for prior DMA transfer to finish
  // Set up DMA transfer from newly-filled buffer
  descriptor->SRCADDR.reg = (uint32_t)&dmaBuf[dmaIdx] + n;
  dma_busy = true;         // Flag as busy
  dma.startJob();          // Start new DMA transfer
  dmaIdx = 1 - dmaIdx;     // And swap DMA buffer indices
}
