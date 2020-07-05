// "Minotaur Maze" plaything for Adafruit Hallowing. Uses ray casting,
// DMA and related shenanigans to smoothly move about a 3D maze.
// Tilt Hallowing to turn right/left and move forward/back.

// Ray casting code adapted from tutorial by Lode Vandevenne:
// https://lodev.org/cgtutor/raycasting.html

#include <Adafruit_LIS3DH.h>  // Accelerometer library
#include <Adafruit_GFX.h>     // Core graphics library
#include <Adafruit_ST7735.h>  // Display-specific graphics library
#include <Adafruit_ZeroDMA.h> // Direct memory access library

#ifdef ARDUINO_SAMD_CIRCUITPLAYGROUND_EXPRESS
  #define TFT_RST        -1
  #define TFT_DC         A6
  #define TFT_CS         A7
  #define TFT_BACKLIGHT  A3 // Display backlight pin
  #define TFT_SPI        SPI1
  #define TFT_PERIPH     PERIPH_SPI1
  Adafruit_LIS3DH accel(&Wire1);
#else
  #define TFT_RST       37      // TFT reset pin
  #define TFT_DC        38      // TFT display/command mode pin
  #define TFT_CS        39      // TFT chip select pin
  #define TFT_BACKLIGHT  7      // TFT backlight LED pin
  #define TFT_SPI        SPI
  #define TFT_PERIPH     PERIPH_SPI
  Adafruit_LIS3DH accel;
#endif


// Declarations for some Hallowing hardware -- display, accelerometer, SPI
Adafruit_ST7735 tft(&TFT_SPI, TFT_CS, TFT_DC, TFT_RST);
SPISettings     settings(12000000, MSBFIRST, SPI_MODE0);

// Declarations related to DMA (direct memory access), which lets us walk
// and chew gum at the same time. This is VERY specific to SAMD chips and
// means this is not trivially ported to other devices.
Adafruit_ZeroDMA  dma;
DmacDescriptor   *dptr; // Initial allocated DMA descriptor
DmacDescriptor    desc[2][3] __attribute__((aligned(16)));
uint8_t           dList = 0; // Active DMA descriptor list index (0-1)

// DMA transfer-in-progress indicator and callback
static volatile bool dma_busy = false;
static void dma_callback(Adafruit_ZeroDMA *dma) {
  dma_busy = false;
}

// This is the maze map. It's fixed at 32 bits wide, can be any height but
// is 32 in this example. '1' bits indicate solid walls, '0' indicate empty
// space that can be navigated. Perimeter wall bits MUST be set! Keep the
// center area empty since the player is initially placed there.
uint32_t worldMap[] = {
 0b11111111111111111111111111111111,
 0b10000000000000100000000001000001,
 0b10000000000000101111011111011101,
 0b10000000000000001000001000000101,
 0b10000000000000111011101010111101,
 0b10000010100000100010000010000101,
 0b10000010100000111111111010101101,
 0b10000011100000100000000000100001,
 0b10000000000000111011101110111101,
 0b10000000000000100010000010001001,
 0b10000000000000111111111111101111,
 0b10000000000000000000000000000001,
 0b11111011111011100111111011111111,
 0b10000000001010000001000000000001,
 0b10100000101010000001001001001001,
 0b10101010101000000000000000000001,
 0b10101010101000000000000000000001,
 0b10100000101010000001001001001001,
 0b10000000001010000001000000000001,
 0b11111011111011100111111011111111,
 0b10000000000000000000000000000001,
 0b10000010100000000111000010101001,
 0b10001000001000000111000001010101,
 0b10000000000000000111000000000001,
 0b10010000000100000000000011111101,
 0b10000001000000000000000010000101,
 0b10010000000100000011111010100101,
 0b10000000000000000010001010000001,
 0b10001000001000000010101010000101,
 0b10000010100000000010101011111101,
 0b10000000000000000000100000000001,
 0b11111111111111111111111111111111,
};
#define MAPHEIGHT (sizeof worldMap / sizeof worldMap[0])

// This macro tests whether bit at (X,Y) in the map is set.
#define isBitSet(X,Y) (worldMap[MAPHEIGHT-1-(Y)] & (0x80000000>>(X)))
// (X,Y) are in Cartesian coordinates with (0,0) at bottom-left (hence the
// MAPHEIGHT-1-Y inversion above) -- all the navigation and ray-casting math
// is done in Cartesian space, consistent with the trigonometric functions,
// whereas bitmap is represented top-to-bottom.

// DMA shenanigans are used for the solid color fills (sky, walls and
// floor). Typically one would use the DMA "source address increment" to
// copy graphics data from RAM or flash to SPI (to the screen). But a trick
// we can use for certain fills requires only a single byte of storage for
// each color. DMA source increment is turned OFF -- the same byte is issued
// over and over to fill a given span. Downside is a limited palette
// consisting of 256 colors with the high and low bytes of a 16-bit pixel
// value being the same. With the TFT's 5-6-5 bit color packing, the
// resulting selections are a bit weird (there's no 100% pure red, green or
// blue, only combinations) but usable. e.g. an 8-bit value 0x82 expands to
// a 16-bit pixel value of 0x8282 = 0b10000 010100 00010 = 16/31 (~52%) red,
// 20/63 (~32%) green, 2/31 (6%) blue.
const uint8_t colorSky    = 0x3E,   // Color of sky
              colorGround = 0x82,   // Color of ground
              colorNorth  = 0x04,   // Color of north-facing walls
              colorSouth  = 0x05,   // Color of south-facing walls
              colorEast   = 0x06,   // Color of east-facing walls
              colorWest   = 0x07;   // Color of west-facing walls

#define FOV (90.0 * (M_PI / 180.0)) // Field of view

float    posX    = 16.0,            // Observer position,
         posY    = MAPHEIGHT / 2.0, // begin at center of map
         heading = 0.0;             // Initial heading = east

uint32_t startTime, frames = 0;     // For frames-per-second calculation

// SETUP -- RUNS ONCE AT PROGRAM START -------------------------------------

void setup(void) {
  Serial.begin(115200);

  Serial.println("Init accelerometer");
  // Initialize accelerometer, set to 2G range
  if(accel.begin(0x18) || accel.begin(0x19)) {
    accel.setRange(LIS3DH_RANGE_2_G);
  }

  Serial.println("Init display");
  // Initialize and clear screen
  tft.initR(INITR_144GREENTAB);
  tft.setRotation(1);
  tft.fillScreen(0);

  // More shenanigans: the display mapping is reconfigured so pixels are
  // issued in COLUMN-MAJOR sequence (i.e. vertical lines), left-to-right,
  // with pixel (0,0) at top left. The ray casting algorithm determines the
  // wall height at each column...drawing is then just a matter of blasting
  // a column's worth of pixels.
  digitalWrite(TFT_CS, LOW);
  digitalWrite(TFT_DC, LOW);
#ifdef ST77XX_MADCTL
  TFT_SPI.transfer(ST77XX_MADCTL); // Current TFT lib
#else
  TFT_SPI.transfer(ST7735_MADCTL); // Older TFT lib
#endif
  digitalWrite(TFT_DC, HIGH);
  TFT_SPI.transfer(0x28);
  digitalWrite(TFT_CS, HIGH);

  pinMode(TFT_BACKLIGHT, OUTPUT);
  digitalWrite(TFT_BACKLIGHT, HIGH); // Main screen turn on
  Serial.println("Init backlight");

  // Set up SPI DMA.  While the Hallowing has a known SPI peripheral and this
  // could be much simpler, the extra code here will help if adapting this
  // sketch to other SAMD boards (Feather M0, M4, etc.)
  int                dmac_id;
  volatile uint32_t *data_reg;
  dma.allocate();
  if(&TFT_PERIPH == &sercom0) {
    dma.setTrigger(SERCOM0_DMAC_ID_TX);
    data_reg = &SERCOM0->SPI.DATA.reg;
#if defined SERCOM1
  } else if(&TFT_PERIPH == &sercom1) {
    dma.setTrigger(SERCOM1_DMAC_ID_TX);
    data_reg = &SERCOM1->SPI.DATA.reg;
#endif
#if defined SERCOM2
  } else if(&TFT_PERIPH == &sercom2) {
    dma.setTrigger(SERCOM2_DMAC_ID_TX);
    data_reg = &SERCOM2->SPI.DATA.reg;
#endif
#if defined SERCOM3
  } else if(&TFT_PERIPH == &sercom3) {
    dma.setTrigger(SERCOM3_DMAC_ID_TX);
    data_reg = &SERCOM3->SPI.DATA.reg;
#endif
#if defined SERCOM4
  } else if(&TFT_PERIPH == &sercom4) {
    dma.setTrigger(SERCOM4_DMAC_ID_TX);
    data_reg = &SERCOM4->SPI.DATA.reg;
#endif
#if defined SERCOM5
  } else if(&TFT_PERIPH == &sercom5) {
    dma.setTrigger(SERCOM5_DMAC_ID_TX);
    data_reg = &SERCOM5->SPI.DATA.reg;
#endif
  }
  dma.setAction(DMA_TRIGGER_ACTON_BEAT);
  dma.setCallback(dma_callback);

  // Initialize DMA descriptor lists. There are TWO lists, used for
  // alternating even/odd scanlines (columns in this case)...one list is
  // calculated and filled while the other is being transferred out SPI.
  // Each list contains three elements (though not all three are used every
  // time), corresponding to the sky, wall and ground pixels for a column.
  for(uint8_t s=0; s<2; s++) {   // Even/odd scanlines
    for(uint8_t d=0; d<3; d++) { // 3 descriptors per line
      // No need to set SRCADDR, BTCNT or DESCADDR -- done later
      desc[s][d].BTCTRL.bit.VALID    = true;
      desc[s][d].BTCTRL.bit.EVOSEL   = 0x3;
      desc[s][d].BTCTRL.bit.BLOCKACT = DMA_BLOCK_ACTION_NOACT;
      desc[s][d].BTCTRL.bit.BEATSIZE = DMA_BEAT_SIZE_BYTE;
      desc[s][d].BTCTRL.bit.SRCINC   = 0;
      desc[s][d].BTCTRL.bit.DSTINC   = 0;
      desc[s][d].BTCTRL.bit.STEPSEL  = DMA_STEPSEL_SRC;
      desc[s][d].BTCTRL.bit.STEPSIZE = DMA_ADDRESS_INCREMENT_STEP_SIZE_1;
      desc[s][d].DSTADDR.reg         = (uint32_t)data_reg;
    }
  }

  // The DMA library MUST allocate at least one valid descriptor, so that's
  // done here. It's not used in the conventional sense though, just before
  // a transfer we copy the first scanline descriptor to this spot.
  dptr = dma.addDescriptor(NULL, NULL, 42, DMA_BEAT_SIZE_BYTE, false, false);

  startTime = millis(); // Starting time for frame-per-second calculation
}

// LOOP -- REPEATS INDEFINITELY --------------------------------------------

void loop() {

  // Update heading and position from accelerometer...
  uint8_t mapX = (uint8_t)posX,                  // Current square of map
          mapY = (uint8_t)posY;                  // (before changing pos.)
  accel.read();                                  // Read accelerometer
#ifdef ARDUINO_SAMD_CIRCUITPLAYGROUND_EXPRESS
  heading     += (float)accel.x / -20000.0;      // Update direction
  float   v    = (abs(accel.y) < abs(accel.z)) ? // If board held flat(ish)
                 (float)accel.y /  20000.0 :     // Use accel Y for velocity
                 (float)accel.z / -20000.0;      // else accel Z is velocity
#else
  heading     += (float)accel.y / -20000.0;      // Update direction
  float   v    = (abs(accel.x) < abs(accel.z)) ? // If board held flat(ish)
                 (float)accel.x /  20000.0 :     // Use accel X for velocity
                 (float)accel.z / -20000.0;      // else accel Z is velocity
#endif
  if(v > 0.19)       v =  0.19;                  // Keep speed under 0.2
  else if(v < -0.19) v = -0.19;
  float   vx   = cos(heading) * v,               // Direction vector X, Y
          vy   = sin(heading) * v,
          newX = posX + vx,                      // New position
          newY = posY + vy;

  // Prevent going through solid walls (or getting too close to them)
  if(vx > 0) {
    if(isBitSet((int)(newX + 0.2), (int)newY)) newX = mapX + 0.8;
  } else {
    if(isBitSet((int)(newX - 0.2), (int)newY)) newX = mapX + 0.2;
  }
  if(vy > 0) {
    if(isBitSet((int)newX, (int)(newY + 0.2))) newY = mapY + 0.8;
  } else {
    if(isBitSet((int)newX, (int)(newY - 0.2))) newY = mapY + 0.2;
  }

  posX = newX;
  posY = newY;

  TFT_SPI.beginTransaction(settings);    // SPI init
  digitalWrite(TFT_CS, LOW);         // Chip select
  tft.setAddrWindow(0, 0, 128, 128); // Set address window to full screen
  digitalWrite(TFT_CS, LOW);         // Re-select after addr function
  digitalWrite(TFT_DC, HIGH);        // Data mode...

  // Ray casting code is much abbreviated here.
  // See Lode Vandevenne's original tutorial for an in-depth explanation:
  // https://lodev.org/cgtutor/raycasting.html

  int8_t   stepX, stepY;           // X/Y direction steps (+1 or -1)
  uint8_t  skyPixels, floorPixels, // # of pixels in sky, floor
           side,                   // North/south or east/west wall hit?
           i;                      // Index in DMA descriptor list
  uint16_t wallPixels;             // # of wall pixels
  float    frac, rayDirX, rayDirY,
           sideDistX, sideDistY,   // Ray length, current to next X/Y side
           deltaDistX, deltaDistY, // X-to-X, Y-to-Y ray lengths
           perpWallDist,           // Distance to wall
           x1 = cos(heading + FOV / 2.0), // Image plane left edge
           y1 = sin(heading + FOV / 2.0),
           x2 = cos(heading - FOV / 2.0), // Image plane right edge
           y2 = sin(heading - FOV / 2.0),
           dx = x2 - x1, dy = y2 - y1;

  for(uint8_t col = 0; col < 128; col++) { // For each column...
    frac       = ((float)col + 0.5) / 128.0; // 0 to 1 left to right
    rayDirX    = x1 + dx * frac;
    rayDirY    = y1 + dy * frac;
    mapX       = (uint8_t)posX; 
    mapY       = (uint8_t)posY;
    deltaDistX = (rayDirX != 0.0) ? fabs(1 / rayDirX) : 0.0;
    deltaDistY = (rayDirY != 0.0) ? fabs(1 / rayDirY) : 0.0;

    // Calculate X/Y steps and initial sideDist
    if(rayDirX < 0) {
      stepX     = -1;
      sideDistX = (posX - mapX) * deltaDistX;
    } else {
      stepX     = 1;
      sideDistX = (mapX + 1.0 - posX) * deltaDistX;
    } if (rayDirY < 0) {
      stepY     = -1;
      sideDistY = (posY - mapY) * deltaDistY;
    } else {
      stepY     = 1;
      sideDistY = (mapY + 1.0 - posY) * deltaDistY;
    }

    do { // Bresenham DDA line algorithm...walk map squares...
      if(sideDistX < sideDistY) {
        sideDistX += deltaDistX;
        mapX      += stepX;
        side       = 0; // East/west
      } else {
        sideDistY += deltaDistY;
        mapY      += stepY;
        side       = 1; // North/south
      }
    } while(!isBitSet(mapX, mapY)); // Continue until wall hit

    // Calc distance projected on camera direction
    perpWallDist = side ? ((mapY - posY + (1 - stepY) / 2) / rayDirY) :
                          ((mapX - posX + (1 - stepX) / 2) / rayDirX);

    wallPixels = (int)(128.0 / perpWallDist);     // Colum height in pixels
    if(wallPixels >= 128) {                       // >= screen height?
      wallPixels = 128;                           // Clip to screen height
      skyPixels  = floorPixels = 0;               // No sky or ground
    } else {
      skyPixels   = (128 - wallPixels) / 2;       // 1/2 of non-wall is sky
      floorPixels = 128 - wallPixels - skyPixels; // Any remainder is floor
    }

    // Build DMA descriptor list with up to 3 elements...
    i = 0;
    if(skyPixels) { // Any sky pixels in this column?
      desc[dList][i].SRCADDR.reg  = (uint32_t)&colorSky;
      desc[dList][i].BTCNT.reg    = skyPixels * 2;
      desc[dList][i].DESCADDR.reg = (uint32_t)&desc[dList][i + 1];
      i++;
    }
    if(wallPixels) { // Any wall pixels?
      // North/south or east/west facing?
      desc[dList][i].SRCADDR.reg  = (uint32_t)(side ?
        ((stepY > 0) ? &colorSouth : &colorNorth) :
        ((stepX > 0) ? &colorWest  : &colorEast ));
      desc[dList][i].BTCNT.reg    = wallPixels * 2;
      desc[dList][i].DESCADDR.reg = (uint32_t)&desc[dList][i + 1];
      i++;
    }
    if(floorPixels) { // Any floor pixels?
      desc[dList][i].SRCADDR.reg  = (uint32_t)&colorGround;
      desc[dList][i].BTCNT.reg    = floorPixels * 2;
      desc[dList][i].DESCADDR.reg = (uint32_t)&desc[dList][i + 1];
      i++;
    }
    desc[dList][i - 1].DESCADDR.reg = 0; // End descriptor list

    while(dma_busy);          // Wait for prior DMA transfer to finish
    // Copy scanline's first descriptor to the DMA lib's descriptor table
    memcpy(dptr, &desc[dList][0], sizeof(DmacDescriptor));
    dma_busy = true;          // Mark as busy (DMA callback clears this)
    dma.startJob();           // Start new DMA transfer
    dList = 1 - dList;        // Swap active DMA descriptor list index
  }
  while(dma_busy);            // Wait for last DMA transfer to complete
  digitalWrite(TFT_CS, HIGH); // Deselect
  TFT_SPI.endTransaction();       // SPI done

  if(!(++frames & 255)) {     // Every 256th frame, show frame rate
    uint32_t elapsed = (millis() - startTime) / 1000;
    if(elapsed) Serial.println(frames / elapsed);
  }
}
