/*
   JOY: Adafruit PyGamer or PyBadge as a friendly USB HID game controller.
   Requires Arcada, ArduinoJSON and Audio libraries.

   Button-to-key mapping can be configured in the file joy.cfg in the root
   folder of the flash filesystem, else defaults will be used. This is a
   JSON-formatted text file and the syntax is VERY particular. Keywords
   (corresponding to button names) MUST be lowercase, in quotes, and one
   of the recognized strings ("a", "b", "start", "select", "up", "down",
   "left" or "right"). Values (corresponding to HID keyboard codes) are
   not case-sensitive, but must be one of the recognized values in keys.h.
   The key:value list MUST be { enclosed in braces } and the last key:value
   must NOT have a trailing comma. There are NO COMMENTS in the file.
   Picky, yes, but less bother than recompiling all this code to change
   the key mapping (though you can still do that if you want to change the
   default keys when a config file is not found or has syntax trouble).

   Here's an example of a valid joy.cfg file with the default key mapping:

   {
     "a":      "Z",
     "b":      "X",
     "start":  "1",
     "select": "5",
     "up":     "UP_ARROW",
     "down":   "DOWN_ARROW",
     "left":   "LEFT_ARROW",
     "right":  "RIGHT_ARROW"
   }

*/

#if !defined(USE_TINYUSB)
 #error("Please select TinyUSB from the Tools->USB Stack menu!")
#endif

#include <Adafruit_Arcada.h>
#include <Audio.h>
#include "graphics.h" // Face bitmaps are here
#include "sound.h"    // "Pew" sound is here
#include "keys.h"     // Key name-to-value table is here
//#include "Adafruit_TinyUSB.h"

#define JOY_CONFIG_FILE "/joy.cfg"

// These are the indices of each element in the keyCode[] array below,
// so we're not using separate variables for every button.
enum ButtonIndex { BUTTON_A = 0, BUTTON_B, BUTTON_START, BUTTON_SELECT, BUTTON_UP, BUTTON_DOWN, BUTTON_LEFT, BUTTON_RIGHT, NUM_BUTTONS };

// These are default key codes for each of the buttons on the PyBadge / PyGamer.
// Key codes are simply ASCII chars, or one of the values defined in Keyboard.h.
// We'll try loading replacements from a configuration file, else use these fallbacks.
// Order of items must match the ButtonIndex enum above.
uint8_t keyCode[NUM_BUTTONS] = { HID_KEY_Z, HID_KEY_X, HID_KEY_1, HID_KEY_5, HID_KEY_ARROW_UP, HID_KEY_ARROW_DOWN, HID_KEY_ARROW_LEFT, HID_KEY_ARROW_RIGHT };

// Given a key name as a string (e.g. "LEFT_CONTROL"), return the
// corresponding key code (an 8-bit value) from the keys[] array.
uint8_t lookupKey(char *name) {
  for(int i=0; i<NUM_KEYS; i++) {
    if(!strcasecmp(name, key[i].name)) return key[i].code;
  }
  return 0; // Not found
}

// MASK_BUTTONS is used to isolate button inputs from direction inputs
// on PyGamer. MASK_PEW is to isolate just the A & B buttons as triggers
// for the occasional random "pew!" noises.
#define MASK_BUTTONS    (ARCADA_BUTTONMASK_A | ARCADA_BUTTONMASK_B | ARCADA_BUTTONMASK_START | ARCADA_BUTTONMASK_SELECT)
#define MASK_PEW        (ARCADA_BUTTONMASK_A | ARCADA_BUTTONMASK_B)
#define UPPER_LID_SIZE  (EYES_HEIGHT * 3 / 4)
#define LOWER_LID_SIZE  (EYES_HEIGHT - UPPER_LID_SIZE)

Adafruit_Arcada         arcada;
int8_t                  xState, yState; // Joystick state
float                   eyeAngle = 0.0;
bool                    blinking = false;
uint32_t                blinkStartTime, blinkDuration;
uint8_t                 mouthState = 0, priorMouthState = 0, mouthCounter = 0;
uint32_t                stickmask = 0;

Adafruit_USBD_HID       usb_hid;
uint8_t const           desc_hid_report[] = { TUD_HID_REPORT_DESC_KEYBOARD() };
uint8_t                 hidcode[6]        = { 0,0,0,0,0,0 };

AudioPlayMemory         sound;
AudioOutputAnalogStereo audioOut;
AudioConnection         c0(sound, 0, audioOut, 0);

uint32_t                keyBits = 0; // Bitmask of currently-pressed keys
#define press(x)        { keyBits |=  (1 << x); }
#define release(x)      { keyBits &= ~(1 << x); }

// This function converts keyBits value to HID button presses.
void sendKeys(void) {
  static bool prevPressFlag = 0;

  if(usb_hid.ready()) {
    uint8_t count     = 0;
    bool    pressFlag = 0;

    for(int i=0; i<NUM_BUTTONS; i++) { // For each button...
      if(keyBits & (1 << i)) {         // Pressed?
        pressFlag = 1;                 // At least one key is pressed
        hidcode[count++] = keyCode[i]; // Add to HID codes
        if(count >= 6) {               // 6 codes at a time max
          usb_hid.keyboardReport(0, 0, hidcode); // Send what we have
          delay(2);
          memset(hidcode, 0, sizeof(hidcode));   // Clear hidcode list
          count = 0;                             // Reset hidcode counter
        }
      }
    }
    if(count) {                        // Any remaining hiscodes to send?
      usb_hid.keyboardReport(0, 0, hidcode);     // Do it nao!
      delay(2);
      memset(hidcode, 0, sizeof(hidcode));
      count = 0;
    }

    // If no buttons are pressed, but there were previously buttons
    // pressed on the last call, issue a suitable HID event...
    if(prevPressFlag & !pressFlag) {
      usb_hid.keyboardRelease(0);
    }
    prevPressFlag = pressFlag;
  }
}

// SETUP FUNCTION - RUNS ONCE AT STARTUP ***********************************

void setup() {

  // Some of these libraries are SUPER PERSNICKETY about the sequence
  // in which they are initialized. HID MUST be initialized before
  // Serial, which must be initialized before the display.

  int status = arcada.begin(); // Save status for Serial print later

  // HID (keyboard) initialization
  usb_hid.setPollInterval(2);
  usb_hid.setReportDescriptor(desc_hid_report, sizeof(desc_hid_report));
  usb_hid.begin();

  // USB filesystem initialization
  arcada.filesysBeginMSD();

  // Then Serial init, MUST happen after the filesystem init
  Serial.begin(9600);
  // while(!Serial);

  // Now that Serial's initialized, can throw out an error if needed
  if(!status) {
    Serial.println("Arcada failed to init");
    for(;;);
  }

  // Display initialization. This is all part of the persnickety sequence!
  arcada.displayBegin();
  arcada.setBacklight(255);
  arcada.fillScreen(ARCADA_BLACK);

  // Audio initialization
  AudioMemory(10);
  arcada.enableSpeaker(true);
  arcada.setVolume(255);

  if(arcada.filesysBegin()) {
    // Valid filesystem found. Load configuration file (if present).
    File file = arcada.open(JOY_CONFIG_FILE, O_READ);
    if(file) {
      StaticJsonDocument<512> doc;
      char buf[40];
      if(DeserializationError error = deserializeJson(doc, file)) {
        arcada.warnBox("JOY.CFG syntax invalid, using default configuration.");
      } else {
        // Keywords in the JSON file corresponding to each button input.
        // Order of these arrays must follow the ButtonIndex enum (but can be any order in file).
        static const char *buttonName[]    = { "a", "b", "start", "select", "up"      , "down"      , "left"      , "right"       },
                          *buttonDefault[] = { "z", "x", "1"    , "5"     , "UP_ARROW", "DOWN_ARROW", "LEFT_ARROW", "RIGHT_ARROW" };
        // Look up each button in the JSON doc, assign default key value if not found.
        for(int i=0; i<NUM_BUTTONS; i++) {
          strlcpy(buf, doc[buttonName[i]] | buttonDefault[i], sizeof(buf));
          keyCode[i] = lookupKey(buf);
        }
      }
      file.close();
    } else {
      arcada.warnBox("JOY.CFG file not found, using default configuration.");
    }
  } else {
    arcada.warnBox("No filesystem found! Load CircuitPython to init filesystem. Using default configuration.");
  }

  // At start, draw the entire blank/neutral face centered on screen
  arcada.fillScreen(ARCADA_BLACK); // Erase any warnBoxes first
  arcada.drawRGBBitmap(
    (arcada.width()  - FACE_WIDTH ) / 2,
    (arcada.height() - FACE_HEIGHT) / 2,
    (uint16_t *)face, FACE_WIDTH, FACE_HEIGHT);

  // Create an offscreen framebuffer that's just the bounding
  // rectangle of the animayed face parts (eyes, mouth).
  arcada.createFrameBuffer(EYES_WIDTH, 94);
  GFXcanvas16 *canvas = arcada.getCanvas();
  uint16_t    *buffer = canvas->getBuffer();
  // Fill canvas white, then draw mouth in "idle" position.
  memset(buffer, 0xFF, canvas->width() * canvas->height() * 2);
  // Most of the animation is done using memcpy() and bitmaps that are
  // carefully planned to be the same width as the canvas...so we can
  // just move entire scanlines this way, simplifies the code.
  memcpy(&buffer[canvas->width() * (canvas->height() - MOUTH_HEIGHT)],
    mouth_idle, MOUTH_WIDTH * MOUTH_HEIGHT * 2);

  // Initialize button state
  arcada.readButtons();
  uint32_t b = arcada.justPressedButtons();
  if(b & ARCADA_BUTTONMASK_A)      press(BUTTON_A);
  if(b & ARCADA_BUTTONMASK_B)      press(BUTTON_B);
  if(b & ARCADA_BUTTONMASK_START)  press(BUTTON_START);
  if(b & ARCADA_BUTTONMASK_SELECT) press(BUTTON_SELECT);

#if defined(ARCADA_JOYSTICK_X) && defined(ARCADA_JOYSTICK_Y)
  // Initialize joystick state. Although the Arcada lib has stuff for
  // for analog-stick-to-button-press conversion, this code had some nice
  // hysteresis built in, so I'm leaving it here for now, though bulkier.
  int pos = arcada.readJoystickX() + 512;
  if(pos > (1023 * 4 / 5)) {
    press(BUTTON_RIGHT);
    xState =  1;
  } else if(pos < (1023 / 5)) {
    press(BUTTON_LEFT);
    xState = -1;
  } else {
    xState =  0;
  }
  pos = arcada.readJoystickY() + 512;
  if(pos > (1023 * 4 / 5)) {
    press(BUTTON_DOWN);
    yState =  1;
  } else if(pos < (1023 / 5)) {
    press(BUTTON_UP);
    yState = -1;
  } else {
    yState =  0;
  }
#else
  if(b & ARCADA_BUTTONMASK_RIGHT) press(BUTTON_RIGHT);
  if(b & ARCADA_BUTTONMASK_LEFT)  press(BUTTON_LEFT);
  if(b & ARCADA_BUTTONMASK_DOWN)  press(BUTTON_DOWN);
  if(b & ARCADA_BUTTONMASK_UP)    press(BUTTON_UP);
  stickmask = b & ~MASK_BUTTONS;
#endif

  sendKeys(); // Issue initial HID key state
}

// LOOP FUNCTION - RUNS REPEATEDLY, ONCE PER FRAME *************************

void loop() {
  int          dx, dy, upperLidRows=0, lowerLidRows=0, openRows=EYES_HEIGHT;
  float        a;
  uint32_t     b;
  GFXcanvas16 *canvas = arcada.getCanvas();
  uint16_t    *buffer = canvas->getBuffer();

  arcada.readButtons();
  b = arcada.justPressedButtons();
  if(b & ARCADA_BUTTONMASK_A)      press(BUTTON_A);
  if(b & ARCADA_BUTTONMASK_B)      press(BUTTON_B);
  if(b & ARCADA_BUTTONMASK_START)  press(BUTTON_START);
  if(b & ARCADA_BUTTONMASK_SELECT) press(BUTTON_SELECT);
  // If one of the pewing buttons was pressed, and mouth is not currently
  // in the "py" position (so, either idle or "oo"ing), there's a random
  // chance (1/8) of triggering a new "pew!" sound & animation...
  if((b & MASK_PEW) && (mouthState != 1) && !random(8)) {
    mouthState = 1; // Set flag, actual pew starts in the mouth code later
  }
  b = arcada.justReleasedButtons();
  if(b & ARCADA_BUTTONMASK_A)      release(BUTTON_A);
  if(b & ARCADA_BUTTONMASK_B)      release(BUTTON_B);
  if(b & ARCADA_BUTTONMASK_START)  release(BUTTON_START);
  if(b & ARCADA_BUTTONMASK_SELECT) release(BUTTON_SELECT);

#if defined(ARCADA_JOYSTICK_X) && defined(ARCADA_JOYSTICK_Y)

  // Analog joystick input with fancy hysteresis

  dx = arcada.readJoystickX(),    // Joystick position relative to center
  dy = arcada.readJoystickY();    // (+/- 512)

  // Handle joystick X axis
  int pos = dx + 512;
  if(xState == 1) {               // Stick to right last we checked?
    if(pos < (1023 * 3 / 5)) {    // Moved left beyond hysteresis threshold?
      release(BUTTON_RIGHT);      // Release right arrow key
      xState  = 0;                // and set state to neutral center zone
    }
  } else if(xState == -1) {       // Stick to left last we checked?
    if(pos > (1023 * 2 / 5)) {    // Moved right beyond hysteresis threshold?
      release(BUTTON_LEFT);       // Release left arrow key
      xState =  0;                // and set state to neutral center zone
    }
  }
  // This is intentionally NOT an 'else' -- state CAN change twice here!
  // First change releases left/right keys, second change presses new left/right
  if(!xState) {                   // Stick X previously in neutral center zone?
    if(pos > (1023 * 4 / 5)) {    // Moved right?
      press(BUTTON_RIGHT);        // Press right arrow key
      xState =  1;                // and set state to right
    } else if(pos < (1023 / 5)) { // Else moved left?
      press(BUTTON_LEFT);         // Press left arrow key
      xState = -1;                // and set state to left
    }
  }

  // Handle joystick Y axis
  pos = dy + 512;
  if(yState == 1) {               // Stick down last we checked?
    if(pos < (1023 * 3 / 5)) {    // Moved up beyond hysteresis threshold?
      release(BUTTON_DOWN);       // Release down key
      yState =  0;                // and set state to neutral center zone
    }
  } else if(yState == -1) {       // Stick up last we checked?
    if(pos > (1023 * 2 / 5)) {    // Moved down beyond hysteresis threshold?
      release(BUTTON_UP);         // Release up key
      yState =  0;                // and set state to neutral center zone
    }
  }
  // See note above re: not an else
  if(!yState) {                   // Stick Y previously in neutral center zone?
    if(pos > (1023 * 4 / 5)) {    // Moved down?
      press(BUTTON_DOWN);         // Press down key
      yState =  1;                // and set state to down
    } else if(pos < (1023 / 5)) { // Else moved up?
      press(BUTTON_UP);           // Press up key
      yState = -1;                // and set state to up
    }
  }

  // If there's no stick input, have Joy look up, as if watching game.
  if((abs(dx) < 30) && (abs(dy) < 30)) {
    dx =  0;
    dy = -1;
  }

#else

  // PyBadge directional button input

  b          = arcada.justPressedButtons() & ~MASK_BUTTONS;
  stickmask |= b;
  if(b & ARCADA_BUTTONMASK_RIGHT) press(BUTTON_RIGHT);
  if(b & ARCADA_BUTTONMASK_LEFT)  press(BUTTON_LEFT);
  if(b & ARCADA_BUTTONMASK_DOWN)  press(BUTTON_DOWN);
  if(b & ARCADA_BUTTONMASK_UP)    press(BUTTON_UP);
  b          = arcada.justReleasedButtons() & ~MASK_BUTTONS;
  if(b & ARCADA_BUTTONMASK_RIGHT) release(BUTTON_RIGHT);
  if(b & ARCADA_BUTTONMASK_LEFT)  release(BUTTON_LEFT);
  if(b & ARCADA_BUTTONMASK_DOWN)  release(BUTTON_DOWN);
  if(b & ARCADA_BUTTONMASK_UP)    release(BUTTON_UP);
  stickmask &= ~b;
  // If there's no stick input, have Joy look up, as if watching game.
  int dir = stickmask ? stickmask : ARCADA_BUTTONMASK_UP;
  switch(dir) {
    case ARCADA_BUTTONMASK_RIGHT:
      dx =  1; dy =  0; break;
    case ARCADA_BUTTONMASK_RIGHT | ARCADA_BUTTONMASK_UP:
      dx =  1; dy = -1; break;
    case ARCADA_BUTTONMASK_UP:
      dx =  0; dy = -1; break;
    case ARCADA_BUTTONMASK_LEFT | ARCADA_BUTTONMASK_UP:
      dx = -1; dy = -1; break;
    case ARCADA_BUTTONMASK_LEFT:
      dx = -1; dy =  0; break;
    case ARCADA_BUTTONMASK_LEFT | ARCADA_BUTTONMASK_DOWN:
      dx = -1; dy =  1; break;
    case ARCADA_BUTTONMASK_DOWN:
      dx =  0; dy =  1; break;
    case ARCADA_BUTTONMASK_RIGHT | ARCADA_BUTTONMASK_DOWN:
      dx =  1; dy =  1; break;
  }
#endif

  sendKeys(); // Convert button state to HID

  // Joy's eyes don't directly follow the joystick. They're always
  // looking in some direction, pupils are kept around the perimeter
  // of the eyes.

  a  = atan2(dy, dx);          // Joystick angle (+/- M_PI)
  // Deal with 'seam crossing' at +/- 180 degrees:
  if(fabs(a - eyeAngle) > M_PI) {
    if(eyeAngle >= 0.0) eyeAngle -= M_PI * 2.0;
    else                eyeAngle += M_PI * 2.0;
  }
  eyeAngle = (eyeAngle * 0.9) + (a * 0.1); // Low-pass filter old/new angle

  // Determine position of pupils; center +/- 12 pixels
  dx = (int)(cos(eyeAngle) * 11.0 + 13.5),
  dy = (int)(sin(eyeAngle) * 11.0 + 13.5);
  // When eyes are blinking, overwrite sections of offscreen canvas
  // with the 'closed' eye image.  They converge at the 3/4 mark
  // (i.e. upper lid is 3/4 of height, lower lid is 1/4).
  if(blinking) {                            // Currently blinking?
    uint32_t t = micros() - blinkStartTime; // Since how long?
    if(t > blinkDuration) {                 // Past end of blink time?
      blinking = false;                     // Turn off blink flag
    } else {                                // Else in mid-blink...
      int amount = 900 * t / blinkDuration; // Relative time, 0-900
      // First third of blink is fast closing, last 2/3 is slower opening
      if(amount > 300) amount = 300 - ((amount - 300) / 2); // 0-300 blinkyness
      if(amount > 256) amount = 256;                        // Clip to 256
      upperLidRows = UPPER_LID_SIZE * amount / 256; // How much upper lid, in pixels?
      lowerLidRows = LOWER_LID_SIZE * amount / 256; // How much lower lid, in pixels?
      openRows     = EYES_HEIGHT - upperLidRows - lowerLidRows;
    }
  } else { // Not blinking
    if(!random(250)) { // Each time here, 1/250 chance of new blink
      blinking       = true;
      blinkDuration  = random(150000, 250000);
      blinkStartTime = micros();
    }
  }

  // Wait for prior DMA transfer to complete; don't modify canvas
  // while a screen update is currently in progress. (This is assuming
  // SPI DMA is enabled in Adafruit_SPITFT.h. If it is not, that's OK,
  // this function call simply compiles to nothing in that case.)
  arcada.dmaWait();

  if(openRows) {
    // Draw the open section of the eyes, then draw the pupils on top
    // of this. The pupil-drawing may partly obliterate the eyelid areas,
    // so those are drawn last.
    memcpy(&buffer[EYES_WIDTH * upperLidRows],
      &eyes_open[upperLidRows], EYES_WIDTH * openRows * 2);
    canvas->drawRGBBitmap(dx, dy, (uint16_t *)pupil, // Left
      (uint8_t *)pupil_mask, PUPIL_WIDTH, PUPIL_HEIGHT);
    canvas->drawRGBBitmap(64 + dx, dy, (uint16_t *)pupil, // Right
      (uint8_t *)pupil_mask, PUPIL_WIDTH, PUPIL_HEIGHT);
    if(upperLidRows) {
      memcpy(buffer, eyes_closed, EYES_WIDTH * upperLidRows * 2);
    }
    if(lowerLidRows) {
      memcpy(&buffer[EYES_WIDTH * (EYES_HEIGHT - lowerLidRows)],
        &eyes_closed[EYES_HEIGHT - lowerLidRows],
        EYES_WIDTH * lowerLidRows * 2);
    }
  } else {
    // Eyes are closed, super simple...
    memcpy(buffer, eyes_closed, EYES_WIDTH * EYES_HEIGHT * 2);
  }

  // Mouth is re-drawn in canvas only when it changes.
  if(mouthState != priorMouthState) {
    priorMouthState = mouthState;
    uint16_t *ptr;
    if(mouthState == 0) { // Idle
      ptr = (uint16_t *)mouth_idle;
    } else if(mouthState == 1) { // "Pew!" just started ("py")
      ptr = (uint16_t *)mouth_py;
      // New 'pew' sound/animation started...
      mouthCounter = 0;                          // For counting frames
      digitalWrite(ARCADA_SPEAKER_ENABLE, HIGH); // Speaker on
      sound.play(pew);                           // Start the sound
    } else { // "Pew!" underway ("oo")
      ptr = (uint16_t *)mouth_oo;
    }
    // Copy one of the above three images (from ptr) to bottom of canvas.
    memcpy(&buffer[canvas->width() * (canvas->height() - MOUTH_HEIGHT)],
      ptr, MOUTH_WIDTH * MOUTH_HEIGHT * 2);
  } else if(mouthState) { // Same position as before, but "pew!" playing
    if(mouthState == 1) { // "py"
      if(++mouthCounter > 12) mouthState++; // Hold mouth pursed for 12 frames
    } else {              // "oo"
      if(!sound.isPlaying()) { // If end of "pew!" sound reached...
        mouthState = 0;        // Set mouth back to idle
        digitalWrite(ARCADA_SPEAKER_ENABLE, LOW); // Speaker off
      }
    }
  }

  // Redraw just the animated area of face. A big-endian DMA transfer
  // is used...this is fastest as it can continue in the background
  // (while we process input on the next frame).
  arcada.blitFrameBuffer(
    (arcada.width()  - FACE_WIDTH ) / 2 + 13,
    (arcada.height() - FACE_HEIGHT) / 2 + 25,
    false, true); // Non-blocking, big-endian
}
