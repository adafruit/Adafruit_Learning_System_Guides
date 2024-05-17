// SPDX-FileCopyrightText: 2024 ladyada for Adafruit Industries
//
// SPDX-License-Identifier: MIT

#include "SdFat.h"
#include "Adafruit_TestBed.h"
#include "Adafruit_TinyUSB.h"

// HID report descriptor using TinyUSB's template
// Single Report (no ID) descriptor
uint8_t const desc_hid_report[] = {
  TUD_HID_REPORT_DESC_KEYBOARD()
};

Adafruit_USBD_HID usb_hid;

#define TIP_KEYCODE  HID_KEY_SPACE
#define RING_KEYCODE  HID_KEY_ENTER


extern Adafruit_TestBed TB;
uint8_t allpins[] = {PIN_TIP, PIN_RING1, PIN_RING2, PIN_SLEEVE};


bool selftest = false;
bool cableinserted = false;
bool last_cablestate = false;
uint32_t last_i2cscan = 0;
 
void setup() {
  Serial.begin(115200);
  //while (!Serial) { yield(); delay(10); }     // wait till serial port is opened

  usb_hid.setBootProtocol(HID_ITF_PROTOCOL_KEYBOARD);
  usb_hid.setPollInterval(2);
  usb_hid.setReportDescriptor(desc_hid_report, sizeof(desc_hid_report));
  usb_hid.setStringDescriptor("TinyUSB Keyboard");
  usb_hid.begin();
  

  TB.neopixelPin = PIN_NEOPIXEL;
  TB.neopixelNum = NUM_NEOPIXEL;
  TB.begin();
  
  for (int d=0; d < 100; d++) {
    if (Serial.available() && (Serial.read() == 0xAF)) {
      selftest = true;
    }
    delay(1);
  }
}

void loop() {
  delay(10); // sample every 10 ms

  if (Serial.available() && (Serial.read() == 0xAF)) {
    selftest = true;
  }
  
  if (selftest) {
    Serial.println("TRRS Trinkey self-tester!");

    // check tied pins
    if (! TB.testpins(PIN_RING1, PIN_RING2, allpins, sizeof(allpins))) return;
    if (! TB.testpins(PIN_SLEEVE, PIN_TIP, allpins, sizeof(allpins))) return;

    pinMode(PIN_RING1, OUTPUT);
    digitalWrite(PIN_RING1, LOW);
    pinMode(PIN_RING1_SWITCH, INPUT_PULLUP);
    delay(10);
    if (!digitalRead(PIN_RING1_SWITCH)) {
      Serial.println("Ring1 switch not floating");
      return;
    }
    pinMode(PIN_TIP, OUTPUT);
    digitalWrite(PIN_TIP, LOW);
    pinMode(PIN_TIP_SWITCH, INPUT_PULLUP);
    delay(10);
    if (!digitalRead(PIN_TIP_SWITCH)) {
      Serial.println("Tip switch not floating");
      return;
    }

    Serial.println("**TEST OK!**");

    delay(100);
    return;
  }

  uint8_t keycode[6] = { 0 };
  uint8_t count = 0;
  // used to avoid send multiple consecutive zero report for keyboard
  static bool keyPressedPreviously = false;

  pinMode(PIN_TIP, OUTPUT);
  digitalWrite(PIN_TIP, LOW);
  pinMode(PIN_TIP_SWITCH, INPUT_PULLUP);
  cableinserted = digitalRead(PIN_TIP_SWITCH);

  if (!cableinserted) {
    TB.setColor(RED);
  }
  
  if (cableinserted && !last_cablestate) {
    TB.setColor(GREEN);
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

    // do an I2C scan while we're here, if we have pullups on SDA/SCL
    if ((millis() - last_i2cscan) > 1000) {
      TB.disableI2C();
      if (TB.testPullup(SDA) && TB.testPullup(SCL)) {
        Wire.begin();
        TB.printI2CBusScan();
      } else {
        Serial.println("No pullups on SDA/SCL");
      }
      last_i2cscan = millis();
    }
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
