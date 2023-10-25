// SPDX-FileCopyrightText: 2019 Phillip Burgess for Adafruit Industries
//
// SPDX-License-Identifier: MIT

// Animated eyes for Adafruit MONSTER M4SK and HALLOWING M4 dev boards.
// This code is pretty tightly coupled to the resources of these boards
// (one or two ST7789 240x240 pixel TFTs on separate SPI buses, and a
// SAMD51 microcontroller), and not as generally portable as the prior
// "Uncanny Eyes" project (better for SAMD21 chips or Teensy 3.X and
// 128x128 TFT or OLED screens, single SPI bus).

// IMPORTANT: in rare situations, a board may get "bricked" when running
// this code while simultaneously connected to USB. A quick-flashing status
// LED indicates the filesystem has gone corrupt. If this happens, install
// CircuitPython to reinitialize the filesystem, copy over your eye files
// (keep backups!), then re-upload this code. It seems to happen more often
// at high optimization settings (above -O3), but there's not 1:1 causality.
// The exact cause has not yet been found...possibly insufficient yield()
// calls, or some rare alignment in the Arcada library or USB-handling code.

// LET'S HAVE A WORD ABOUT COORDINATE SYSTEMS before continuing. From an
// outside observer's point of view, looking at the display(s) on these
// boards, the eyes are rendered COLUMN AT A TIME, working LEFT TO RIGHT,
// rather than the horizontal scanline order of Uncanny Eyes and most other
// graphics-heavy code. It was found much easier to animate the eyelids when
// working along this axis. A "column major" display is easily achieved by
// setting the screen(s) to ROTATION 3, which is a 90 degree
// counterclockwise rotation relative to the default. This places (0,0) at
// the BOTTOM-LEFT of the display, with +X being UP and +Y being RIGHT --
// so, conceptually, just swapping axes you have a traditional Cartesian
// coordinate system and trigonometric functions work As Intended, and the
// code tends to "think" that way in most places. Since the rotation is done
// in hardware though...from the display driver's point of view, one might
// think of these as "horizontal" "scanlines," and that the eye is being
// drawn sideways, with a left and right eyelid rather than bottom and top.
// Just mentioning it here because there may still be lingering comments
// and/or variables in the code where I refer to "scanlines" even though
// visually/spatially these are columns. Will do my best to comment local
// coordinate systems in different spots. (Any raster images loaded by
// Adafruit_ImageReader are referenced in typical +Y = DOWN order.)

// Oh also, "left eye" and "right eye" refer to the MONSTER'S left and
// right. From an observer's point of view, looking AT the monster, the
// "right eye" is on the left.


#define GLOBAL_VAR
#include "globals.h"


Adafruit_FlashTransport_ESP32 flashTransport;
Adafruit_SPIFlash flash(&flashTransport);
FatVolume fatfs;

Adafruit_ImageReader *theImageReader = NULL;

Arduino_XCA9554SWSPI *expander = new Arduino_XCA9554SWSPI(
    PCA_TFT_RESET, PCA_TFT_CS, PCA_TFT_SCK, PCA_TFT_MOSI,
    &Wire, 0x3F);
    
Arduino_ESP32RGBPanel *rgbpanel = new Arduino_ESP32RGBPanel(
    TFT_DE, TFT_VSYNC, TFT_HSYNC, TFT_PCLK,
    TFT_R1, TFT_R2, TFT_R3, TFT_R4, TFT_R5,
    TFT_G0, TFT_G1, TFT_G2, TFT_G3, TFT_G4, TFT_G5,
    TFT_B1, TFT_B2, TFT_B3, TFT_B4, TFT_B5,
    1 /* hsync_polarity */, 50 /* hsync_front_porch */, 2 /* hsync_pulse_width */, 44 /* hsync_back_porch */,
    1 /* vsync_polarity */, 16 /* vsync_front_porch */, 2 /* vsync_pulse_width */, 18 /* vsync_back_porch */
    //,0, 6000000
    );

Arduino_RGB_Display *gfx = new Arduino_RGB_Display(
//    480 /* width */, 480 /* height */, rgbpanel, 0 /* rotation */, true /* auto_flush */,
//    expander, GFX_NOT_DEFINED /* RST */, tl034wvs05_b1477a_init_operations, sizeof(tl034wvs05_b1477a_init_operations));
    480 /* width */, 480 /* height */, rgbpanel, 0 /* rotation */, true /* auto_flush */,
    expander, GFX_NOT_DEFINED /* RST */, TL021WVC02_init_operations, sizeof(TL021WVC02_init_operations));
//    480 /* width */, 480 /* height */, rgbpanel, 0 /* rotation */, true /* auto_flush */,
//    expander, GFX_NOT_DEFINED /* RST */, TL028WVC01_init_operations, sizeof(TL028WVC01_init_operations));
//    720 /* width */, 720 /* height */, rgbpanel, 0 /* rotation */, true /* auto_flush */,
//    expander, GFX_NOT_DEFINED /* RST */, NULL, 0);


// Global eye state that applies to all eyes (not per-eye):
bool     eyeInMotion = false;
float    eyeOldX, eyeOldY, eyeNewX, eyeNewY;
uint32_t eyeMoveStartTime = 0L;
int32_t  eyeMoveDuration  = 0L;
uint32_t lastSaccadeStop  = 0L;
int32_t  saccadeInterval  = 0L;

// Some sloppy eye state stuff, some carried over from old eye code...
// kinda messy and badly named and will get cleaned up/moved/etc.
uint32_t timeOfLastBlink         = 0L,
         timeToNextBlink         = 0L;
int      xPositionOverMap        = 0;
int      yPositionOverMap        = 0;
uint8_t  eyeNum                  = 0;
uint32_t frames                  = 0;
uint32_t lastFrameRateReportTime = 0;
uint32_t lastLightReadTime       = 0;
float    lastLightValue          = 0.5;
double   irisValue               = 0.5;
int      iPupilFactor            = 42;
int      fixate                  = 7;
uint8_t  lightSensorFailCount    = 0;

// For autonomous iris scaling
#define  IRIS_LEVELS 7
float    iris_prev[IRIS_LEVELS] = { 0 };
float    iris_next[IRIS_LEVELS] = { 0 };
uint16_t iris_frame = 0;

uint8_t scaling = 1;

// Crude error handler. Prints message to Serial Monitor, blinks LED.
void fatal(const char *message, uint16_t blinkDelay) {
  Serial.begin(115200);
  Serial.println(message);
  while (1) yield();
}

#include <unistd.h> // sbrk() function


// SETUP FUNCTION - CALLED ONCE AT PROGRAM START ---------------------------

void setup() {
  Serial.begin(115200);
  //while (!Serial) { delay(100); }
  Serial.println("Adafruit Qualia Eyes");

  // Initialize flash library and check its chip ID.
  if (!flash.begin()) {
    Serial.println("Error, failed to initialize flash chip!");
    while (1) delay(10);
  }
  Serial.printf("Flash chip JEDEC ID: 0x%04X \n\r", flash.getJEDECID());
  // to make sure the filesystem was mounted.
  if (!fatfs.begin(&flash)) {
    Serial.println("Failed to mount filesystem!");
    Serial.println("Was CircuitPython loaded on the board first to create the "
                   "filesystem?");
    while (1) delay(10);
  }
  Serial.println("Mounted filesystem.");
  // Print out filesystem
  fatfs.ls("/", LS_R | LS_DATE | LS_SIZE);
  theImageReader = new Adafruit_ImageReader(fatfs);

  user_setup();


#ifdef GFX_EXTRA_PRE_INIT
  GFX_EXTRA_PRE_INIT();
#endif

  Serial.println("Beginning");
  // Init Display

  Wire.setClock(400000); // speed up I2C 
  if (!gfx->begin()) {
    Serial.println("gfx->begin() failed!");
    while (1) delay(10);
  }
  gfx->fillScreen(BLUE);

  expander->pinMode(PCA_TFT_BACKLIGHT, OUTPUT);
  expander->digitalWrite(PCA_TFT_BACKLIGHT, HIGH);

  DISPLAY_SIZE =  min(gfx->width(), gfx->height());
  if (DISPLAY_SIZE > 480) { 
    DISPLAY_SIZE /= 2; // pixel doubling!
    scaling = 2;
  }
  // No file selector yet. In the meantime, you can override the default
  // config file by holding one of the 3 edge buttons at startup (loads
  // config1.eye, config2.eye or config3.eye instead). Keep fingers clear
  // of the nose booper when doing this...it self-calibrates on startup.
  // DO THIS BEFORE THE SPLASH SO IT DOESN'T REQUIRE A LENGTHY HOLD.
  char *filename = (char *)"config.eye";
 
  expander->pinMode(PCA_BUTTON_UP, INPUT);
  expander->pinMode(PCA_BUTTON_DOWN, INPUT);

  if((! expander->digitalRead(PCA_BUTTON_DOWN)) && fatfs.exists("config1.eye")) {
    filename = (char *)"config1.eye";
  } else if((! expander->digitalRead(PCA_BUTTON_UP)) && fatfs.exists("config2.eye")) {
    filename = (char *)"config2.eye";
  }


  yield();
  // Initialize display(s)
  eye[0].display = gfx;

  uint8_t e;
  for(e=0; e<NUM_EYES; e++) {
    eye[e].display->fillScreen(0);

    // Default settings that can be overridden in config file
    eye[e].pupilColor        = 0x0000;
    eye[e].backColor         = 0xFFFF;
    eye[e].iris.color        = 0xFF01;
    eye[e].iris.data         = NULL;
    eye[e].iris.filename     = NULL;
    eye[e].iris.startAngle   = (e & 1) ? 512 : 0; // Rotate alternate eyes 180 degrees
    eye[e].iris.angle        = eye[e].iris.startAngle;
    eye[e].iris.mirror       = 0;
    eye[e].iris.spin         = 0.0;
    eye[e].iris.iSpin        = 0;
    eye[e].sclera.color      = 0xFFFF;
    eye[e].sclera.data       = NULL;
    eye[e].sclera.filename   = NULL;
    eye[e].sclera.startAngle = (e & 1) ? 512 : 0; // Rotate alternate eyes 180 degrees
    eye[e].sclera.angle      = eye[e].sclera.startAngle;
    eye[e].sclera.mirror     = 0;
    eye[e].sclera.spin       = 0.0;
    eye[e].sclera.iSpin      = 0;
    eye[e].rotation          = 3;

    // Uncanny eyes carryover stuff for now, all messy:
    eye[e].blink.state = NOBLINK;
    eye[e].blinkFactor = 0.0;
  }
  // SPLASH SCREEN (IF FILE PRESENT) ---------------------------------------

  yield();
  uint32_t startTime, elapsed;
  if (showSplashScreen) {
    /*
    showSplashScreen = ((theImageReader.drawBMP((char *)"/splash.bmp",
                         0, 0, eye[0].display)) == IMAGE_SUCCESS);
    if (showSplashScreen) { // Loaded OK?
      Serial.println("Splashing");
      if (NUM_EYES > 1) {   // Load on other eye too, ignore status
        yield();
        theImageReader.drawBMP((char *)"/splash.bmp", 0, 0, eye[1].display);
      }
      expander->digitalWrite(PCA_TFT_BACKLIGHT, HIGH);
      startTime = millis();     // Note current time for backlight hold later
    }
    */
  }

  // If no splash, or load failed, turn backlight on early so user gets a
  // little feedback, that the board is not locked up, just thinking.
  if (!showSplashScreen) expander->digitalWrite(PCA_TFT_BACKLIGHT, HIGH);

  // LOAD CONFIGURATION FILE -----------------------------------------------

  loadConfig(filename);

  // LOAD EYELIDS AND TEXTURE MAPS -----------------------------------------

  // Load texture maps for eyes
  uint8_t e2;
  for(e=0; e<NUM_EYES; e++) { // For each eye...
    yield();
    for(e2=0; e2<e; e2++) {    // Compare against each prior eye...
      // If both eyes have the same iris filename...
      if((eye[e].iris.filename && eye[e2].iris.filename) &&
         (!strcmp(eye[e].iris.filename, eye[e2].iris.filename))) {
        // Then eye 'e' can share the iris graphics from 'e2'
        // rotate & mirror are kept distinct, just share image
        eye[e].iris.data   = eye[e2].iris.data;
        eye[e].iris.width  = eye[e2].iris.width;
        eye[e].iris.height = eye[e2].iris.height;
        break;
      }
    }
    if((!e) || (e2 >= e)) { // If first eye, or no match found...
      // If no iris filename was specified, or if file fails to load...
      if((eye[e].iris.filename == NULL) || (loadTexture(eye[e].iris.filename,
        &eye[e].iris.data, &eye[e].iris.width, &eye[e].iris.height) != IMAGE_SUCCESS)) {
        // Point iris data at the color variable and set image size to 1px
        eye[e].iris.data  = &eye[e].iris.color;
        eye[e].iris.width = eye[e].iris.height = 1;
        Serial.printf("Iris load texture fail: %s\n\r", eye[e].iris.filename);
      }
    }
    // Repeat for sclera...
    for(e2=0; e2<e; e2++) {    // Compare against each prior eye...
      // If both eyes have the same sclera filename...
      if((eye[e].sclera.filename && eye[e2].sclera.filename) &&
         (!strcmp(eye[e].sclera.filename, eye[e2].sclera.filename))) {
        // Then eye 'e' can share the sclera graphics from 'e2'
        // rotate & mirror are kept distinct, just share image
        eye[e].sclera.data   = eye[e2].sclera.data;
        eye[e].sclera.width  = eye[e2].sclera.width;
        eye[e].sclera.height = eye[e2].sclera.height;
        break;
      }
    }
    if((!e) || (e2 >= e)) { // If first eye, or no match found...
      // If no sclera filename was specified, or if file fails to load...
      if((eye[e].sclera.filename == NULL) || (loadTexture(eye[e].sclera.filename,
        &eye[e].sclera.data, &eye[e].sclera.width, &eye[e].sclera.height) != IMAGE_SUCCESS)) {
        // Point sclera data at the color variable and set image size to 1px
        eye[e].sclera.data  = &eye[e].sclera.color;
        eye[e].sclera.width = eye[e].sclera.height = 1;
        Serial.printf("Sclera load texture fail: %s\n\r", eye[e].sclera.filename);
      }
    }
  }
  // Load eyelid graphics.
  yield();
  ImageReturnCode status;
 
  status = loadEyelid(upperEyelidFilename ?
    upperEyelidFilename : (char *)"upper.bmp",
    upperClosed, upperOpen, DISPLAY_SIZE-1);
  if (status != IMAGE_SUCCESS) {
    Serial.println("Upper eyelid load fail");
  } 

  // print out contents of upperclosed & upperopen
  for (int i = 0; i < DISPLAY_SIZE; i++) {
    Serial.printf("upperclosed[%d] = %d\tupperopen[%d] = %d\n\r", i, upperClosed[i], i, upperOpen[i]);
  }

  status = loadEyelid(lowerEyelidFilename ?
    lowerEyelidFilename : (char *)"lower.bmp",
    lowerOpen, lowerClosed, 0);
  if (status != IMAGE_SUCCESS) {
    Serial.println("Lower eyelid load fail");
  } 
  Serial.println("Loaded eyelids");

  calcMap();
  calcDisplacement();

  randomSeed(analogRead(A0));
  eyeOldX = eyeNewX = eyeOldY = eyeNewY = mapRadius; // Start in center
  for(e=0; e<NUM_EYES; e++) { // For each eye...
    //eye[e].display->setRotation(eye[e].rotation);  // MEME FIX
    eye[e].eyeX = eyeOldX; // Set up initial position
    eye[e].eyeY = eyeOldY;
  }

  if (showSplashScreen) { // Image(s) loaded above?
    // Hold backlight on for up to 2 seconds (minus other initialization time)
    if ((elapsed = (millis() - startTime)) < 2000) {
      delay(2000 - elapsed);
    }
    expander->digitalWrite(PCA_TFT_BACKLIGHT, LOW);
    for(e=0; e<NUM_EYES; e++) {
      eye[e].display->fillScreen(0);
      eye[e].colNum = 0;
    }
  }

  expander->digitalWrite(PCA_TFT_BACKLIGHT, HIGH); // Back on, impending graphics

  yield();

  lastLightReadTime = micros() + 2000000; // Delay initial light reading

  pinMode(SCK, OUTPUT);
  pinMode(MOSI, OUTPUT);
  pinMode(MISO, OUTPUT);
  pinMode(SS, OUTPUT);
}


// LOOP FUNCTION - CALLED REPEATEDLY UNTIL POWER-OFF -----------------------

/*
The loop() function in this code is a weird animal, operating a bit
differently from the earlier "Uncanny Eyes" eye project. Whereas in the
prior project we did this:

  for(each eye) {
    * do position calculations, etc. for one frame of animation *
    for(each scanline) {
      * draw a row of pixels *
    }
  }

This new code works "inside out," more like this:

  for(each column) {
    if(first column of display) {
      * do position calculations, etc. for one frame of animation *
    }
    * draw a column of pixels *
  }

The reasons for this are that A) we have an INORDINATE number of pixels to
draw compared to the old project (nearly 4X as much), and B) each screen is
now on its own SPI bus...data can be issued concurrently...so, rather than
stalling in a while() loop waiting for each scanline transfer to complete
(just wasting cycles), the code looks for opportunities to work on other
eyes (the eye updates aren't necessarily synchronized; each can function at
an independent frame rate depending on particular complexity at the moment).
*/

// LOOP FUNCTION - CALLED REPEATEDLY UNTIL POWER-OFF -----------------------

/*
The loop() function in this code is a weird animal, operating a bit
differently from the earlier "Uncanny Eyes" eye project. Whereas in the
prior project we did this:

  for(each eye) {
    * do position calculations, etc. for one frame of animation *
    for(each scanline) {
      * draw a row of pixels *
    }
  }

This new code works "inside out," more like this:

  for(each column) {
    if(first column of display) {
      * do position calculations, etc. for one frame of animation *
    }
    * draw a column of pixels *
  }

The reasons for this are that A) we have an INORDINATE number of pixels to
draw compared to the old project (nearly 4X as much), and B) each screen is
now on its own SPI bus...data can be issued concurrently...so, rather than
stalling in a while() loop waiting for each scanline transfer to complete
(just wasting cycles), the code looks for opportunities to work on other
eyes (the eye updates aren't necessarily synchronized; each can function at
an independent frame rate depending on particular complexity at the moment).
*/

// loop() function processes ONE COLUMN of ONE EYE...
uint32_t timestamp = 0;

void loop() {
  uint16_t column[MAX_DISPLAY_SIZE];
  if(++eyeNum >= NUM_EYES) eyeNum = 0; // Cycle through eyes...

  uint16_t  x = eye[eyeNum].colNum;
  uint32_t t = micros();
  //Serial.println(x);
  if(!x) { // If it's the first column...
    digitalWrite(SS, HIGH);
    Serial.printf("Timestamp: %d ms\n\r", millis() - timestamp);
    timestamp = millis();
    // ONCE-PER-FRAME EYE ANIMATION LOGIC HAPPENS HERE -------------------

    // Eye movement
    float eyeX, eyeY;
    if(moveEyesRandomly) {
      int32_t dt = t - eyeMoveStartTime;      // uS elapsed since last eye event
      if(eyeInMotion) {                       // Eye currently moving?
        if(dt >= eyeMoveDuration) {           // Time up?  Destination reached.
          eyeInMotion = false;                // Stop moving
          // The "move" duration temporarily becomes a hold duration...
          // Normally this is 35 ms to 1 sec, but don't exceed gazeMax setting
          uint32_t limit = min((uint32_t)1000000, gazeMax);
          eyeMoveDuration = random(35000, limit); // Time between microsaccades
          if(!saccadeInterval) {              // Cleared when "big" saccade finishes
            lastSaccadeStop = t;              // Time when saccade stopped
            saccadeInterval = random(eyeMoveDuration, gazeMax); // Next in 30ms to 3sec
          }
          // Similarly, the "move" start time becomes the "stop" starting time...
          eyeMoveStartTime = t;               // Save time of event
          eyeX = eyeOldX = eyeNewX;           // Save position
          eyeY = eyeOldY = eyeNewY;
        } else { // Move time's not yet fully elapsed -- interpolate position
          float e  = (float)dt / float(eyeMoveDuration); // 0.0 to 1.0 during move
          e = 3 * e * e - 2 * e * e * e; // Easing function: 3*e^2-2*e^3 0.0 to 1.0
          eyeX = eyeOldX + (eyeNewX - eyeOldX) * e; // Interp X
          eyeY = eyeOldY + (eyeNewY - eyeOldY) * e; // and Y
        }
      } else {                       // Eye is currently stopped
        eyeX = eyeOldX;
        eyeY = eyeOldY;
        if(dt > eyeMoveDuration) {   // Time up?  Begin new move.
          if((t - lastSaccadeStop) > saccadeInterval) { // Time for a "big" saccade
            // r is the radius in X and Y that the eye can go, from (0,0) in the center.
            float r = ((float)mapDiameter - (float)DISPLAY_SIZE * M_PI_2) * 0.75;
            Serial.printf("mapDiameter: %d, DISPLAY_SIZE: %d, r: %f\n\r", mapDiameter, DISPLAY_SIZE, r);
            eyeNewX = random(-r, r);
            float h = sqrt(r * r - eyeNewX * eyeNewX);
            eyeNewY = random(-h, h);
            // Set the duration for this move, and start it going.
            eyeMoveDuration = random(83000, 166000); // ~1/12 - ~1/6 sec
            saccadeInterval = 0; // Calc next interval when this one stops
          } else { // Microsaccade
            // r is possible radius of motion, ~1/10 size of full saccade.
            // We don't bother with clipping because if it strays just a little,
            // that's okay, it'll get put in-bounds on next full saccade.
            float r = (float)mapDiameter - (float)DISPLAY_SIZE * M_PI_2;
            r *= 0.07;
            float dx = random(-r, r);
            eyeNewX = eyeX - mapRadius + dx;
            float h = sqrt(r * r - dx * dx);
            eyeNewY = eyeY - mapRadius + random(-h, h);
            eyeMoveDuration = random(7000, 25000); // 7-25 ms microsaccade
          }
          eyeNewX += mapRadius;    // Translate new point into map space
          eyeNewY += mapRadius;
          eyeMoveStartTime = t;    // Save initial time of move
          eyeInMotion      = true; // Start move on next frame
        }
      }
    } else {
      // Allow user code to control eye position (e.g. IR sensor, joystick, etc.)
      float r = ((float)mapDiameter - (float)DISPLAY_SIZE * M_PI_2) * 0.9;
      eyeX = mapRadius + eyeTargetX * r;
      eyeY = mapRadius + eyeTargetY * r;
    }

    // Eyes fixate (are slightly crossed) -- amount is filtered for boops
    int nufix = 7;
    fixate = ((fixate * 15) + nufix) / 16;
    // save eye position to this eye's struct so it's same throughout render
    if(eyeNum & 1) eyeX += fixate; // Eyes converge slightly toward center
    else           eyeX -= fixate;
    eye[eyeNum].eyeX = eyeX;
    eye[eyeNum].eyeY = eyeY;

    //Serial.printf("eye location: (%f, %f)\n\r", eyeX, eyeY);

    // pupilFactor? irisValue? TO DO: pick a name and stick with it
    eye[eyeNum].pupilFactor = irisValue;
    // Also note - irisValue is calculated at the END of this function
    // for the next frame (because the sensor must be read when there's
    // no SPI traffic to the left eye)

    // Similar to the autonomous eye movement above -- blink start times
    // and durations are random (within ranges).
    if((t - timeOfLastBlink) >= timeToNextBlink) { // Start new blink?
      timeOfLastBlink = t;
      uint32_t blinkDuration = random(36000, 72000); // ~1/28 - ~1/14 sec
      // Set up durations for both eyes (if not already winking)
      for(uint8_t e=0; e<NUM_EYES; e++) {
        if(eye[e].blink.state == NOBLINK) {
          eye[e].blink.state     = ENBLINK;
          eye[e].blink.startTime = t;
          eye[e].blink.duration  = blinkDuration;
          //Serial.println("Blink");
        }
      }
      timeToNextBlink = blinkDuration * 3 + random(4000000);
    }

    float uq, lq; // So many sloppy temp vars in here for now, sorry
    if(tracking) {
      // Eyelids naturally "track" the pupils (move up or down automatically)
      int ix = (int)map2screen(mapRadius - eye[eyeNum].eyeX) + (DISPLAY_SIZE/2), // Pupil position
          iy = (int)map2screen(mapRadius - eye[eyeNum].eyeY) + (DISPLAY_SIZE/2); // on screen
      iy += irisRadius * trackFactor;
      if(eyeNum & 1) ix = DISPLAY_SIZE - 1 - ix; // Flip for right eye
      if(iy > upperOpen[ix]) {
        uq = 1.0;
      } else if(iy < upperClosed[ix]) {
        uq = 0.0;
      } else {
        uq = (float)(iy - upperClosed[ix]) / (float)(upperOpen[ix] - upperClosed[ix]);
      }
      lq = 1.0 - uq;
    } else {
      // If no tracking, eye is FULLY OPEN when not blinking
      uq = 1.0;
      lq = 1.0;
    }
    // Dampen eyelid movements slightly
    // SAVE upper & lower lid factors per eye,
    // they need to stay consistent across frame
    eye[eyeNum].upperLidFactor = (eye[eyeNum].upperLidFactor * 0.6) + (uq * 0.4);
    eye[eyeNum].lowerLidFactor = (eye[eyeNum].lowerLidFactor * 0.6) + (lq * 0.4);

    // Process blinks
    if(eye[eyeNum].blink.state) { // Eye currently blinking?
      // Check if current blink state time has elapsed
      if((t - eye[eyeNum].blink.startTime) >= eye[eyeNum].blink.duration) {
        if(++eye[eyeNum].blink.state > DEBLINK) { // Deblinking finished?
          eye[eyeNum].blink.state = NOBLINK;      // No longer blinking
          eye[eyeNum].blinkFactor = 0.0;
        } else { // Advancing from ENBLINK to DEBLINK mode
          eye[eyeNum].blink.duration *= 2; // DEBLINK is 1/2 ENBLINK speed
          eye[eyeNum].blink.startTime = t;
          eye[eyeNum].blinkFactor = 1.0;
        }
      } else {
        eye[eyeNum].blinkFactor = (float)(t - eye[eyeNum].blink.startTime) / (float)eye[eyeNum].blink.duration;
        if(eye[eyeNum].blink.state == DEBLINK) eye[eyeNum].blinkFactor = 1.0 - eye[eyeNum].blinkFactor;
      }
    }

    // Periodically report frame rate. Really this is "total number of
    // eyeballs drawn." If there are two eyes, the overall refresh rate
    // of both screens is about 1/2 this.
    frames++;
    if(((t - lastFrameRateReportTime) >= 1000000) && t) { // Once per sec.
      Serial.println((frames * 1000) / (t / 1000));
      lastFrameRateReportTime = t;
    }

    float mins = (float)millis() / 60000.0;
    if(eye[eyeNum].iris.iSpin) {
      // Spin works in fixed amount per frame (eyes may lose sync, but "wagon wheel" tricks work)
      eye[eyeNum].iris.angle   += eye[eyeNum].iris.iSpin;
    } else {
      // Keep consistent timing in spin animation (eyes stay in sync, no "wagon wheel" effects)
      eye[eyeNum].iris.angle    = (int)((float)eye[eyeNum].iris.startAngle   + eye[eyeNum].iris.spin   * mins + 0.5);
    }
    if(eye[eyeNum].sclera.iSpin) {
      eye[eyeNum].sclera.angle += eye[eyeNum].sclera.iSpin;
    } else {
      eye[eyeNum].sclera.angle  = (int)((float)eye[eyeNum].sclera.startAngle + eye[eyeNum].sclera.spin * mins + 0.5);
    }
    digitalWrite(SS, LOW);
    // END ONCE-PER-FRAME EYE ANIMATION ----------------------------------

  } // end first-scanline check
  // PER-COLUMN RENDERING ------------------------------------------------

  digitalWrite(SCK, HIGH);
  // Should be possible for these to be local vars,
  // but the animation becomes super chunky then, what gives?
  xPositionOverMap = (int)(eye[eyeNum].eyeX - (DISPLAY_SIZE/2.0));
  yPositionOverMap = (int)(eye[eyeNum].eyeY - (DISPLAY_SIZE/2.0));

  // These are constant across frame and could be stored in eye struct
  float upperLidFactor = (1.0 - eye[eyeNum].blinkFactor) * eye[eyeNum].upperLidFactor,
        lowerLidFactor = (1.0 - eye[eyeNum].blinkFactor) * eye[eyeNum].lowerLidFactor;
  iPupilFactor = (int)((float)eye[eyeNum].iris.height * 256 * (1.0 / eye[eyeNum].pupilFactor));

  int y1, y2;
  int lidColumn = (eyeNum & 1) ? (DISPLAY_SIZE - 1 - x) : x; // Reverse eyelid columns for left eye

  // Render column 'x' into eye's next available renderBuf
  uint16_t *ptr = column; //eye[eyeNum].column;
  memset(ptr, 0x0, DISPLAY_SIZE * 2); // Fill with background color

  if(upperOpen[lidColumn] == 65535) {
    // No eyelid data for this line; eyelid image is smaller than screen.
    // Great! Make a full scanline of nothing, no rendering needed:
  } else {
    y1 = lowerClosed[lidColumn] + (int)(0.5 + lowerLidFactor *
      (float)((int)lowerOpen[lidColumn] - (int)lowerClosed[lidColumn]));
    y2 = upperClosed[lidColumn] + (int)(0.5 + upperLidFactor *
      (float)((int)upperOpen[lidColumn] - (int)upperClosed[lidColumn]));
    if(y1 > DISPLAY_SIZE-1)    y1 = DISPLAY_SIZE-1; // Clip results in case lidfactor
    else if(y1 < 0) y1 = 0;   // is beyond the usual 0.0 to 1.0 range
    if(y2 > DISPLAY_SIZE-1)    y2 = DISPLAY_SIZE-1;
    else if(y2 < 0) y2 = 0;

    //Serial.printf("Eye opening from %d to %d\n\r", y1, y2);

    if(y1 >= y2) {
      // Eyelid is fully or partially closed, enough that there are no
      // pixels to be rendered for this line. Make "nothing," as above.
    } else {
      // If single eye, dynamically build descriptor list as needed,
      // else use a single descriptor & fully buffer each line.

      int xx = xPositionOverMap + x;
      int y;
      for(y=0; y<y1; y++) *ptr++ = eyelidColor;

      // tablegen.cpp explains a bit of the displacement mapping trick.
      uint16_t *displaceX, *displaceY;
      int16_t   xmul; // Sign of X displacement: +1 or -1
      int      doff; // Offset into displacement arrays
      if(x < (DISPLAY_SIZE/2)) {  // Left half of screen (quadrants 2, 3)
        displaceX = &displace[ (DISPLAY_SIZE/2 - 1) - x       ];
        displaceY = &displace[((DISPLAY_SIZE/2 - 1) - x) * (DISPLAY_SIZE/2)];
        xmul      = -1; // X displacement is always negative
      } else {       // Right half of screen( quadrants 1, 4)
        displaceX = &displace[ x - (DISPLAY_SIZE/2)       ];
        displaceY = &displace[(x - (DISPLAY_SIZE/2)) * (DISPLAY_SIZE/2)];
        xmul      =  1; // X displacement is always positive
      }
      digitalWrite(MOSI, HIGH);
      for(; y<=y2; y++) { // For each pixel of open eye in this column...
        int yy = yPositionOverMap + y;
        int dx, dy;

        if(y < (DISPLAY_SIZE/2)) { // Lower half of screen (quadrants 3, 4)
          doff = (DISPLAY_SIZE/2 - 1) - y;
          dy   = -displaceY[doff];
        } else {      // Upper half of screen (quadrants 1, 2)
          doff = y - (DISPLAY_SIZE/2);
          dy   =  displaceY[doff];
        }
        dx = displaceX[doff * (DISPLAY_SIZE/2)];
        if(dx < 65535) {      // Inside eyeball area
          dx *= xmul;       // Flip sign of x offset if in quadrants 2 or 3
          int mx = xx + dx; // Polar angle/dist map coords
          int my = yy + dy;
          if((mx >= 0) && (mx < mapDiameter) && (my >= 0) && (my < mapDiameter)) {
            // Inside polar angle/dist map
            int angle, dist, moff;
            if(my >= mapRadius) {
              if(mx >= mapRadius) { // Quadrant 1
                // Use angle & dist directly
                mx   -= mapRadius;
                my   -= mapRadius;
                moff  = my * mapRadius + mx; // Offset into map arrays
                angle = polarAngle[moff];
                dist  = polarDist[moff];
              } else {                // Quadrant 2
                // ROTATE angle by 90 degrees (270 degrees clockwise; 768)
                // MIRROR dist on X axis
                mx    = mapRadius - 1 - mx;
                my   -= mapRadius;
                angle = polarAngle[mx * mapRadius + my] + 768;
                dist  = polarDist[ my * mapRadius + mx];
              }
            } else {
              if(mx < mapRadius) {  // Quadrant 3
                // ROTATE angle by 180 degrees
                // MIRROR dist on X & Y axes
                mx    = mapRadius - 1 - mx;
                my    = mapRadius - 1 - my;
                moff  = my * mapRadius + mx;
                angle = polarAngle[moff] + 512;
                dist  = polarDist[ moff];
              } else {                // Quadrant 4
                // ROTATE angle by 270 degrees (90 degrees clockwise; 256)
                // MIRROR dist on Y axis
                mx   -= mapRadius;
                my    = mapRadius - 1 - my;
                angle = polarAngle[mx * mapRadius + my] + 256;
                dist  = polarDist[ my * mapRadius + mx];
              }
            }
            // Convert angle/dist to texture map coords
            if(dist >= 0) { // Sclera
              angle = ((angle + eye[eyeNum].sclera.angle) & 1023) ^ eye[eyeNum].sclera.mirror;
              int tx = angle * eye[eyeNum].sclera.width  / 1024; // Texture map x/y
              int ty = dist  * eye[eyeNum].sclera.height / 128;
              *ptr++ = eye[eyeNum].sclera.data[ty * eye[eyeNum].sclera.width + tx];
            } else if(dist > -128) { // Iris or pupil
              int ty = dist * iPupilFactor / -32768;
              if(ty >= eye[eyeNum].iris.height) { // Pupil
                *ptr++ = eye[eyeNum].pupilColor;
              } else { // Iris
                angle = ((angle + eye[eyeNum].iris.angle) & 1023) ^ eye[eyeNum].iris.mirror;
                int tx = angle * eye[eyeNum].iris.width / 1024;
                *ptr++ = eye[eyeNum].iris.data[ty * eye[eyeNum].iris.width + tx];
              }
            } else {
              *ptr++ = eye[eyeNum].backColor; // Back of eye
            }
          } else {
            *ptr++ = eye[eyeNum].backColor; // Off map, use back-of-eye color
          }
        } else { // Outside eyeball area
          *ptr++ = eyelidColor;
        }
      }
      digitalWrite(MOSI, LOW);

      for(; y<DISPLAY_SIZE; y++) *ptr++ = eyelidColor;
    }
  }
  digitalWrite(SCK, LOW);

  digitalWrite(MISO, HIGH);

  uint8_t *framebuf = (uint8_t *) gfx->getFramebuffer();
  uint16_t colnum = eye[eyeNum].colNum;
  if (scaling == 1) {
    memcpy(framebuf+(colnum * DISPLAY_SIZE * 2), column, DISPLAY_SIZE * 2);
  } else if (scaling == 2) {
    uint16_t scaled[DISPLAY_SIZE * 2];

    for(int i = 0; i < DISPLAY_SIZE; i++) {
        uint16_t pixel = column[i];
        scaled[i * 2] = pixel;
        scaled[i * 2 + 1] = pixel;
    }
    memcpy(framebuf + ((2*colnum) * DISPLAY_SIZE * 4), scaled, DISPLAY_SIZE * 4);
    memcpy(framebuf + ((2*colnum + 1) * DISPLAY_SIZE * 4), scaled, DISPLAY_SIZE * 4);
  }
  //gfx->draw16bitRGBBitmap(0, eye[eyeNum].colNum, column, DISPLAY_SIZE, 1);

  // At this point, above checks confirm that column is ready and DMA is free
  if(!x) { // If it's the first column...
    if(eyeNum == (NUM_EYES-1)) {
      // Handle pupil scaling
      if(lightSensorPin >= 0) {
        // Read light sensor, but not too often (Seesaw hates that)
        #define LIGHT_INTERVAL (1000000 / 10) // 10 Hz, don't poll Seesaw too often
        if((t - lastLightReadTime) >= LIGHT_INTERVAL) {
          // Fun fact: eyes have a "consensual response" to light -- both
          // pupils will react even if the opposite eye is stimulated.
          // Meaning we can get away with using a single light sensor for
          // both eyes. This comment has nothing to do with the code.
          uint16_t rawReading = analogRead(lightSensorPin);
          if(rawReading <= 1023) {
            if(rawReading < lightSensorMin)      rawReading = lightSensorMin; // Clamp light sensor range
            else if(rawReading > lightSensorMax) rawReading = lightSensorMax; // to within usable range
            float v = (float)(rawReading - lightSensorMin) / (float)(lightSensorMax - lightSensorMin); // 0.0 to 1.0
            v = pow(v, lightSensorCurve);
            lastLightValue    = irisMin + v * irisRange;
            lastLightReadTime = t;
            lightSensorFailCount = 0;
          }
        }
        irisValue = (irisValue * 0.97) + (lastLightValue * 0.03); // Filter response for smooth reaction
      } else {
        // Not light responsive. Use autonomous iris w/fractal subdivision
        float n, sum = 0.5;
        for(uint16_t i=0; i<IRIS_LEVELS; i++) { // 0,1,2,3,...
          uint16_t iexp  = 1 << (i+1);          // 2,4,8,16,...
          uint16_t imask = (iexp - 1);          // 2^i-1 (1,3,7,15,...)
          uint16_t ibits = iris_frame & imask;  // 0 to mask
          if(ibits) {
            float weight = (float)ibits / (float)iexp; // 0.0 to <1.0
            n            = iris_prev[i] * (1.0 - weight) + iris_next[i] * weight;
          } else {
            n            = iris_next[i];
            iris_prev[i] = iris_next[i];
            iris_next[i] = -0.5 + ((float)random(1000) / 999.0); // -0.5 to +0.5
          }
          iexp = 1 << (IRIS_LEVELS - i); // ...8,4,2,1
          sum += n / (float)iexp;
        }
        irisValue = irisMin + (sum * irisRange); // 0.0-1.0 -> iris min/max
        if((++iris_frame) >= (1 << IRIS_LEVELS)) iris_frame = 0;
      }
      user_loop();
    }
  }
  if(++eye[eyeNum].colNum >= DISPLAY_SIZE) { // If last line sent...
    eye[eyeNum].colNum      = 0;    // Wrap to beginning
  }
  digitalWrite(MISO, LOW);
}

/*
void loop()
{
  Serial.println("Hello!");
  gfx->fillScreen(BLACK);
  gfx->setCursor(0, gfx->height() / 2 - 75);
  gfx->setTextSize(5);
  gfx->setTextColor(WHITE);
  gfx->setTextWrap(false);
  gfx->println("Hello World 123");

  gfx->setCursor(0, gfx->height() / 2 - 25);
  gfx->setTextColor(RED);
  gfx->println("RED");

  gfx->setCursor(0, gfx->height() / 2 + 25);
  gfx->setTextColor(GREEN);
  gfx->println("GREEN");

  gfx->setCursor(00, gfx->height() / 2 + 75);
  gfx->setTextColor(BLUE);
  gfx->println("BLUE");

  delay(3000);

  gfx->fillScreen(RED);
  delay(500);
  gfx->fillScreen(GREEN);
  delay(500);
  gfx->fillScreen(BLUE);
  delay(500);
  gfx->fillScreen(WHITE);
  delay(500);
}*/