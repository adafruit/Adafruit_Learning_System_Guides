// SPDX-FileCopyrightText: 2019 Limor Fried for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#if 0 // Change to 1 to enable this code (must enable ONE user*.cpp only!)

#include <Arduino.h>
#include "Adafruit_TinyUSB.h"
#include "globals.h"
extern volatile uint16_t voiceLastReading, voiceMin, voiceMax; // In pdmvoice.cpp

#define UP_BUTTON_KEYCODE_TO_SEND    HID_KEY_U
#define A_BUTTON_KEYCODE_TO_SEND     HID_KEY_A
#define DOWN_BUTTON_KEYCODE_TO_SEND  HID_KEY_D
#define SHAKE_KEYCODE_TO_SEND        HID_KEY_SPACE
// Sound reaction REQUIRES '"voice" : true' in config.eye,
// even if not using sound output...we're using it to steal
// access to the mic here.
#define SOUND_KEYCODE_TO_SEND        HID_KEY_SPACE
#define SOUND_THRESHOLD              10000

// HID report descriptor using TinyUSB's template
// Single Report (no ID) descriptor
uint8_t const desc_hid_report[] =
{
  TUD_HID_REPORT_DESC_KEYBOARD(),
};

Adafruit_USBD_HID usb_hid;

void user_setup(void) {
  usb_hid.setPollInterval(20);
  usb_hid.setReportDescriptor(desc_hid_report, sizeof(desc_hid_report));

  usb_hid.begin();

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  arcada.accel.setClick(1, 50);
  
  // wait until device mounted
  while( !USBDevice.mounted() ) delay(1);
}

void user_loop(void) {
  if ( !usb_hid.ready() ) {
    Serial.println("not ready");
    return;
  }

  uint8_t keycode[6] = { 0 };

  uint32_t buttonState = arcada.readButtons();
  if (buttonState & ARCADA_BUTTONMASK_UP) {
    Serial.println("Up");
    keycode[0] = UP_BUTTON_KEYCODE_TO_SEND;
  }
  if (buttonState & ARCADA_BUTTONMASK_A) {
    Serial.println("A");
    keycode[1] = A_BUTTON_KEYCODE_TO_SEND;
  }
  if (buttonState & ARCADA_BUTTONMASK_DOWN) {
    Serial.println("Down");
    keycode[2] = DOWN_BUTTON_KEYCODE_TO_SEND;
  }

  uint8_t shake = arcada.accel.getClick();
  if (shake & 0x30) {
    Serial.print("shake detected (0x"); Serial.print(shake, HEX); Serial.print("): ");
    if (shake & 0x10) Serial.println(" single shake");
    keycode[3] = SHAKE_KEYCODE_TO_SEND;
  }

  uint16_t p2p = voiceMax - voiceMin; // Max peak-to-peak since last reading
  if(p2p) { // usu. non-zero if voice changer enabled
    if(p2p > SOUND_THRESHOLD) {
      Serial.println("Sound");
      keycode[4] = SOUND_KEYCODE_TO_SEND;
    }
  }
  voiceMin = voiceMax = 32768; // Reset p2p range for next pass

  bool anypressed = false;
  for (int k=0; k<sizeof(keycode); k++) {
    if (keycode[k] != 0) {
      anypressed = true;
      break;
    }
  }
  if (anypressed) {
    digitalWrite(LED_BUILTIN, HIGH);
    usb_hid.keyboardReport(0, 0, keycode);
  } else {
    digitalWrite(LED_BUILTIN, LOW);   
    usb_hid.keyboardRelease(0);  
  }
}

#endif
