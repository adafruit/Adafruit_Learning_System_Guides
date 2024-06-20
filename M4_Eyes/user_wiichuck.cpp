#if 0 // Change to 0 to disable this code (must enable ONE user*.cpp only!)

// This user loop is designed to be used with a WiiChuck for command inputs and 
// connects to a NeoPixel strip for additional output. It was used with a unicorn 
// mask with the NeoPixel strip wrapped around the horn. Both the eyes and
// NeoPixel strip react to inputs from the WiiChuck.
// Wiichuck (AdaFruit PID: 342), Nunchucky (PID: 345), QWiiC cable
// NeoPixel strip (PID: 3919)

// The user setup initializes the WiiChuck.
// The doc-based user setup controls whether there is a NeoPixel
// strip and, if so, initializes the NeoPixel strip based on where
// it is connected and how many pixels are being controlled.

// The user loop does three things:
// 1) reads the WiiChuck state for command inputs
// 2) moves the eyes based on the WiiChuck state
// 3) selects which pattern is displayed on the NeoPixel strip.

// The joystick's states:
// Neutral (no buttons pushed, joystick in center):
//    a) eyes move randomly, NeoPixels are in a fading shimmer pattern
// Joystick left: eyes look left, NeoPixels rotate left with green
// Joystick right: eyes look right, NeoPixels rotate right with blue
// Joystick up: eyes look up, NeoPixels spiral up with green
// Joystick down: eyes look down, NeoPixels spiral down with blue
// Button C: eyes go wide (ala boop), NeoPixels sparkle
// Button Z: eyes blink
// BOTH buttons: eyes are both wide AND blinking, and the colors change to red

#include <ArduinoJson.h>          // JSON config file functions
#include <WiiChuck.h>
#include <Adafruit_NeoPixel.h>
#include "globals.h"

Accessory nunchuck1;

static int low = 0, high = 255, divFactor = 86;
static int neoPixelPin = -1, neoPixelMax = 0;
Adafruit_NeoPixel strip;

const int LUMINESCENT = 0; // shimmer between colors
const int CHASE_RIGHT = 1; 
const int CHASE_LEFT = 2;
const int CHASE_UP = 3;
const int CHASE_DOWN = 4;
const int SPARKLE = 5;

int neoPixelState = LUMINESCENT;
long firstPixelHue = 0;
long curChasePixel = 0;

const int green = Adafruit_NeoPixel::Color(0,127,0);
const int blue = Adafruit_NeoPixel::Color(0,0,127);
const int red = Adafruit_NeoPixel::Color(127,0,0);


// Called once near the end of the setup() function. If your code requires
// a lot of time to initialize, make periodic calls to yield() to keep the
// USB mass storage filesystem alive.
void user_setup(void) {
  // follow the WiiAccessory.ino example:
  nunchuck1.begin();
  if (nunchuck1.type == Unknown) {
    /** If the device isn't auto-detected, set the type explicatly
     * 	NUNCHUCK,
     WIICLASSIC,
     GuitarHeroController,
     GuitarHeroWorldTourDrums,
     DrumController,
     DrawsomeTablet,
     Turntable
    */
    nunchuck1.type = NUNCHUCK;
  }
}

// Called once after the processing of the configuration file. This allows
// user configuration to also be done via the config file.
void user_setup(StaticJsonDocument<2048> &doc) {
  low = getDocInt(doc, "wiichuck", "min", 0);
  high = getDocInt(doc, "wiichuck", "max", 255);
  divFactor = (high - low) / 3 + 1;
  Serial.println("user_setup(doc)");

  const char *neopin = doc["wiichuck"]["neopixel"]["pin"];
  Serial.println("neopin=" + String(neopin ? neopin : "(null)"));
  int32_t neomax = getDocInt(doc, "wiichuck","neopixel","max",-1);
  Serial.println("neopin=" + String(neomax));

  if (neopin && neomax > -1) {
    if ((strcmp(neopin, "d2") == 0) || (strcmp(neopin, "D2") == 0))
      neoPixelPin = 2;
    else if ((strcmp(neopin, "d3") == 0) || (strcmp(neopin, "D3") == 0))
      neoPixelPin = 3;
    neoPixelMax = neomax;

    strip.setPin(neoPixelPin);
    strip.updateLength(neoPixelMax);
    strip.updateType(NEO_GRB + NEO_KHZ800);
    strip.setBrightness(50); // Set BRIGHTNESS to about 1/5 (max = 255)
    strip.show();            // Turn OFF all pixels ASAP
    strip.begin();           // INITIALIZE NeoPixel strip object (REQUIRED)
  }    
}

static void neoChase(int addend, int div, int color)
{
  curChasePixel += addend;
  curChasePixel %= div;

  strip.clear();
  for (int c = curChasePixel; c < strip.numPixels(); c += 3) {
    strip.setPixelColor(c, color);
  }
  strip.show();
}

static void neoUpDown(int color, int dir)
{
  int np = strip.numPixels();
  curChasePixel += np + dir;
  curChasePixel %= np;
  strip.clear();
  strip.setPixelColor(curChasePixel, color);
  strip.setPixelColor((curChasePixel + np / 3) % np, color);
  strip.setPixelColor((curChasePixel + np * 2 / 3) % np, color);
  strip.show();
}

static void neoShine()
{
  // code from user_neopixel.cpp
  for(int i=0; i<strip.numPixels(); i++) { // For each pixel in strip...
    // Offset pixel hue by an amount to make one full revolution of the
    // color wheel (range of 65536) along the length of the strip
    // (strip.numPixels() steps):
    int pixelHue = firstPixelHue + (i * 65536L / strip.numPixels());
    // strip.ColorHSV() can take 1 or 3 arguments: a hue (0 to 65535) or
    // optionally add saturation and value (brightness) (each 0 to 255).
    // Here we're using just the single-argument hue variant. The result
    // is passed through strip.gamma32() to provide 'truer' colors
    // before assigning to each pixel:
    strip.setPixelColor(i, strip.gamma32(strip.ColorHSV(pixelHue)));
  }
  strip.show(); // Update strip with new contents
  firstPixelHue += 256;
}

static void neoSparkle()
{
  strip.clear();
  int i = random(0, strip.numPixels());
  int pixelHue = firstPixelHue + (i * 65536L / strip.numPixels());
  strip.setPixelColor(i, strip.gamma32(strip.ColorHSV(pixelHue)));
  strip.show(); // Update strip with new contents  
}


// the normal map() function doesn't seem to work properly for floats
static float map2(long x, long in_min, long in_max, float out_min, float out_max) {
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

// Called periodically during eye animation. This is invoked in the
// interval before starting drawing on the last eye (left eye on MONSTER
// M4SK, sole eye on HalloWing M0) so it won't exacerbate visible tearing
// in eye rendering. This is also SPI "quiet time" on the MONSTER M4SK so
// it's OK to do I2C or other communication across the bridge.
// This function BLOCKS, it does NOT multitask with the eye animation code,
// and performance here will have a direct impact on overall refresh rates,
// so keep it simple. Avoid loops (e.g. if animating something like a servo
// or NeoPixels in response to some trigger) and instead rely on state
// machines or similar. Additionally, calls to this function are NOT time-
// constant -- eye rendering time can vary frame to frame, so animation or
// other over-time operations won't look very good using simple +/-
// increments, it's better to use millis() or micros() and work
// algebraically with elapsed times instead.
void user_loop(void) {
  nunchuck1.readData();    // Read inputs and update maps
  
  int joyX = nunchuck1.getJoyX();
  int joyY = nunchuck1.getJoyY();
  float x = map2(joyX, low, high, -1.0, 1.0);
  float y = map2(joyY, low, high, -1.0, 1.0);
  int cornerX = (joyX - low) / divFactor;
  int cornerY = (joyY - low) / divFactor;
  int chaseColor = 0;
  // Serial.println("cornerXY=" + String(cornerX) + "," + String(cornerY));
  if (cornerX == 1 && cornerY == 1) { // return to normal when the joystick is in the middle
    // Serial.println("eyesNormal()");
    eyesNormal();
    neoPixelState = LUMINESCENT;
  } else {
    // Serial.println("eyesToCorner(" + String(x) + "," + String(-y) + ")");
    eyesToCorner(x, -y, true);
    if (cornerX < 1) {
      chaseColor = green;
      neoPixelState = CHASE_LEFT;
    } else if (cornerX > 1) {
      chaseColor = blue;
      neoPixelState = CHASE_RIGHT;
    } else if (cornerY > 1) {
      neoPixelState = CHASE_UP;
      chaseColor = green;
    } else if (cornerY < 1) {
      neoPixelState = CHASE_DOWN;
      chaseColor = blue;
    }
  }
  
  bool buttonC = nunchuck1.getButtonC();
  eyesWide(buttonC);
  bool buttonZ = nunchuck1.getButtonZ();
  if (buttonZ)
    eyesBlink();

  if (buttonC && buttonZ) {
    chaseColor = red;
    if (neoPixelState == LUMINESCENT) neoPixelState = CHASE_UP;
  } else if (buttonC) {
    neoPixelState = SPARKLE;
  }
  // Serial.println("neo state=" + String(neoPixelState));

  if (strip.numPixels() > 0) {
    switch (neoPixelState) {
      case LUMINESCENT: neoShine(); break;
      case CHASE_RIGHT: neoChase(4, 3, chaseColor); break;
      case CHASE_LEFT: neoChase(2, 3,  chaseColor); break;
      case CHASE_UP: neoUpDown(chaseColor, 1); break;
      case CHASE_DOWN: neoUpDown(chaseColor, -1); break;
      case SPARKLE: neoSparkle(); break;
    }
  }
}

#endif // 0
