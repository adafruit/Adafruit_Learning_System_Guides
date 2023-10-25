// SPDX-FileCopyrightText: 2019 Phillip Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT
#include <Arduino.h>
#include <SdFat.h>
#include <Adafruit_SPIFlash.h>
#include <Adafruit_ImageReader.h> // Image-reading functions
#include <Arduino_GFX_Library.h>

//34567890123456789012345678901234567890123456789012345678901234567890123456

#if defined(GLOBAL_VAR) // #defined in .ino file ONLY!
  #define GLOBAL_INIT(X) = (X)
  #define INIT_EYESTRUCTS
#else
  #define GLOBAL_VAR extern
  #define GLOBAL_INIT(X)
#endif

#define NUM_EYES 1

// GLOBAL VARIABLES --------------------------------------------------------

GLOBAL_VAR bool      showSplashScreen    GLOBAL_INIT(false);   // Clear to suppress the splash screen

#define MAX_DISPLAY_SIZE 480
GLOBAL_VAR int       DISPLAY_SIZE        GLOBAL_INIT(240);    // Start with assuming a 240x240 display
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
GLOBAL_VAR uint16_t  *displace            GLOBAL_INIT(NULL);
GLOBAL_VAR uint8_t  *polarAngle          GLOBAL_INIT(NULL);
GLOBAL_VAR int8_t   *polarDist           GLOBAL_INIT(NULL);
GLOBAL_VAR uint16_t   upperOpen[MAX_DISPLAY_SIZE];
GLOBAL_VAR uint16_t   upperClosed[MAX_DISPLAY_SIZE];
GLOBAL_VAR uint16_t   lowerOpen[MAX_DISPLAY_SIZE];
GLOBAL_VAR uint16_t   lowerClosed[MAX_DISPLAY_SIZE];
GLOBAL_VAR char     *upperEyelidFilename GLOBAL_INIT(NULL);
GLOBAL_VAR char     *lowerEyelidFilename GLOBAL_INIT(NULL);
GLOBAL_VAR uint16_t  lightSensorMin      GLOBAL_INIT(0);
GLOBAL_VAR uint16_t  lightSensorMax      GLOBAL_INIT(1023);
GLOBAL_VAR float     lightSensorCurve    GLOBAL_INIT(1.0);
GLOBAL_VAR float     irisMin             GLOBAL_INIT(0.45);
GLOBAL_VAR float     irisRange           GLOBAL_INIT(0.35);
GLOBAL_VAR bool      tracking            GLOBAL_INIT(true);
GLOBAL_VAR float     trackFactor         GLOBAL_INIT(0.5);
GLOBAL_VAR uint32_t  gazeMax             GLOBAL_INIT(3000000); // Max wait time (uS) for major eye movements

// Random eye motion: provided by the base project, but overridable by user code.
GLOBAL_VAR bool      moveEyesRandomly    GLOBAL_INIT(true);   // Clear to suppress random eye motion and let user code control it
GLOBAL_VAR float     eyeTargetX          GLOBAL_INIT(0.0);  // Then set these continuously in user_loop.
GLOBAL_VAR float     eyeTargetY          GLOBAL_INIT(0.0);  // Range is from -1.0 to +1.0.

// Pin definition stuff will go here

GLOBAL_VAR int8_t    lightSensorPin      GLOBAL_INIT(-1);
GLOBAL_VAR int8_t    blinkPin            GLOBAL_INIT(-1); // Manual both-eyes blink pin (-1 = none)


// EYE-RELATED STRUCTURES --------------------------------------------------

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
  uint16_t  iSpin;      // Per-frame fixed integer spin, overrides 'spin' value
} texture;

// Each eye then uses the following structure. Each eye must be on its own
// SPI bus with distinct control lines (unlike the Uncanny Eyes code where
// they take turns on one bus). Two of the column structures as described
// above, then a lot of DMA nitty-gritty and animation state data.
typedef struct {
  // These first values are initialized in the tables below:
  const char      *name;         // For loading per-eye configurables
  int8_t           winkPin;      // Manual eye wink control (-1 = none)

  Arduino_RGB_Display *display;
  // Remaining values are initialized in code:
  uint16_t         pupilColor;   // 16-bit 565 RGB, big-endian
  uint16_t         backColor;    // 16-bit 565 RGB, big-endian
  texture          iris;         // iris texture map
  texture          sclera;       // sclera texture map
  uint8_t          rotation;     // Screen rotation (GFX lib)


  uint16_t column[MAX_DISPLAY_SIZE];
  uint16_t colNum;

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
    {  NULL, -1 } };
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
extern ImageReturnCode loadEyelid(char *filename, uint16_t *minArray, uint16_t *maxArray, uint16_t init);
extern ImageReturnCode loadTexture(char *filename, uint16_t **data, uint16_t *width, uint16_t *height);

// Functions in tablegen.cpp
extern void            calcDisplacement(void);
extern void            calcMap(void);
extern float           screen2map(int in);
extern float           map2screen(int in);

// Functions in user.cpp
extern void            user_setup(void);
extern void            user_loop(void);
