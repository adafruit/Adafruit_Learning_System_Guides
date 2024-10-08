// SPDX-FileCopyrightText: 2024 Liz Clark for Adafruit Industries
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

/* This example demonstrates use of both device and host, where
 * - Device runs on native USB controller (roothub port0)
 * - Host depends on MCU:
 *   - rp2040: bit-banging 2 GPIOs with Pico-PIO-USB library (roothub port1)
 *
 * Requirements:
 * - For rp2040:
 *   - Pico-PIO-USB library
 *   - 2 consecutive GPIOs: D+ is defined by PIN_USB_HOST_DP, D- = D+ +1
 *   - Provide VBus (5v) and GND for peripheral
 *   - CPU Speed must be either 120 or 240 MHz. Selected via "Menu -> CPU Speed"
 */

// USBHost is defined in usbh_helper.h
#include "usbh_helper.h"
#include "tusb.h"
#include "Adafruit_TinyUSB.h"
#include "gamepad_reports.h"

// HID report descriptor using TinyUSB's template
// Single Report (no ID) descriptor
uint8_t const desc_hid_report[] = {
    TUD_HID_REPORT_DESC_GAMEPAD()
};

// USB HID object
Adafruit_USBD_HID usb_hid;

// Report payload defined in src/class/hid/hid.h
// - For Gamepad Button Bit Mask see  hid_gamepad_button_bm_t
// - For Gamepad Hat    Bit Mask see  hid_gamepad_hat_t
hid_gamepad_report_t gp;

bool combo_active = false;

void setup() {
  if (!TinyUSBDevice.isInitialized()) {
    TinyUSBDevice.begin(0);
  }
  Serial.begin(115200);
  // Setup HID
  usb_hid.setPollInterval(2);
  usb_hid.setReportDescriptor(desc_hid_report, sizeof(desc_hid_report));
  usb_hid.begin();

  // If already enumerated, additional class driverr begin() e.g msc, hid, midi won't take effect until re-enumeration
  if (TinyUSBDevice.mounted()) {
    TinyUSBDevice.detach();
    delay(10);
    TinyUSBDevice.attach();
  }
}

#if defined(ARDUINO_ARCH_RP2040)
//--------------------------------------------------------------------+
// For RP2040 use both core0 for device stack, core1 for host stack
//--------------------------------------------------------------------//

//------------- Core0 -------------//
void loop() {
}

//------------- Core1 -------------//
void setup1() {
  // configure pio-usb: defined in usbh_helper.h
  rp2040_configure_pio_usb();

  // run host stack on controller (rhport) 1
  // Note: For rp2040 pico-pio-usb, calling USBHost.begin() on core1 will have most of the
  // host bit-banging processing works done in core1 to free up core0 for other works
  USBHost.begin(1);
}

void loop1() {
  USBHost.task();
  Serial.flush();
  if (combo_active) {
    turbo_button();
  }
}
#endif

//--------------------------------------------------------------------+
// HID Host Callback Functions
//--------------------------------------------------------------------+

void tuh_hid_mount_cb(uint8_t dev_addr, uint8_t instance, uint8_t const* desc_report, uint16_t desc_len)
{
  Serial.printf("HID device mounted (address %d, instance %d)\n", dev_addr, instance);

  // Start receiving HID reports
  if (!tuh_hid_receive_report(dev_addr, instance))
  {
    Serial.printf("Error: cannot request to receive report\n");
  }
}

void tuh_hid_umount_cb(uint8_t dev_addr, uint8_t instance)
{
  Serial.printf("HID device unmounted (address %d, instance %d)\n", dev_addr, instance);
}

void turbo_button() {
  if (combo_active) {
    while (!usb_hid.ready()) {
        yield();
      }
    Serial.println("A");
    gp.buttons = GAMEPAD_BUTTON_A;
    usb_hid.sendReport(0, &gp, sizeof(gp));
    Serial.println("off");
    delay(2);
    gp.buttons = 0;
    usb_hid.sendReport(0, &gp, sizeof(gp));
    delay(2);
  }
}

void tuh_hid_report_received_cb(uint8_t dev_addr, uint8_t instance, uint8_t const* report, uint16_t len) {
  // Known report when the combo is pressed
  //uint8_t combo_report[] = { 0x80, 0x7F, 0x80, 0x7F, 0x28, 0x03, 0x00, 0xFF };
  // Check if the incoming report matches the combo report
  bool combo_detected = ((report[4] == combo_report[4]) && (report[5] == combo_report[5]));// len == sizeof(combo_report)) && (memcmp(report, combo_report, sizeof(combo_report)) == 0);

  // Manage the combo state and print messages
  if (combo_detected && !combo_active) {
    combo_active = true;
    Serial.println("combo!");
  } else if (combo_detected && combo_active) {
    combo_active = false;
    Serial.println("combo released!");
  }
  if (!(combo_active)) {
    if (!(report[BYTE_LEFT_STICK_X] == LEFT_STICK_X_NEUTRAL)) {
      int16_t leftStickX = report[BYTE_LEFT_STICK_X];
      Serial.print("left stick X: ");
      Serial.println(leftStickX);
      int16_t new_leftStickX = map(leftStickX, 0, 255, -127, 127);
      gp.x = new_leftStickX;
    } else {
      gp.x = 0;
    }
    if (!(report[BYTE_LEFT_STICK_Y] == LEFT_STICK_Y_NEUTRAL)) {
      int16_t leftStickY = report[BYTE_LEFT_STICK_Y];
      Serial.print("left stick Y: ");
      Serial.println(leftStickY);
      int16_t new_leftStickY = map(leftStickY, 0, 255, -127, 127);
      gp.y = new_leftStickY;
    } else {
      gp.y = 0;
    }
    if (!(report[BYTE_RIGHT_STICK_X] == RIGHT_STICK_X_NEUTRAL)) {
      int8_t rightStickX = report[BYTE_RIGHT_STICK_X];
      Serial.print("right stick X: ");
      Serial.println(rightStickX);
      int16_t new_rightStickX = map(rightStickX, 0, 255, 127, -127);
      gp.z = new_rightStickX;
    } else {
      gp.z = 0;
    }
    if (!(report[BYTE_RIGHT_STICK_Y] == RIGHT_STICK_Y_NEUTRAL)) {
      int8_t rightStickY = report[BYTE_RIGHT_STICK_Y];
      Serial.print("right stick Y: ");
      Serial.println(rightStickY);
      int16_t new_rightStickY = map(rightStickY, 0, 255, -127, 127);
      gp.rz = new_rightStickY;
    } else {
      gp.rz = 0;
    }
    if (!(report[BYTE_DPAD_BUTTONS] == DPAD_NEUTRAL)) {
      // D-Pad is active
      uint8_t buttonsSelect = report[BYTE_DPAD_BUTTONS];
      switch (buttonsSelect) {
        case BUTTON_X:
          Serial.println("x");
          gp.buttons = GAMEPAD_BUTTON_X;
          break;
        case BUTTON_A:
          Serial.println("a");
          gp.buttons = GAMEPAD_BUTTON_A;
          break;
        case BUTTON_B:
          Serial.println("b");
          gp.buttons = GAMEPAD_BUTTON_B;
          break;
        case BUTTON_Y:
          Serial.println("y");
          gp.buttons = GAMEPAD_BUTTON_Y;
          break;
      }
    } else {
      gp.hat = 0;
      gp.buttons = 0;
    }
    if (!(report[BYTE_DPAD_BUTTONS] == DPAD_NEUTRAL)) {
      // D-Pad is active
      uint8_t dpadDirection = report[BYTE_DPAD_BUTTONS];
      switch (dpadDirection) {
        case DPAD_UP:
          Serial.println("up");
          gp.hat = 1; // GAMEPAD_HAT_UP;
          break;
        case DPAD_UP_RIGHT:
          Serial.println("up/right");
          gp.hat = 2;
          break;
        case DPAD_RIGHT:
          Serial.println("right");
          gp.hat = 3;
          break;
        case DPAD_DOWN_RIGHT:
          Serial.println("down/right");
          gp.hat = 4;
          break;
        case DPAD_DOWN:
          Serial.println("down");
          gp.hat = 5;
          break;
        case DPAD_DOWN_LEFT:
          Serial.println("down/left");
          gp.hat = 6;
          break;
        case DPAD_LEFT:
          Serial.println("left");
          gp.hat = 7;
          break;
        case DPAD_UP_LEFT:
          Serial.println("up/left");
          gp.hat = 8;
          break;
      }
    } else {
      gp.hat = 0;
    }
    if (!(report[BYTE_MISC_BUTTONS] == MISC_NEUTRAL)) {
      // misc are active
      uint8_t miscDirection = report[BYTE_MISC_BUTTONS];
      switch (miscDirection) {
        case BUTTON_LEFT_PADDLE:
          Serial.println("left paddle");
          gp.buttons = GAMEPAD_BUTTON_TL;
          break;
        case BUTTON_RIGHT_PADDLE:
          Serial.println("right paddle");
          gp.buttons = GAMEPAD_BUTTON_TR;
          break;
        case BUTTON_LEFT_TRIGGER:
          Serial.println("left trigger");
          gp.buttons = GAMEPAD_BUTTON_TL2;
          break;
        case BUTTON_RIGHT_TRIGGER:
          Serial.println("right trigger");
          gp.buttons = GAMEPAD_BUTTON_TR2;
          break;
        case BUTTON_BACK:
          Serial.println("back");
          gp.buttons = GAMEPAD_BUTTON_SELECT;
          break;
        case BUTTON_START:
          Serial.println("start");
          gp.buttons = GAMEPAD_BUTTON_START;
          break;  
        }
      }
  } else {
    gp.buttons = GAMEPAD_BUTTON_A;
  }
  while (!usb_hid.ready()) {
      yield();
    }
    usb_hid.sendReport(0, &gp, sizeof(gp));
  // Continue to receive the next report
  if (!tuh_hid_receive_report(dev_addr, instance)) {
    Serial.println("Error: cannot request to receive report");
  }
}
