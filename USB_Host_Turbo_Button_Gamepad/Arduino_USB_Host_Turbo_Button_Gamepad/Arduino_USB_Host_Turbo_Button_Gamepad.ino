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

bool is_combo_detected(const uint8_t* combo, size_t combo_size, const uint8_t* report) {
  for (size_t i = 0; i < combo_size; i++) {
    uint8_t button = combo[i];
    
    // Determine which byte the button is in and then check if it is pressed
    if (button & BUTTON_A || button & BUTTON_B || button & BUTTON_X || button & BUTTON_Y) {
      if ((report[BYTE_DPAD_BUTTONS] & button) != button) {
        return false;  // Button is not pressed
      }
    } else if (button & BUTTON_LEFT_PADDLE || button & BUTTON_RIGHT_PADDLE || 
               button & BUTTON_LEFT_TRIGGER || button & BUTTON_RIGHT_TRIGGER || 
               button & BUTTON_BACK || button & BUTTON_START) {
      if ((report[BYTE_MISC_BUTTONS] & button) != button) {
        return false;  // Button is not pressed
      }
    }
  }
  return true;  // All buttons in the combo are pressed
}

void tuh_hid_report_received_cb(uint8_t dev_addr, uint8_t instance, uint8_t const* report, uint16_t len) {

  // Manage the combo state and print messages
  if ((is_combo_detected(combo_report, combo_size, report)) && !combo_active) {
    combo_active = true;
    Serial.println("combo!");
  } else if ((is_combo_detected(combo_report, combo_size, report)) && combo_active) {
    combo_active = false;
    Serial.println("combo released!");
  }
    // Handle analog stick inputs
    gp.x = (report[BYTE_LEFT_STICK_X] != LEFT_STICK_X_NEUTRAL) ? map(report[BYTE_LEFT_STICK_X], 0, 255, -127, 127) : 0;
    gp.y = (report[BYTE_LEFT_STICK_Y] != LEFT_STICK_Y_NEUTRAL) ? map(report[BYTE_LEFT_STICK_Y], 0, 255, -127, 127) : 0;
    gp.z = (report[BYTE_RIGHT_STICK_X] != RIGHT_STICK_X_NEUTRAL) ? map(report[BYTE_RIGHT_STICK_X], 0, 255, -127, 127) : 0;
    gp.rz = (report[BYTE_RIGHT_STICK_Y] != RIGHT_STICK_Y_NEUTRAL) ? map(report[BYTE_RIGHT_STICK_Y], 0, 255, -127, 127) : 0;

    // Debug print for report data
    /*Serial.print("Report data: ");
    for (int i = 0; i < len; i++) {
      Serial.print(report[i], HEX);
      Serial.print(" ");
    }
    Serial.println();*/

    uint8_t dpad_value = report[BYTE_DPAD_BUTTONS] & DPAD_MASK;

    // Handle D-pad direction
    if ((report[BYTE_DPAD_BUTTONS] & DPAD_NEUTRAL) == 0) {
      switch (dpad_value) {
        case DPAD_UP: gp.hat = 1; Serial.println("up"); break;
        case DPAD_UP_RIGHT: gp.hat = 2; Serial.println("up/right"); break;
        case DPAD_RIGHT: gp.hat = 3; Serial.println("right"); break;
        case DPAD_DOWN_RIGHT: gp.hat = 4; Serial.println("down/right"); break;
        case DPAD_DOWN: gp.hat = 5; Serial.println("down"); break;
        case DPAD_DOWN_LEFT: gp.hat = 6; Serial.println("down/left"); break;
        case DPAD_LEFT: gp.hat = 7; Serial.println("left"); break;
        case DPAD_UP_LEFT: gp.hat = 8; Serial.println("up/left"); break;
        }
    } else {
      gp.hat = 0;
    }
    uint16_t buttons = gp.buttons;
    if ((report[BYTE_DPAD_BUTTONS] & BUTTON_X) == BUTTON_X) {
      buttons |= GAMEPAD_BUTTON_X;
      Serial.println("x");
    } else {
      buttons &= ~GAMEPAD_BUTTON_X;
    }
    if ((report[BYTE_DPAD_BUTTONS] & BUTTON_A) == BUTTON_A) {
      buttons |= GAMEPAD_BUTTON_A;
      Serial.println("a");
    } else {
      buttons &= ~GAMEPAD_BUTTON_A;
    }
    if ((report[BYTE_DPAD_BUTTONS] & BUTTON_B) == BUTTON_B) {
      buttons |= GAMEPAD_BUTTON_B;
      Serial.println("b");
    } else {
      buttons &= ~GAMEPAD_BUTTON_B;
    }
    if ((report[BYTE_DPAD_BUTTONS] & BUTTON_Y) == BUTTON_Y) {
      buttons |= GAMEPAD_BUTTON_Y;
      Serial.println("y");
    } else {
      buttons &= ~GAMEPAD_BUTTON_Y;
    }
    gp.buttons = buttons;

    if ((report[BYTE_MISC_BUTTONS] & BUTTON_LEFT_PADDLE) == BUTTON_LEFT_PADDLE) {
      buttons |= GAMEPAD_BUTTON_TL;
      Serial.println("left paddle");
    } else {
      buttons &= ~GAMEPAD_BUTTON_TL;
    }
    if ((report[BYTE_MISC_BUTTONS] & BUTTON_RIGHT_PADDLE) == BUTTON_RIGHT_PADDLE) {
      buttons |= GAMEPAD_BUTTON_TR;
      Serial.println("right paddle");
    } else {
      buttons &= ~GAMEPAD_BUTTON_TR;
    }
    if ((report[BYTE_MISC_BUTTONS] & BUTTON_LEFT_TRIGGER) == BUTTON_LEFT_TRIGGER) {
      buttons |= GAMEPAD_BUTTON_TL2;
      Serial.println("left trigger");
    } else {
      buttons &= ~GAMEPAD_BUTTON_TL2;
    }
    if ((report[BYTE_MISC_BUTTONS] & BUTTON_RIGHT_TRIGGER) == BUTTON_RIGHT_TRIGGER) {
      buttons |= GAMEPAD_BUTTON_TR2;
      Serial.println("right trigger");
    } else {
      buttons &= ~GAMEPAD_BUTTON_TR2;
    }
    if ((report[BYTE_MISC_BUTTONS] & BUTTON_BACK) == BUTTON_BACK) {
      buttons |= GAMEPAD_BUTTON_SELECT;
      Serial.println("back");
    } else {
      buttons &= ~GAMEPAD_BUTTON_SELECT;
    }
    if ((report[BYTE_MISC_BUTTONS] & BUTTON_START) == BUTTON_START) {
      buttons |= GAMEPAD_BUTTON_START;
      Serial.println("start");
    } else {
      buttons &= ~GAMEPAD_BUTTON_START;
    }
    // Set the final buttons state
    gp.buttons = buttons;

  // Debug print for gp contents
  /*Serial.print("gp.x: "); Serial.println(gp.x);
  Serial.print("gp.y: "); Serial.println(gp.y);
  Serial.print("gp.z: "); Serial.println(gp.z);
  Serial.print("gp.rz: "); Serial.println(gp.rz);
  Serial.print("gp.hat: "); Serial.println(gp.hat);
  Serial.print("gp.buttons: "); Serial.println(gp.buttons, HEX);*/

  while (!usb_hid.ready()) {
    yield();
  }
  usb_hid.sendReport(0, &gp, sizeof(gp));

  // Continue to receive the next report
  if (!tuh_hid_receive_report(dev_addr, instance)) {
    Serial.println("Error: cannot request to receive report");
  }
}
