// SPDX-FileCopyrightText: 2025 Tim Cocks for Adafruit Industries
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

/* This example demonstrates use of usb host with a SNES-like game controller
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

bool printed_blank = false;

void setup() {
  Serial.begin(115200);

  // configure pio-usb: defined in usbh_helper.h
  rp2040_configure_pio_usb();

  // run host stack on controller (rhport) 1
  USBHost.begin(1);
  delay(3000);
  Serial.print("USB D+ Pin:");
  Serial.println(PIN_USB_HOST_DP);
  Serial.print("USB 5V Pin:");
  Serial.println(PIN_5V_EN);
}

void loop() {
  USBHost.task();
  Serial.flush();

}

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

void tuh_hid_report_received_cb(uint8_t dev_addr, uint8_t instance, uint8_t const* report, uint16_t len) {

    if (report[BYTE_DPAD_LEFT_RIGHT] != DPAD_NEUTRAL ||
        report[BYTE_DPAD_UP_DOWN] != DPAD_NEUTRAL ||
        report[BYTE_ABXY_BUTTONS] != BUTTON_NEUTRAL ||
        report[BYTE_OTHER_BUTTONS] != BUTTON_MISC_NEUTRAL){

      printed_blank = false;

      //debug print report data
      // Serial.print("Report data: ");
      // for (int i = 0; i < len; i++) {
      //   Serial.print(report[i], HEX);
      //   Serial.print(" ");
      // }
      // Serial.println();

      if (report[BYTE_DPAD_LEFT_RIGHT] == DPAD_LEFT){
        Serial.print("Left ");
      }else  if (report[BYTE_DPAD_LEFT_RIGHT] == DPAD_RIGHT){
        Serial.print("Right ");
      }

      if (report[BYTE_DPAD_UP_DOWN] == DPAD_UP){
        Serial.print("Up ");
      }else  if (report[BYTE_DPAD_UP_DOWN] == DPAD_DOWN){
        Serial.print("Down ");
      }

      if ((report[BYTE_ABXY_BUTTONS] & BUTTON_A) == BUTTON_A){
        Serial.print("A ");
      }
      if ((report[BYTE_ABXY_BUTTONS] & BUTTON_B) == BUTTON_B){
        Serial.print("B ");
      }
      if ((report[BYTE_ABXY_BUTTONS] & BUTTON_X) == BUTTON_X){
        Serial.print("X ");
      }
      if ((report[BYTE_ABXY_BUTTONS] & BUTTON_Y) == BUTTON_Y){
        Serial.print("Y ");
      }

      if ((report[BYTE_OTHER_BUTTONS] & BUTTON_LEFT_SHOULDER) == BUTTON_LEFT_SHOULDER){
        Serial.print("Left Shoulder ");
      }
      if ((report[BYTE_OTHER_BUTTONS] & BUTTON_RIGHT_SHOULDER) == BUTTON_RIGHT_SHOULDER){
        Serial.print("Right Shoulder ");
      }
      if ((report[BYTE_OTHER_BUTTONS] & BUTTON_START) == BUTTON_START){
        Serial.print("Start ");
      }
      if ((report[BYTE_OTHER_BUTTONS] & BUTTON_SELECT) == BUTTON_SELECT){
        Serial.print("Select ");
      }
      Serial.println();
    } else {
      if (! printed_blank){
        Serial.println("NEUTRAL");
        printed_blank = true;
      }
    }

  // Continue to receive the next report
  if (!tuh_hid_receive_report(dev_addr, instance)) {
    Serial.println("Error: cannot request to receive report");
  }
}
