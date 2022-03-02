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

#if !defined(USE_TINYUSB)
  #error "Please select Tools->USB Stack->TinyUSB before compiling"
#endif

#define GLOBAL_VAR
#include "globals.h"

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
uint32_t boopSum                 = 0,
         boopSumFiltered         = 0;
bool     booped                  = false;
int      fixate                  = 7;
uint8_t  lightSensorFailCount    = 0;

// For autonomous iris scaling
#define  IRIS_LEVELS 7
float    iris_prev[IRIS_LEVELS] = { 0 };
float    iris_next[IRIS_LEVELS] = { 0 };
uint16_t iris_frame = 0;

// Callback invoked after each SPI DMA transfer - sets a flag indicating
// the next line of graphics can be issued as soon as its ready.
static void dma_callback(Adafruit_ZeroDMA *dma) {
  // It's possible to assign each DMA channel its own callback function
  // (freeing up a few cycles vs. this channel-to-eye lookup), but it's
  // written this way to scale to as many eyes as needed (up to one per
  // SERCOM if this is ported to something like Grand Central).
  for(uint8_t e=0; e<NUM_EYES; e++) {
    if(dma == &eye[e].dma) {
      eye[e].dma_busy = false;
      return;
    }
  }
}

// >50MHz SPI was fun but just too glitchy to rely on
//#if F_CPU < 200000000
// #define DISPLAY_FREQ   (F_CPU / 2)
// #define DISPLAY_CLKSRC SERCOM_CLOCK_SOURCE_FCPU
//#else
 #define DISPLAY_FREQ   50000000
 #define DISPLAY_CLKSRC SERCOM_CLOCK_SOURCE_100M
//#endif

SPISettings settings(DISPLAY_FREQ, MSBFIRST, SPI_MODE0);

// The time required to issue one scanline (DISPLAY_SIZE pixels x 16 bits) over
// SPI is a known(ish) quantity. The DMA scheduler isn't always perfectly
// deterministic though...especially on startup, as things make their way
// into caches. Very occasionally, something (not known yet) is causing
// SPI DMA to seize up. This condition is pretty easy to check for...
// periodically the code needs to wait on a DMA transfer to finish
// anyway, and we can use the micros() function to determine if it's taken
// considerably longer than expected (a factor of 4 is used - the "4000"
// below, to allow for caching/scheduling fudge). If so, that's our signal
// that something is likely amiss and we take evasive maneuvers, resetting
// the affected DMA channel (DMAbuddy::fix()).
#define DMA_TIMEOUT (uint32_t)((DISPLAY_SIZE * 16 * 4000) / (DISPLAY_FREQ / 1000))

static inline uint16_t readBoop(void) {
  uint16_t counter = 0;
  pinMode(boopPin, OUTPUT);
  digitalWrite(boopPin, HIGH);
  pinMode(boopPin, INPUT);
  while(digitalRead(boopPin) && (++counter < 1000));
  return counter;
}

// Crude error handler. Prints message to Serial Monitor, blinks LED.
void fatal(const char *message, uint16_t blinkDelay) {
  Serial.begin(9600);
  Serial.println(message);
  for(bool ledState = HIGH;; ledState = !ledState) {
    digitalWrite(LED_BUILTIN, ledState);
    delay(blinkDelay);
  }
}

#include <unistd.h> // sbrk() function

uint32_t availableRAM(void) {
  char top;                      // Local variable pushed on stack
  return &top - (char *)sbrk(0); // Top of stack minus end of heap
}

// SETUP FUNCTION - CALLED ONCE AT PROGRAM START ---------------------------

void setup() {
  if(!arcada.arcadaBegin())     fatal("Arcada init fail!", 100);
#if defined(USE_TINYUSB)
  if(!arcada.filesysBeginMSD()) fatal("No filesystem found!", 250);
#else
  if(!arcada.filesysBegin())    fatal("No filesystem found!", 250);
#endif

  user_setup();

  arcada.displayBegin();

  // Backlight(s) off ASAP, they'll switch on after screen(s) init & clear
  arcada.setBacklight(0);

  DISPLAY_SIZE = min(ARCADA_TFT_WIDTH, ARCADA_TFT_HEIGHT);

  Serial.begin(115200);
  //while(!Serial) yield();

  Serial.printf("Available RAM at start: %d\n", availableRAM());
  Serial.printf("Available flash at start: %d\n", arcada.availableFlash());
  yield(); // Periodic yield() makes sure mass storage filesystem stays alive

  // No file selector yet. In the meantime, you can override the default
  // config file by holding one of the 3 edge buttons at startup (loads
  // config1.eye, config2.eye or config3.eye instead). Keep fingers clear
  // of the nose booper when doing this...it self-calibrates on startup.
  // DO THIS BEFORE THE SPLASH SO IT DOESN'T REQUIRE A LENGTHY HOLD.
  char *filename = (char *)"config.eye";
 
  uint32_t buttonState = arcada.readButtons();
  if((buttonState & ARCADA_BUTTONMASK_UP) && arcada.exists("config1.eye")) {
    filename = (char *)"config1.eye";
  } else if((buttonState & ARCADA_BUTTONMASK_A) && arcada.exists("config2.eye")) {
    filename = (char *)"config2.eye";
  } else if((buttonState & ARCADA_BUTTONMASK_DOWN) && arcada.exists("config3.eye")) {
    filename = (char *)"config3.eye";
  }

  yield();
  // Initialize display(s)
#if (NUM_EYES > 1)
  eye[0].display = arcada._display;
  eye[1].display = arcada.display2;  
#else
  eye[0].display = arcada.display;
#endif

  // Initialize DMAs
  yield();
  uint8_t e;
  for(e=0; e<NUM_EYES; e++) {
#if (ARCADA_TFT_WIDTH != 160) && (ARCADA_TFT_HEIGHT != 128) // 160x128 is ST7735 which isn't able to deal
    eye[e].spi->setClockSource(DISPLAY_CLKSRC); // Accelerate SPI!
#endif
    eye[e].display->fillScreen(0);
    eye[e].dma.allocate();
    eye[e].dma.setTrigger(eye[e].spi->getDMAC_ID_TX());
    eye[e].dma.setAction(DMA_TRIGGER_ACTON_BEAT);
    eye[e].dptr = eye[e].dma.addDescriptor(NULL, NULL, 42, DMA_BEAT_SIZE_BYTE, false, false);
    eye[e].dma.setCallback(dma_callback);
    eye[e].dma.setPriority(DMA_PRIORITY_0);
    uint32_t spi_data_reg = (uint32_t)eye[e].spi->getDataRegister();
    for(int i=0; i<2; i++) {   // For each of 2 scanlines...
      for(int j=0; j<NUM_DESCRIPTORS; j++) { // For each descriptor on scanline...
        eye[e].column[i].descriptor[j].BTCTRL.bit.VALID    = true;
        eye[e].column[i].descriptor[j].BTCTRL.bit.EVOSEL   = DMA_EVENT_OUTPUT_DISABLE;
        eye[e].column[i].descriptor[j].BTCTRL.bit.BLOCKACT = DMA_BLOCK_ACTION_NOACT;
        eye[e].column[i].descriptor[j].BTCTRL.bit.BEATSIZE = DMA_BEAT_SIZE_BYTE;
        eye[e].column[i].descriptor[j].BTCTRL.bit.DSTINC   = 0;
        eye[e].column[i].descriptor[j].BTCTRL.bit.STEPSEL  = DMA_STEPSEL_SRC;
        eye[e].column[i].descriptor[j].BTCTRL.bit.STEPSIZE = DMA_ADDRESS_INCREMENT_STEP_SIZE_1;
        eye[e].column[i].descriptor[j].DSTADDR.reg         = spi_data_reg;
      }
    }
    eye[e].colNum       = DISPLAY_SIZE; // Force initial wraparound to first column
    eye[e].colIdx       = 0;
    eye[e].dma_busy     = false;
    eye[e].column_ready = false;
    eye[e].dmaStartTime = 0;

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
    showSplashScreen = ((arcada.drawBMP((char *)"/splash.bmp",
                         0, 0, eye[0].display)) == IMAGE_SUCCESS);
    if (showSplashScreen) { // Loaded OK?
      Serial.println("Splashing");
      if (NUM_EYES > 1) {   // Load on other eye too, ignore status
        yield();
        arcada.drawBMP((char *)"/splash.bmp", 0, 0, eye[1].display);
      }
      // Ramp up backlight over 1/2 sec duration
      startTime = millis();
      while ((elapsed = (millis() - startTime)) <= 500) {
        yield();
        arcada.setBacklight(255 * elapsed / 500);
      }
      arcada.setBacklight(255); // To the max
      startTime = millis();     // Note current time for backlight hold later
    }
  }

  // If no splash, or load failed, turn backlight on early so user gets a
  // little feedback, that the board is not locked up, just thinking.
  if (!showSplashScreen) arcada.setBacklight(255);

  // LOAD CONFIGURATION FILE -----------------------------------------------

  loadConfig(filename);

  // LOAD EYELIDS AND TEXTURE MAPS -----------------------------------------

  // Experiencing a problem with MEMORY FRAGMENTATION when loading texture
  // maps. These images only occupy RAM temporarily -- they're copied to
  // internal flash memory and then freed. However, something is preventing
  // the freed memory from restoring to a contiguous block. For example,
  // if a texture image equal to about 50% of RAM is loaded/copied/freed,
  // following this with a larger texture (or trying to allocate a larger
  // polar lookup array) fails because RAM is fragmented into two segments.
  // I've been through this code, Adafruit_ImageReader and Adafruit_GFX
  // pretty carefully and they appear to be freeing RAM in the reverse order
  // that they allocate (which should avoid fragmentation), but I'm likely
  // overlooking something there or additional allocations are occurring
  // in other libraries -- perhaps the filesystem and/or mass storage code.
  // SO, here is the DIRTY WORKAROUND...
  // Adafruit_ImageReader provides a bmpDimensions() function to determine
  // the pixel size of an image without actually loading it. We can use this
  // to estimate the RAM requirements for loading the image, then allocate
  // a "booster seat" which makes the subsequent image load occur in higher
  // memory, and the fragmenting part a bit beyond that. When the image and
  // booster are both freed, that should restore a large contiguous chunk,
  // leaving the fragments in high memory. Not TOO high though, we need to
  // leave some RAM for the stack to operate over the lifetime of this
  // program and to handle small heap allocations.

  uint32_t maxRam = availableRAM() - stackReserve;

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
        &eye[e].iris.data, &eye[e].iris.width, &eye[e].iris.height,
        maxRam) != IMAGE_SUCCESS)) {
        // Point iris data at the color variable and set image size to 1px
        eye[e].iris.data  = &eye[e].iris.color;
        eye[e].iris.width = eye[e].iris.height = 1;
      }
      // Huh. The booster seat idea STILL doesn't always work right,
      // something leaking in upper memory. Keep shrinking down the
      // booster seat size a bit each time we load a texture. Feh.
      maxRam -= 20;
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
        &eye[e].sclera.data, &eye[e].sclera.width, &eye[e].sclera.height,
        maxRam) != IMAGE_SUCCESS)) {
        // Point sclera data at the color variable and set image size to 1px
        eye[e].sclera.data  = &eye[e].sclera.color;
        eye[e].sclera.width = eye[e].sclera.height = 1;
      }
      maxRam -= 20; // See note above
    }
  }

  // Load eyelid graphics.
  yield();
  ImageReturnCode status;

  status = loadEyelid(upperEyelidFilename ?
    upperEyelidFilename : (char *)"upper.bmp",
    upperClosed, upperOpen, DISPLAY_SIZE-1, maxRam);

  status = loadEyelid(lowerEyelidFilename ?
    lowerEyelidFilename : (char *)"lower.bmp",
    lowerOpen, lowerClosed, 0, maxRam);

  // Filenames are no longer needed...
  for(e=0; e<NUM_EYES; e++) {
    if(eye[e].sclera.filename) free(eye[e].sclera.filename);
    if(eye[e].iris.filename)   free(eye[e].iris.filename);
  }
  if(lowerEyelidFilename) free(lowerEyelidFilename);
  if(upperEyelidFilename) free(upperEyelidFilename);

  // Note that calls to availableRAM() at this point will return something
  // close to reserveSpace, suggesting very little RAM...but that function
  // really just returns the space between the heap and stack, and we've
  // established above that the top of the heap is something of a mirage.
  // Large allocations CAN still take place in the lower heap!

  calcMap();
  calcDisplacement();
  Serial.printf("Free RAM: %d\n", availableRAM());

  randomSeed(SysTick->VAL + analogRead(A2));
  eyeOldX = eyeNewX = eyeOldY = eyeNewY = mapRadius; // Start in center
  for(e=0; e<NUM_EYES; e++) { // For each eye...
    eye[e].display->setRotation(eye[e].rotation);
    eye[e].eyeX = eyeOldX; // Set up initial position
    eye[e].eyeY = eyeOldY;
  }

  if (showSplashScreen) { // Image(s) loaded above?
    // Hold backlight on for up to 2 seconds (minus other initialization time)
    if ((elapsed = (millis() - startTime)) < 2000) {
      delay(2000 - elapsed);
    }
    // Ramp down backlight over 1/2 sec duration
    startTime = millis();
    while ((elapsed = (millis() - startTime)) <= 500) {
      yield();
      arcada.setBacklight(255 - (255 * elapsed / 500));
    }
    arcada.setBacklight(0);
    for(e=0; e<NUM_EYES; e++) {
      eye[e].display->fillScreen(0);
    }
  }

#if defined(ADAFRUIT_MONSTER_M4SK_EXPRESS)
  if(voiceOn) {
    if(!voiceSetup((waveform > 0))) {
      Serial.println("Voice init fail, continuing without");
      voiceOn = false;
    } else {
      voiceGain(gain);
      currentPitch = voicePitch(currentPitch);
      if(waveform) voiceMod(modulate, waveform);
      arcada.enableSpeaker(true);
    }
  }
#endif

  arcada.setBacklight(255); // Back on, impending graphics

  yield();
  if(boopPin >= 0) {
    boopThreshold = 0;
    for(int i=0; i<DISPLAY_SIZE; i++) {
      boopThreshold += readBoop();
    }
    boopThreshold = boopThreshold * 110 / 100; // 10% overhead
  }

  lastLightReadTime = micros() + 2000000; // Delay initial light reading
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

// loop() function processes ONE COLUMN of ONE EYE...

void loop() {
  if(++eyeNum >= NUM_EYES) eyeNum = 0; // Cycle through eyes...

  uint8_t  x = eye[eyeNum].colNum;
  uint32_t t = micros();

  // If next column for this eye is not yet rendered...
  if(!eye[eyeNum].column_ready) {
    if(!x) { // If it's the first column...

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
            uint32_t limit = min(1000000, gazeMax);
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
      int nufix = booped ? 90 : 7;
      fixate = ((fixate * 15) + nufix) / 16;
      // save eye position to this eye's struct so it's same throughout render
      if(eyeNum & 1) eyeX += fixate; // Eyes converge slightly toward center
      else           eyeX -= fixate;
      eye[eyeNum].eyeX = eyeX;
      eye[eyeNum].eyeY = eyeY;

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
        if(booped) {
          uq = 0.9;
          lq = 0.7;
        } else {
          lq = 1.0 - uq;
        }
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

      // Once per frame (of eye #0), reset boopSum...
      if((eyeNum == 0) && (boopPin >= 0)) {
        boopSumFiltered = ((boopSumFiltered * 3) + boopSum) / 4;
        if(boopSumFiltered > boopThreshold) {
          if(!booped) {
            Serial.println("BOOP!");
          }
          booped = true;
        } else {
          booped = false;
        }
        boopSum = 0;
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

      // END ONCE-PER-FRAME EYE ANIMATION ----------------------------------

    } // end first-scanline check

    // PER-COLUMN RENDERING ------------------------------------------------

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

    DmacDescriptor *d = &eye[eyeNum].column[eye[eyeNum].colIdx].descriptor[0];

    if(upperOpen[lidColumn] == 255) {
      // No eyelid data for this line; eyelid image is smaller than screen.
      // Great! Make a full scanline of nothing, no rendering needed:
      d->BTCTRL.bit.SRCINC = 0;
      d->BTCNT.reg         = DISPLAY_SIZE * 2;
      d->SRCADDR.reg       = (uint32_t)&eyelidIndex;
      d->DESCADDR.reg      = 0; // No linked descriptor
    } else {
      y1 = lowerClosed[lidColumn] + (int)(0.5 + lowerLidFactor *
        (float)((int)lowerOpen[lidColumn] - (int)lowerClosed[lidColumn]));
      y2 = upperClosed[lidColumn] + (int)(0.5 + upperLidFactor *
        (float)((int)upperOpen[lidColumn] - (int)upperClosed[lidColumn]));
      if(y1 > DISPLAY_SIZE-1)    y1 = DISPLAY_SIZE-1; // Clip results in case lidfactor
      else if(y1 < 0) y1 = 0;   // is beyond the usual 0.0 to 1.0 range
      if(y2 > DISPLAY_SIZE-1)    y2 = DISPLAY_SIZE-1;
      else if(y2 < 0) y2 = 0;
      if(y1 >= y2) {
        // Eyelid is fully or partially closed, enough that there are no
        // pixels to be rendered for this line. Make "nothing," as above.
        d->BTCTRL.bit.SRCINC = 0;
        d->BTCNT.reg         = DISPLAY_SIZE * 2;
        d->SRCADDR.reg       = (uint32_t)&eyelidIndex;
        d->DESCADDR.reg      = 0; // No linked descriptors
      } else {
        // If single eye, dynamically build descriptor list as needed,
        // else use a single descriptor & fully buffer each line.
#if NUM_DESCRIPTORS > 1
        DmacDescriptor *next;
        int             renderlen;
        if(y1 > 0) { // Do upper eyelid unless at top of image
          d->BTCTRL.bit.SRCINC = 0;
          d->BTCNT.reg         = y1 * 2;
          d->SRCADDR.reg       = (uint32_t)&eyelidIndex;
          next                 = &eye[eyeNum].column[eye[eyeNum].colIdx].descriptor[1];
          d->DESCADDR.reg      = (uint32_t)next; // Link to next descriptor
          d                    = next;           // Advance to next descriptor
        }
        // Partial column will be rendered
        renderlen            = y2 - y1 + 1;
        d->BTCTRL.bit.SRCINC = 1;
        d->BTCNT.reg         = renderlen * 2;
        d->SRCADDR.reg       = (uint32_t)eye[eyeNum].column[eye[eyeNum].colIdx].renderBuf + renderlen * 2; // Point to END of data!
#else
        // Full column will be rendered; DISPLAY_SIZE pixels, point source to end of
        // renderBuf and enable source increment.
        d->BTCTRL.bit.SRCINC = 1;
        d->BTCNT.reg         = DISPLAY_SIZE * 2;
        d->SRCADDR.reg       = (uint32_t)eye[eyeNum].column[eye[eyeNum].colIdx].renderBuf + DISPLAY_SIZE * 2;
        d->DESCADDR.reg      = 0; // No linked descriptors
#endif
        // Render column 'x' into eye's next available renderBuf
        uint16_t *ptr = eye[eyeNum].column[eye[eyeNum].colIdx].renderBuf;
        int xx = xPositionOverMap + x;
        int y;

#if NUM_DESCRIPTORS == 1
        // Render lower eyelid if needed
        for(y=0; y<y1; y++) *ptr++ = eyelidColor;
#else
        y = y1;
#endif

        // tablegen.cpp explains a bit of the displacement mapping trick.
        uint8_t *displaceX, *displaceY;
        int8_t   xmul; // Sign of X displacement: +1 or -1
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
          if(dx < 255) {      // Inside eyeball area
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

#if NUM_DESCRIPTORS == 1
        // Render upper eyelid if needed
        for(; y<DISPLAY_SIZE; y++) *ptr++ = eyelidColor;
#else
        if(y2 >= (DISPLAY_SIZE-1)) {
          // No third descriptor; close it off
          d->DESCADDR.reg      = 0;
        } else {
          next                 = &eye[eyeNum].column[eye[eyeNum].colIdx].descriptor[(y1 > 0) ? 2 : 1];
          d->DESCADDR.reg      = (uint32_t)next; // link to next descriptor
          d                    = next; // Increment descriptor
          d->BTCTRL.bit.SRCINC = 0;
          d->BTCNT.reg         = ((DISPLAY_SIZE-1) - y2) * 2;
          d->SRCADDR.reg       = (uint32_t)&eyelidIndex;
          d->DESCADDR.reg      = 0; // end of descriptor list
        }
#endif
      }
    }
    eye[eyeNum].column_ready = true; // Line is rendered!
  }

  // If DMA for this eye is currently busy, don't block, try next eye...
  if(eye[eyeNum].dma_busy) {
    if((micros() - eye[eyeNum].dmaStartTime) < DMA_TIMEOUT) return;
    // If we reach this point in the code, an SPI DMA transfer has taken
    // noticably longer than expected and is probably stalled (see comments
    // in the DMAbuddy.h file and above the DMA_TIMEOUT declaration earlier
    // in this code). Take action!
    // digitalWrite(13, HIGH);
    Serial.printf("Eye #%d stalled, resetting DMA channel...\n", eyeNum);
    eye[eyeNum].dma.fix();
    // If this somehow proves to be inadequate, we still have the Nuclear
    // Option of just completely restarting the sketch from the beginning,
    // though this stalls animation for several seconds during startup.
    // DO NOT enable this line unless the fix() function isn't fixing!
    //NVIC_SystemReset();
  }

  // At this point, above checks confirm that column is ready and DMA is free
  if(!x) { // If it's the first column...
    // End prior SPI transaction...
    digitalWrite(eye[eyeNum].cs, HIGH); // Deselect
    eye[eyeNum].spi->endTransaction();
    // Initialize new SPI transaction & address window...
    eye[eyeNum].spi->beginTransaction(settings);
    digitalWrite(eye[eyeNum].cs, LOW);  // Chip select
    eye[eyeNum].display->setAddrWindow((eye[eyeNum].display->width() - DISPLAY_SIZE) / 2, (eye[eyeNum].display->height() - DISPLAY_SIZE) / 2, DISPLAY_SIZE, DISPLAY_SIZE);
    delayMicroseconds(1);
    digitalWrite(eye[eyeNum].dc, HIGH); // Data mode
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
          uint16_t rawReading = arcada.readLightSensor();
          if(rawReading <= 1023) {
            if(rawReading < lightSensorMin)      rawReading = lightSensorMin; // Clamp light sensor range
            else if(rawReading > lightSensorMax) rawReading = lightSensorMax; // to within usable range
            float v = (float)(rawReading - lightSensorMin) / (float)(lightSensorMax - lightSensorMin); // 0.0 to 1.0
            v = pow(v, lightSensorCurve);
            lastLightValue    = irisMin + v * irisRange;
            lastLightReadTime = t;
            lightSensorFailCount = 0;
          } else { // I2C error
            if(++lightSensorFailCount >= 25) { // If repeated errors in succession...
              lightSensorPin = -1; // Stop trying to use the light sensor
            } else {
              lastLightReadTime = t - LIGHT_INTERVAL + 30000; // Try again in 30 ms
            } }
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
#if defined(ADAFRUIT_MONSTER_M4SK_EXPRESS)
      if(voiceOn) {
        // Read buttons, change pitch
        arcada.readButtons();
        uint32_t buttonState = arcada.justPressedButtons();
        if(       buttonState & ARCADA_BUTTONMASK_UP) {
          currentPitch *= 1.05;
        } else if(buttonState & ARCADA_BUTTONMASK_A) {
          currentPitch = defaultPitch;
        } else if(buttonState & ARCADA_BUTTONMASK_DOWN) {
          currentPitch *= 0.95;
        }
        if(buttonState & (ARCADA_BUTTONMASK_UP | ARCADA_BUTTONMASK_A | ARCADA_BUTTONMASK_DOWN)) {
          currentPitch = voicePitch(currentPitch);
          if(waveform) voiceMod(modulate, waveform);
          Serial.print("Voice pitch: ");
          Serial.println(currentPitch);
        }
      }
#endif
      user_loop();
    }
  } // end first-column check

  // MUST read the booper when there’s no SPI traffic across the nose!
  if((eyeNum == (NUM_EYES-1)) && (boopPin >= 0)) {
    boopSum += readBoop();
  }

  memcpy(eye[eyeNum].dptr, &eye[eyeNum].column[eye[eyeNum].colIdx].descriptor[0], sizeof(DmacDescriptor));
  eye[eyeNum].dma_busy       = true;
  eye[eyeNum].dma.startJob();
  eye[eyeNum].dmaStartTime   = micros();
  if(++eye[eyeNum].colNum >= DISPLAY_SIZE) { // If last line sent...
    eye[eyeNum].colNum      = 0;    // Wrap to beginning
  }
  eye[eyeNum].colIdx       ^= 1;    // Alternate 0/1 line structs
  eye[eyeNum].column_ready = false; // OK to render next line
}
