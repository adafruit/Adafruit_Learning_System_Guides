// SPDX-FileCopyrightText: 2017 Noe Ruiz for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include <Keyboard.h>
#include <Adafruit_ST7735.h>
#include <SPI.h>
#include "graphics.h"

// Special keycodes (e.g. shift, arrows, etc.) are documented here:
// https://www.arduino.cc/en/Reference/KeyboardModifiers


// GLOBAL VARIABLES --------------------------------------------------------

#define TFT_CS  10
#define TFT_RST 9
#define TFT_DC  6
Adafruit_ST7735 display(TFT_CS, TFT_DC, TFT_RST);

struct { // Button structure:
  int8_t   pin; // Button is wired between this pin and GND
  uint8_t  key; // Corresponding key code to send
  bool     prevState;
  uint32_t lastChangeTime;
} button[] = {
  { A5, 'a' },              // Button 0 Blue
  { A4, 's'},               // Button 1 Pink
  { A3, 'x' },              // Button 2 Yellow
  { A2, 'z' },              // Button 3 Green
  { 11, KEY_RETURN },       // Joystick select click
};
#define N_BUTTONS (sizeof(button) / sizeof(button[0]))
#define DEBOUNCE_US 600 // Button debounce time, microseconds

struct { // Joystick axis structure (2 axes per stick):
  int8_t  pin;   // Analog pin where stick axis is connected
  int     lower; // Typical value in left/upper position
  int     upper; // Typical value in right/lower positionax

  uint8_t key1;  // Key code to send when left/up
  uint8_t key2;  // Key code to send when down/right
  int     value; // Last-read-and-mapped value (0-1023)
  int8_t  state;
} axis[] = {
  { A1,   65, 1023, KEY_LEFT_ARROW, KEY_RIGHT_ARROW }, // X axis
  { A0, 1023,   65, KEY_UP_ARROW  , KEY_DOWN_ARROW  }, // Y axis
};
#define N_AXES (sizeof(axis) / sizeof(axis[0]))

SPISettings SPIset = SPISettings(24000000, MSBFIRST, SPI_MODE0);
GFXcanvas16 canvas(EYES_WIDTH, EYES_HEIGHT);
float       eyeAngle = 0.0;
bool        blinking = false;
uint32_t    blinkStartTime, blinkDuration;
#define     UPPER_LID_SIZE (EYES_HEIGHT * 3 / 4)
#define     LOWER_LID_SIZE (EYES_HEIGHT - UPPER_LID_SIZE)
uint8_t     state = 0;


// SETUP - RUNS ONCE AT STARTUP --------------------------------------------

void setup() {
  uint8_t i;

  display.initR(INITR_144GREENTAB);
  display.fillScreen(0);
  display.setRotation(2);
  display.drawRGBBitmap(31, 90, (uint16_t *)teef, TEEF_WIDTH, TEEF_HEIGHT);

  Keyboard.begin();

  // Initialize button states...
  for(i=0; i<N_BUTTONS; i++) {
    pinMode(button[i].pin, INPUT_PULLUP);
    button[i].prevState      = digitalRead(button[i].pin);
    button[i].lastChangeTime = micros();
  }

  // Initialize joystick state...
  for(i=0; i<N_AXES; i++) {
    int value = map(analogRead(axis[i].pin), axis[i].lower, axis[i].upper, 0, 1023);
    if(value > (1023 * 4 / 5)) {
      Keyboard.press(axis[i].key2);
      axis[i].state =  1;
    } else if(value < (1023 / 5)) {
      Keyboard.press(axis[i].key1);
      axis[i].state = -1;
    } else {
      axis[i].state = 0;
    }
  }
}


// MAIN LOOP - RUNS OVER AND OVER FOREVER ----------------------------------

void loop() {
  uint32_t  t;
  bool      s;
  int       i, value, dx, dy;
  float     a;
  uint16_t *buf;

  // Read and debounce button inputs...
  for(i=0; i<N_BUTTONS; i++) {
    s = digitalRead(button[i].pin);       // Current button state
    if(s != button[i].prevState) {        // Changed from before?
      t = micros();                       // Check time; wait for debounce
      if((t - button[i].lastChangeTime) >= DEBOUNCE_US) {
        if(s) Keyboard.release(button[i].key); // Button released
        else  Keyboard.press(  button[i].key); // Button pressed
        button[i].prevState      = state; // Save new button state
        button[i].lastChangeTime = t;     // and time of change
      }
    }
  }

  // Read joystick axes
  for(i=0; i<N_AXES; i++) {
    // Remap analog reading to 0-1023 range (0=top/left, 1023=down/right)
    value = map(analogRead(axis[i].pin), axis[i].lower, axis[i].upper, 0, 1023);
    if(axis[i].state == 1) {            // Axis previously down/right?
      if(value < (1023 * 3 / 5)) {      // Moved up/left past hysteresis threshold?
        Keyboard.release(axis[i].key2); // Release corresponding key
        axis[i].state = 0;              // and set state to neutral center zone
      }
    } else if(axis[i].state == -1) {    // Else axis previously up/left?
      if(value > (1023 * 2 / 5)) {      // Moved down/right past hysteresis threshold?
        Keyboard.release(axis[i].key1); // Release corresponding key
        axis[i].state = 0;              // and set state to neutral center zone
      }
    } // This is intentionally NOT an 'else' -- state CAN change twice here!
    if(!axis[i].state) {                // Axis previously in neutral center zone?
      if(value > (1023 * 4 / 5)) {      // Moved down/right?
        Keyboard.press(axis[i].key2);   // Press corresponding key
        axis[i].state = 1;              // and set state to down/right
      } else if(value < (1023 / 5)) {   // Else axis moved up/left?
        Keyboard.press(axis[i].key1);   // Press corresponding key
        axis[i].state = -1;             // and set state to up/left
      }
    }
    axis[i].value = value; // Save for later
  }

  // REDRAW FACE -----------------------------------------------------------
  // In order to keep the joystick and buttons more responsive, the face
  // drawing is broken down into several steps, only one of which is
  // performed on each pass through loop().  There's floating-point math
  // and SPI transfers and stuff...doing all of them every time would
  // make the controls sluggish.

  switch(state) { // Which face-drawing step to handle this time?

   case 0: // Eye position calc
    // Determine direction eyes are pointing (follows joystick, sorta)
    dx = axis[0].value - 512, // Joystick position relative to center
    dy = axis[1].value - 512; // (+/- 512)
    a  = atan2(dy, dx);       // Joystick angle (+/- M_PI)
    // Deal with 'seam crossing' at +/- 180 degrees:
    if(fabs(a - eyeAngle) > M_PI) {
      if(eyeAngle >= 0.0) eyeAngle -= M_PI * 2.0;
      else                eyeAngle += M_PI * 2.0;
    }
    eyeAngle = (eyeAngle * 0.8) + (a * 0.2); // Low-pass filter old/new angle
    break;

   case 1: // Draw eyes in offscreen canvas
    canvas.fillScreen(0); // Clear offscreen canvas
    // Determine position of pupils; center +/- 12 pixels
    dx = (int)(cos(eyeAngle) * 12.0 + 0.5),
    dy = (int)(sin(eyeAngle) * 12.0 + 0.5);
    canvas.drawRGBBitmap(15 + dx, 15 + dy, (uint16_t *)pupil, // Left
      (uint8_t *)pupil_mask, PUPIL_WIDTH, PUPIL_HEIGHT);
    canvas.drawRGBBitmap(75 + dx, 15 + dy, (uint16_t *)pupil, // Right
      (uint8_t *)pupil_mask, PUPIL_WIDTH, PUPIL_HEIGHT);
    // When eyes are blinking, overwrite sections of offscreen canvas
    // with the 'closed' eye image.  They converge at the 3/4 mark
    // (i.e. upper lid is 3/4 of height, lower lid is 1/4).
    if(blinking) {                            // Currently blinking?
      uint32_t t = micros() - blinkStartTime; // Since how long?
      if(t > blinkDuration) {                 // Past end of blink time?
        blinking = false;                     // Turn off blink flag
      } else {                                // Else in mid-blink...
        int a2, amount = 900 * t / blinkDuration; // Relative time, 0-900
        // First third of blink is fast closing, last 2/3 is slower opening
        if(amount > 300) amount = 300 - ((amount - 300) / 2); // 0-300 blinkyness
        if(amount > 256) amount = 256;                        // Clip to 256
        if((a2 = UPPER_LID_SIZE * amount / 256))  // How much upper lid, in pixels?
          canvas.drawRGBBitmap(0, 0, (uint16_t *)eyelids, EYES_WIDTH, a2);
        if((a2 = LOWER_LID_SIZE * amount / 256)) { // How much lower lid, in pixels?
          int a3 = EYES_HEIGHT - a2;               // Y offset in canvas
          canvas.drawRGBBitmap(0, a3, (uint16_t *)&eyelids[a3], EYES_WIDTH, a2);
        }
      }
    } else { // Not blinking
      if(!random(50)) { // Each time here, 1/50 chance of new blink
        blinking       = true;
        blinkDuration  = random(200000, 300000);
        blinkStartTime = micros();
      }
    }
    break;

   case 2: // Process offscreen canvas data
    // TFT endianism requires byte swapping for raw screen write:
    buf = canvas.getBuffer();
    for(i=0; i<EYES_WIDTH * EYES_HEIGHT; i++) {
      buf[i] = (buf[i] << 8) | (buf[i] >> 8);
    }
    break;

   case 3: // Issue data
    // Blit offscreen canvas to TFT using SPI transaction
    display.setAddrWindow(12, 25, 12 + EYES_WIDTH - 1, 25 + EYES_HEIGHT - 1);
    SPI.beginTransaction(SPIset);
    digitalWrite(TFT_DC, HIGH);
    digitalWrite(TFT_CS, LOW);
    SPI.transfer(canvas.getBuffer(), EYES_WIDTH * EYES_HEIGHT * 2);
    digitalWrite(TFT_CS, HIGH);
    SPI.endTransaction();
    break;
  }

  if(++state > 3) state = 0;
}

