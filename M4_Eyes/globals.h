//34567890123456789012345678901234567890123456789012345678901234567890123456

#include <Adafruit_GFX.h>         // Core graphics for Adafruit displays
#include <Adafruit_ST7789.h>      // TFT-specific display library
#include <Adafruit_ZeroDMA.h>     // SAMD-specific DMA library
#include <Adafruit_ImageReader.h> // ImageReturnCode type
#include "DMAbuddy.h"             // DMA-bug-workaround class

#if defined(GLOBAL_VAR) // #defined in .ino file ONLY!
  #define GLOBAL_INIT(X) = (X)
  #define INIT_EYESTRUCTS
#else
  #define GLOBAL_VAR extern
  #define GLOBAL_INIT(X)
#endif

#if defined(ADAFRUIT_MONSTER_M4SK_EXPRESS)
  #define NUM_EYES 2
  #include <Adafruit_seesaw.h>
  GLOBAL_VAR Adafruit_seesaw seesaw; // Controls some left-eye signals
  #define SEESAW_TFT_RESET_PIN 8     // Left eye TFT reset
  #define SEESAW_BACKLIGHT_PIN 5     // Left eye TFT backlight
  #define BACKLIGHT_PIN       21     // Right eye TFT backlight
  #define LIGHTSENSOR_PIN      2
  // Light sensor is not active by default. Use "lightSensor : 102" in config
#else
  #define NUM_EYES 1
  #define BACKLIGHT_PIN       47
#endif

// GLOBAL VARIABLES --------------------------------------------------------

GLOBAL_VAR uint32_t  stackReserve        GLOBAL_INIT(8192);   // See image-loading code
GLOBAL_VAR int       eyeRadius           GLOBAL_INIT(0);      // 0 = Use default in loadConfig()
GLOBAL_VAR int       eyeDiameter;                             // Calculated from eyeRadius later
GLOBAL_VAR int       irisRadius          GLOBAL_INIT(60);     // Approx size in screen pixels
GLOBAL_VAR int       slitPupilRadius     GLOBAL_INIT(0);      // 0 = round pupil
GLOBAL_VAR uint8_t   eyelidIndex         GLOBAL_INIT(0x00);   // From table: learn.adafruit.com/assets/61921
GLOBAL_VAR uint16_t  eyelidColor         GLOBAL_INIT(0x0000); // Expand eyelidIndex to 16-bit
// mapRadius is the size of one quadrant of the polar-to-rectangular map,
// in pixels. To cover the front hemisphere of the eye, this should be a
// minimum of (eyeRadius * Pi / 2) -- but, to provide some coverage beyond
// just the front hemisphere, the value of 'coverage' determines how far
// this map wraps around the eye. 0.0 = no coverage, 0.5 = front hemisphere,
// 1.0 = full sphere. Do not bother making this 1.0 -- the far back side of
// the eye is never actually seen, since we're using a displacement map hack
// and not actually rotating a sphere, plus the resulting map would take a
// TON of RAM, probably more than we have. The default here, 0.6, provides
// a good balance between coverage and RAM, only occasionally will you see
// a crescent of back-of-eye color (and the sclera texture map can be
// designed to blend into it). eyeRadius is calculated in loadConfig() as
// eyeRadius * Pi * coverage -- if eyeRadius is 125 and coverage is 0.6,
// mapRadius will be 236 pixels, and the resulting polar angle/dist maps
// will total about 111K RAM.
GLOBAL_VAR float     coverage            GLOBAL_INIT(0.6);
GLOBAL_VAR int       mapRadius;          // calculated in loadConfig()
GLOBAL_VAR int       mapDiameter;        // calculated in loadConfig()
GLOBAL_VAR uint8_t  *displace            GLOBAL_INIT(NULL);
GLOBAL_VAR uint8_t  *polarAngle          GLOBAL_INIT(NULL);
GLOBAL_VAR int8_t   *polarDist           GLOBAL_INIT(NULL);
GLOBAL_VAR uint8_t   upperOpen[240];
GLOBAL_VAR uint8_t   upperClosed[240];
GLOBAL_VAR uint8_t   lowerOpen[240];
GLOBAL_VAR uint8_t   lowerClosed[240];
GLOBAL_VAR char     *upperEyelidFilename GLOBAL_INIT(NULL);
GLOBAL_VAR char     *lowerEyelidFilename GLOBAL_INIT(NULL);
GLOBAL_VAR uint16_t  lightSensorMin      GLOBAL_INIT(0);
GLOBAL_VAR uint16_t  lightSensorMax      GLOBAL_INIT(1023);
GLOBAL_VAR float     lightSensorCurve    GLOBAL_INIT(1.0);
GLOBAL_VAR float     irisMin             GLOBAL_INIT(0.45);
GLOBAL_VAR float     irisRange           GLOBAL_INIT(0.35);

// Pin definition stuff will go here

GLOBAL_VAR int8_t    lightSensorPin      GLOBAL_INIT(-1);
GLOBAL_VAR int8_t    blinkPin            GLOBAL_INIT(-1); // Manual both-eyes blink pin (-1 = none)

#if defined(ADAFRUIT_MONSTER_M4SK_EXPRESS)
  GLOBAL_VAR int8_t  boopPin             GLOBAL_INIT(A2);
#else
  GLOBAL_VAR int8_t  boopPin             GLOBAL_INIT(-1);
#endif
GLOBAL_VAR uint32_t  boopThreshold       GLOBAL_INIT(17500);


// EYE-RELATED STRUCTURES --------------------------------------------------

// Eyes are rendered column-at-a-time, using DMA to issue one column of
// data while the next is being calculated, alternating between two column
// structures (there would be barely enough RAM to buffer a whole 240x240
// screen anyway). Each column being rendered/issued makes use of 1 to 3
// linked DMA descriptors, ostensibly containing: 1) background pixels in
// the eyelid area "below" the eye, 2) rendered pixels within the eye
// itself (drawn in the renderBuf[] scanline buffer, allocated for 240
// pixels to match the screen size, though usually only a portion will be
// used, and 3) more background pixels in the eyelid area "above" the eye.
#if NUM_EYES > 1
  #define NUM_DESCRIPTORS 1 // See note below
#else
  #define NUM_DESCRIPTORS 3
#endif
  // IMPORTANT NOTE: original plan (described above, with dynamic descriptor
  // list) was FOILED by a silicon bug (documented in the SAMD51 errata)
  // when using linked descriptors on multiple channels. The fix, for now,
  // is to skip the eyelid optimization and fully buffer/render each line,
  // with a single descriptor. This is NOT a problem with a single eye
  // (since only one channel) and we can still use the hack for HalloWing M4.
typedef struct {
  uint16_t       renderBuf[240];              // Pixel buffer
  DmacDescriptor descriptor[NUM_DESCRIPTORS]; // DMA descriptor list
} columnStruct;

// A simple state machine is used to control eye blinks/winks:
#define NOBLINK 0       // Not currently engaged in a blink
#define ENBLINK 1       // Eyelid is currently closing
#define DEBLINK 2       // Eyelid is currently opening
typedef struct {
  uint8_t  state;       // NOBLINK/ENBLINK/DEBLINK
  uint32_t duration;    // Duration of blink state (micros)
  uint32_t startTime;   // Time (micros) of last state change
} eyeBlink;

// Data for iris and sclera texture maps
typedef struct {
  char     *filename;
  float     spin;       // RPM * 1024.0
  uint16_t  color;
  uint16_t *data;
  uint16_t  width;
  uint16_t  height;
  uint16_t  startAngle; // INITIAL rotation 0-1023 CCW
  uint16_t  angle;      // CURRENT rotation 0-1023 CCW
  uint16_t  mirror;     // 0 = normal, 1023 = flip X axis
} texture;

// Each eye then uses the following structure. Each eye must be on its own
// SPI bus with distinct control lines (unlike the Uncanny Eyes code where
// they take turns on one bus). Two of the column structures as described
// above, then a lot of DMA nitty-gritty and animation state data.
typedef struct {
  // These first values are initialized in the tables below:
  const char      *name;         // For loading per-eye configurables
  SPIClass        *spi;          // Pointer to corresponding SPI object
  int8_t           cs;           // CS pin #
  int8_t           dc;           // DC pin #
  int8_t           rst;          // RST pin # (-1 if using Seesaw)
  int8_t           winkPin;      // Manual eye wink control (-1 = none)
  // Remaining values are initialized in code:
  columnStruct     column[2];    // Alternating column structures A/B
  Adafruit_ST7789 *display;      // Pointer to display object
  DMAbuddy         dma;          // DMA channel object with fix() function
  DmacDescriptor  *dptr;         // DMA channel descriptor pointer
  uint32_t         dmaStartTime; // For DMA timeout handler
  uint8_t          colNum;       // Column counter (0-239)
  uint8_t          colIdx;       // Alternating 0/1 index into column[] array
  bool             dma_busy;     // true = DMA transfer in progress
  bool             column_ready; // true = next column is already rendered
  uint16_t         pupilColor;   // 16-bit 565 RGB, big-endian
  uint16_t         backColor;    // 16-bit 565 RGB, big-endian
  texture          iris;         // iris texture map
  texture          sclera;       // sclera texture map

  // Stuff carried over from Uncanny Eyes code. It now needs to be
  // independent per-eye because we interleave between drawing the
  // two eyes scanline-by-line rather than drawing each eye in full.
  // This'll likely get cleaned up a little, but for now...
  eyeBlink blink;
  float    eyeX, eyeY;  // Save per-eye to avoid tearing
  float    pupilFactor; // ditto
  float    blinkFactor;
  float    upperLidFactor, lowerLidFactor;
} eyeStruct;

#ifdef INIT_EYESTRUCTS
  eyeStruct eye[NUM_EYES] = {
  #if defined(ADAFRUIT_MONSTER_M4SK_EXPRESS)
    // name     spi  cs  dc rst wink
    { "right", &SPI , 5,  6,  4, -1 },
    { "left" , &SPI1, 9, 10, -1, -1 } };
  #elif defined(ADAFRUIT_HALLOWING_M4_EXPRESS)
    {  NULL  , &SPI1, 44, 45, 46, -1 } };
  #else
    #error "This project supports Adafruit MONSTER M4SK and HALLOWING M4 only"
  #endif
#else
  extern eyeStruct eye[];
#endif

// FUNCTION PROTOTYPES -----------------------------------------------------

// Functions in file.cpp
extern int             file_setup(bool msc=true);
extern void            handle_filesystem_change();
// This is set true when filesystem contents have changed.
// Set true initially so the program starts with the "changed" task.
extern bool            filesystem_change_flag GLOBAL_INIT(true);
extern void            loadConfig(char *filename);
extern ImageReturnCode loadEyelid(char *filename, uint8_t *minArray, uint8_t *maxArray, uint8_t init, uint32_t maxRam);
extern ImageReturnCode loadTexture(char *filename, uint16_t **data, uint16_t *width, uint16_t *height, uint32_t maxRam);

// Functions in memory.cpp
extern uint32_t        availableRAM(void);
extern uint32_t        availableNVM(void);
extern uint8_t        *writeDataToFlash(uint8_t *src, uint32_t len);

// Functions in tablegen.cpp
extern void            calcDisplacement(void);
extern void            calcMap(void);
extern float           screen2map(int in);
extern float           map2screen(int in);
