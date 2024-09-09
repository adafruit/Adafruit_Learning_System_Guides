// SPDX-FileCopyrightText: 2024 Ha Thach for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*********************************************************************
 Adafruit invests time and resources providing this open source code,
 please support Adafruit and open-source hardware by purchasing
 products from Adafruit!

 MIT license, check LICENSE for more information
 Copyright (c) 2019 Ha Thach for Adafruit Industries
 All text above, and the splash screen below must be included in
 any redistribution
*********************************************************************/

#include <Arduino.h>
#include "Adafruit_TinyUSB.h"
#include <Adafruit_NeoPixel.h>

const int neopixel_pin = PA4;
#define LED_COUNT 1
Adafruit_NeoPixel pixels(LED_COUNT, neopixel_pin, NEO_GRB + NEO_KHZ800);

//------------- Input Pins -------------//
// Array of pins and its keycode.
// Notes: these pins can be replaced by PIN_BUTTONn if defined in setup()

uint8_t pins[] = {PB1, PB0, PA1, PA0}; //A0, A1, A2, A3

// HID report descriptor using TinyUSB's template
// Single Report (no ID) descriptor
uint8_t const desc_hid_report[] = {
    TUD_HID_REPORT_DESC_KEYBOARD()
};

// USB HID object. For ESP32 these values cannot be changed after this declaration
// desc report, desc len, protocol, interval, use out endpoint
Adafruit_USBD_HID usb_hid;


// number of pins
uint8_t pincount = sizeof(pins) / sizeof(pins[0]);

// For keycode definition check out https://github.com/hathach/tinyusb/blob/master/src/class/hid/hid.h
uint8_t hidcode[] = {HID_KEY_0, HID_KEY_1, HID_KEY_2, HID_KEY_3};

bool activeState = false;

// the setup function runs once when you press reset or power the board
void setup() {
  pixels.begin();
  // Manual begin() is required on core without built-in support e.g. mbed rp2040
  if (!TinyUSBDevice.isInitialized()) {
    TinyUSBDevice.begin(0);
  }

  // Setup HID
  usb_hid.setBootProtocol(HID_ITF_PROTOCOL_KEYBOARD);
  usb_hid.setPollInterval(2);
  usb_hid.setReportDescriptor(desc_hid_report, sizeof(desc_hid_report));
  usb_hid.setStringDescriptor("TinyUSB Keyboard");

  // Set up output report (on control endpoint) for Capslock indicator
  usb_hid.setReportCallback(NULL, hid_report_callback);

  usb_hid.begin();

  // overwrite input pin with PIN_BUTTONx
#ifdef PIN_BUTTON1
  pins[0] = PIN_BUTTON1;
#endif

#ifdef PIN_BUTTON2
  pins[1] = PIN_BUTTON2;
#endif

#ifdef PIN_BUTTON3
  pins[2] = PIN_BUTTON3;
#endif

#ifdef PIN_BUTTON4
  pins[3] = PIN_BUTTON4;
#endif

  // Set up pin as input
  for (uint8_t i = 0; i < pincount; i++) {
    pinMode(pins[i], activeState ? INPUT_PULLDOWN : INPUT_PULLUP);
  }
}

void process_hid() {
  // used to avoid send multiple consecutive zero report for keyboard
  static bool keyPressedPreviously = false;

  uint8_t count = 0;
  uint8_t keycode[6] = {0};

  // scan normal key and send report
  for (uint8_t i = 0; i < pincount; i++) {
    if (activeState == digitalRead(pins[i])) {
      // if pin is active (low), add its hid code to key report
      keycode[count++] = hidcode[i];

      // 6 is max keycode per report
      if (count == 6) break;
    }
  }

  if (TinyUSBDevice.suspended() && count) {
    // Wake up host if we are in suspend mode
    // and REMOTE_WAKEUP feature is enabled by host
    TinyUSBDevice.remoteWakeup();
  }

  // skip if hid is not ready e.g still transferring previous report
  if (!usb_hid.ready()) return;

  if (count) {
    // Send report if there is key pressed
    uint8_t const report_id = 0;
    uint8_t const modifier = 0;

    keyPressedPreviously = true;
    usb_hid.keyboardReport(report_id, modifier, keycode);
  } else {
    // Send All-zero report to indicate there is no keys pressed
    // Most of the time, it is, though we don't need to send zero report
    // every loop(), only a key is pressed in previous loop()
    if (keyPressedPreviously) {
      keyPressedPreviously = false;
      usb_hid.keyboardRelease(0);
    }
  }
}

void loop() {
  #ifdef TINYUSB_NEED_POLLING_TASK
  // Manual call tud_task since it isn't called by Core's background
  TinyUSBDevice.task();
  #endif

  // not enumerated()/mounted() yet: nothing to do
  if (!TinyUSBDevice.mounted()) {
    return;
  }

  // poll gpio once each 2 ms
  static uint32_t ms = 0;
  if (millis() - ms > 2) {
    ms = millis();
    process_hid();
  }
}

void setLED(bool state) {
  pixels.setPixelColor(0, pixels.Color(0, state ? 150 : 0, 0));
  pixels.show();
}

// Output report callback for LED indicator such as Caplocks
void hid_report_callback(uint8_t report_id, hid_report_type_t report_type, uint8_t const* buffer, uint16_t bufsize) {
  (void) report_id;
  (void) bufsize;

  // LED indicator is output report with only 1 byte length
  if (report_type != HID_REPORT_TYPE_OUTPUT) return;

  // The LED bit map is as follows: (also defined by KEYBOARD_LED_* )
  // Kana (4) | Compose (3) | ScrollLock (2) | CapsLock (1) | Numlock (0)
  uint8_t ledIndicator = buffer[0];

  // turn on LED if capslock is set
  setLED(ledIndicator & KEYBOARD_LED_CAPSLOCK);
}
