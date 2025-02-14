// SPDX-FileCopyrightText: 2024 John Park for Adafruit Industries
//
// SPDX-License-Identifier: MIT

/*********************************************************************
 Adafruit invests time and resources providing this open source code,
 please support Adafruit and open-source hardware by purchasing
 products from Adafruit!

 MIT license, check LICENSE for more information
 Copyright (c) 2024 John Park for Adafruit Industries
 Copyright (c) 2019 Ha Thach for Adafruit Industries
 All text above, and the splash screen below must be included in
 any redistribution
*********************************************************************/

/* Keyboard HID Keycode Reporter
 * - Device runs on native usb controller (roothub port0)
 *   - esp32-s2 TFT Feather : using MAX3421e controller featherwing
 *   - SPI instance, CS pin, INT pin are correctly configured in usbh_helper.h
 */

// USBHost is defined in usbh_helper.h
#include "usbh_helper.h"
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <Fonts/FreeMono18pt7b.h>
#include <Fonts/FreeMono12pt7b.h>

Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);

void setup() {
  Serial.begin(115200);
  // turn on backlight
  pinMode(TFT_BACKLITE, OUTPUT);
  digitalWrite(TFT_BACKLITE, HIGH);

  // turn on the TFT / I2C power supply
  pinMode(TFT_I2C_POWER, OUTPUT);
  digitalWrite(TFT_I2C_POWER, HIGH);
  delay(10);

  // initialize TFT
  tft.init(135, 240); // Init ST7789 240x135
  tft.setRotation(3);
  tft.fillScreen(ST77XX_BLACK);

  tft.setFont(&FreeMono18pt7b);
  tft.setTextWrap(true);
  tft.fillScreen(ST77XX_BLACK);
  tft.setCursor(0, 20);
  tft.setTextColor(ST77XX_GREEN);
  tft.setTextSize(1);
  tft.println("HIDreporter");

  // init host stack on controller (rhport) 1
  USBHost.begin(1);

//  while ( !Serial ) delay(10);   // wait for native usb
  Serial.println("TinyUSB Dual: HID Device Reporter");
}

void loop() {
  USBHost.task();
  Serial.flush();
}

extern "C" {

// Invoked when device with hid interface is mounted
// Report descriptor is also available for use.
// tuh_hid_parse_report_descriptor() can be used to parse common/simple enough
// descriptor. Note: if report descriptor length > CFG_TUH_ENUMERATION_BUFSIZE,
// it will be skipped therefore report_desc = NULL, desc_len = 0
void tuh_hid_mount_cb(uint8_t dev_addr, uint8_t instance, uint8_t const *desc_report, uint16_t desc_len) {
  (void) desc_report;
  (void) desc_len;
  uint16_t vid, pid;
  tuh_vid_pid_get(dev_addr, &vid, &pid);

  Serial.printf("HID device address = %d, instance = %d is mounted\r\n", dev_addr, instance);
  Serial.printf("VID = %04x, PID = %04x\r\n", vid, pid);
  tft.fillRect(0, 34, 240, 80, ST77XX_BLACK);
  tft.setFont(&FreeMono12pt7b);
  tft.setCursor(0, 50);
  tft.printf("VID=%04x,PID=%04x\r\n", vid, pid);
  if (!tuh_hid_receive_report(dev_addr, instance)) {
    Serial.printf("Error: cannot request to receive report\r\n");
  }
}

// Invoked when device with hid interface is un-mounted
void tuh_hid_umount_cb(uint8_t dev_addr, uint8_t instance) {
  Serial.printf("HID device address = %d, instance = %d is unmounted\r\n", dev_addr, instance);
  tft.fillRect(0, 34, 240, 140, ST77XX_BLACK);
  tft.setFont(&FreeMono12pt7b);
  tft.setTextColor(ST77XX_YELLOW);
  tft.setCursor(0, 50);
  tft.printf("--  unmounted  --");
  tft.setTextColor(ST77XX_GREEN);

}

// Invoked when received report from device via interrupt endpoint
void tuh_hid_report_received_cb(uint8_t dev_addr, uint8_t instance, uint8_t const *report, uint16_t len) {
  Serial.printf("HIDreport : ");
  tft.fillRect(0, 64, 240, 80, ST77XX_BLACK);
  tft.setCursor(0, 88);
   tft.setFont(&FreeMono18pt7b);

  for (uint16_t i = 0; i < len; i++) {
    Serial.printf("0x%02X ", report[i]);
    tft.printf("%02X ", report[i]);
  }

  Serial.println();
  // continue to request to receive report
  if (!tuh_hid_receive_report(dev_addr, instance)) {
    Serial.printf("Error: cannot request to receive report\r\n");
  }
}

} // extern C
