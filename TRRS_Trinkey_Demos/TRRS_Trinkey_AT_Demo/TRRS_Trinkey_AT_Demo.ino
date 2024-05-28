// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include "Adafruit_TinyUSB.h"

// HID report descriptor using TinyUSB's template
// Single Report (no ID) descriptor
uint8_t const desc_hid_report[] = {
  TUD_HID_REPORT_DESC_KEYBOARD()
};

Adafruit_USBD_HID usb_hid;

#define TIP_KEYCODE  HID_KEY_A
#define RING_KEYCODE  HID_KEY_B

uint8_t allpins[] = {PIN_TIP, PIN_RING1, PIN_RING2, PIN_SLEEVE};

bool cableinserted = false;
bool last_cablestate = false;
uint32_t last_i2cscan = 0;
 
void setup() {
  Serial.begin(115200);
  //while (!Serial) { yield(); delay(10); }     // wait till serial port is opened

  usb_hid.setBootProtocol(HID_ITF_PROTOCOL_KEYBOARD);
  usb_hid.setPollInterval(2);
  usb_hid.setReportDescriptor(desc_hid_report, sizeof(desc_hid_report));
  usb_hid.setStringDescriptor("TRRS Trinkey Keyboard");
  usb_hid.begin();

}

void loop() {
  delay(10); // sample every 10 ms

  uint8_t keycode[6] = { 0 };
  uint8_t count = 0;
  // used to avoid send multiple consecutive zero report for keyboard
  static bool keyPressedPreviously = false;

  pinMode(PIN_TIP, OUTPUT);
  digitalWrite(PIN_TIP, LOW);
  pinMode(PIN_TIP_SWITCH, INPUT_PULLUP);
  cableinserted = digitalRead(PIN_TIP_SWITCH);
  
  if (cableinserted && !last_cablestate) {
    Serial.println("inserted!");
    delay(250);  // give em a quarter second to plug completely
  }
  
  last_cablestate = cableinserted;

  // Wake up host if we are in suspend mode
  if ( TinyUSBDevice.suspended() && count ) {
    TinyUSBDevice.remoteWakeup();
  }
  // skip if hid is not ready e.g still transferring previous report
  if ( !usb_hid.ready() ) return;
  
  if (!cableinserted) {
    keyPressedPreviously = false;
    usb_hid.keyboardRelease(0);
    return;
  }
  // make two inputs
  pinMode(PIN_TIP, INPUT_PULLUP);
  pinMode(PIN_RING1, INPUT_PULLUP);

  // make two 'ground' pins
  pinMode(PIN_SLEEVE, OUTPUT);
  digitalWrite(PIN_SLEEVE, LOW);
  pinMode(PIN_RING2, OUTPUT);
  digitalWrite(PIN_RING2, LOW);

  delay(1);
  
  if (!digitalRead(PIN_TIP)) {
    keycode[0] = TIP_KEYCODE;
    count++;
  }
  if (!digitalRead(PIN_RING1)) {
    keycode[1] = RING_KEYCODE;
    count++;
  }  

  if (count) {   // Send report if there is key pressed
    uint8_t const report_id = 0;
    uint8_t const modifier = 0;

    keyPressedPreviously = true;
    usb_hid.keyboardReport(report_id, modifier, keycode);
  }
  else
  {
    // Send All-zero report to indicate there is no keys pressed
    // Most of the time, it is, though we don't need to send zero report
    // every loop(), only a key is pressed in previous loop()
    if ( keyPressedPreviously )
    {
      keyPressedPreviously = false;
      usb_hid.keyboardRelease(0);
    }
  }
}
