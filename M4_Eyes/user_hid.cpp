#if 0 // Change to 1 to enable this code (must enable ONE user*.cpp only!)

#include <Arduino.h>
#include "Adafruit_TinyUSB.h"
#include "globals.h"

#define KEYCODE_TO_SEND  HID_KEY_SPACE

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

  pinMode(13, OUTPUT);
  digitalWrite(13, LOW);

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
  if (buttonState & ARCADA_BUTTONMASK_A) {
    Serial.println("A");
    keycode[0] = KEYCODE_TO_SEND;
    usb_hid.keyboardReport(0, 0, keycode);
  } else {
    usb_hid.keyboardRelease(0);  
  }
}

#endif
