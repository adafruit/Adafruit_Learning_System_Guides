////////////////////////////////////////////////////////////////////////////
// Circuit Playground Capacitive Touch Tones
//
// Send keyboard and mouse events for each touch pad.
// https://www.arduino.cc/en/Reference/MouseKeyboard
//
// Author: Carter Nelson
// MIT License (https://opensource.org/licenses/MIT)

#include <Adafruit_CircuitPlayground.h>
#include <Mouse.h>
#include <Keyboard.h>

#define CAP_THRESHOLD   50
#define DEBOUNCE        250

uint8_t pads[] = {3, 2, 0, 1, 12, 6, 9, 10};
uint8_t numberOfPads = sizeof(pads)/sizeof(uint8_t);

boolean emulatorActive = false;

////////////////////////////////////////////////////////////////////////////
void takeAction(uint8_t pad) {
  Serial.print("PAD "); Serial.println(pad);
  switch (pad) {
    case 3:
      sendKey(KEY_LEFT_ARROW);
      break;
    case 2:
      sendKey(KEY_UP_ARROW);
      break;
    case 0:
      sendKey(KEY_DOWN_ARROW);
      break;
    case 1:
      sendKey(KEY_RIGHT_ARROW);
      break;
    case 12:
      sendKey(' ');
      break;
    case 6:
      sendMouse(MOUSE_LEFT);
      break;
    case 9:
      sendMouse(MOUSE_MIDDLE);
      break;
    case 10:
      sendMouse(MOUSE_RIGHT);
      break;
    default:
      Serial.println("THIS SHOULD NEVER HAPPEN.");
  }
}

////////////////////////////////////////////////////////////////////////////
boolean capButton(uint8_t pad) {
  // Check if capacitive touch exceeds threshold.
  if (CircuitPlayground.readCap(pad) > CAP_THRESHOLD) {
    return true;  
  } else {
    return false;
  }
}

////////////////////////////////////////////////////////////////////////////
void sendKey(char key) {
  Keyboard.press(key);
  Keyboard.releaseAll();
}

////////////////////////////////////////////////////////////////////////////
void sendMouse(char key) {
  Mouse.click(key);
}

////////////////////////////////////////////////////////////////////////////
void setup() {
  // Initialize serial.
  Serial.begin(9600); 
  
  // Initialize Circuit Playground library.
  CircuitPlayground.begin();
}

////////////////////////////////////////////////////////////////////////////
void loop() {
  // Indicate emulator status on red LED.
  CircuitPlayground.redLED(emulatorActive);

  // Check slide switch.
  if (!CircuitPlayground.slideSwitch()) {

    //-----------| EMULATOR OFF |-------------
    if (emulatorActive) {
      Keyboard.end();
      Mouse.end();
      emulatorActive = false;
    }
    
  } else {

    //-----------| EMULATOR ON |-------------
    if (!emulatorActive) {
      Keyboard.begin();
      Mouse.begin();
      emulatorActive = true;
    } 
 
    // Loop over every pad.
    for (int i=0; i<numberOfPads; i++) {
      
      // Check if pad is touched.
      if (capButton(pads[i])) {
        
        // Do something.
        takeAction(pads[i]);
        
        // But not too often.
        delay(DEBOUNCE);
      }
    }
  }
}
