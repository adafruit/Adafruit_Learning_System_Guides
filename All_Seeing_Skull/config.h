// Pin selections here are based on the original Adafruit Learning System
// guide for the Teensy 3.x project.  Some of these pin numbers don't even
// exist on the smaller SAMD M0 & M4 boards, so you may need to make other
// selections:

// GRAPHICS SETTINGS (appearance of eye) -----------------------------------

// If using a SINGLE EYE, you might want this next line enabled, which
// uses a simpler "football-shaped" eye that's left/right symmetrical.
// Default shape includes the caruncle, creating distinct left/right eyes.
#ifdef ADAFRUIT_HALLOWING // Hallowing, with one eye, does this by default
  //#define SYMMETRICAL_EYELID
#else                     // Otherwise your choice, standard is asymmetrical
  //#define SYMMETRICAL_EYELID
#endif

// Enable ONE of these #includes -- HUGE graphics tables for various eyes:
#include "graphics/defaultEye.h"    // Standard human-ish hazel eye -OR-
//#include "graphics/dragonEye.h"   // Slit pupil fiery dragon/demon eye -OR-
//#include "graphics/noScleraEye.h" // Large iris, no sclera -OR-
//#include "graphics/goatEye.h"     // Horizontal pupil goat/Krampus eye -OR-
//#include "graphics/newtEye.h"     // Eye of newt

// Optional: enable this line for startup logo (screen test/orient):
#if !defined ADAFRUIT_HALLOWING     // Hallowing can't always fit logo+eye
  #include "graphics/logo.h"        // Otherwise your choice, if it fits
#endif

// EYE LIST ----------------------------------------------------------------

// This table contains ONE LINE PER EYE.  The table MUST be present with
// this name and contain ONE OR MORE lines.  Each line contains THREE items:
// a pin number for the corresponding TFT/OLED display's SELECT line, a pin
// pin number for that eye's "wink" button (or -1 if not used), and a screen
// rotation value (0-3) for that eye.

eyeInfo_t eyeInfo[] = {
#ifdef ADAFRUIT_HALLOWING
  { 39, -1, 2 }, // SINGLE EYE display-select and wink pins, rotate 180
#else
  {  9, 0, 0 }, // LEFT EYE display-select and wink pins, no rotation
  { 10, 2, 0 }, // RIGHT EYE display-select and wink pins, no rotation
#endif
};

// DISPLAY HARDWARE SETTINGS (screen type & connections) -------------------

#ifdef ADAFRUIT_HALLOWING
  #include <Adafruit_ST7735.h> // TFT display library
  #define DISPLAY_DC       38  // Display data/command pin
  #define DISPLAY_RESET    37  // Display reset pin
  #define DISPLAY_BACKLIGHT 7
  #define BACKLIGHT_MAX   128 // def 128
#else
  // Enable ONE of these #includes to specify the display type being used
  #include <Adafruit_SSD1351.h>  // OLED display library -OR-
  //#include <Adafruit_ST7735.h> // TFT display library (enable one only)
  #define DISPLAY_DC        7    // Data/command pin for ALL displays
  #define DISPLAY_RESET     8    // Reset pin for ALL displays
#endif

#if defined(_ADAFRUIT_ST7735H_) || defined(_ADAFRUIT_ST77XXH_)
  #define SPI_FREQ 24000000    // TFT: use max SPI (clips to 12 MHz on M0)
#else // OLED
  #if !defined(ARDUINO_ARCH_SAMD) && (F_CPU <= 72000000)
    #define SPI_FREQ 24000000  // OLED: 24 MHz on 72 MHz Teensy only
  #else
    #define SPI_FREQ 12000000  // OLED: 12 MHz in all other cases
  #endif
#endif

// INPUT SETTINGS (for controlling eye motion) -----------------------------

// JOYSTICK_X_PIN and JOYSTICK_Y_PIN specify analog input pins for manually
// controlling the eye with an analog joystick.  If set to -1 or if not
// defined, the eye will move on its own.
// IRIS_PIN speficies an analog input pin for a photocell to make pupils
// react to light (or potentiometer for manual control).  If set to -1 or
// if not defined, the pupils will change on their own.
// BLINK_PIN specifies an input pin for a button (to ground) that will
// make any/all eyes blink.  If set to -1 or if not defined, the eyes will
// only blink if AUTOBLINK is defined, or if the eyeInfo[] table above
// includes wink button settings for each eye.

//#define JOYSTICK_X_PIN A0 // Analog pin for eye horiz pos (else auto)
//#define JOYSTICK_Y_PIN A1 // Analog pin for eye vert position (")
//#define JOYSTICK_X_FLIP   // If defined, reverse stick X axis
//#define JOYSTICK_Y_FLIP   // If defined, reverse stick Y axis
//#define TRACKING            // If defined, eyelid tracks pupil
#define BLINK_PIN         1 // Pin for manual blink button (BOTH eyes)
//#define AUTOBLINK           // If defined, eyes also blink autonomously
#ifdef ADAFRUIT_HALLOWING  //adjust min/max if inside a skull
  #define LIGHT_PIN      A1 // Hallowing light sensor pin
  #define LIGHT_CURVE  0.33 // Light sensor adjustment curve
  #define LIGHT_MIN      30 // Minimum useful reading from light sensor def 30
  #define LIGHT_MAX     80 // Maximum useful reading from sensor def 980
#else
  #define LIGHT_PIN      A2 // Photocell or potentiometer (else auto iris)
//#define LIGHT_PIN_FLIP    // If defined, reverse reading from dial/photocell
  #define LIGHT_MIN       0 // Lower reading from sensor
  #define LIGHT_MAX    1023 // Upper reading from sensor
#endif
#define IRIS_SMOOTH         // If enabled, filter input from IRIS_PIN
#if !defined(IRIS_MIN)      // Each eye might have its own MIN/MAX
  #define IRIS_MIN      120 // Iris size (0-1023) in brightest light
#endif
#if !defined(IRIS_MAX)
  #define IRIS_MAX      720 // Iris size (0-1023) in darkest light
#endif
//Adjust these offsets and ranges if inside a mask or skull eye socket
#define eyeXOffset      -150 // aim offset on x for autonomous move, default 0
#define eyeYOffset      300  // aim offset on y, default 0
#define eyeXRange       300  // Range of motion on x, full range is 1023
#define eyeYRange       300  // Range of motion on y, full range is 1023
